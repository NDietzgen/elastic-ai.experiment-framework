//////////////////////////////////////////////////////////////////////////////////
// Company:         University of Duisburg-Essen, Intelligent Embedded Systems Lab
// Engineer:        AE
//
// Create Date:     19.04.2023 21:15:14
// Copied on: 	    §{date_copy_created}
// Module Name:     UART FIFO Module for building complete communication protocols
// Target Devices:  FPGA
// Tool Versions:   1v0
// Dependencies:    None
//
// State: 	        Tested!
// Improvements:    None
// Comments:        None
// Parameters:      BITWIDTH_DATA   --> Number of bits for data handling of the procotol
//                  BITWIDTH_ADR    --> Number of bits for address width
//                  BITWIDTH_CMDS   --> Number of bits for commando
//                  BITWIDTH        --> BITWIDTH FOR DATA TRANSMISSION
//                  BITWIDTH_HEAD   --> Number of bits for processing DUT skeleton header information
//////////////////////////////////////////////////////////////////////////////////
// Example of the implemented data structure
// ------------------------------- DATA FRAME -----------------------------------------------------------------------
// # ---- CMD (2 bits) ---- # ---- ADR (BITWIDTH_ADR) ----                  # ---- DATA (BITWIDTH_DATA) ----        #
// # 0: REG_DUT_CNTL        # xx | TOGGLE_LED | CH_LED | SEL_DUT | DO_TEST  # xx | SEL_DUT[N:0] | LED               #
// # 1: REG_DUT_WR          # ---- ADR ----                                 # ---- DATA ----                        #
// # 2: REG_DUT_RD          # ---- ADR ----                                 # xxxxxx                                #
// # 3: REG_HEAD_RD         # ---- ADR ----                                 # xxxxxx                                #
// ------------------------------- DATA FRAME -----------------------------------------------------------------------

module SPI_MIDDLEWARE#(
    parameter integer NUM_DUT = 5,
    parameter integer BITWIDTH = 24,
    parameter integer BITWIDTH_CMDS = 2,
    parameter integer BITWIDTH_ADR = 6,
    parameter integer BITWIDTH_DATA = 16,
    parameter integer BITWIDTH_HEAD = 32
)(
    // Global signals
    input wire                              CLK_SYS,
    input wire                              RSTN,
    // Control lines between middlware and FIFO
    input wire                              FIFO_RDY,
    input wire [BITWIDTH-'d1:0]  FIFO_DIN,
    output reg [BITWIDTH-'d1:0]  FIFO_DOUT,
    // Output signals
    output reg                              LED_CONTROL,
    output wire                             DUT_DO_TEST,
    output reg [$clog2(NUM_DUT):0]          DUT_SEL,
    output reg [BITWIDTH_DATA-'d1:0]        DUT_DIN,
    input wire [BITWIDTH_DATA-'d1:0]        DUT_DOUT,
    output reg [BITWIDTH_ADR-'d1:0]         DUT_ADR,
    output reg                              DUT_RnW,
    input wire [BITWIDTH_HEAD-'d1:0]        DUT_HEADER
);
    localparam REG_DUT_CNTL = 2'd0, REG_DUT_WR = 2'd1, REG_DUT_RD = 2'd2, REG_HEADER = 2'd3;

    reg [1:0] shift_drdy;
    reg [1:0] shift_test;
    reg trigger_test;
    wire do_update_data;
    wire [BITWIDTH_CMDS-'d1:0] sel_cmds;
    wire [BITWIDTH_ADR-'d1:0] sel_adr;
    wire [BITWIDTH_DATA-'d1:0] sel_data;

    // --- Slicing header information
    localparam NUM_HEAD_TRANSMISSION = 2**($clog2(BITWIDTH_HEAD) - $clog2(BITWIDTH_DATA));
    wire [BITWIDTH_DATA-'d1:0] data_head_send [NUM_HEAD_TRANSMISSION-'d1:0];
    genvar i1;
    for(i1 = 'd0; i1 < NUM_HEAD_TRANSMISSION; i1 = i1 + 'd1) begin
        assign data_head_send[i1] = DUT_HEADER[i1* BITWIDTH_DATA+:BITWIDTH_DATA];
    end

    // --- Data handler for Test module
    assign do_update_data = shift_drdy[0] && !shift_drdy[1];
    assign DUT_DO_TEST = shift_test[0] ^ shift_test[1];
    assign sel_cmds = (FIFO_RDY) ? FIFO_DIN[(BITWIDTH_DATA+BITWIDTH_ADR)+:BITWIDTH_CMDS] : 'd0;
    assign sel_adr = (FIFO_RDY) ? FIFO_DIN[BITWIDTH_DATA+:BITWIDTH_ADR] : 'd0;
    assign sel_data = (FIFO_RDY) ? FIFO_DIN[0+:BITWIDTH_DATA] : 'd0;

    // --- Implemented data protocol
    always@(posedge CLK_SYS) begin
        if(!RSTN) begin
            shift_drdy <= 2'd3;
            shift_test <= 2'd0;
            FIFO_DOUT <= 'd0;

            LED_CONTROL <= 1'd1;
            trigger_test <= 1'd0;
            DUT_SEL <= 'd0;
            DUT_RnW <= 1'd1;
            DUT_ADR <= 'd0;
            DUT_DIN <= 'd0;
        end else begin
            shift_drdy <= {shift_drdy[0], FIFO_RDY};
            shift_test <= {shift_test[0], trigger_test};
            FIFO_DOUT <= (do_update_data) ? {sel_cmds, sel_adr, ((sel_cmds == REG_HEADER) ? data_head_send[sel_adr] : DUT_DOUT)} : FIFO_DOUT;

            LED_CONTROL     <= (do_update_data && sel_cmds == REG_DUT_CNTL && |sel_adr[3:2])    ? ((sel_adr[3]) ? !LED_CONTROL : sel_data[0])  : LED_CONTROL;
            trigger_test    <= (do_update_data && sel_cmds == REG_DUT_CNTL && sel_adr[0])       ? !trigger_test : trigger_test;
            DUT_SEL         <= (do_update_data && sel_cmds == REG_DUT_CNTL && sel_adr[1])       ? sel_data[$clog2(NUM_DUT)+'d1:1] : DUT_SEL;
            DUT_RnW         <= (do_update_data)                                                 ? !(sel_cmds == REG_DUT_WR) : DUT_RnW;
            DUT_ADR         <= (do_update_data)                                                 ? sel_adr : DUT_ADR;
            DUT_DIN         <= (do_update_data && sel_cmds == REG_DUT_WR)                       ? sel_data : DUT_DIN;
        end
    end
endmodule