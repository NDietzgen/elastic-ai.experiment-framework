"""Baut ein Vivado-Projekt aus ENV5-Kern und DUT-Ordner: <dest>/core/ + <dest>/user/"""

import shutil
from pathlib import Path

TEMPLATE_DIR = Path(__file__).parent / "verilog_template"
CORE_DIR = TEMPLATE_DIR / "core"
USER_TEMPLATE_DIR = TEMPLATE_DIR / "user"
CONSTRAINTS = CORE_DIR / "env5_constraints.xdc"
TOP = "TOP_MODULE"

_IGNORE = shutil.ignore_patterns("__pycache__", "*.py", "*.pyc")


def assemble_project(dut_dir: Path | str, dest: Path | str) -> Path:
    """Leert dest, kopiert Kern und DUT-Ordner hinein und gibt dest zurück.
    Eine top_module.v im DUT-Ordner ersetzt die aus dem Kern, .xdc ist dort verboten"""
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
