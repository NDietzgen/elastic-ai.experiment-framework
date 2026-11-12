from enum import IntEnum

BYTE_ORDER = "little"


class TaskDefinitionIds(IntEnum):
    FPGA_INIT = 0x3
    FPGA_POWER_ON = 0x4
    FPGA_POWER_OFF = 0x5
    FPGA_WRITE_TO_FLASH = 0x6
    FPGA_READ_SKELETON_ID = 0x7
    FPGA_PREDICT = 0x8
    FPGA_CLEAR_FLASH = 0x0a
    FPGA_SPI_ECHO = 0x0c
    FPGA_RESET = 0x0d
    FPGA_READ_DUT_HEADER = 0x0e
    FPGA_PREDICT_DUT = 0x0f

# Reset-Dauer (GPIO13 (RSTN) auf Low)
FPGA_RESET_DURATION_S = 5.0


# --- SPI_MIDDLEWARE aus dem Verilog-Template (read_dut_header / predict_dut)
DEFAULT_DUT = 1
HEADER_BYTES = 4  # 32-Bit-DUT-Header
