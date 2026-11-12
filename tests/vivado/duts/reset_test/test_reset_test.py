import logging
import time
from pathlib import Path
import pytest
from elasticai.experiment_framework.env5.config import FPGA_RESET_DURATION_S
from elasticai.experiment_framework.env5.sync_fpga_remote_control import (
    SyncFPGARemoteControl,
)
from elasticai.experiment_framework.synthesis import (
    LocalSynthesisConfig,
    LocalVivadoSynthesis,
)
from elasticai.experiment_framework.vivado import read_metrics

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------- Build
# DUT-Ordner = Ordner dieser Datei (dut_config.vh + Quellen).
# Der feste Kern (verilog_template/core/) wird beim Build automatisch dazugenommen.
DUT_DIR = Path(__file__).parent

# Gemeinsame Ablage für Bitstreams, Reports und builds.csv
ARTIFACTS = Path(__file__).parents[2] / "artifacts"

SYNTH = LocalVivadoSynthesis().set_config(
    LocalSynthesisConfig(
        part="xc7s50ftgb196-1",  # FPGA-Typ des Boards
        vivado_path=r"C:\AMDDesignTools\2026.1\Vivado\bin\vivado.bat",  # Windows-Pfad
        proj_dir=r"C:\Users\Nils\vivado_tmp",  # Windows-Pfad, Vivado-Projekt
        jobs=4,
    )
)
CFG = SYNTH.build_config(DUT_DIR)  # Projektname env5_<Ordnername>, Pfade, Part
OUTPUT_DIR = ARTIFACTS / CFG.proj_name
BIT_STREAM_PATH = OUTPUT_DIR / f"{CFG.top}.bit"


# ============================================================================= Build
def test_vivado_available():
    assert SYNTH.check(), "Vivado ist nicht verfügbar!"


def test_bitstream_build():
    start = time.time()
    SYNTH.synthesize(DUT_DIR, OUTPUT_DIR)  # Bitstream, Reports und metrics.json

    bit = OUTPUT_DIR / f"{CFG.top}.bit"
    assert bit.exists() and bit.stat().st_mtime >= start - 2, "Bitstream nicht frisch"
    assert CFG.xpr.exists(), f"Projektdatei fehlt: {CFG.xpr}"
    assert CFG.xpr.stat().st_mtime >= start - 2, "Projektdatei nicht frisch erzeugt"


def test_build_metrics():
    # liest die Reports aus test_bitstream_build, startet Vivado nicht erneut
    metrics = read_metrics(CFG)
    print(metrics.summary())
    metrics.append_csv(ARTIFACTS / "builds.csv")

    assert "lut" in metrics.utilization, "Utilization-Report nicht ausgewertet"
    assert metrics.timing is not None and metrics.timing.wns is not None
    assert metrics.timing.met, f"Timing verletzt: {metrics.timing}"


# ========================================================================== Hardware
@pytest.mark.hardware
def test_flash(wait_for_device):
    if not BIT_STREAM_PATH.is_file():
        pytest.skip(f"{BIT_STREAM_PATH} fehlt, zuerst test_bitstream_build ausführen")
    with wait_for_device.connect_sync() as stream:
        with SyncFPGARemoteControl(stream) as control:
            control.program_fpga(BIT_STREAM_PATH)


@pytest.fixture(scope="module")
def fpga(wait_for_device):
    with wait_for_device.connect_sync() as stream:
        with SyncFPGARemoteControl(stream) as control:
            yield control


"""Bestätigung nur über die LEDs (siehe reset_test.v):
Lauflicht 0001 -> 0010 -> 0100 -> 1000, während des Resets Wechselblinken
0101 <-> 1010, danach wieder Lauflicht"""

@pytest.mark.hardware
def test_reset(fpga):
    fpga.fpga_reset()  # wirft RuntimeError, wenn die Firmware den Task ablehnt
    logger.warning(
        "Reset für %.0f s aktiv: LEDs müssen jetzt wechselblinken (0101 <-> 1010)",
        FPGA_RESET_DURATION_S,
    )
    time.sleep(FPGA_RESET_DURATION_S + 1)
    logger.warning("Reset freigegeben: LEDs müssen wieder ein Lauflicht zeigen")
