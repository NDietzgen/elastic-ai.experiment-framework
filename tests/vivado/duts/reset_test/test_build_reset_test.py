import time
from pathlib import Path

from elasticai.experiment_framework.vivado import (
    BuildConfig,
    build_bitstream,
    check_vivado,
    read_metrics,
)

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


def test_vivado_available():
    assert check_vivado(CFG), "Vivado ist nicht verfügbar!"


def test_bitstream_build():
    start = time.time()
    bit = build_bitstream(CFG, output_dir=ARTIFACTS / CFG.proj_name)

    assert bit.exists() and bit.suffix == ".bit"
    assert CFG.xpr.exists(), f"Projektdatei fehlt: {CFG.xpr}"
    assert CFG.xpr.stat().st_mtime >= start - 2, "Projektdatei nicht frisch erzeugt"


def test_build_metrics():
    # nutzt die Reports aus test_bitstream_build, startet Vivado nicht erneut
    metrics = read_metrics(CFG, output_dir=ARTIFACTS / CFG.proj_name)
    print(metrics.summary())
    metrics.append_csv(ARTIFACTS / "builds.csv")

    assert "lut" in metrics.utilization, "Utilization-Report nicht ausgewertet"
    assert metrics.timing is not None and metrics.timing.wns is not None
    assert metrics.timing.met, f"Timing verletzt: {metrics.timing}"
