import atexit
import logging
import readline
import shlex
import time
from pathlib import Path
from typing import override

import click

from ..remote_control.devices import _DeviceSpec, _SerialDevice, probe_for_devices
from ..remote_control.io_stream import IOStream
from ..remote_control.logging_config import configure_logging
from ..remote_control.sync_remote_control import (
    SyncRemoteControl,
)
from .config import (
    BYTE_ORDER,
    DEFAULT_DUT,
    FPGA_RESET_DURATION_S,
    HEADER_BYTES,
    TaskDefinitionIds,
)
from .tasks_registry import (
    FPGAInitTask,
    FPGAWriteToFlashTask,
    PredictDutTask,
    SimpleTask,
)

BYTE_STREAM_PATH = Path("tests/fpga/env5_top_reconfig.bin")
SPECS: set[_DeviceSpec] = {
    _DeviceSpec(10, 11914, "env5"),
}
HISTORY_FILE = Path.home() / ".local" / "state" / "eaixp" / "fpga-history"


logger = logging.getLogger(__name__)


class SyncFPGARemoteControl(SyncRemoteControl):
    def __init__(self, device: IOStream):
        super().__init__(device)
        self._chunk_size = 0

    @override
    def initialize(self, need_ack=False, has_crc=False):
        task = FPGAInitTask(TaskDefinitionIds.FPGA_INIT)

        self._run_task(task)
        chunk_size = int.from_bytes(task.received_data[0])
        logger.info("chunk_size = %d", chunk_size)

        self._chunk_size = chunk_size

    def fpga_power_on(self, need_ack: bool = False, has_crc: bool = False):
        task = SimpleTask(
            TaskDefinitionIds.FPGA_POWER_ON,
            need_ack=need_ack,
            has_crc=has_crc,
        )
        return self._run_task(task)

    def fpga_power_off(self, need_ack: bool = False, has_crc: bool = False):
        task = SimpleTask(
            TaskDefinitionIds.FPGA_POWER_OFF,
            need_ack=need_ack,
            has_crc=has_crc,
        )
        return self._run_task(task)

    def fpga_reset(self, need_ack: bool = False, has_crc: bool = False):
        task = SimpleTask(
            TaskDefinitionIds.FPGA_RESET,
            need_ack=need_ack,
            has_crc=has_crc,
        )
        return self._run_task(task)

    def read_skeleton_id(
        self,
        need_ack: bool = False,
        has_crc: bool = False,
    ) -> str:
        """Liest die 16-Byte-Skeleton-ID als Hex"""
        task = SimpleTask(
            TaskDefinitionIds.FPGA_READ_SKELETON_ID,
            need_ack=need_ack,
            has_crc=has_crc,
        )

        self._run_task(task)
        return task.result.hex()

    def predict(
        self,
        data: bytes,
        result_size: int,
        need_ack: bool = False,
        has_crc: bool = False,
    ) -> bytes:
        task = SimpleTask(
            TaskDefinitionIds.FPGA_PREDICT,
            result_size.to_bytes(1, BYTE_ORDER) + data,
            need_ack=need_ack,
            has_crc=has_crc,
        )

        self._run_task(task)
        return task.result

    def read_dut_header(
        self,
        dut: int = DEFAULT_DUT,
        need_ack: bool = False,
        has_crc: bool = False,
    ) -> str:
        """Liest den 32-Bit-Header des DUT (Verilog-Template) als Hex"""
        task = SimpleTask(
            TaskDefinitionIds.FPGA_READ_DUT_HEADER,
            bytes([dut]),
            need_ack=need_ack,
            has_crc=has_crc,
        )

        self._run_task(task)
        return task.result[-HEADER_BYTES:].hex()

    def clear_flash(
        self,
        need_ack: bool = False,
        has_crc: bool = False,
    ):
        task = SimpleTask(
            TaskDefinitionIds.FPGA_CLEAR_FLASH,
            data=b"a",
            need_ack=need_ack,
            has_crc=has_crc,
        )

        self._run_task(task)

    def predict_dut(
        self,
        data: bytes,
        result_size: int,
        dut: int = DEFAULT_DUT,
        need_ack: bool = False,
        has_crc: bool = False,
    ) -> bytes:
        """Schreibt data ins DUT (Verilog-Template), startet es und liest result_size Bytes"""
        """Daten und Ergebnis sind 16-Bit-Worte (Little Endian) ab Adresse 0"""
        task = PredictDutTask(
            TaskDefinitionIds.FPGA_PREDICT_DUT,
            data,
            result_size,
            dut,
            need_ack=need_ack,
            has_crc=has_crc,
        )

        self._run_task(task)
        return task.result

    def spi_echo(
        self,
        data: bytes,
        need_ack: bool = False,
        has_crc: bool = False,
    ) -> bytes:
        """Schickt data per SPI ans FPGA und gibt die Echo-Antwort zurück"""
        task = SimpleTask(
            TaskDefinitionIds.FPGA_SPI_ECHO,
            data,
            need_ack=need_ack,
            has_crc=has_crc,
        )

        self._run_task(task)
        return task.result

    def upload_bitstream(
        self,
        flash_sector: int,
        path_to_bitstream: str,
        need_ack: bool = False,
        has_crc: bool = False,
    ):
        with open(path_to_bitstream, "rb") as f:
            bitstream = f.read()

        task = FPGAWriteToFlashTask(
            task_def_id=TaskDefinitionIds.FPGA_WRITE_TO_FLASH,
            sector=flash_sector,
            data=bitstream,
            chunk_size=self._chunk_size,
            need_ack=need_ack,
            has_crc=has_crc,
        )

        self._run_task(task)

    def program_fpga(
        self,
        path_to_bitstream: str | Path,
        flash_sector: int = 0,
        need_ack: bool = True,
        has_crc: bool = False,
        boot_delay: float = 1.0,
    ):
        """Löscht den Flash, schreibt den Bitstream und startet das FPGA neu."""
        self.fpga_power_off()
        self.clear_flash()
        self.upload_bitstream(
            flash_sector=flash_sector,
            path_to_bitstream=path_to_bitstream,
            need_ack=need_ack,
            has_crc=has_crc,
        )
        self.fpga_power_off()
        self.fpga_power_on()
        time.sleep(boot_delay)  # FPGA braucht Zeit zum Booten aus dem Flash


