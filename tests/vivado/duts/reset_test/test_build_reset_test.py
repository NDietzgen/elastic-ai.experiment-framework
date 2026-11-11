import time
from pathlib import Path

from elasticai.experiment_framework.synthesis import (
    LocalSynthesisConfig,
    LocalVivadoSynthesis,
)
from elasticai.experiment_framework.vivado import read_metrics

# DUT-Ordner = Ordner dieser Datei (dut_config.vh + Quellen).
# Der feste Kern (verilog_template/core/) wird beim Build automatisch dazugenommen.
DUT_DIR = Path(__file__).parent

# Gemeinsame Ablage aller DUTs für Bitstreams, Reports und builds.csv (WSL-Pfad)
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
