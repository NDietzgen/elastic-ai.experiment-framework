module TEST_ENVIRONMENT#(
    parameter DUT_TYPE = "USER",
    parameter integer DUT_BITWIDTH_IN = 16,
    parameter integer BITWIDTH_DATA = 16,
    parameter integer BITWIDTH_ADR = 6,
    parameter integer NUM_DUT = 2,
    parameter integer NUM_BITS_HEADER = 32,
    parameter integer UINT_DATATYPE = 1,
    parameter integer NUM_LEDS = 4
)(
    input wire CLK,
    input wire RSTN,
    input wire START_FLAG,
    input wire [$clog2(NUM_DUT):0] SEL,
    input wire [BITWIDTH_ADR-'d1:0] ADR,
    input wire RnW,
    input wire [BITWIDTH_DATA-'d1:0] DATA_IN,
    output wire [BITWIDTH_DATA-'d1:0] DATA_OUT,
    output wire [NUM_BITS_HEADER-'d1:0] HEAD_INFO, 
    output wire RDY_FLAG,
    output wire [NUM_LEDS-'d1:0] DUT_LEDS
);

    localparam BITWIDTH_HEAD = NUM_BITS_HEADER - 'd6;
    //################## CONTROL LINES ################## 
    wire [BITWIDTH_DATA-'d1:0] dout [NUM_DUT:0];
    assign DATA_OUT = dout[SEL]; 

    wire [NUM_DUT:0] rdy_filt;
    assign RDY_FLAG = rdy_filt[SEL];
    
    //* This variable contains information about the module for read-in in Python 
    //  - NUM_DUTS (6-bits):        Total number of DUTs available in this function (automated added here)
    //  - DUT_TYPE (4-bits):        0 = Disabled, 1 = Echo, 2 = ROM, 3 = RAM, 4 = Math, 5 = Filter, 6 = Pre-Processing, 7 = elasticAI.creator,  8 = End-To-End Processor
    //  - NUM_INPUTS (6-bits):      Number of used inputs
    //  - NUM_OUTPUTS (6-bits):     Number of used outputs
    //  - BITWIDTH_IN (5-bits):     Bitwidth of input data
    //  - BITWIDTH_OUT (5-bits):    Bitwidth of output data
    wire [NUM_BITS_HEADER-'d7:0] head_array [NUM_DUT:0];
    assign HEAD_INFO = {NUM_DUT[5:0], head_array[SEL]};

    // SEL == 'd0 will be skipped!
    assign dout[0] = 'd0123;
    assign head_array[0] = {4'd0, 6'd0, 6'd1, 5'd0, BITWIDTH_DATA[4:0]};
    assign rdy_filt[0] = 1'd0; 

    //################## List with DUT ################## 
    SKELETON_ECHO#(
        .BITWIDTH_SYS(BITWIDTH_DATA),
        .BITWIDTH_HEAD(BITWIDTH_HEAD)
    ) DUT_01 (
        .CLK_SYS(CLK),
        .RSTN(RSTN),
        .EN(SEL == 'd1),
        .TRGG_START_CALC(START_FLAG),
        .DATA_IN(DATA_IN),
        .DATA_OUT(dout[1]),
        .DATA_HEAD(head_array[1]),
        .DATA_VALID(rdy_filt[1])
    );    
        
    // DUT under test: selected by DUT_TYPE / DUT_BITWIDTH_IN in TOP_MODULE
    SKELETON#(
        .DUT_TYPE(DUT_TYPE),
        .BITWIDTH_IN(DUT_BITWIDTH_IN),
        .BITWIDTH_SYS(BITWIDTH_DATA),
        .BITWIDTH_HEAD(BITWIDTH_HEAD),
        .BITWIDTH_ADR(BITWIDTH_ADR),
        .NUM_LEDS(NUM_LEDS)
    ) DUT_02 (
        .CLK_SYS(CLK),
        .RSTN(RSTN),
        .EN(SEL == 'd2),
        .RnW(RnW),
        .ADR(ADR),
        .TRGG_START_CALC(START_FLAG),
        .DATA_IN(DATA_IN),
        .DATA_OUT(dout[2]),
        .DATA_HEAD(head_array[2]),
        .RDY(rdy_filt[2]),
        .DATA_VALID(),
        .LEDS(DUT_LEDS)
    );  
        
endmodule