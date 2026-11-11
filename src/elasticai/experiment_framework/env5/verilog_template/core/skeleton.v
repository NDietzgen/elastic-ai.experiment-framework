//////////////////////////////////////////////////////////////////////////////////
// Create Date:     09.11.2026
// Module Name:     SKELETON
// Target Devices:  FPGA
// Description:     Einheitliches Skeleton: wählt per DUT_TYPE (dut_config.vh)
//                  genau einen Wrapper aus. Jeder Wrapper steht für eine Klasse
//                  von DUTs, der Modulname des DUT ist über DUT_MODULE frei.
//                  Anleitung und Referenz: README.md
//
//                  Aufbau dieser Datei:
//                    0 DUT_MOD_*         --> Modulnamen der DUTs
//                    1 SKELETON          --> Auswahl des Wrappers
//                    2 DUT_WRAPPER_*     --> Wrapper der Klassen
//                  DUT_WRAPPER_USER liegt in user/dut_wrapper_user.v.
// Dependencies:    user/dut_config.vh, DUT des gewählten Wrappers
//
// State: 	        Not tested!
//////////////////////////////////////////////////////////////////////////////////


`include "../user/dut_config.vh"

// =============================================================================
// 0 DUT MODULE NAMES (do not change)
// =============================================================================
// Module name instantiated by each wrapper: `DUT_MODULE from user/dut_config.vh,
// otherwise the default name of the class. Only the selected wrapper is
// elaborated, so all classes may share the one `DUT_MODULE.
`ifdef DUT_MODULE
    `define DUT_MOD_ROM  `DUT_MODULE
    `define DUT_MOD_RAM  `DUT_MODULE
    `define DUT_MOD_MULT `DUT_MODULE
    `define DUT_MOD_MAC  `DUT_MODULE
    `define DUT_MOD_FILT `DUT_MODULE
    `define DUT_MOD_DNN  `DUT_MODULE
`else
    `define DUT_MOD_ROM  LUT_WVF_GEN0
    `define DUT_MOD_RAM  BRAM_SINGLE
    `define DUT_MOD_MULT MULT_SIGNED
    `define DUT_MOD_MAC  MAC
    `define DUT_MOD_FILT Filter_IIR_1
    `define DUT_MOD_DNN  skeleton
`endif


// =============================================================================
// 1 SKELETON (selects the wrapper, do not change)
// =============================================================================
module SKELETON#(
    parameter DUT_TYPE              = "USER",
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
    output wire [NUM_LEDS-'d1:0] LEDS       // only driven by DUT_WRAPPER_USER
);

// Only the USER wrapper drives the LEDs, all other wrappers leave them off
wire [NUM_LEDS-'d1:0] leds_user;
assign LEDS = (DUT_TYPE == "USER") ? leds_user : {NUM_LEDS{1'd0}};

// All wrappers share the same port list, so the connection is defined once
`define DUT_WRAPPER_PARAMS \
    .BITWIDTH_IN(BITWIDTH_IN), \
    .BITWIDTH_SYS(BITWIDTH_SYS), \
    .BITWIDTH_HEAD(BITWIDTH_HEAD), \
    .BITWIDTH_ADR(BITWIDTH_ADR)
