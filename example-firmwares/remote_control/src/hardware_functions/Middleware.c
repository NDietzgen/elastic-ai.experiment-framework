#include "Middleware.h"

#include <stddef.h>

#include "Spi.h"
#include "hardware/gpio.h"
#include "pico/time.h"

enum FpgaPowerStatus
{
  FPGA_OFF,
  FPGA_IDLE,
  FPGA_BUSY,
};

enum FpgaMiddlewareState
{
  FPGA_MIDDLEWARE_USERLOGIC_ENABLED,
  FPGA_MIDDLEWARE_INITIALIZED,
  FPGA_MIDDLEWARE_UNINITIALIZED
};

static const FpgaMiddlewareAddresses default_addresses = {
    .leds = 0x0003,
    .user_logic_reset = 0x0004,
    .multi_boot = 0x0005,
    .user_logic_offset = 0x0100,
    .fpga_busy_pin = 15};

typedef struct FpgaMiddleware
{
  Spi *spi;
  SpiConfig *spiConfig;
  uint8_t powerStatus;
  uint8_t state;
  uint8_t slaveHandle;
  const FpgaMiddlewareAddresses *addresses;
} FpgaMiddleware;

static void write(FpgaMiddleware *self, const uint8_t *data, uint16_t startAddress, uint16_t length)
{
  Spi_select(self->spi, self->slaveHandle);
  uint8_t cmd[3] = {0x80, startAddress >> 8, startAddress};
  Spi_write(self->spi, cmd, sizeof(cmd));
  Spi_write(self->spi, data, length);
  Spi_deselect(self->spi, self->slaveHandle);
}

static void read(FpgaMiddleware *self, uint8_t *data, uint16_t startAddress, uint16_t length)
{
  Spi_select(self->spi, self->slaveHandle);
  uint8_t cmd[3] = {0x40, (startAddress >> 8) & 0xFF, startAddress & 0xFF};
  Spi_write(self->spi, cmd, sizeof(cmd));
  Spi_read(self->spi, data, length);
  Spi_deselect(self->spi, self->slaveHandle);
}

FpgaMiddleware *FpgaMiddleware_new(Spi *spi, uint8_t slaveHandle)
{
  static FpgaMiddleware middleware = {
      .spiConfig = NULL,
      .powerStatus = FPGA_OFF,
      .state = FPGA_MIDDLEWARE_UNINITIALIZED,
      .addresses = &default_addresses};
  middleware.slaveHandle = slaveHandle;
  middleware.spi = spi;
  Spi_setupSlave(spi, slaveHandle);
  return &middleware;
}

static void setBusyPinToInput(const FpgaMiddleware *self)
{
  gpio_set_dir(self->addresses->fpga_busy_pin, false);
}

void FpgaMiddleware_init(FpgaMiddleware *self)
{
  Spi_init(self->spi);
  setBusyPinToInput(self);
  Spi_setupSlave(self->spi, self->slaveHandle);
  self->state = FPGA_MIDDLEWARE_INITIALIZED;
}

void FpgaMiddleware_deinit(FpgaMiddleware *self)
{
  if (self->state == FPGA_MIDDLEWARE_USERLOGIC_ENABLED)
  {
    FpgaMiddleware_disableUserLogic(self);
  }
  Spi_deinit(self->spi);
  self->state = FPGA_MIDDLEWARE_UNINITIALIZED;
}

void FpgaMiddleware_enableUserLogic(FpgaMiddleware *self)
{
  if (self->state == FPGA_MIDDLEWARE_UNINITIALIZED)
  {
    FpgaMiddleware_init(self);
  }
  if (self->state == FPGA_MIDDLEWARE_INITIALIZED)
  {
    uint8_t enable = 0x00;
    write(self, &enable, self->addresses->user_logic_reset, sizeof(enable));
    self->state = FPGA_MIDDLEWARE_USERLOGIC_ENABLED;
  }
}

void FpgaMiddleware_disableUserLogic(FpgaMiddleware *self)
{
  if (self->state == FPGA_MIDDLEWARE_UNINITIALIZED)
  {
    FpgaMiddleware_init(self);
  }
  if (self->state == FPGA_MIDDLEWARE_USERLOGIC_ENABLED)
  {
    uint8_t disable = 0x01;
    write(self, &disable, self->addresses->user_logic_reset, sizeof(disable));
    self->state = FPGA_MIDDLEWARE_INITIALIZED;
  }
}

void FpgaMiddleware_read(FpgaMiddleware *self, uint8_t *data, uint16_t startAddress, uint16_t length)
{
  read(self, data, startAddress + self->addresses->user_logic_offset, length);
}

