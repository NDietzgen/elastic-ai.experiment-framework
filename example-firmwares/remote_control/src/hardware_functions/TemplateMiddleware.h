#ifndef TEMPLATE_MIDDLEWARE_H
#define TEMPLATE_MIDDLEWARE_H
/*
 * ---------------------------------------------------------------------------
 * Protokoll von SPI_MIDDLEWARE aus dem Verilog-Template (env5/verilog_template)
 * ---------------------------------------------------------------------------
 * Die Bedeutung der Bits legt die Logik im FPGA-Bitstream fest, nicht der Pico.
 * Dieses Modul funktioniert daher nur mit einem Bitstream, der SPI_MIDDLEWARE
 * enthält. Für Bitstreams mit der Standard-Middleware (Befehlsbyte
 * 0x80/0x40 + 16-Bit-Adresse + beliebig viele Bytes, SPI-Mode 1) gibt es
 * Middleware.h. Beide Formate sind nicht kompatibel.
 *
 * Frame (24 Bit, MSB first, SPI-Mode 0):
 *   CMD[23:22] | ADR[21:16] | DATA[15:0]
 *
 *   CMD 0 CNTL: ADR-Bits steuern  [0] DO_TEST, [1] SEL_DUT (DATA[N:1] = DUT),
 *               [2] LED = DATA[0], [3] LED toggeln
 *   CMD 1 WR:   DATA an Adresse ADR des gewählten DUT schreiben
 *   CMD 2 RD:   Adresse ADR des gewählten DUT lesen
 *   CMD 3 HEAD: 16-Bit-Teil ADR des DUT-Headers lesen
 *
 * Die Antwort {CMD, ADR, DATA} auf einen Frame kommt erst im nächsten Frame
 * zurück. Die Lesefunktionen schicken deshalb Folge-Frames und prüfen, ob
 * CMD und ADR der Antwort zur Anfrage passen.
 *
 * Vorher TemplateMiddleware_init aufrufen, danach TemplateMiddleware_deinit.
 * TemplateMiddleware_isBusy entspricht FPGA_BUSY = !RDY des gewählten DUT.
 */

#include <stdbool.h>
#include <stdint.h>

#include "Spi.h"

#define TEMPLATE_MIDDLEWARE_ADR_MASK 0x3F
#define TEMPLATE_MIDDLEWARE_MAX_WORDS 64 // 6-Bit-Adressraum

typedef enum
{
  TEMPLATE_MIDDLEWARE_CMD_CNTL = 0,
  TEMPLATE_MIDDLEWARE_CMD_WR = 1,
  TEMPLATE_MIDDLEWARE_CMD_RD = 2,
  TEMPLATE_MIDDLEWARE_CMD_HEAD = 3,
} TemplateMiddlewareCmd;

typedef struct TemplateMiddleware TemplateMiddleware;

/* spi muss auf SPI-Mode 0 konfiguriert sein (siehe Config_getTemplateSpi). */
TemplateMiddleware *TemplateMiddleware_new(Spi *spi, uint8_t slaveHandle, uint8_t busyPin);

void TemplateMiddleware_init(TemplateMiddleware *self);
void TemplateMiddleware_deinit(TemplateMiddleware *self);

/* Schickt einen Frame und gibt die Antwort auf den VORHERIGEN Frame zurück. */
uint32_t TemplateMiddleware_transferFrame(TemplateMiddleware *self, TemplateMiddlewareCmd cmd, uint8_t adr, uint16_t data);

void TemplateMiddleware_selectDut(TemplateMiddleware *self, uint8_t dut);
void TemplateMiddleware_writeWord(TemplateMiddleware *self, uint8_t adr, uint16_t data);
bool TemplateMiddleware_readWord(TemplateMiddleware *self, uint8_t adr, uint16_t *data);
bool TemplateMiddleware_readHeader(TemplateMiddleware *self, uint32_t *header);
void TemplateMiddleware_startTest(TemplateMiddleware *self);
bool TemplateMiddleware_isBusy(TemplateMiddleware *self);
bool TemplateMiddleware_waitWhileBusy(TemplateMiddleware *self, uint32_t timeout_us);

#endif // TEMPLATE_MIDDLEWARE_H