`define DUT_WRAPPER_PORTS \
    .CLK_SYS(CLK_SYS), \
    .RSTN(RSTN), \
    .EN(EN), \
    .TRGG_START_CALC(TRGG_START_CALC), \
    .RnW(RnW), \
    .ADR(ADR), \
    .DATA_IN(DATA_IN), \
    .DATA_OUT(DATA_OUT), \
    .DATA_HEAD(DATA_HEAD), \
    .RDY(RDY), \
    .DATA_VALID(DATA_VALID)

generate
    if (DUT_TYPE == "USER") begin : gen_user
        DUT_WRAPPER_USER#(`DUT_WRAPPER_PARAMS, .NUM_LEDS(NUM_LEDS))
            WRAPPER(`DUT_WRAPPER_PORTS, .LEDS(leds_user));
    end else if (DUT_TYPE == "ROM") begin : gen_rom
        DUT_WRAPPER_ROM#(`DUT_WRAPPER_PARAMS) WRAPPER(`DUT_WRAPPER_PORTS);
    end else if (DUT_TYPE == "RAM") begin : gen_ram
        DUT_WRAPPER_RAM#(`DUT_WRAPPER_PARAMS) WRAPPER(`DUT_WRAPPER_PORTS);
    end else if (DUT_TYPE == "MULT") begin : gen_mult
        DUT_WRAPPER_MULT#(`DUT_WRAPPER_PARAMS) WRAPPER(`DUT_WRAPPER_PORTS);
    end else if (DUT_TYPE == "MAC") begin : gen_mac
        DUT_WRAPPER_MAC#(`DUT_WRAPPER_PARAMS) WRAPPER(`DUT_WRAPPER_PORTS);
    end else if (DUT_TYPE == "FILT") begin : gen_filt
        DUT_WRAPPER_FILT#(`DUT_WRAPPER_PARAMS) WRAPPER(`DUT_WRAPPER_PORTS);
    end else if (DUT_TYPE == "DNN") begin : gen_dnn
        DUT_WRAPPER_DNN#(`DUT_WRAPPER_PARAMS) WRAPPER(`DUT_WRAPPER_PORTS);
    end else begin : gen_invalid
        // Unknown DUT_TYPE: this module does not exist on purpose, so that
        // elaboration fails with a readable error message.
        ERROR_UNKNOWN_DUT_TYPE_CHECK_USER_DUT_CONFIG INVALID();
    end
endgenerate

`undef DUT_WRAPPER_PARAMS
`undef DUT_WRAPPER_PORTS

endmodule


// #############################################################################
// 2 READY-TO-USE WRAPPERS 
// #############################################################################


// =============================================================================
// 2a DUT_WRAPPER_ROM
// =============================================================================
module DUT_WRAPPER_ROM#(
    parameter integer BITWIDTH_IN   = 16,
    parameter integer BITWIDTH_SYS  = 16,
    parameter integer BITWIDTH_HEAD = 26,
    parameter integer BITWIDTH_ADR  = 6
)(
    input wire CLK_SYS,
    input wire RSTN,
    input wire EN,
    input wire TRGG_START_CALC,
    input wire RnW,                         // unused
    input wire [BITWIDTH_ADR-'d1:0] ADR,    // unused
    input wire [BITWIDTH_SYS-'d1:0] DATA_IN,
    output wire [BITWIDTH_SYS-'d1:0] DATA_OUT,
    output wire [BITWIDTH_HEAD-'d1:0] DATA_HEAD,
    output wire RDY,
    output wire DATA_VALID                  // unused
);

localparam integer BITWIDTH_OFFSET = BITWIDTH_SYS - BITWIDTH_IN;
assign DATA_HEAD = {4'd2, 6'd0, 6'd21, 5'd0, BITWIDTH_IN[4:0]};
assign DATA_VALID = 1'd0;

wire [BITWIDTH_IN-'d1:0] dout_rom;
assign DATA_OUT = {dout_rom, {BITWIDTH_OFFSET{1'd0}}};

wire din_rom;
assign din_rom = |DATA_IN && EN;

`DUT_MOD_ROM DUT(
    .CLK_SYS(CLK_SYS),
    .nRST(RSTN),
    .EN(din_rom),
    .TRGG_CNT_FLAG(TRGG_START_CALC),
    .LUT_VALUE(dout_rom),
    .LUT_END(RDY)
);

endmodule


// =============================================================================
// 2b DUT_WRAPPER_RAM
// =============================================================================
module DUT_WRAPPER_RAM#(
    parameter integer BITWIDTH_IN   = 12,
    parameter integer BITWIDTH_SYS  = 16,
    parameter integer BITWIDTH_HEAD = 26,
    parameter integer BITWIDTH_ADR  = 6
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
    output wire DATA_VALID                  // unused
);

