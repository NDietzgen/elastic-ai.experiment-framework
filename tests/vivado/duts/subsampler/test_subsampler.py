import logging
import time
from pathlib import Path
import pytest
from elasticai.experiment_framework.env5.sync_fpga_remote_control import (
    SyncFPGARemoteControl,
)
from elasticai.experiment_framework.vivado import (
    BuildConfig,
    build_bitstream,
    check_vivado,
    read_metrics,
)

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------- Build
VIVADO = r"C:\AMDDesignTools\2026.1\Vivado\bin\vivado.bat"   # Windows-Pfad
PROJ_DIR = r"C:\Users\Nils\vivado_tmp"                       # Windows-Pfad

# DUT-Ordner = Ordner dieser Datei (dut_config.vh + Quellen).
# Der feste Kern (verilog_template/core/) wird beim Build automatisch dazugenommen.
DUT_DIR = Path(__file__).parent

# Gemeinsame Ablage aller DUTs für Bitstreams, Reports und builds.csv (WSL-Pfad)
ARTIFACTS = Path(__file__).parents[2] / "artifacts"

CFG = BuildConfig(
    part="xc7s50ftgb196-1",
    dut_dir=DUT_DIR,
    proj_name=f"env5_{DUT_DIR.name}",  # Vivado-Projekt, wird neu erstellt
    proj_dir=PROJ_DIR,  # Zielordner für das Projekt (von Vivado/TCL genutzt)
    vivado=VIVADO,      # Pfad zu lokalem Vivado
    jobs=4,
)
OUTPUT_DIR = ARTIFACTS / CFG.proj_name
BIT_STREAM_PATH = OUTPUT_DIR / "TOP_MODULE.bit"

# -------------------------------------------------------------------------- Hardware
DUT = 2       # SEL = 2: DUT unter Test
DEC_RATE = 4  # wie in dut_wrapper_user.v
INPUTS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]  # nicht 0, das ist der Reset-Wert


# ============================================================================= Build
def test_vivado_available():
    assert check_vivado(CFG), "Vivado ist nicht verfügbar!"


def test_bitstream_build():
    start = time.time()
    bit = build_bitstream(CFG, output_dir=OUTPUT_DIR)

    assert bit.exists() and bit.suffix == ".bit"
    assert CFG.xpr.exists(), f"Projektdatei fehlt: {CFG.xpr}"
    assert CFG.xpr.stat().st_mtime >= start - 2, "Projektdatei nicht frisch erzeugt"


def test_build_metrics():
    # nutzt die Reports aus test_bitstream_build, startet Vivado nicht erneut
    metrics = read_metrics(CFG, output_dir=OUTPUT_DIR)
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


def send(fpga, value: int) -> int:
    result = fpga.predict(value.to_bytes(2, "little"), 2, dut=DUT)
    return int.from_bytes(result, "little")


"""Pro predict() geht ein 16-Bit-Wert hinein, und der aktuelle Ausgang kommt zurück.
Der Subsampler übernimmt jeden DEC_RATE-ten Wert und hält ihn bis zur nächsten
Übernahme. Wo der interne Zähler beim Start steht, ist egal"""

@pytest.mark.hardware
def test_subsampling(fpga):
    outputs = [send(fpga, v) for v in INPUTS]
    logger.info("in:  %s", INPUTS)
    logger.info("out: %s", outputs)

    # Erste Übernahme muss innerhalb der ersten DEC_RATE Werte liegen
    start = next((i for i in range(DEC_RATE) if outputs[i] == INPUTS[i]), None)
    assert start is not None, "kein Wert in den ersten DEC_RATE Aufrufen übernommen"

    # Ab da: jeder DEC_RATE-te Wert wird übernommen und bis zur nächsten Übernahme gehalten.
    # Bei start = 0 (direkt nach dem Flashen): [1, 1, 1, 1, 5, 5, 5, 5, 9, 9, 9, 9]
    expected = [INPUTS[i - (i - start) % DEC_RATE] for i in range(start, len(INPUTS))]
    assert outputs[start:] == expected
