import logging
from typing import override

from ..remote_control.io_stream import IOStream
from ..remote_control.remote_control import RemoteControl
from .config import (
    BYTE_ORDER,
    DEFAULT_DUT,
    HEADER_BYTES,
    TaskDefinitionIds,
)
from .tasks_registry import (
    FPGAInitTask,
    FPGAWriteToFlashTask,
    PredictDutTask,
    SimpleTask,
)

logger = logging.getLogger(__name__)


class FPGARemoteControl(RemoteControl):
    def __init__(self, device: IOStream):
        super().__init__(device)
        self._chunk_size = 0

    @override
    async def initialize(self):
        task = FPGAInitTask(TaskDefinitionIds.FPGA_INIT)

        await self._run_task(task)
        chunk_size = int.from_bytes(task.received_data[0])
        logger.info("chunk_size = %d", chunk_size)

        self._chunk_size = chunk_size

    async def fpga_power_on(self):
        task = SimpleTask(TaskDefinitionIds.FPGA_POWER_ON)
        return await self._run_task(task)

    async def fpga_power_off(self):
        task = SimpleTask(TaskDefinitionIds.FPGA_POWER_OFF)
        return await self._run_task(task)

    async def fpga_clear_flash(self):
        task = SimpleTask(TaskDefinitionIds.FPGA_CLEAR_FLASH)
        return await self._run_task(task)

    async def read_skeleton_id(self) -> str:
        """Liest die 16-Byte-Skeleton-ID als Hex"""
        task = SimpleTask(TaskDefinitionIds.FPGA_READ_SKELETON_ID)

        await self._run_task(task)

        return task.result.hex()

    async def predict(
        self,
        data: bytes,
        result_size: int,
    ) -> bytes:
        task = SimpleTask(
            TaskDefinitionIds.FPGA_PREDICT,
            result_size.to_bytes(1, BYTE_ORDER) + data,
        )

        await self._run_task(task)

        return task.result

    async def read_dut_header(self, dut: int = DEFAULT_DUT) -> str:
        """Liest den 32-Bit-Header des DUT (Verilog-Template) als Hex"""
        task = SimpleTask(TaskDefinitionIds.FPGA_READ_DUT_HEADER, bytes([dut]))

        await self._run_task(task)

        return task.result[-HEADER_BYTES:].hex()

    async def predict_dut(
        self,
        data: bytes,
        result_size: int,
        dut: int = DEFAULT_DUT,
    ) -> bytes:
        """Schreibt data ins DUT (Verilog-Template), startet es und liest result_size Bytes"""
        task = PredictDutTask(TaskDefinitionIds.FPGA_PREDICT_DUT, data, result_size, dut)

        await self._run_task(task)

        return task.result

    async def upload_bitstream(
        self,
        flash_sector: int,
        path_to_bitstream: str,
    ):
        with open(path_to_bitstream, "rb") as f:
            bitstream = f.read()

        task = FPGAWriteToFlashTask(
            task_def_id=TaskDefinitionIds.FPGA_WRITE_TO_FLASH,
            sector=flash_sector,
            data=bitstream,
            chunk_size=self._chunk_size,
        )

        await self._run_task(task)
