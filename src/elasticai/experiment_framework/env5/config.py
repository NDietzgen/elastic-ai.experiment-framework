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


# --- SPI_MIDDLEWARE aus dem Verilog-Template (read_skeleton_id / predict)
DEFAULT_DUT = 1
HEADER_BYTES = 4  # 32-Bit-DUT-Header


def predict_payload(data: bytes, result_size: int, dut: int) -> tuple[bytes, int]:
    """Baut die Task-Daten für predict: [DUT, Ergebnisbytes, Daten].

    Daten und Ergebnis sind 16-Bit-Worte (Little Endian); ungerade Längen
    werden auf ganze Worte aufgefüllt. Gibt Payload und Ergebnisbytes zurück.
    """
    if len(data) % 2:
        data += b"\x00"
    words_bytes = result_size + (result_size % 2)
    return bytes([dut, words_bytes]) + data, words_bytes
