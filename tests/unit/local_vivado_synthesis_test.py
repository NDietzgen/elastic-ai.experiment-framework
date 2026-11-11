"""LocalVivadoSynthesis ohne Vivado: Config, FPGA-Typ, Quellen kopieren."""

from pathlib import Path

import pytest

from elasticai.experiment_framework.synthesis import (
    LocalSynthesisConfig,
    LocalVivadoSynthesis,
    load_synthesis_config_from_env,
)
from elasticai.experiment_framework.vivado import BuildConfig
from elasticai.experiment_framework.vivado.runner import _stage_sources


def build_config(config: LocalSynthesisConfig, src="projects/my_dut"):
    # build_config liest nichts von der Platte, der Ordner muss nicht existieren
    return LocalVivadoSynthesis().set_config(config).build_config(src)


def test_config_from_env() -> None:
    env = {"SYNTH_PART": "xc7a35t", "SYNTH_JOBS": "8"}
    conf = load_synthesis_config_from_env(LocalSynthesisConfig, env)
    assert (conf.part, conf.jobs) == ("xc7a35t", 8)


@pytest.mark.parametrize(
    "config, part",
    [
        (LocalSynthesisConfig(part="xc7a35t"), "xc7a35t"),
        (LocalSynthesisConfig(target="env5"), "xc7s15ftgb196-2"),
        (LocalSynthesisConfig(target="env5_s50"), "xc7s50ftgb196-1"),
    ],
)
def test_part_from_config_or_target(config, part) -> None:
    assert build_config(config).part == part


def test_project_name_from_target_and_folder() -> None:
    assert build_config(LocalSynthesisConfig()).proj_name == "env5_my_dut"


def test_stage_dut_dir_adds_core(tmp_path: Path, monkeypatch) -> None:
    dut = tmp_path / "dut"
    dut.mkdir()
    (dut / "dut_config.vh").write_text('`define DUT_TYPE "USER"\n')
    (dut / "dut.v").write_text("module DUT(); endmodule\n")
    monkeypatch.setattr(BuildConfig, "work_cwd", property(lambda self: tmp_path / "w"))

    staged, xdc = _stage_sources(build_config(LocalSynthesisConfig(), dut))

    assert (staged / "core" / "top_module.v").is_file()
    assert (staged / "user" / "dut.v").is_file()
    assert xdc.is_file() and not list(staged.rglob("*.xdc"))
