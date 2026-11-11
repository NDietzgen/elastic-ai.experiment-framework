"""Zusammenstellen eines Vivado-Projekts aus dem festen ENV5-Kern und einem DUT-Ordner.

Der Kern (verilog_template/core/) ist für alle DUTs gleich. Ein DUT-Ordner enthält
nur dut_config.vh, die DUT-Quellen und bei DUT_TYPE "USER" dut_wrapper_user.v.

assemble_project() kopiert beides in die Struktur, die der Kern erwartet:

    <dest>/core/   Kern (top_module.v, skeleton.v, SPI, Constraints, ...)
    <dest>/user/   Inhalt des DUT-Ordners

Den Ordner <dest> kann man direkt an build.tcl oder VivadoSynthesis.synthesize()
übergeben (Top-Modul: TOP_MODULE).
"""

import shutil
from pathlib import Path

TEMPLATE_DIR = Path(__file__).parent / "verilog_template"
CORE_DIR = TEMPLATE_DIR / "core"
USER_TEMPLATE_DIR = TEMPLATE_DIR / "user"
CONSTRAINTS = CORE_DIR / "env5_constraints.xdc"
TOP = "TOP_MODULE"

# Python-Dateien (z. B. der Test im DUT-Ordner) gehören nicht ins Vivado-Projekt
_IGNORE = shutil.ignore_patterns("__pycache__", "*.py", "*.pyc")


def assemble_project(dut_dir: Path | str, dest: Path | str) -> Path:
    """Legt Kern und DUT-Ordner unter dest an und gibt dest zurück.

    dest wird vorher geleert. Liegt im DUT-Ordner eine eigene top_module.v,
    ersetzt sie die aus dem Kern. Constraints kommen immer aus dem Kern,
    .xdc-Dateien im DUT-Ordner sind nicht erlaubt.
    """
    dut_dir = Path(dut_dir)
    dest = Path(dest)

    if not (dut_dir / "dut_config.vh").is_file():
        raise FileNotFoundError(f"dut_config.vh fehlt in {dut_dir}")
    if xdcs := sorted(dut_dir.rglob("*.xdc")):
        raise ValueError(
            f"Constraints kommen aus {CORE_DIR}, keine .xdc im DUT-Ordner: {xdcs}"
        )

    if dest.exists():
        shutil.rmtree(dest)

    own_top = (dut_dir / "top_module.v").is_file()
    core_ignore = (
        shutil.ignore_patterns("__pycache__", "*.py", "*.pyc", "top_module.v")
        if own_top
        else _IGNORE
    )
    shutil.copytree(CORE_DIR, dest / "core", ignore=core_ignore)
    shutil.copytree(dut_dir, dest / "user", ignore=_IGNORE)
    return dest