@click.group
def fpga():
    pass


def wait_for_device(timeout: float = 15):
    start = time.monotonic()

    while time.monotonic() - start < timeout:
        devices = probe_for_devices(SPECS)

        if devices:
            time.sleep(0.5)
            return devices[0]

        time.sleep(0.5)

    raise click.ClickException("Pico did not re-enumerate")


@fpga.command("shell")
@click.option("--debug", is_flag=True)
@click.option("--raw", "show_raw", is_flag=True)
@click.option("-p", "--port", default="auto")
def fpga_shell_command(port, debug, show_raw):
    configure_logging(
        level=logging.DEBUG if debug else logging.INFO,
        show_raw=show_raw,
    )
    if port == "auto":
        device = wait_for_device()

    else:
        device = _SerialDevice(port)

    with device.connect_sync() as stream:
        with SyncFPGARemoteControl(stream) as control:
            run_fpga_shell(control)


def setup_readline() -> None:

    readline.parse_and_bind("set editing-mode emacs")
    readline.parse_and_bind('"\\e[A": previous-history')
    readline.parse_and_bind('"\\e[B": next-history')

    readline.set_history_length(1000)

    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    try:
        readline.read_history_file(HISTORY_FILE)
    except FileNotFoundError:
        pass

    atexit.register(readline.write_history_file, HISTORY_FILE)


def run_fpga_shell(control):
    setup_readline()
    click.echo("FPGA interactive shell. Type 'exit' to quit.")

    while True:
        try:
            line = input("fpga>")
        except (EOFError, KeyboardInterrupt):
            break

        if line.strip() in {"exit", "quit"}:
            break

        try:
            args = shlex.split(line)

            fpga.main(
                args=args,
                prog_name="fpga",
                obj=control,
                standalone_mode=False,
            )
        except click.ClickException as exc:
            exc.show()
        except Exception as exc:
            print(exc)


def communication_options(func):
    func = click.option(
        "--ack",
        "--need_ack",
        "need_ack",
        is_flag=True,
        help="Request acknowledgements.",
    )(func)
    func = click.option(
        "--crc",
        "has_crc",
        is_flag=True,
        help="Enable CRC checks.",
    )(func)
    return func


