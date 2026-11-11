"""Lokaler Vivado-Build (Vivado unter Windows, aufgerufen aus WSL) und Auswertung der Reports."""

from .reports import BuildMetrics, Power, Resource, Timing, parse_reports
from .runner import (
    BuildConfig,
    BuildError,
    build_bitstream,
    check_vivado,
    is_dut_dir,
    read_metrics,
)

__all__ = [
    "BuildConfig",
    "BuildError",
    "BuildMetrics",
    "Power",
    "Resource",
    "Timing",
    "build_bitstream",
    "check_vivado",
    "is_dut_dir",
    "parse_reports",
    "read_metrics",
]
