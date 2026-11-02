import logging
from pathlib import Path
import time

import pytest

from elasticai.experiment_framework.env5.sync_fpga_remote_control import (
    SyncFPGARemoteControl,
)

logger = logging.getLogger(__name__)

BYTE_STREAM_PATH = Path("tests/fpga/TOP_MODULE_1.bit")  # LED Test


@pytest.fixture(scope="session")
def fpga_remote_control(wait_for_device):
    device = wait_for_device

    with device.connect_sync() as stream:
        with SyncFPGARemoteControl(stream) as control:
            yield control


def test_fpga_flashing(fpga_remote_control): # works
    fpga_remote_control.fpga_power_off()
    fpga_remote_control.clear_flash() 
    fpga_remote_control.upload_bitstream(
        flash_sector=0, path_to_bitstream=BYTE_STREAM_PATH, need_ack=True
    )
    fpga_remote_control.fpga_power_off()
    fpga_remote_control.fpga_power_on()
    time.sleep(1)    # Damit Skeleton-ID erkannt wird
    skeleton_id = fpga_remote_control.read_skeleton_id()
    logger.info(f"skeleton id: {skeleton_id}")

    assert skeleton_id != 0
    
