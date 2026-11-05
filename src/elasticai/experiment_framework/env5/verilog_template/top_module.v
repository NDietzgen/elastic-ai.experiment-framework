module TOP_MODULE#(
    parameter integer NUM_DUT = 2,
    parameter integer TEST_ENV_CMDS_BITWIDTH = 2,
    parameter integer TEST_ENV_ADR_WIDTH = 6,
    parameter integer TEST_ENV_DATA_BITWIDTH = 16
)(
    // --- Global signals
    input wire          CLK_SYS,
    input wire          RSTN_MCU,               // active-low, asynchron von MCU (Pin M13)
    // --- General purpose I/O
    output wire         LED,
    output wire         FPGA_BUSY,
    // --- SPI Communication
    output wire         SPI_MISO,
    input wire          SPI_MOSI,
    input wire          SPI_SCLK,
    input wire          SPI_CSN
);

	localparam SPI_BITWIDTH = TEST_ENV_CMDS_BITWIDTH + TEST_ENV_ADR_WIDTH + TEST_ENV_DATA_BITWIDTH;
    localparam TEST_HEAD_BITWIDTH = 32;

    //##########################################################
    //RESET-SYNCHRONISIERUNG
    // RSTN_MCU von der MCU ist asynchron: 2-FF-Kette synchronisiert Setzen und Freigeben auf CLK_SYS,
    // damit alle Module gleichzeitig und ohne Metastabilitaet starten (2 Takte Verzoegerung).
    (* ASYNC_REG = "TRUE" *) reg [1:0] rstn_sync = 2'b00;
    always @(posedge CLK_SYS) rstn_sync <= {rstn_sync[0], RSTN_MCU};
    wire RSTN = rstn_sync[1];                   // synchronisierter Reset fuer alle Untermodule

    //Signals for SPI module
    wire spi_mod_rdy;
    wire [SPI_BITWIDTH -'d1:0] data_spi_to_mid, data_mid_to_spi;

    wire dut_start_flag, dut_rdy, dut_rnw;
    wire [$clog2(NUM_DUT):0] dut_sel;
    wire [TEST_ENV_ADR_WIDTH-'d1:0] dut_adr;
    wire [TEST_ENV_DATA_BITWIDTH-'d1:0] dut_din, dut_dout;
    wire [TEST_HEAD_BITWIDTH-'d1:0] dut_header;

    //Interface for Debugging modules
    assign FPGA_BUSY = !dut_rdy;

    //##########################################################
    //UNTER-MODULE: DEVICE UNDER TEST
    TEST_ENVIRONMENT#(
        .NUM_DUT(NUM_DUT),
        .BITWIDTH_DATA(TEST_ENV_DATA_BITWIDTH),
        .BITWIDTH_ADR(TEST_ENV_ADR_WIDTH),
        .NUM_BITS_HEADER(TEST_HEAD_BITWIDTH),
        .UINT_DATATYPE(1'd1)
    ) DUT(
        .CLK(CLK_SYS),
        .RSTN(RSTN),
        .START_FLAG(dut_start_flag),
        .SEL(dut_sel),
        .ADR(dut_adr),
        .RnW(dut_rnw),
        .DATA_IN(dut_din),
        .DATA_OUT(dut_dout),
        .HEAD_INFO(dut_header),
        .RDY_FLAG(dut_rdy)
    );

    //##########################################################
    //UNTER-MODULE: Communication + DUT_Handler in DataHandler
    SPI_SLAVE_WCLK#(
        .BITWIDTH(SPI_BITWIDTH),
        .CPOL(1'd0),
        .CPHA(1'd0),
        .MSB(1'd1)
    ) SPI_MOD (
        .CLK_SYS(CLK_SYS),
        .RSTN(RSTN),
        .CSN(SPI_CSN),
        .SCLK(SPI_SCLK),
        .MOSI(SPI_MOSI),
        .MISO(SPI_MISO),
        .DFROM_MIDDLEWARE(data_mid_to_spi),
        .DFOR_MIDDLEWARE(data_spi_to_mid),
        .DRDY(spi_mod_rdy)
    );
    SPI_MIDDLEWARE#(
        .BITWIDTH(SPI_BITWIDTH),
        .BITWIDTH_CMDS(TEST_ENV_CMDS_BITWIDTH),
        .BITWIDTH_DATA(TEST_ENV_DATA_BITWIDTH),
        .BITWIDTH_ADR(TEST_ENV_ADR_WIDTH),
        .BITWIDTH_HEAD(TEST_HEAD_BITWIDTH),
        .NUM_DUT(NUM_DUT)
    ) MIDDLEWARE(
        .CLK_SYS(CLK_SYS),
        .RSTN(RSTN),
        .FIFO_RDY(spi_mod_rdy),
        .FIFO_DIN(data_spi_to_mid),
        .FIFO_DOUT(data_mid_to_spi),
        .LED_CONTROL(LED),
        .DUT_DO_TEST(dut_start_flag),
        .DUT_SEL(dut_sel),
        .DUT_DIN(dut_din),
        .DUT_DOUT(dut_dout),
        .DUT_ADR(dut_adr),
        .DUT_RnW(dut_rnw),
        .DUT_HEADER(dut_header)
    );
endmodule