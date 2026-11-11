//////////////////////////////////////////////////////////////////////////////////
// Module Name:     DUT_WRAPPER_USER
// Target Devices:  FPGA (ENV5)
// Description:     Vorlage zum Anbinden eines eigenen Moduls (DUT_TYPE = "USER").
//                  Eingetragen: Reset-Test (reset_test.v).
//                  Abschnitte und verfügbare Signale: README.md, Fall B
// Dependencies:    reset_test.v
//
// State: 	        Not tested!
//
// [FIX] nie ändern · [ÄNDERN] für jedes DUT anpassen · [OPTIONAL] siehe Abschnitt
//////////////////////////////////////////////////////////////////////////////////


// =============================================================================
// Portliste + localparam                                               [FIX]
// Identisch mit den Wrappern in core/skeleton.v, zusätzlich LEDS.
// =============================================================================
module DUT_WRAPPER_USER#(
    parameter integer BITWIDTH_IN   = 16,
    parameter integer BITWIDTH_SYS  = 16,
    parameter integer BITWIDTH_HEAD = 26,
    parameter integer BITWIDTH_ADR  = 6,
    parameter integer NUM_LEDS      = 4
)(
    input wire CLK_SYS,
    input wire RSTN,
    input wire EN,
    input wire TRGG_START_CALC,
    input wire RnW,
    input wire [BITWIDTH_ADR-'d1:0] ADR,
    input wire [BITWIDTH_SYS-'d1:0] DATA_IN,
    output wire [BITWIDTH_SYS-'d1:0] DATA_OUT,
    output wire [BITWIDTH_HEAD-'d1:0] DATA_HEAD,
    output wire RDY,
    output wire DATA_VALID,
    output wire [NUM_LEDS-'d1:0] LEDS
);

localparam integer BITWIDTH_OFFSET = BITWIDTH_SYS - BITWIDTH_IN;


// =============================================================================
// (1) Header                                                        [ÄNDERN]
// =============================================================================
// Wird von der Software gelesen (read-skeleton-id), um das DUT zu erkennen:
//   {TYPE_ID[3:0], SIZE_INPUT[5:0], SIZE_OUTPUT[5:0], BITWIDTH_IN[4:0], BITWIDTH_OUT[4:0]}
//   TYPE_ID:     1 Echo, 2 ROM, 3 RAM, 4 Math, 5 Filter, 6 USER, 7 DNN
//   SIZE_INPUT:  Anzahl Eingangswerte
//   SIZE_OUTPUT: Anzahl Ausgangswerte
assign DATA_HEAD = {4'd6, 6'd1, 6'd1, BITWIDTH_IN[4:0], BITWIDTH_IN[4:0]};


// =============================================================================
// (2) Datenanpassung                                                   [FIX]
// =============================================================================
// Die Nutzdaten liegen linksbündig (MSB) auf dem 16-Bit-Bus.
// Nur ändern, wenn Ausgangs- und Eingangsbitbreite des DUT verschieden sind.
wire [BITWIDTH_IN-'d1:0] dut_in, dut_out;
assign dut_in   = DATA_IN[(BITWIDTH_SYS-'d1)-:BITWIDTH_IN];
assign DATA_OUT = {dut_out, {BITWIDTH_OFFSET{1'd0}}};


// =============================================================================
// (3) Statussignale                                                    [FIX]
// =============================================================================
// dut_done wird in (4) vom DUT getrieben (oder in (5) vom Loopback).
wire dut_done;
assign RDY        = dut_done;
assign DATA_VALID = 1'd0;


// =============================================================================
// (4) DUT-Instanz                                                   [ÄNDERN]
// =============================================================================

RESET_TEST#(
    .NUM_LEDS(NUM_LEDS)
) DUT(
    .CLK(CLK_SYS),
    .RSTN(RSTN),
    .LEDS(LEDS)
);



// =============================================================================
// (5) Loopback                                                    [OPTIONAL]
// =============================================================================
// Gibt die Eingangsdaten unverändert zurück (DATA_OUT = DATA_IN).
//   DUT ohne Datenpfad (z. B. Reset-Test)   --> stehen lassen
//   DUT treibt dut_out und dut_done          --> diese zwei Zeilen LÖSCHEN
assign dut_out  = dut_in;
assign dut_done = 1'd1;


// =============================================================================
// (6) LEDs                                                        [OPTIONAL]
// =============================================================================
//   DUT treibt LEDS (z. B. Reset-Test)       --> auskommentiert lassen
//   DUT nutzt keine LEDs                     --> Zeile EINKOMMENTIEREN
// assign LEDS = 'd0;


endmodule