@fpga.command("power-off")
@communication_options
@click.pass_obj
def power_off(control, need_ack, has_crc):
    control.fpga_power_off(
        need_ack=need_ack,
        has_crc=has_crc,
    )


@fpga.command("power-on")
@communication_options
@click.pass_obj
def power_on(control, need_ack, has_crc):
    control.fpga_power_on(
        need_ack=need_ack,
        has_crc=has_crc,
    )


@fpga.command("reset")
@communication_options
@click.pass_obj
def reset(control, need_ack, has_crc):
    """Hält die FPGA-Logik über GPIO13 (RSTN) kurz im Reset, ohne das FPGA abzuschalten"""
    control.fpga_reset(
        need_ack=need_ack,
        has_crc=has_crc,
    )
    click.echo(f"FPGA reset active for {FPGA_RESET_DURATION_S:.0f}s ...")
    time.sleep(FPGA_RESET_DURATION_S)
    click.echo("FPGA reset released.")


@fpga.command("clear-flash")
@communication_options
@click.pass_obj
def clear_flash(control, need_ack, has_crc):
    control.clear_flash(
        need_ack=need_ack,
        has_crc=has_crc,
    )
    click.echo("Flash cleared")


@fpga.command("read-skeleton-id")
@communication_options
@click.pass_obj
def read_skeleton_id(control, need_ack, has_crc):
    """16-Byte-Skeleton-ID lesen"""
    result = control.read_skeleton_id(
        need_ack=need_ack,
        has_crc=has_crc,
    )
    click.echo(f"Skeleton ID: {result}")


@fpga.command("predict")
@click.argument("data")
@click.argument("length", type=int)
@communication_options
@click.pass_obj
def predict(control, data, length, need_ack, has_crc):
    """Predict über die Standard-Middleware"""
    result = control.predict(
        bytes.fromhex(data.removeprefix("0x")),
        length,
        need_ack=need_ack,
        has_crc=has_crc,
    )
    click.echo(f"Predict result: {result}")


@fpga.command("read-dut-header")
@click.option("--dut", type=int, default=DEFAULT_DUT, show_default=True)
@communication_options
@click.pass_obj
def read_dut_header(control, dut, need_ack, has_crc):
    """32-Bit-DUT-Header lesen (Verilog-Template)"""
    result = control.read_dut_header(
        dut=dut,
        need_ack=need_ack,
        has_crc=has_crc,
    )
    click.echo(f"DUT header: {result}")


@fpga.command("upload")
@click.argument("flash_sector", type=int)
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@communication_options
@click.pass_obj
def upload(control, flash_sector, path, need_ack, has_crc):
    control.upload_bitstream(
        flash_sector=flash_sector,
        path_to_bitstream=path,
        need_ack=need_ack,
        has_crc=has_crc,
    )
    click.echo("Upload was successful")


@fpga.command("predict-dut")
@click.argument("data")
@click.argument("length", type=int)
@click.option("--dut", type=int, default=DEFAULT_DUT, show_default=True)
@communication_options
@click.pass_obj
def predict_dut(control, data, length, dut, need_ack, has_crc):
    """Daten ins DUT schreiben, Test starten, Ergebnis lesen (Verilog-Template)"""
    result = control.predict_dut(
        bytes.fromhex(data.removeprefix("0x")),
        length,
        dut=dut,
        need_ack=need_ack,
        has_crc=has_crc,
    )
    click.echo(f"Predict result: {result}")


@fpga.command("echo")
@click.argument("data")
@communication_options
@click.pass_obj
def echo(control, data, need_ack, has_crc):
    """Schickt Daten ans FPGA und zeigt das Echo"""
    try:
        sent = bytes.fromhex(data.removeprefix("0x"))
    except ValueError as exc:
        raise click.BadParameter(f"kein gültiger Hex-Wert: {data}") from exc
    if not sent:
        raise click.BadParameter("mindestens ein Byte angeben")

    received = control.spi_echo(sent, need_ack=need_ack, has_crc=has_crc)
    click.echo(f"gesendet : {sent.hex(' ')}")
    click.echo(f"empfangen: {received.hex(' ')}")
    click.echo("OK" if received == sent else "MISMATCH")