void FpgaMiddleware_write(FpgaMiddleware *self, const uint8_t *data, uint16_t startAddress, uint16_t length)
{
  write(self, data, startAddress + self->addresses->user_logic_offset, length);
}

void FpgaMiddleware_setAddresses(FpgaMiddleware *self, const FpgaMiddlewareAddresses *addresses);

bool FpgaMiddleware_fpgaIsBusy(FpgaMiddleware *self)
{
  return gpio_get(self->addresses->fpga_busy_pin) == 1;
}

bool FpgaMiddleware_isIdle(FpgaMiddleware *self)
{
  return gpio_get(self->addresses->fpga_busy_pin) == 0;
}

// ---------------------------------------------------------------------------
// Protokoll von SPI_MIDDLEWARE aus dem Verilog-Template (siehe Middleware.h)
// ---------------------------------------------------------------------------
#define CNTL_DO_TEST (1u << 0)
#define CNTL_SEL_DUT (1u << 1)

// CSN muss zwischen zwei Frames kurz high sein, damit SPI_SLAVE_WCLK den Frame
// abschließt und SPI_MIDDLEWARE die Antwort für den nächsten Frame bereitstellt.
#define INTER_FRAME_DELAY_US 1

static uint32_t frameHead(FpgaMiddlewareCmd cmd, uint8_t adr)
{
  return ((uint32_t)cmd << 6) | (adr & FPGA_MIDDLEWARE_ADR_MASK);
}

static bool frameMatches(uint32_t rx, FpgaMiddlewareCmd cmd, uint8_t adr)
{
  return (rx >> 16) == frameHead(cmd, adr);
}

uint32_t FpgaMiddleware_transferFrame(FpgaMiddleware *self, FpgaMiddlewareCmd cmd, uint8_t adr, uint16_t data)
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

void FpgaMiddleware_selectDut(FpgaMiddleware *self, uint8_t dut)
{
  FpgaMiddleware_transferFrame(self, FPGA_MIDDLEWARE_CMD_CNTL, CNTL_SEL_DUT, (uint16_t)dut << 1);
}

void FpgaMiddleware_writeWord(FpgaMiddleware *self, uint8_t adr, uint16_t data)
{
  FpgaMiddleware_transferFrame(self, FPGA_MIDDLEWARE_CMD_WR, adr, data);
}

bool FpgaMiddleware_readWord(FpgaMiddleware *self, uint8_t adr, uint16_t *data)
{
  // 1. Frame setzt DUT_ADR, 2. Frame übernimmt DUT_DOUT dieser Adresse,
  // 3. Frame schiebt die Antwort des 2. Frames heraus.
  FpgaMiddleware_transferFrame(self, FPGA_MIDDLEWARE_CMD_RD, adr, 0);
  FpgaMiddleware_transferFrame(self, FPGA_MIDDLEWARE_CMD_RD, adr, 0);
  uint32_t rx = FpgaMiddleware_transferFrame(self, FPGA_MIDDLEWARE_CMD_RD, adr, 0);

  *data = (uint16_t)rx;
  return frameMatches(rx, FPGA_MIDDLEWARE_CMD_RD, adr);
}

bool FpgaMiddleware_readHeader(FpgaMiddleware *self, uint32_t *header)
{
  // Header (32 Bit) liegt in zwei 16-Bit-Teilen: ADR 0 = [15:0], ADR 1 = [31:16]
  FpgaMiddleware_transferFrame(self, FPGA_MIDDLEWARE_CMD_HEAD, 0, 0);
  uint32_t low = FpgaMiddleware_transferFrame(self, FPGA_MIDDLEWARE_CMD_HEAD, 1, 0);
  uint32_t high = FpgaMiddleware_transferFrame(self, FPGA_MIDDLEWARE_CMD_HEAD, 1, 0);

  *header = ((high & 0xFFFF) << 16) | (low & 0xFFFF);
  return frameMatches(low, FPGA_MIDDLEWARE_CMD_HEAD, 0) && frameMatches(high, FPGA_MIDDLEWARE_CMD_HEAD, 1);
}

void FpgaMiddleware_startTest(FpgaMiddleware *self)
{
  FpgaMiddleware_transferFrame(self, FPGA_MIDDLEWARE_CMD_CNTL, CNTL_DO_TEST, 0);
}

bool FpgaMiddleware_waitWhileBusy(FpgaMiddleware *self, uint32_t timeout_us)
{
  absolute_time_t deadline = make_timeout_time_us(timeout_us);
  while (FpgaMiddleware_fpgaIsBusy(self))
  {
    if (time_reached(deadline))
    {
      return false;
    }
  }
  return true;
}
