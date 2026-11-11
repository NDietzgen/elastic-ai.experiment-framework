import logging
from pathlib import Path

import pytest

from elasticai.experiment_framework.env5.sync_fpga_remote_control import (
    SyncFPGARemoteControl,
)

logger = logging.getLogger(__name__)

# Bitstream aus dem Vivado-Test des Reset-Tests (tests/vivado/duts/reset_test/test_build.py)
BIT_STREAM_PATH = Path("tests/vivado/artifacts/env5_reset_test/TOP_MODULE.bit")


@pytest.fixture(scope="session")
def fpga_remote_control(wait_for_device):
    device = wait_for_device

    with device.connect_sync() as stream:
        with SyncFPGARemoteControl(stream) as control:
            yield control


def test_fpga_flashing(fpga_remote_control): # works
    fpga_remote_control.program_fpga(BIT_STREAM_PATH)

    skeleton_id = fpga_remote_control.read_skeleton_id()
    logger.info("skeleton id: %s", skeleton_id)
    assert int(skeleton_id, 16) != 0
    
