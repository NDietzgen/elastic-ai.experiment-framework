"""Auswertung der Vivado-Reports, die build.tcl nach <projekt>/reports schreibt."""

import csv
import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

# Zeilen aus report_utilization, die übernommen werden (Site Type -> Schlüssel)
UTILIZATION_KEYS = {
    "Slice LUTs": "lut",
    "LUT as Logic": "lut_logic",
    "LUT as Memory": "lut_memory",
    "Slice Registers": "ff",
    "Slice": "slice",
    "Block RAM Tile": "bram",
    "DSPs": "dsp",
    "Bonded IOB": "io",
    "BUFGCTRL": "bufg",
}

REPORT_FILES = (
    "utilization.rpt",
    "utilization_hier.rpt",
    "timing_summary.rpt",
    "power.rpt",
    "metrics.txt",
)


@dataclass
class Resource:
    used: float
    available: float | None
    util_percent: float | None


@dataclass
class Timing:
    wns: float | None  # Worst Negative Slack (Setup), ns
    tns: float | None  # Total Negative Slack (Setup), ns
    whs: float | None  # Worst Hold Slack, ns
    ths: float | None  # Total Hold Slack, ns
    tpws: float | None  # Total Pulse Width Slack, ns

    @property
    def met(self) -> bool:
        return (self.wns is None or self.wns >= 0) and (
            self.whs is None or self.whs >= 0
        )


@dataclass
class Power:
    total_w: float | None
    dynamic_w: float | None
    static_w: float | None


@dataclass
class BuildMetrics:
    name: str
    report_dir: Path
    utilization: dict[str, Resource] = field(default_factory=dict)
    timing: Timing | None = None
    power: Power | None = None
    build_time_s: float | None = None
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["report_dir"] = str(self.report_dir)
        if self.timing is not None:
            d["timing"]["met"] = self.timing.met
        return d

    def to_row(self) -> dict:
        """Flache Darstellung, z. B. für eine CSV-Zeile pro Build."""
        row = {
            "timestamp": self.timestamp,
            "name": self.name,
            "build_time_s": self.build_time_s,
        }
        for key, res in self.utilization.items():
            row[f"{key}_used"] = res.used
            row[f"{key}_util_percent"] = res.util_percent
        if self.timing is not None:
            row.update(asdict(self.timing))
            row["timing_met"] = self.timing.met
        if self.power is not None:
            row.update({f"power_{k}": v for k, v in asdict(self.power).items()})
        return row

    def save(self, output_dir: Path | str, copy_reports: bool = True) -> Path:
        """Schreibt metrics.json (und optional die Roh-Reports) nach output_dir."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        if copy_reports:
            for name in REPORT_FILES:
                src = self.report_dir / name
                if src.exists() and src.parent.resolve() != output_dir.resolve():
                    shutil.copy2(src, output_dir / name)
        path = output_dir / "metrics.json"
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))
        return path

    def append_csv(self, csv_path: Path | str) -> Path:
        """Hängt die Metriken als Zeile an eine CSV an (Header wird bei Bedarf angelegt)."""
        csv_path = Path(csv_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        row = self.to_row()
        write_header = not csv_path.exists() or csv_path.stat().st_size == 0
        with csv_path.open("a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(row), extrasaction="ignore")
            if write_header:
                writer.writeheader()
            writer.writerow(row)
        return csv_path

    def summary(self) -> str:
        lines = [f"{self.name} (Build-Dauer: {self.build_time_s} s)"]
        for key, r in self.utilization.items():
            avail = f"{r.available:g}" if r.available is not None else "-"
            lines.append(f"  {key:<11} {r.used:>8g} / {avail:>8} ({r.util_percent}%)")
        if self.timing:
            t = self.timing
            lines.append(
                f"  Timing: WNS={t.wns} ns, TNS={t.tns} ns, WHS={t.whs} ns, "
                f"THS={t.ths} ns -> {'erfüllt' if t.met else 'VERLETZT'}"
            )
        if self.power:
            lines.append(f"  Leistung: {self.power.total_w} W gesamt")
        return "\n".join(lines)


def _to_float(value: str) -> float | None:
    value = value.strip().rstrip("*").replace("<", "")
    try:
        return float(value)
    except ValueError:
        return None


def parse_utilization(text: str) -> dict[str, Resource]:
    """Liest die Tabellen aus report_utilization; Spalten werden über den Header gefunden,
    damit es mit und ohne 'Prohibited'-Spalte (je nach Vivado-Version) funktioniert."""
    result: dict[str, Resource] = {}
    header: list[str] | None = None
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0] == "Site Type":
            header = cells
            continue
        if header is None or len(cells) != len(header):
            continue
        name = cells[0].rstrip("*").strip()
        key = UTILIZATION_KEYS.get(name)
        if key is None or key in result:
            continue
        col = dict(zip(header, cells))
        used = _to_float(col.get("Used", ""))
        if used is None:
            continue
        result[key] = Resource(
            used=used,
            available=_to_float(col.get("Available", "")),
            util_percent=_to_float(col.get("Util%", "")),
        )
    return result


def parse_key_values(text: str) -> dict[str, float | None]:
    values = {}
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            values[k.strip()] = _to_float(v)
    return values


def parse_power(text: str) -> Power:
    def find(label: str) -> float | None:
        m = re.search(rf"\|\s*{re.escape(label)}\s*\|\s*([^|]+)\|", text)
        return _to_float(m.group(1)) if m else None

    return Power(
        total_w=find("Total On-Chip Power (W)"),
        dynamic_w=find("Dynamic (W)"),
        static_w=find("Device Static (W)"),
    )


def parse_reports(report_dir: Path | str, name: str = "") -> BuildMetrics:
    """Liest alle Reports aus report_dir, ohne Vivado zu starten."""
    report_dir = Path(report_dir)

    def read(file: str) -> str | None:
        p = report_dir / file
        return p.read_text(errors="replace") if p.exists() else None

    util = read("utilization.rpt")
    power = read("power.rpt")
    kv_text = read("metrics.txt")
    kv = parse_key_values(kv_text) if kv_text else {}

    timing = None
    if kv_text:
        timing = Timing(**{k: kv.get(k) for k in ("wns", "tns", "whs", "ths", "tpws")})

    return BuildMetrics(
        name=name or report_dir.parent.name,
        report_dir=report_dir,
        utilization=parse_utilization(util) if util else {},
        timing=timing,
        power=parse_power(power) if power else None,
        build_time_s=kv.get("build_time_s"),
    )
