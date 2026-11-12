"""Lokale Synthese mit Vivado unter Windows, aufgerufen aus WSL.

Gleiche Schnittstelle wie VivadoSynthesis (Remote über SSH). Die eigentliche Arbeit
macht das Paket elasticai.experiment_framework.vivado.

    synth = LocalVivadoSynthesis().set_config(LocalSynthesisConfig(part="xc7s50"))
    synth.synthesize("tests/vivado/duts/subsampler", "build/subsampler")

src_dir ist ein DUT-Ordner des Verilog-Templates (mit dut_config.vh, Kern kommt
dazu) oder ein beliebiger Ordner mit HDL-Quellen. In out_path landen <top>.bit,
die Reports und metrics.json.
"""

import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import Self, override

from elasticai.experiment_framework.env5.template_project import TOP
from elasticai.experiment_framework.vivado import (
    BuildConfig,
    build_bitstream,
    check_vivado,
    read_metrics,
)

from .synthesis import (
    SynthesisConfig,
    SynthesisStrategy,
    TargetPlatforms,
    load_synthesis_config_from_env,
)
from .vivado_synthesis import _fpga_model_for_platform


@dataclass(frozen=True)
class LocalSynthesisConfig(SynthesisConfig):
    """Alle Felder lassen sich über SYNTH_<FELD> setzen, z. B. SYNTH_PART."""

    vivado_path: str = r"C:\AMDDesignTools\2026.1\Vivado\bin\vivado.bat"  # Windows
    proj_dir: str = r"C:\Users\Nils\vivado_tmp"  # Windows, für Vivado-Projekte
    part: str = ""  # FPGA-Typ, z. B. "xc7s50ftgb196-1"; leer = aus target
    top: str = TOP
    jobs: int = 4


class LocalVivadoSynthesis(SynthesisStrategy[LocalSynthesisConfig]):
    def __init__(self) -> None:
        self._config: LocalSynthesisConfig | None = None

    @override
    def get_config(self) -> LocalSynthesisConfig:
        if self._config is None:
            self._config = load_synthesis_config_from_env(LocalSynthesisConfig)
        return self._config

    @override
    def set_config(self, config: SynthesisConfig) -> Self:
        fields = dataclasses.asdict(config)
        self._config = dataclasses.replace(self.get_config(), **fields)
        return self

    def build_config(self, src_dir: Path | str) -> BuildConfig:
        """BuildConfig des vivado-Pakets, Projektname "<target>_<Ordnername>"."""
        config = self.get_config()
        src_dir = Path(src_dir).absolute()
        default_part = _fpga_model_for_platform[TargetPlatforms(config.target)]
        return BuildConfig(
            part=config.part or default_part,
            dut_dir=src_dir,
            proj_name=f"{config.target}_{src_dir.name}",
            proj_dir=config.proj_dir,
            vivado=config.vivado_path,
            jobs=config.jobs,
            top=config.top,
        )

    def check(self) -> bool:
        """True, wenn Vivado unter vivado_path startet."""
        return check_vivado(self.build_config("."))

    @override
    def synthesize(
        self, src_dir: Path | str, out_path: Path | str | None = None
    ) -> Path:
        src_dir = Path(src_dir)
        out_path = Path(out_path or src_dir.absolute().parent / "synthesis_result")
        cfg = self.build_config(src_dir)
        build_bitstream(cfg, output_dir=out_path)
        read_metrics(cfg, output_dir=out_path)  # Reports + metrics.json dazulegen
        return out_path