localparam integer BITWIDTH_OFFSET = BITWIDTH_SYS - BITWIDTH_IN;
localparam integer NUM_POSITIONS = (2 ** BITWIDTH_ADR) - 4;
assign DATA_HEAD = {4'd3, NUM_POSITIONS[5:0], NUM_POSITIONS[5:0], BITWIDTH_IN[4:0], BITWIDTH_IN[4:0]};
assign DATA_VALID = 1'd0;

wire en_module, we_module;
wire [BITWIDTH_IN-'d1:0] ram_din, ram_dout;
assign en_module = EN && RSTN && !TRGG_START_CALC;
assign we_module = !RnW;
assign ram_din = DATA_IN[(BITWIDTH_SYS-'d1)-:BITWIDTH_IN];
assign DATA_OUT = {ram_dout, {BITWIDTH_OFFSET{1'd0}}};
assign RDY = 1'd1;

`DUT_MOD_RAM#(
    BITWIDTH_IN,
    NUM_POSITIONS,
    ""
) DUT (
    .CLK_RAM(CLK_SYS),
    .EN(en_module),
    .WE(we_module),
    .ADR(ADR),
    .DIN(ram_din),
    .DOUT(ram_dout)
);

endmodule


// =============================================================================
// 2c DUT_WRAPPER_MULT
// =============================================================================
module DUT_WRAPPER_MULT#(
    parameter integer BITWIDTH_IN   = 8,
    parameter integer BITWIDTH_SYS  = 16,
    parameter integer BITWIDTH_HEAD = 26,
    parameter integer BITWIDTH_ADR  = 6
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
    output wire DATA_VALID                  // unused
);

localparam integer WAIT_CYC_MULT = 1;
localparam integer BITWIDTH_OFFSET = BITWIDTH_SYS - BITWIDTH_IN;
localparam integer BITWIDTH_OUT = 2 * BITWIDTH_IN;

localparam integer NUM_MULT = 1;
localparam integer SIZE_INPUT = 2;      // was 1, but data_dut[1] is used below
localparam integer SIZE_OUTPUT = 1;

assign DATA_HEAD = {4'd4, SIZE_INPUT[5:0], SIZE_OUTPUT[5:0], BITWIDTH_IN[4:0], BITWIDTH_OUT[4:0]};
assign DATA_VALID = 1'd0;

// --- Control lines
reg run_test;
reg [$clog2(WAIT_CYC_MULT):0] cnt_mult_wait;

reg [BITWIDTH_IN-'d1:0] data_dut [SIZE_INPUT-'d1:0];

reg [SIZE_OUTPUT*BITWIDTH_OUT-'d1:0] pipe_dut_out;
wire signed [SIZE_OUTPUT*BITWIDTH_OUT-'d1:0] data_mul;
assign RDY = ~run_test;

// --- Flag in LSBs of DATA_IN (guard against zero-width slice)
wire din_lsb_flag;
if (BITWIDTH_OFFSET > 0) begin : gen_lsb_flag
    assign din_lsb_flag = |DATA_IN[0+:BITWIDTH_OFFSET];
end else begin : gen_lsb_flag_none
    assign din_lsb_flag = 1'd1;
end

// --- Converting data
if((BITWIDTH_SYS-BITWIDTH_OUT) > 0) begin : gen_out_pad
    assign DATA_OUT = {pipe_dut_out[0+:BITWIDTH_OUT], {(BITWIDTH_SYS-BITWIDTH_OUT){1'd0}}};
end else begin : gen_out_trunc
    assign DATA_OUT = pipe_dut_out[0+:BITWIDTH_OUT];
end

// --- Testing routine
integer i0;
always@(posedge CLK_SYS) begin
    if(!(RSTN && EN)) begin
        run_test <= 1'd0;
        cnt_mult_wait <= 'd0;
        pipe_dut_out <= 'd0;
        for(i0 = 'd0; i0 < SIZE_INPUT; i0 = i0 + 'd1) begin
            data_dut[i0] <= 'd0;
        end
    end else begin
        // --- Loading data to internal RAM
        if(!RnW && (ADR < SIZE_INPUT))
            data_dut[ADR] <= DATA_IN[(BITWIDTH_SYS-'d1)-:BITWIDTH_IN];

        // --- Pipelining Multiplier Input (1-Delay Stage)
        if(run_test && din_lsb_flag) begin
            run_test <= (cnt_mult_wait == WAIT_CYC_MULT) ? 1'd0 : run_test;
            cnt_mult_wait <= (cnt_mult_wait == WAIT_CYC_MULT) ? 'd0 : cnt_mult_wait + 'd1;
            pipe_dut_out <= data_mul;
        end else begin
            run_test <= TRGG_START_CALC;
            cnt_mult_wait <= 'd0;
            pipe_dut_out <= pipe_dut_out;
        end
    end
end

`DUT_MOD_MULT#(
    .BITWIDTH(BITWIDTH_IN)
) MULT (
    .A(data_dut[0]),
    .B(data_dut[1]),
    .Q(data_mul)
);

endmodule


// =============================================================================
// 2d DUT_WRAPPER_MAC
// =============================================================================
module DUT_WRAPPER_MAC#(
    parameter integer BITWIDTH_IN   = 8,
    parameter integer BITWIDTH_SYS  = 16,
    parameter integer BITWIDTH_HEAD = 26,
    parameter integer BITWIDTH_ADR  = 6
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
    output wire DATA_VALID                  // unused
);

localparam integer WAIT_CYC_MULT = 1;
localparam integer BITWIDTH_OFFSET = BITWIDTH_SYS - BITWIDTH_IN;
localparam integer BITWIDTH_OUT = 2 * BITWIDTH_IN;

localparam integer NUM_PARAMS = 16;
localparam integer SIZE_INPUT = 2*NUM_PARAMS + 1;
localparam integer SIZE_OUTPUT = 1;
localparam integer NUM_MULT = 2;

assign DATA_HEAD = {4'd4, SIZE_INPUT[5:0], SIZE_OUTPUT[5:0], BITWIDTH_IN[4:0], BITWIDTH_OUT[4:0]};
assign DATA_VALID = 1'd0;

// --- Control lines
reg run_test;
reg [$clog2(WAIT_CYC_MULT):0] cnt_mult_wait;

reg [BITWIDTH_IN-'d1:0] data_dut [SIZE_INPUT-'d1:0];

reg [SIZE_OUTPUT*BITWIDTH_OUT-'d1:0] pipe_dut_out;
wire signed [SIZE_OUTPUT*BITWIDTH_OUT-'d1:0] data_mul;

// --- Flag in LSBs of DATA_IN (guard against zero-width slice)
wire din_lsb_flag;
if (BITWIDTH_OFFSET > 0) begin : gen_lsb_flag
    assign din_lsb_flag = |DATA_IN[0+:BITWIDTH_OFFSET];
end else begin : gen_lsb_flag_none
    assign din_lsb_flag = 1'd1;
end

// --- Converting data
genvar k0;
wire [BITWIDTH_IN-'d1:0] bias0;
wire [BITWIDTH_IN*NUM_PARAMS-'d1:0] wght0, data0;

assign bias0 = data_dut[0];
for(k0 = 'd0; k0 < NUM_PARAMS; k0 = k0 + 'd1) begin : gen_unpack
    assign data0[(k0*BITWIDTH_IN)+:BITWIDTH_IN] = data_dut[1 + k0];
    assign wght0[(k0*BITWIDTH_IN)+:BITWIDTH_IN] = data_dut[NUM_PARAMS + 1 + k0];
end

if((BITWIDTH_SYS-BITWIDTH_OUT) > 0) begin : gen_out_pad
    assign DATA_OUT = {pipe_dut_out[0+:BITWIDTH_OUT], {(BITWIDTH_SYS-BITWIDTH_OUT){1'd0}}};
end else begin : gen_out_trunc
    assign DATA_OUT = pipe_dut_out[0+:BITWIDTH_OUT];
end

// --- Testing routine
integer i0;
always@(posedge CLK_SYS) begin
    if(!(RSTN && EN)) begin
        run_test <= 1'd0;
        cnt_mult_wait <= 'd0;
        pipe_dut_out <= 'd0;
        for(i0 = 'd0; i0 < SIZE_INPUT; i0 = i0 + 'd1) begin
            data_dut[i0] <= 'd0;
        end
    end else begin
        // --- Loading data to internal RAM
        if(!RnW && (ADR < SIZE_INPUT))
            data_dut[ADR] <= DATA_IN[(BITWIDTH_SYS-'d1)-:BITWIDTH_IN];

        // --- Pipelining Multiplier Input (1-Delay Stage)
        if(run_test && din_lsb_flag) begin
            run_test <= (cnt_mult_wait == WAIT_CYC_MULT) ? 1'd0 : run_test;
            cnt_mult_wait <= (cnt_mult_wait == WAIT_CYC_MULT) ? 'd0 : cnt_mult_wait + 'd1;
            pipe_dut_out <= data_mul;
        end else begin
            run_test <= TRGG_START_CALC;
            cnt_mult_wait <= 'd0;
            pipe_dut_out <= pipe_dut_out;
        end
    end
end

`DUT_MOD_MAC#(BITWIDTH_IN, NUM_PARAMS, NUM_MULT) MAC(
    .CLK_SYS(CLK_SYS),
    .RSTN(RSTN),
    .EN(EN),
    .DO_CALC(run_test),
    .IN_BIAS(bias0),
    .IN_WEIGHTS(wght0),
    .IN_DATA(data0),
    .OUT_DATA(data_mul),
    .DATA_RDY(RDY)
);

endmodule


// =============================================================================
// 2e DUT_WRAPPER_FILT
// =============================================================================
module DUT_WRAPPER_FILT#(
    parameter integer BITWIDTH_IN   = 16,
    parameter integer BITWIDTH_SYS  = 16,
    parameter integer BITWIDTH_HEAD = 26,
    parameter integer BITWIDTH_ADR  = 6
)(
    input wire CLK_SYS,
    input wire RSTN,
    input wire EN,
    input wire TRGG_START_CALC,
    input wire RnW,                         // unused
    input wire [BITWIDTH_ADR-'d1:0] ADR,    // unused
    input wire [BITWIDTH_SYS-'d1:0] DATA_IN,
    output wire [BITWIDTH_SYS-'d1:0] DATA_OUT,
    output wire [BITWIDTH_HEAD-'d1:0] DATA_HEAD,
    output wire RDY,
    output wire DATA_VALID                  // unused
);

localparam integer BITWIDTH_OFFSET = BITWIDTH_SYS - BITWIDTH_IN;
assign DATA_HEAD = {4'd5, 6'd1, 6'd1, BITWIDTH_IN[4:0], BITWIDTH_IN[4:0]};
assign DATA_VALID = 1'd0;

wire module_drdy, module_dvalid;
wire [BITWIDTH_IN-'d1:0] data_filt_in, data_filt_out;
assign data_filt_in = DATA_IN[BITWIDTH_OFFSET+:BITWIDTH_IN];

assign RDY = module_drdy && module_dvalid;
assign DATA_OUT = {data_filt_out, {BITWIDTH_OFFSET{1'd0}}};

`DUT_MOD_FILT#(BITWIDTH_IN) FILT_STAGE(
    .CLK(CLK_SYS),
    .RSTN(RSTN),
    .EN(EN),
    .START_FLAG(TRGG_START_CALC),
    .DATA_IN(data_filt_in),
    .DATA_OUT(data_filt_out),
    .DATA_RDY(module_drdy),
    .DATA_VALID(module_dvalid)
);

endmodule


// =============================================================================
// 2f DUT_WRAPPER_DNN
// =============================================================================
module DUT_WRAPPER_DNN#(
    parameter integer BITWIDTH_IN   = 8,
    parameter integer BITWIDTH_SYS  = 16,
    parameter integer BITWIDTH_HEAD = 26,
    parameter integer BITWIDTH_ADR  = 6
)(
    input wire CLK_SYS,
    input wire RSTN,
    input wire EN,
    input wire TRGG_START_CALC,             // unused
    input wire RnW,
    input wire [BITWIDTH_ADR-'d1:0] ADR,
    input wire [BITWIDTH_SYS-'d1:0] DATA_IN,
    output wire [BITWIDTH_SYS-'d1:0] DATA_OUT,
    output wire [BITWIDTH_HEAD-'d1:0] DATA_HEAD,
    output wire RDY,                        // unused
    output wire DATA_VALID
);

localparam integer BITWIDTH_OFFSET = BITWIDTH_SYS - BITWIDTH_IN;
localparam integer NUM_INPUT = 5;
localparam integer NUM_OUTPUT = 3;

assign DATA_HEAD = {4'd7, NUM_INPUT[5:0], NUM_OUTPUT[5:0], BITWIDTH_IN[4:0], BITWIDTH_IN[4:0]};
assign RDY = 1'd0;

wire [BITWIDTH_IN-'d1:0] dnn_dout;
assign DATA_OUT = {dnn_dout, {BITWIDTH_OFFSET{1'd0}}};

//If using skeleton from elasticAI.creator please include shift, otherwise software API does not work!
//Also include SEL in reset input
`DUT_MOD_DNN LinearDesign(
    .clock(CLK_SYS),
    .clk_hadamard(CLK_SYS),
    .reset(!(RSTN && EN)),
    .busy(DATA_VALID),
    .wake_up(),
    .rd(RnW),
    .wr(!RnW),
    .data_in(DATA_IN[BITWIDTH_OFFSET+:BITWIDTH_IN]),
    .address_in({{('d16-BITWIDTH_ADR){1'd0}}, ADR}),
    .data_out(dnn_dout),
    .debug()
);

endmodule


`undef DUT_MOD_ROM
`undef DUT_MOD_RAM
`undef DUT_MOD_MULT
`undef DUT_MOD_MAC
`undef DUT_MOD_FILT
`undef DUT_MOD_DNN
