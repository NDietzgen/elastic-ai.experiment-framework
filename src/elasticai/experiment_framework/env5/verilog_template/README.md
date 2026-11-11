# ENV5 Verilog-Template

Testumgebung, um ein Modul (DUT, *Device Under Test*) auf dem ENV5-FPGA zu
testen. Die Software spricht das FPGA über SPI an und erkennt das DUT an
seinem Header.

Die Testumgebung (`core/`) ist für alle DUTs gleich und wird nicht geändert.
Jedes DUT hat einen eigenen **DUT-Ordner** mit seiner Konfiguration
(`dut_config.vh`) und seinen Quellen. Beim Build werden Kern und DUT-Ordner
automatisch zu einem Projekt zusammengesetzt.

## Ordnerstruktur

```
verilog_template/
├── core/                     nicht ändern
│   ├── top_module.v                         Top-Modul: Reset-Sync, SPI, Testumgebung
│   ├── skeleton.v                           SKELETON + Wrapper der DUT-Klassen
│   ├── test_dut.v                           TEST_ENVIRONMENT, Multiplexer über SEL
│   ├── skeleton_echo.v                      Echo-Selbsttest (SEL = 1)
│   ├── spi_slave_wclk.v                     SPI-Slave (24-Bit-Frames)
│   ├── spi_middleware.v                     SPI-Protokoll -> Steuersignale
│   ├── bram_single.v / .mem                 BRAM für die Klasse RAM
│   └── env5_constraints.xdc                 Pins: Takt, SPI, LEDs, Reset, BUSY
└── user/                     Vorlage für einen DUT-Ordner
    ├── dut_config.vh                        Auswahl des DUT
    └── dut_wrapper_user.v                   Anbindung eigener Module ("USER")
```

Ein DUT-Ordner liegt irgendwo, zum Beispiel unter `tests/vivado/duts/<name>/`:

```
<name>/
├── dut_config.vh             Pflicht       Klasse, Bitbreite, Modulname
├── <dein Modul>.v            Pflicht       DUT, Untermodule, .mem-Dateien
├── dut_wrapper_user.v        nur "USER"    Anbindung des eigenen Moduls
├── test_build_<name>.py                    Build-Test (siehe Build)
└── top_module.v              optional      ersetzt core/top_module.v (Sonderfall)
```

### Zusammensetzen beim Build

`assemble_project()` aus `elasticai.experiment_framework.env5.verilog_project`
kopiert Kern und DUT-Ordner in die Struktur, die der Kern erwartet:

```
<build>/core/   Kopie von verilog_template/core/
<build>/user/   Kopie des DUT-Ordners
```

Die Includes in `core/` (`../user/dut_config.vh`) funktionieren deshalb
unabhängig davon, wo der DUT-Ordner im Repo liegt. Alle `.v`-, `.sv`-, `.vh`-
und `.mem`-Dateien werden eingesammelt, auch aus Unterordnern. `.xdc`-Dateien
im DUT-Ordner sind nicht erlaubt, die Constraints kommen immer aus `core/`.

Eine eigene `top_module.v` im DUT-Ordner ersetzt die aus `core/`. Sie liegt
dann neben der Config und bindet sie mit `` `include "dut_config.vh" `` ein.
Das ist nur für Sonderfälle gedacht, zum Beispiel für zusätzliche Pins.

## Aufbau

```
TOP_MODULE
├── Reset-Synchronisierung   RSTN_MCU (Pin M13, asynchron) -> RSTN
├── SPI_SLAVE_WCLK           SPI-Leitungen <-> 24-Bit-Frames
├── SPI_MIDDLEWARE           Frames -> SEL, ADR, RnW, DIN, START
└── TEST_ENVIRONMENT         Multiplexer über SEL
    ├── SEL = 0              Dummy (DOUT = 0x0123)
    ├── SEL = 1              SKELETON_ECHO
    └── SEL = 2              SKELETON
                             └── DUT_WRAPPER_<DUT_TYPE>   (per generate gewählt)
                                 └── dein DUT
