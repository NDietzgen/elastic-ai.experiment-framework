#include "task_definitions_pico.h"

#include "embedded_fpga_bitstream.h"
#include "hardware_functions/Middleware.h"
#include "config/config.h"
#include "eai/flash/Flash.h"
#include "hardware_functions/Fpga.h"

#include "eai/hal/EnV5HwConfiguration.h"
#include "eai/hal/EnV5HwController.h"
#include "pico/time.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>

#define USER_LOGIC_START_ADDRESS 18
#define COMPUTE_BYTE 16

static void startCompute(void)
{
    uint8_t cmd[1] = {0x01};
    FpgaMiddleware *fpga = Config_getFpgaMiddleware();
    FpgaMiddleware_write(fpga, cmd, COMPUTE_BYTE, 1);
}
static void stopCompute(void)
{
    uint8_t cmd[1] = {0x00};
    FpgaMiddleware *fpga = Config_getFpgaMiddleware();
    FpgaMiddleware_write(fpga, cmd, COMPUTE_BYTE, 1);
}

static uint8_t eraseFlash(flashConfiguration_t *flashConfig,
    uint32_t startAddress,
    uint32_t length)
{
    if (length == 0)
        return 0;

    const uint32_t sectorSize = flashGetBytesPerSector(flashConfig);

    // auf Sektorgrenzen aus-/aufrunden
    uint32_t first = startAddress - (startAddress % sectorSize);
    uint32_t end   = startAddress + length;                       
    uint32_t last  = ((end + sectorSize - 1) / sectorSize) * sectorSize;

    for (uint32_t addr = first; addr < last; addr += sectorSize)
    {
        uint8_t error_code = flashEraseSector(flashConfig, addr);
        if (error_code != 0)
        {
            return error_code;   
        }
    }
    return 0;
}


uint32_t flashWriteBitstream(
    flashConfiguration_t *flashConfig,
    const uint8_t *bitstream,
    uint32_t size)
{
    uint32_t written = 0;
    uint32_t address = 0;

    const uint32_t pageSize = flashConfig->bytesPerPage;

    // erase the flash before writing the bitstream with length of bitstream
    eraseFlash(flashConfig, 0, size);

    while (written < size)
    {
        uint32_t remaining = size - written;
        uint32_t bytesToWrite = remaining < pageSize ? remaining : pageSize;

        uint32_t result = flashWritePage(
            flashConfig,
            address,
            (uint8_t *)&bitstream[written],
            bytesToWrite);

        if (result != bytesToWrite)
        {
            printf("Flash write failed at address 0x%08lx\n", address);
            return written;
        }

        written += bytesToWrite;
        address += bytesToWrite;
    }

    return written;
}

uint32_t count_flash_ones(TaskContext *task_context, uint32_t length)
{
    data_t data_buffer = {0};
    data_buffer.length = length;

    task_context->task_services.send_data(&task_context->task_services, 0, (uint8_t *)&data_buffer.length, 4, false);
    uint32_t read_bytes = flashReadData(&flashConfig, 0, &data_buffer);
    task_context->task_services.send_data(&task_context->task_services, 0, (uint8_t *)&read_bytes, 4, false);

    // simple id
    uint32_t ones = 0;

    for (size_t i = 0; i < data_buffer.length; i++)
    {
        uint8_t byte = data_buffer.data[i];

        for (int bit = 0; bit < 8; bit++)
        {
            ones += (byte >> bit) & 1;
        }
    }

    return ones;
}

typedef struct
{
    uint8_t frames[3][9];
} AverageFramesStruct;
// ---------------------------------------------------------------

void fast_setup_hardware_init(TaskContext *task_context)
{
    hardware_init(task_context);
}

void fast_setup_fpga_power_on(TaskContext *task_context)
{
    fpga_power_on(task_context);
}

void fast_setup_fpga_power_off(TaskContext *task_context)
{
    fpga_power_off(task_context);
}

void fast_setup_read_skeleton_id(TaskContext *task_context)
{
    read_skeleton_id(task_context);
}

