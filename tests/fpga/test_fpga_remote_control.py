import logging
from pathlib import Path
import time

import pytest

from elasticai.experiment_framework.env5.sync_fpga_remote_control import (
    SyncFPGARemoteControl,
)

logging.basicConfig(format="%(message)s")
logger = logging.getLogger(__name__)

BYTE_STREAM_PATH = Path("tests/fpga/test_bitstreams/env5_top_reconfig.bin")
TEMPLATE_BIT_STREAM_PATH = Path("tests/fpga/test_bitstreams/TOP_MODULE_LED_1.bit")


@pytest.fixture(scope="session")
def fpga_remote_control(flashed_pico, wait_for_device):
    device = wait_for_device

    with device.connect_sync() as stream:
        with SyncFPGARemoteControl(stream) as control:
            yield control


def test_fpga_flashing(fpga_remote_control):
    fpga_remote_control.fpga_power_off()
    fpga_remote_control.upload_bitstream(
        flash_sector=0,
        path_to_bitstream=BYTE_STREAM_PATH,
    )
    fpga_remote_control.fpga_power_on()
    time.sleep(1)
    fpga_remote_control.read_skeleton_id()
    res = fpga_remote_control.predict(b"\xff", 1)

    logger.info(f"Predict result: {res}")

    assert res == b"\x01"


def test_fpga_flashing_template_middleware(fpga_remote_control):
    fpga_remote_control.program_fpga(TEMPLATE_BIT_STREAM_PATH)

    header = fpga_remote_control.read_dut_header()
    logger.info("dut header: %s", header)
    assert int(header, 16) != 0
