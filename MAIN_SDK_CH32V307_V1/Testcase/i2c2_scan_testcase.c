/**
 * @file    i2c2_scan_testcase.c
 * @brief   I2C2 bus scan test case.
 */

#include "ch32v30x.h"
#include "sdkconfig.h"
#include "debug.h"
#include "i2c.h"
#include "shell.h"

#if defined(SDK_USING_TESTCASE_I2C_SCAN)

#define I2C2_SCAN_TIMEOUT        0x8000UL

static void I2C2_ScanBusRecover(void)
{
    RCC_APB1PeriphResetCmd(RCC_APB1Periph_I2C2, ENABLE);
    RCC_APB1PeriphResetCmd(RCC_APB1Periph_I2C2, DISABLE);
    I2C_SoftwareResetCmd(I2C2, ENABLE);
    I2C_SoftwareResetCmd(I2C2, DISABLE);
    I2C_Cmd(I2C2, ENABLE);
    I2C_AcknowledgeConfig(I2C2, ENABLE);
}

static int I2C2_WaitBusyIdle(void)
{
    uint32_t timeout = I2C2_SCAN_TIMEOUT;

    while (I2C_GetFlagStatus(I2C2, I2C_FLAG_BUSY) != RESET) {
        if (timeout-- == 0U) {
            I2C2_ScanBusRecover();
            return -1;
        }
    }

    return 0;
}

static int I2C2_ProbeAddress(uint8_t addr_7bit)
{
    uint32_t timeout = I2C2_SCAN_TIMEOUT;

    if (I2C2_WaitBusyIdle() != 0) {
        return -1;
    }

    I2C_GenerateSTART(I2C2, ENABLE);
    timeout = I2C2_SCAN_TIMEOUT;
    while (!I2C_CheckEvent(I2C2, I2C_EVENT_MASTER_MODE_SELECT)) {
        if (timeout-- == 0U) {
            I2C_GenerateSTOP(I2C2, ENABLE);
            return -1;
        }
    }

    I2C_Send7bitAddress(I2C2, (uint8_t)(addr_7bit << 1), I2C_Direction_Transmitter);

    timeout = I2C2_SCAN_TIMEOUT;
    while (1) {
        if (I2C_CheckEvent(I2C2, I2C_EVENT_MASTER_TRANSMITTER_MODE_SELECTED)) {
            (void)I2C2->STAR1;
            (void)I2C2->STAR2;
            I2C_GenerateSTOP(I2C2, ENABLE);
            return 0;
        }

        if (I2C_GetFlagStatus(I2C2, I2C_FLAG_AF) != RESET) {
            I2C_ClearFlag(I2C2, I2C_FLAG_AF);
            I2C_GenerateSTOP(I2C2, ENABLE);
            return 1;
        }

        if (timeout-- == 0U) {
            I2C_GenerateSTOP(I2C2, ENABLE);
            I2C2_ScanBusRecover();
            return -1;
        }
    }
}

/**
 * @brief   Scan all valid 7-bit device addresses on I2C2.
 *
 * @return  0 on completion.
 */
int i2c2_scan_testcase_func(void)
{
    uint8_t addr;
    int found = 0;
    int probe_status;

    I2C_GPIO_Init(100000U, 0x00U);

    printf("I2C2 scanning...\r\n");

    for (addr = 0x08U; addr <= 0x77U; addr++) {
        probe_status = I2C2_ProbeAddress(addr);
        if (probe_status == 0) {
            printf("Found device at 0x%02X\r\n", addr);
            found++;
        } else if (probe_status < 0) {
            printf("Probe error at 0x%02X\r\n", addr);
        }
    }

    if (found == 0) {
        printf("No I2C device acknowledged on I2C2.\r\n");
    } else {
        printf("I2C2 scan done, %d device(s) found.\r\n", found);
    }

    return 0;
}

SHELL_EXPORT_CMD(SHELL_CMD_PERMISSION(0) | SHELL_CMD_TYPE(SHELL_TYPE_CMD_FUNC),
                 i2c2_scan_testcase_func,
                 i2c2_scan_testcase_func,
                 scan all i2c2 device addresses (testcase));

#endif /* SDK_USING_TESTCASE_I2C_SCAN */