```

`SKELETON` wählt anhand von `DUT_TYPE` genau einen Wrapper aus. Nur dieser
wird gebaut. Die Module der anderen Wrapper müssen deshalb nicht im Projekt
liegen.

## Neues Modul testen

1. **DUT-Ordner anlegen**, zum Beispiel `tests/vivado/duts/<name>/`, und
   `user/dut_config.vh` hineinkopieren.
2. **Quellen in den DUT-Ordner kopieren:** das Modul, seine Untermodule und
   `.mem`-Dateien. In `$readmemh` steht nur der Dateiname, ohne Pfad.
3. **Prüfen, ob das Modul zu einer DUT-Klasse passt** (siehe unten).
   - Passt es, folgt Fall A.
   - Passt es nicht, folgt Fall B.

### Fall A: DUT-Klasse (nur `dut_config.vh` anpassen)

Jeder Wrapper in `core/skeleton.v` steht für eine **Klasse** von DUTs. Ein
Modul passt, wenn es die Parameter und Ports der Klasse hat. Der
**Modulname ist frei** und wird mit `DUT_MODULE` eingetragen:

```verilog
`define DUT_TYPE        "FILT"
`define DUT_BITWIDTH_IN 12
`define DUT_MODULE      Filter_FIR_8   // auskommentiert = Standardname
```

| `DUT_TYPE` | Klasse            | Standardname   | Parameter                   | Ports                                                                         |
|------------|-------------------|----------------|-----------------------------|-------------------------------------------------------------------------------|
| `"ROM"`    | LUT-Generator     | `LUT_WVF_GEN0` | –                           | `CLK_SYS, nRST, EN, TRGG_CNT_FLAG, LUT_VALUE, LUT_END`                        |
| `"RAM"`    | Speicher          | `BRAM_SINGLE`  | `BITWIDTH, RAMWIDTH, DATAFILE` | `CLK_RAM, EN, WE, ADR, DIN, DOUT`                                          |
| `"MULT"`   | Multiplizierer    | `MULT_SIGNED`  | `BITWIDTH`                  | `A, B, Q`                                                                     |
| `"MAC"`    | Multiply-Accumulate | `MAC`        | 3 positionell: Bitbreite, Anzahl Parameter, Anzahl Multiplizierer | `CLK_SYS, RSTN, EN, DO_CALC, IN_BIAS, IN_WEIGHTS, IN_DATA, OUT_DATA, DATA_RDY` |
| `"FILT"`   | Filter            | `Filter_IIR_1` | 1 positionell: Bitbreite    | `CLK, RSTN, EN, START_FLAG, DATA_IN, DATA_OUT, DATA_RDY, DATA_VALID`          |
| `"DNN"`    | elasticAI.creator | `skeleton`     | –                           | `clock, clk_hadamard, reset, busy, wake_up, rd, wr, data_in, address_in, data_out, debug` |

Die genaue Instanz mit allen Bitbreiten steht im jeweiligen Wrapper
`DUT_WRAPPER_<TYP>` in `core/skeleton.v`. `BRAM_SINGLE` liegt schon in
`core/`, für `"RAM"` musst du nichts kopieren.

### Fall B: eigenes Modul (`"USER"`)

Für Module, die zu keiner Klasse passen, zum Beispiel weil sie LEDs
ansteuern oder eine eigene Schnittstelle haben.

1. In `dut_config.vh` `DUT_TYPE` auf `"USER"` setzen und `DUT_BITWIDTH_IN`
   eintragen. `DUT_MODULE` wird hier nicht gebraucht.
2. `user/dut_wrapper_user.v` in den DUT-Ordner kopieren und dort das eigene
   Modul anbinden. Die Abschnitte sind markiert:

| Abschnitt              | Markierung   | Inhalt                                                        |
|------------------------|--------------|---------------------------------------------------------------|
| Portliste + localparam | `[FIX]`      | identisch mit den Wrappern in `core/`, zusätzlich `LEDS`      |
| (1) Header             | `[ÄNDERN]`   | TYPE_ID, Anzahl Ein-/Ausgänge, Bitbreiten                     |
| (2) Datenanpassung     | `[FIX]`      | 16-Bit-Bus <-> `dut_in` / `dut_out`                           |
| (3) Statussignale      | `[FIX]`      | `RDY = dut_done`, `DATA_VALID = 0`                            |
| (4) DUT-Instanz        | `[ÄNDERN]`   | eigenes Modul instanziieren                                   |
| (5) Loopback           | `[OPTIONAL]` | löschen, wenn das Modul `dut_out` und `dut_done` selbst treibt |
| (6) LEDs               | `[OPTIONAL]` | löschen, wenn das Modul die LEDs selbst ansteuert             |

Ein vollständiges Beispiel ist der Reset-Test in `tests/vivado/duts/reset_test/`.

Signale, die in (4) zur Verfügung stehen:

| Signal            | Bedeutung                                                    |
|-------------------|--------------------------------------------------------------|
| `CLK_SYS`         | Systemtakt (100 MHz)                                         |
| `RSTN`            | Reset, active-low (vom MCU-Pin, synchronisiert)              |
| `EN`              | 1 = DUT per SPI ausgewählt (SEL = 2)                          |
| `TRGG_START_CALC` | Startimpuls per SPI (DO_TEST)                                |
| `RnW`, `ADR`      | Lesen/Schreiben und Adresse per SPI                          |
| `dut_in`          | Eingangsdaten, bereits auf `DUT_BITWIDTH_IN` zugeschnitten  |
| `dut_out`         | Ausgangsdaten (vom DUT treiben)                              |
| `dut_done`        | 1 = DUT fertig/bereit (vom DUT treiben)                      |
| `LEDS`            | die 4 LEDs auf dem Board (vom DUT treiben oder (6))         |

## Testen auf dem Board

| Wert            | Bedeutung                                                     |
|-----------------|---------------------------------------------------------------|
| SPI `SEL = 1`   | Echo-Selbsttest, prüft die SPI-Strecke (immer vorhanden)      |
| SPI `SEL = 2`   | das ausgewählte DUT                                           |
| `LEDS`          | bei `"USER"` vom DUT, sonst `LEDS[0]` per SPI (`REG_DUT_CNTL`) |
| `FPGA_BUSY`     | an, solange das per SEL ausgewählte DUT nicht bereit ist     |

## Referenz

### SPI-Protokoll

Ein Frame ist 24 Bit breit: `{CMD[1:0], ADR[5:0], DATA[15:0]}`.

| CMD | Name           | Wirkung                                                                 |
|-----|----------------|-------------------------------------------------------------------------|
| 0   | `REG_DUT_CNTL` | ADR-Bits: [0] DO_TEST, [1] SEL = DATA[2:1], [2] LED = DATA[0], [3] LED umschalten |
| 1   | `REG_DUT_WR`   | `DUT_ADR = ADR`, `DUT_DIN = DATA`, `RnW = 0`                            |
| 2   | `REG_DUT_RD`   | `RnW = 1`, Antwort enthält `DUT_DOUT`                                   |
| 3   | `REG_HEAD_RD`  | Header lesen: ADR 0 = unteres, ADR 1 = oberes 16-Bit-Wort               |

Die Antwort auf einen Frame kommt mit dem **nächsten** Frame zurück.

### Header

32 Bit, gelesen von der Software (`read-skeleton-id`):

```
{NUM_DUT[5:0], TYPE_ID[3:0], SIZE_INPUT[5:0], SIZE_OUTPUT[5:0], BITWIDTH_IN[4:0], BITWIDTH_OUT[4:0]}
```

`NUM_DUT` ergänzt `TEST_ENVIRONMENT`, die restlichen 26 Bit liefert der Wrapper.

| TYPE_ID | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| DUT | aus | Echo | ROM | RAM | MULT/MAC | Filter | USER | DNN |

### Daten auf dem Bus

Die Nutzdaten liegen **linksbündig (MSB)** auf dem 16-Bit-Bus:
`dut_in = DATA_IN[15 -: DUT_BITWIDTH_IN]`, `DATA_OUT = {dut_out, 0…}`.

### Build

**Lokal (Vivado unter Windows, aus WSL):** über das Paket
`elasticai.experiment_framework.vivado` (`BuildConfig`, `build_bitstream`,
`read_metrics`). Jeder DUT-Ordner unter `tests/vivado/duts/` hat einen eigenen
Test `test_build_<name>.py`, der genau diesen Ordner baut. Bitstream und Reports landen in
`tests/vivado/artifacts/env5_<name>/`.

```bash
pytest tests/vivado                       # alle DUTs
pytest tests/vivado/duts/reset_test       # ein DUT
```

Für ein neues DUT kopierst du den Test aus einem bestehenden DUT-Ordner mit
und benennst ihn in `test_build_<name>.py` um. Er baut automatisch den Ordner,
in dem er liegt.

**Remote (`vivado_synthesis.py`):** zuerst zusammensetzen, dann synthetisieren:

```python
from elasticai.experiment_framework.env5.verilog_project import TOP, assemble_project

src = assemble_project("tests/vivado/duts/reset_test", "build/reset_test")
# VivadoSynthesis mit top=TOP, bzw. CLI: --top TOP_MODULE build/reset_test
```

Weitere Hinweise:
- Ein unbekannter `DUT_TYPE` bricht die Synthese mit dem Fehler
  `ERROR_UNKNOWN_DUT_TYPE_CHECK_USER_DUT_CONFIG` ab.
