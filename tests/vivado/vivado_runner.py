import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).parent


def to_win(p):
    return subprocess.check_output(["wslpath", "-w", str(p)], text=True).strip()


def to_wsl(p):
    return Path(subprocess.check_output(["wslpath", "-u", str(p)], text=True).strip())


@dataclass
class BuildConfig:
    part: str
    top: str
    src_dir: Path      # WSL-Pfad, Ordner mit allen .v/.sv-Dateien
    src_xdc: Path      # WSL-Pfad
    proj_name: str
    proj_dir: str      # Windows-Pfad, z. B. r"C:\Users\Nils\vivado_tmp"
    vivado: str        # Windows-Pfad zur vivado.bat
    work_cwd: str      # WSL-Pfad, z. B. "/mnt/c/Users/Nils/vivado_tmp"
    jobs: int 

    @property
    def proj_path(self) -> Path:
        return to_wsl(self.proj_dir) / self.proj_name

    @property
    def xpr(self) -> Path:
        return self.proj_path / f"{self.proj_name}.xpr"

    @property
    def impl_dir(self) -> Path:
        return self.proj_path / f"{self.proj_name}.runs" / "impl_1"


class BuildError(RuntimeError):
    """Build fehlgeschlagen. Das Vivado-Log steht in .log."""

    def __init__(self, message, log=""):
        super().__init__(message)
        self.log = log


def run_vivado(cfg: BuildConfig, *args):
    Path(cfg.work_cwd).mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        ["cmd.exe", "/c", cfg.vivado, *args],
        capture_output=True,
        text=True,
        cwd=cfg.work_cwd,
    )


def check_vivado(cfg: BuildConfig) -> bool:
    result = run_vivado(cfg, "-version")
    # Vivado liefert bei -version Returncode 1, deshalb zählt nur die Versionszeile
    return "vivado v" in result.stdout.lower()


def build_bitstream(cfg: BuildConfig, output_dir: Path | None = None) -> Path:
    """Baut das Projekt bis zum Bitstream und gibt den Pfad (WSL) zur .bit-Datei zurück."""
    start = time.time() - 2

    result = run_vivado(
        cfg,
        "-mode", "batch",
        "-source", to_win(HERE / "build.tcl"),
        "-tclargs",
        "-part", cfg.part,
        "-top", cfg.top,
        "-proj_name", cfg.proj_name,
        "-proj_dir", cfg.proj_dir,
        "-src_dir", to_win(cfg.src_dir),
        "-src_xdc", to_win(cfg.src_xdc),
        "-jobs", str(cfg.jobs),
    )
    log = result.stdout + result.stderr

    if result.returncode != 0 or "ERROR:" in result.stdout:
        raise BuildError(f"Vivado-Build fehlgeschlagen (Exit-Code {result.returncode})", log)

    bits = sorted(cfg.impl_dir.glob("*.bit"), key=lambda p: p.stat().st_mtime)
    if not bits:
        raise BuildError(f"Keine .bit-Datei in {cfg.impl_dir}", log)

    bit = bits[-1]
    if bit.stat().st_mtime < start:
        raise BuildError(f"Bitstream ist veraltet: {bit}", log)

    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        bit = Path(shutil.copy2(bit, output_dir / bit.name))

    return bit
