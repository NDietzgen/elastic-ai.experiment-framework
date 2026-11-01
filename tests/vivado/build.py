# startet Synthese, Implementierung und Bitstream-Generierung

import subprocess
import sys

import vivado_config as cfg

result = subprocess.run(
    [
        "cmd.exe", "/c", cfg.VIVADO,
        "-mode", "batch",
        "-source", cfg.to_win(cfg.HERE / "build.tcl"),
        "-tclargs",
        "-part", cfg.PART,
        "-top", cfg.TOP,
        "-proj_name", cfg.PROJ_NAME,
        "-proj_dir", cfg.PROJ_DIR,
        "-src_dir", cfg.to_win(cfg.SRC_V),
        "-src_xdc", cfg.to_win(cfg.SRC_XDC),
    ],
    capture_output=True,
    text=True,
    cwd=cfg.WORK_CWD,
)
print(result.stdout, result.stderr)

if result.returncode != 0 or "ERROR:" in result.stdout:
    print(f"Vivado fehlgeschlagen: Exit-Code {result.returncode}")
    sys.exit(1)

print("Vivado-Prozess erfolgreich beendet.")

