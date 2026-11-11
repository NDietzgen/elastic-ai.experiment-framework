//////////////////////////////////////////////////////////////////////////////////
// Module Name:     RESET_TEST
// Target Devices:  FPGA (ENV5)
// Description:     LED-Test für den Reset-Pin der MCU (RSTN_MCU, Pin M13):
//                    Normalbetrieb (RSTN = 1): Lauflicht  0001 -> 0010 -> 0100 -> 1000
//                    Reset aktiv   (RSTN = 0): Wechselblinken  0101 <-> 1010
//                  Funktioniert ohne SPI-Kommunikation.
// Dependencies:    None
//
// State: 	        Not tested!
// Parameters:      LED_CNT_WIDTH --> Breite des Zählers, bestimmt die Geschwindigkeit
//                                    (26 bei 100 MHz: ca. 168 ms pro LED-Schritt)
//////////////////////////////////////////////////////////////////////////////////
module RESET_TEST#(
    parameter integer NUM_LEDS      = 4,
    parameter integer LED_CNT_WIDTH = 26
)(
    input wire CLK,
    input wire RSTN,                        // synchronisierter Reset aus TOP_MODULE
    output reg [NUM_LEDS-1:0] LEDS
);

    // Zähler hat bewusst KEINEN Reset, damit er auch im Reset weiterläuft
    // und das Wechselblinken sichtbar ist.
    reg [LED_CNT_WIDTH-1:0] led_cnt = {LED_CNT_WIDTH{1'b0}};
    always @(posedge CLK)
        led_cnt <= led_cnt + 1'b1;

    wire [1:0] led_pos   = led_cnt[LED_CNT_WIDTH-1 -: 2];
    wire       led_blink = led_cnt[LED_CNT_WIDTH-2];

    always @(*) begin
        if (!RSTN)
            LEDS = led_blink ? 4'b1010 : 4'b0101;
        else
            LEDS = 4'b0001 << led_pos;
    end

endmodule