// ---------------------------------------------------------------
void hardware_init(TaskContext *task_context)
{
    if (flashSpi.spiInstance == NULL)
    {
        init_hardware();
    }
    uint16_t value = flashConfig.bytesPerPage;

    uint8_t data[2] = {
        (uint8_t)(value >> 8),
        (uint8_t)(value & 0xFF)};

    task_context->task_services.send_data(&task_context->task_services, 0, data, 2, false);
    task_context->task_services.send_return(&task_context->task_services, 0, 0, false);
}

void fpga_power_on(TaskContext *task_context)
{
    Fpga *fpga = Config_getFpga();
    Fpga_powerOn(fpga);
    task_context->task_services.send_return(&task_context->task_services, 0, 0, false);
}

void fpga_power_off(TaskContext *task_context)
{
    Fpga *fpga = Config_getFpga();
    Fpga_powerOff(fpga);
    task_context->task_services.send_return(&task_context->task_services, 0, 0, false);
}

void erase_fpga_flash(TaskContext *task_context)
{
    uint32_t amount_to_delete = 550000;
    task_context->task_services.send_data(&task_context->task_services, 0, (uint8_t *)&flashConfig, 1, false);

    uint8_t error_code = eraseFlash(&flashConfig, 0, amount_to_delete);
    if (error_code != 0)
    {
        task_context->task_services.send_data(&task_context->task_services, 0, (uint8_t *)&error_code, 1, false);
    }

    task_context->task_services.send_return(&task_context->task_services, 0, 0, false);
}

void write_to_flash(TaskContext *task_context)
{
    init_hardware();
    uint32_t writtenBytes = flashWriteBitstream(&flashConfig, (uint8_t *)&fpga_bitstream, fpga_bitstream_size);
    task_context->task_services.send_data(&task_context->task_services, 0, (uint8_t *)&writtenBytes, 4, false);
    task_context->task_services.send_return(&task_context->task_services, 0, 0, false);
}

typedef struct
{
    uint8_t target_sector;
    uint32_t written_bytes;
} UserDataStruct;


static void finish_transfer(TaskContext *ctx, UserDataStruct *ud)
{
    ctx->task_services.send_data(&ctx->task_services, 0,
                                 (uint8_t *)&ud->written_bytes, 4, false);
    ctx->task_services.send_return(&ctx->task_services, 0, 0, false);
    free(ud);
    ctx->user_data = NULL;
}

static void fail_transfer(TaskContext *ctx, UserDataStruct *ud, const char *msg)
{
    ctx->task_services.send_data(&ctx->task_services, 0,
                                 (uint8_t *)msg, strlen(msg), false);
    ctx->task_services.send_return(&ctx->task_services, 0, 1, false); // 1 = Fehler
    if (ud) free(ud);
    ctx->user_data = NULL;
}

void write_to_flash_from_remote(TaskContext *task_context)
{
    if (task_context->step_counter == 0)
    {
        Fpga *fpga = Config_getFpga();
        if (Fpga_isPoweredOn(fpga))
        {
            Fpga_powerOff(fpga);
        }

        UserDataStruct *ud = malloc(sizeof(UserDataStruct));
        if (ud == NULL)
        {
            fail_transfer(task_context, NULL, "Out of memory");
            return;
        }
        ud->written_bytes = 0;
        ud->target_sector = task_context->input_data[0];
        task_context->user_data = ud;

        task_context->input_data_len = 0;
        task_context->step_counter++;
        return;
    }

    UserDataStruct *ud = (UserDataStruct *)task_context->user_data;
    uint32_t len = task_context->input_data_len;

    if (len == 0)
    {
        finish_transfer(task_context, ud);
        return;
    }

    uint32_t page_index = task_context->step_counter - 1;
    uint32_t address = (uint32_t)ud->target_sector * flashConfig.bytesPerSector
                     + page_index * flashConfig.bytesPerPage;

    if ((address % flashConfig.bytesPerSector) == 0)
    {
        uint8_t err = eraseFlash(&flashConfig, address, flashConfig.bytesPerSector);
        if (err != 0)
        {
            fail_transfer(task_context, ud, "Flash erase failed");
            return;
        }
    }

    int32_t written = flashWritePage(&flashConfig, address,
                                     task_context->input_data, len);
    if (written <= 0 || (uint32_t)written != len)
    {
        fail_transfer(task_context, ud, "Flash write failed");
        return;
    }
    ud->written_bytes += (uint32_t)written;

    if (len < flashConfig.bytesPerPage)
    {
        finish_transfer(task_context, ud);
        return;
    }

    task_context->input_data_len = 0; // Platz für neue Daten
    task_context->step_counter++;
}


