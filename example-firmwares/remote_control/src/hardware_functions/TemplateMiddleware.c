#include "TemplateMiddleware.h"

#include "Spi.h"
#include "hardware/gpio.h"
#include "pico/time.h"

#define CNTL_DO_TEST (1u << 0)
#define CNTL_SEL_DUT (1u << 1)

// CSN muss zwischen zwei Frames kurz high sein, damit SPI_SLAVE_WCLK den Frame
// abschließt und SPI_MIDDLEWARE die Antwort für den nächsten Frame bereitstellt.
#define INTER_FRAME_DELAY_US 1

struct TemplateMiddleware
{
  Spi *spi;
  uint8_t slaveHandle;
  uint8_t busyPin;
};

TemplateMiddleware *TemplateMiddleware_new(Spi *spi, uint8_t slaveHandle, uint8_t busyPin)
{
  static TemplateMiddleware middleware;
  middleware.spi = spi;
  middleware.slaveHandle = slaveHandle;
  middleware.busyPin = busyPin;
  return &middleware;
}

void TemplateMiddleware_init(TemplateMiddleware *self)
{
  Spi_init(self->spi);
  Spi_setupSlave(self->spi, self->slaveHandle);
  gpio_init(self->busyPin);
  gpio_set_dir(self->busyPin, GPIO_IN);
}

void TemplateMiddleware_deinit(TemplateMiddleware *self)
{
  Spi_deinit(self->spi);
}

static uint32_t frameHead(TemplateMiddlewareCmd cmd, uint8_t adr)
{
  return ((uint32_t)cmd << 6) | (adr & TEMPLATE_MIDDLEWARE_ADR_MASK);
}

static bool frameMatches(uint32_t rx, TemplateMiddlewareCmd cmd, uint8_t adr)
{
  return (rx >> 16) == frameHead(cmd, adr);
}

uint32_t TemplateMiddleware_transferFrame(TemplateMiddleware *self, TemplateMiddlewareCmd cmd, uint8_t adr, uint16_t data)
{
  const uint8_t tx[3] = {
      (uint8_t)frameHead(cmd, adr),
      (uint8_t)(data >> 8),
      (uint8_t)(data & 0xFF)};
  uint8_t rx[3] = {0};

  Spi_select(self->spi, self->slaveHandle);
  Spi_read_write(self->spi, tx, rx, sizeof(tx));
  Spi_deselect(self->spi, self->slaveHandle);
  busy_wait_us(INTER_FRAME_DELAY_US);

  return ((uint32_t)rx[0] << 16) | ((uint32_t)rx[1] << 8) | rx[2];
}

void TemplateMiddleware_selectDut(TemplateMiddleware *self, uint8_t dut)
{
  TemplateMiddleware_transferFrame(self, TEMPLATE_MIDDLEWARE_CMD_CNTL, CNTL_SEL_DUT, (uint16_t)dut << 1);
}

void TemplateMiddleware_writeWord(TemplateMiddleware *self, uint8_t adr, uint16_t data)
{
  TemplateMiddleware_transferFrame(self, TEMPLATE_MIDDLEWARE_CMD_WR, adr, data);
}

bool TemplateMiddleware_readWord(TemplateMiddleware *self, uint8_t adr, uint16_t *data)
{
  // 1. Frame setzt DUT_ADR, 2. Frame übernimmt DUT_DOUT dieser Adresse,
  // 3. Frame schiebt die Antwort des 2. Frames heraus.
  TemplateMiddleware_transferFrame(self, TEMPLATE_MIDDLEWARE_CMD_RD, adr, 0);
  TemplateMiddleware_transferFrame(self, TEMPLATE_MIDDLEWARE_CMD_RD, adr, 0);
  uint32_t rx = TemplateMiddleware_transferFrame(self, TEMPLATE_MIDDLEWARE_CMD_RD, adr, 0);

  *data = (uint16_t)rx;
  return frameMatches(rx, TEMPLATE_MIDDLEWARE_CMD_RD, adr);
}

bool TemplateMiddleware_readHeader(TemplateMiddleware *self, uint32_t *header)
{
  // Header (32 Bit) liegt in zwei 16-Bit-Teilen: ADR 0 = [15:0], ADR 1 = [31:16]
  TemplateMiddleware_transferFrame(self, TEMPLATE_MIDDLEWARE_CMD_HEAD, 0, 0);
  uint32_t low = TemplateMiddleware_transferFrame(self, TEMPLATE_MIDDLEWARE_CMD_HEAD, 1, 0);
  uint32_t high = TemplateMiddleware_transferFrame(self, TEMPLATE_MIDDLEWARE_CMD_HEAD, 1, 0);

  *header = ((high & 0xFFFF) << 16) | (low & 0xFFFF);
  return frameMatches(low, TEMPLATE_MIDDLEWARE_CMD_HEAD, 0) && frameMatches(high, TEMPLATE_MIDDLEWARE_CMD_HEAD, 1);
}

void TemplateMiddleware_startTest(TemplateMiddleware *self)
{
  TemplateMiddleware_transferFrame(self, TEMPLATE_MIDDLEWARE_CMD_CNTL, CNTL_DO_TEST, 0);
}

bool TemplateMiddleware_isBusy(TemplateMiddleware *self)
{
  return gpio_get(self->busyPin) == 1;
}

bool TemplateMiddleware_waitWhileBusy(TemplateMiddleware *self, uint32_t timeout_us)
{
  absolute_time_t deadline = make_timeout_time_us(timeout_us);
  while (TemplateMiddleware_isBusy(self))
  {
    if (time_reached(deadline))
    {
      return false;
    }
  }
  return true;
}
