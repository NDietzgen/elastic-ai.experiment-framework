import time
from pathlib import Path

from vivado_runner import BuildConfig, build_bitstream, check_vivado

VIVADO = r"C:\AMDDesignTools\2026.1\Vivado\bin\vivado.bat"   # Windows-Pfad
PROJ_DIR = r"C:\Users\Nils\vivado_tmp"                       # Windows-Pfad
WORK_CWD = "/mnt/c/Users/Nils/vivado_tmp"                    # WSL-Pfad

# Basis des Vivado-Projekts (WSL-Pfad)
PROJECT_PATH = Path("/mnt/c/Users/Nils/env5_led_test/env5_led_test.srcs")

# Konfiguration für dieses Modul
CFG = BuildConfig(
    part="xc7s50ftgb196-1",
    top="top_module",
    src_dir=PROJECT_PATH / "sources_1" / "new",     # Ordner mit allen .v-Dateien
    src_xdc=PROJECT_PATH / "constrs_1" / "new" / "io.xdc",
    proj_name="env5_led_test_1", # Name des Projektes, das neu erstellt wird
    proj_dir=PROJ_DIR, # Zielordner für erstelltes Projekt (Von Vivado (TCL) genutzt)
    vivado=VIVADO,     # Pfad zu lokalem Vivado
    work_cwd=WORK_CWD, # Startordner von cmd.exe und Vivado
    jobs=4, 
)

def test_vivado_available():
    assert check_vivado(CFG), "Vivado ist nicht verfügbar!"


def test_bitstream_build():
    start = time.time()
    bit = build_bitstream(CFG)

    assert bit.exists() and bit.suffix == ".bit"
    assert CFG.xpr.exists(), f"Projektdatei fehlt: {CFG.xpr}"
    assert CFG.xpr.stat().st_mtime >= start - 2, "Projektdatei nicht frisch erzeugt"

# Weiterarbeit:

# from vivado_runner import build_bitstream, to_win

# bit = build_bitstream(CFG, output_dir=HERE / "artifacts")   # WSL-Pfad
# bit_win = to_win(bit)   
# Funktion gibt WSL-Pfad zurück, muss für Windows angepasst werden