#define ADDR_MODEL_ID 0
#define BYTES_MODEL_ID 16

void read_skeleton_id(TaskContext *task_context)
{
    uint8_t skeleton_id[16] = {0};
    Fpga *fpga = Config_getFpga();
    if (!Fpga_isPoweredOn(fpga))
    {
        Fpga_powerOn(fpga);
        sleep_ms(100); // wait for FPGA to power up
        char *msg = "power_fpga";
        task_context->task_services.send_data(&task_context->task_services, 0, msg, 10, false);
    }
    FpgaMiddleware *fpga_middleware = Config_getFpgaMiddleware();

    FpgaMiddleware_init(fpga_middleware);
    FpgaMiddleware_enableUserLogic(fpga_middleware);
    FpgaMiddleware_read(fpga_middleware, skeleton_id, ADDR_MODEL_ID, BYTES_MODEL_ID);
    FpgaMiddleware_disableUserLogic(fpga_middleware);
    FpgaMiddleware_deinit(fpga_middleware);

    task_context->task_services.send_data(&task_context->task_services, 0, (uint8_t *)&skeleton_id, BYTES_MODEL_ID, false);
    task_context->task_services.send_return(&task_context->task_services, 0, 0, false);
}

void predict(TaskContext *task_context)
{

    // task_context->task_services.send_data(&task_context->task_services, 0, task_context->input_data, 1, false);
    // return;
    Fpga *fpga = Config_getFpga();
    if (!Fpga_isPoweredOn(fpga))
    {
        Fpga_powerOn(fpga);
        sleep_ms(100); // wait for FPGA to power up
        char *msg = "power_fpga";
        task_context->task_services.send_data(&task_context->task_services, 0, msg, 10, false);
    }
    FpgaMiddleware *fpga_middleware = Config_getFpgaMiddleware();
    FpgaMiddleware_init(fpga_middleware);
    FpgaMiddleware_enableUserLogic(fpga_middleware);

    uint8_t result_size = task_context->input_data[0];
    uint8_t model_inference_input = task_context->input_data[1];

    FpgaMiddleware_write(fpga_middleware, &model_inference_input, USER_LOGIC_START_ADDRESS, 1);

    startCompute();
    while (FpgaMiddleware_fpgaIsBusy(fpga_middleware))
    {
    }
    stopCompute();

    FpgaMiddleware_read(fpga_middleware, task_context->output_data, USER_LOGIC_START_ADDRESS, result_size);
    task_context->output_data_len = task_context->input_data_len;

    FpgaMiddleware_disableUserLogic(fpga_middleware);
    FpgaMiddleware_deinit(fpga_middleware);

    task_context->task_services.send_data(&task_context->task_services, 0, task_context->output_data, result_size, false);
    task_context->task_services.send_return(&task_context->task_services, 0, 0, false);
}

void get_flash_ones(TaskContext *task_context)
{
    init_hardware();
    uint32_t ones = count_flash_ones(task_context, 1024);

    task_context->task_services.send_data(&task_context->task_services, 0, (uint8_t *)&ones, 4, false);
    task_context->task_services.send_return(&task_context->task_services, 0, 0, false);
}

void compute_sensor_data(TaskContext *task_context)
{
    if (task_context->step_counter == 0 && task_context->user_data == NULL)
    {
        task_context->user_data = malloc(sizeof(AverageFramesStruct));
    }
    AverageFramesStruct *frames = (AverageFramesStruct *)task_context->user_data;

    memcpy(frames->frames[task_context->step_counter % 3], task_context->input_data, 9);
    task_context->input_data_len = 0;

    if (task_context->step_counter >= 2)
    {
        uint8_t average_frame[9] = {0};
        for (size_t i = 0; i < 9; i++)
        {
            uint16_t sum = 0;
            for (size_t j = 0; j < 3; j++)
            {
                sum += frames->frames[j][i];
            }
            average_frame[i] = sum / 3;
        }
        task_context->task_services.send_data(&task_context->task_services, 0, average_frame, 9, false);
    }

    task_context->step_counter++;
}
