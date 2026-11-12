import logging
import pytest
from elasticai.experiment_framework.env5.sync_fpga_remote_control import (
    SyncFPGARemoteControl,
)

pytestmark = pytest.mark.hardware
logger = logging.getLogger(__name__)

"""SPI-Echo-Test zwischen Pico und FPGA"""
"""Erwartet, dass bereits ein Bitstream aus dem Verilog-Template auf dem FPGA ist"""

@pytest.fixture(scope="module")
def fpga(wait_for_device):
    """Verbindet sich einmal pro Modul mit dem Pico, ohne das FPGA neu zu flashen"""
    with wait_for_device.connect_sync() as stream:
        with SyncFPGARemoteControl(stream) as control:
            yield control

@pytest.mark.parametrize("data", [b"\x5a", b"\x00\xff\xaa\x55"], ids=["1B", "4B"])
def test_spi_echo(fpga, data):
    """Sendet data und umgedreht, erwartet beide exakt zurück"""
    for sent in (data, data[::-1]):  # umgedreht: Restbytes dürfen nicht stören
        received = fpga.spi_echo(sent)
        logger.info("erwartet  (%d B): %s", len(sent), sent.hex(" "))
        logger.info("empfangen (%d B): %s", len(received), received.hex(" "))
        assert received == sent
