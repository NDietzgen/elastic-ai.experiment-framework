//////////////////////////////////////////////////////////////////////////////////
// Company:         University of Duisburg-Essen, Intelligent Embedded Systems Lab
// Engineer:        ND, AE
//
// Create Date:     10.08.2026, 17:54:12
// Copied on: 	    §{date_copy_created}
// Module Name:     Simple Datarate Subsampler
// Target Devices:  FPGA
// Tool Versions:   1v0
// Processing:      Data applied on posedge CLK_SYS
// Dependencies:    None
//
// State: 	        Not tested!
// Improvements:    None
// Parameters:      BITWIDTH --> Bitwidth of input data
//                  DEC_RATE --> Decimation rate
//                  INDEX    --> Index with updating output
//////////////////////////////////////////////////////////////////////////////////


module SUBSAMPLER #(
    parameter integer DEC_RATE = 4,
    parameter integer INDEX = 0,
    parameter integer BITWIDTH = 8
)(
    input wire                      CLK_SYS,
    input wire                      RSTN,
    input wire                      EN,
    input wire                      IN_VALID,
    input wire [BITWIDTH-'d1:0]     DATA_IN,
    output reg                      DATA_RDY,
    output reg  [BITWIDTH-'d1:0]    DATA_OUT
);

    reg [$clog2(DEC_RATE):0] counter;
    reg in_valid_dly;

    always @(posedge CLK_SYS) begin
        if (!RSTN) begin
            counter <= 'd0;
            in_valid_dly <= 1'd0;
            DATA_RDY <= 1'b0;
            DATA_OUT  <= {BITWIDTH{1'b0}};
        end else begin
            in_valid_dly <= IN_VALID;
            if (IN_VALID && !in_valid_dly && EN) begin
                counter <= (counter == DEC_RATE - 'd1) ? 'd0 : counter + 'd1;
                DATA_OUT <= (counter == INDEX) ? DATA_IN : DATA_OUT;
                DATA_RDY <= (counter == INDEX) ? 1'd1 : 1'd0;
            end else begin
                counter <= counter;
                DATA_OUT <= DATA_OUT;
                DATA_RDY <= DATA_RDY;
            end
        end
    end
endmodule