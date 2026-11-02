import time
from pathlib import Path

from vivado_runner import BuildConfig, build_bitstream, check_vivado, read_metrics

VIVADO = r"C:\AMDDesignTools\2026.1\Vivado\bin\vivado.bat"   # Windows-Pfad
PROJ_DIR = r"C:\Users\Nils\vivado_tmp"                       # Windows-Pfad

# Basis des Vivado-Projekts (WSL-Pfad)
PROJECT_PATH = Path("/mnt/c/Users/Nils/Downloads/led_test_template")

# Ablage für Bitstreams, Reports und metrics.json/builds.csv (WSL-Pfad)
ARTIFACTS = Path(__file__).parent / "artifacts"

# Konfiguration für dieses Modul
CFG = BuildConfig(
    part="xc7s50ftgb196-1",
    top="TOP_MODULE",  # Modulname aus dem Verilog
    src_dir=PROJECT_PATH,  # Ordner mit allen .v/.sv/.mem-Dateien
    src_xdc=PROJECT_PATH / "env5_constraints.xdc",
    proj_name="env5_led_test_67", # Name des Projektes, das neu erstellt wird
    proj_dir=PROJ_DIR, # Zielordner für erstelltes Projekt (Von Vivado (TCL) genutzt)
    vivado=VIVADO,     # Pfad zu lokalem Vivado
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


# Weiterarbeit:

# bit = build_bitstream(CFG, output_dir=ARTIFACTS / CFG.proj_name)
# metrics = read_metrics(CFG, output_dir=ARTIFACTS / CFG.proj_name)
# metrics.append_csv(ARTIFACTS / "builds.csv")
