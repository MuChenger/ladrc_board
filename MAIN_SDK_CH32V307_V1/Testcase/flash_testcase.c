/**
 * @file flash_testcase.c
 * @brief W25Qxx flash test case.
 */

#include "ch32v30x.h"
#include "sdkconfig.h"
#include "debug.h"
#include "w25q16.h"
#include "shell.h"
#include "elog.h"

#ifdef LOG_TAG
#undef LOG_TAG
#endif /* LOG_TAG */

#define LOG_TAG "testcase/flash/"

#if defined(SDK_USING_TESTCASE_W25Q16)

#define FLASH_TEST_SIZE (sizeof(TEXT_Buf))

static const u8 TEXT_Buf[] = {"LADRC BOARD SPI FLASH W25Qxx"};

/**
 * @brief Erase, write and read W25Qxx flash.
 *
 * @param cnt Unused.
 */
void case_flash(int cnt)
{
    u8 datap[FLASH_TEST_SIZE + 1] = {0};
    u16 flash_model;

    (void)cnt;

    SPI_Flash_Init();
    flash_model = SPI_Flash_ReadID();

    switch (flash_model) {
    case W25Q80:
        log_d("W25Q80 OK!");
        break;
    case W25Q16:
        log_d("W25Q16 OK!");
        break;
    case W25Q32:
        log_d("W25Q32 OK!");
        break;
    case W25Q64:
        log_d("W25Q64 OK!");
        break;
    case W25Q128:
        log_d("W25Q128 OK!");
        break;
    default:
        log_d("Fail!");
        break;
    }

    log_d("Start Erase W25Qxx....");
    SPI_Flash_Erase_Sector(0);
    log_d("W25Qxx Erase Finished!");

    Delay_Ms(500);
    log_d("Start Read W25Qxx....");
    SPI_Flash_Read(datap, 0x0, FLASH_TEST_SIZE);
    datap[FLASH_TEST_SIZE] = '\0';
    log_d("%s", datap);

    Delay_Ms(500);
    log_d("Start Write W25Qxx....");
    SPI_Flash_Write((u8 *)TEXT_Buf, 0, FLASH_TEST_SIZE);
    log_d("W25Qxx Write Finished!");

    Delay_Ms(500);
    log_d("Start Read W25Qxx....");
    SPI_Flash_Read(datap, 0x0, FLASH_TEST_SIZE);
    datap[FLASH_TEST_SIZE] = '\0';
    log_d("%s", datap);
}

SHELL_EXPORT_CMD(SHELL_CMD_PERMISSION(0) | SHELL_CMD_TYPE(SHELL_TYPE_CMD_FUNC),
                 case_flash,
                 case_flash,
                 test board flash);

#endif /* SDK_USING_TESTCASE_W25Q16 */
