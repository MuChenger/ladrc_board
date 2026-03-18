/**
 * @file    i2c2_scan_testcase.c
 * @brief   I2C bus scan test case.
 */

#include "ch32v30x.h"
#include "sdkconfig.h"
#include "debug.h"
#include "i2c.h"
#include "shell.h"
#include "elog.h"

#ifdef LOG_TAG
#undef LOG_TAG
#endif /* LOG_TAG */

#define LOG_TAG "testcase/i2cscan/"

#if defined(SDK_USING_TESTCASE_I2C_SCAN)

#define I2C_SCAN_TIMEOUT        0x8000UL

static void I2C_ScanBusRecover(I2C_TypeDef *i2c, uint32_t apb1_periph)
{
    if (apb1_periph != 0) {
        RCC_APB1PeriphResetCmd(apb1_periph, ENABLE);
        RCC_APB1PeriphResetCmd(apb1_periph, DISABLE);
    }
    I2C_SoftwareResetCmd(i2c, ENABLE);
    I2C_SoftwareResetCmd(i2c, DISABLE);
    I2C_Cmd(i2c, ENABLE);
    I2C_AcknowledgeConfig(i2c, ENABLE);
}

static int I2C_WaitBusyIdle(I2C_TypeDef *i2c, uint32_t apb1_periph)
{
    uint32_t timeout = I2C_SCAN_TIMEOUT;

    while (I2C_GetFlagStatus(i2c, I2C_FLAG_BUSY) != RESET) {
        if (timeout-- == 0U) {
            I2C_ScanBusRecover(i2c, apb1_periph);
            return -1;
        }
    }

    return 0;
}

static int I2C_ProbeAddress(I2C_TypeDef *i2c, uint32_t apb1_periph, uint8_t addr_7bit)
{
    uint32_t timeout = I2C_SCAN_TIMEOUT;

    if (I2C_WaitBusyIdle(i2c, apb1_periph) != 0) {
        return -1;
    }

    I2C_GenerateSTART(i2c, ENABLE);
    timeout = I2C_SCAN_TIMEOUT;
    while (!I2C_CheckEvent(i2c, I2C_EVENT_MASTER_MODE_SELECT)) {
        if (timeout-- == 0U) {
            I2C_GenerateSTOP(i2c, ENABLE);
            I2C_ScanBusRecover(i2c, apb1_periph);
            return -1;
        }
    }

    I2C_Send7bitAddress(i2c, (uint8_t)(addr_7bit << 1), I2C_Direction_Transmitter);

    timeout = I2C_SCAN_TIMEOUT;
    while (1) {
        if (I2C_CheckEvent(i2c, I2C_EVENT_MASTER_TRANSMITTER_MODE_SELECTED)) {
            (void)i2c->STAR1;
            (void)i2c->STAR2;
            I2C_GenerateSTOP(i2c, ENABLE);
            return 0;
        }

        if (I2C_GetFlagStatus(i2c, I2C_FLAG_AF) != RESET) {
            I2C_ClearFlag(i2c, I2C_FLAG_AF);
            I2C_GenerateSTOP(i2c, ENABLE);
            return 1;
        }

        if (timeout-- == 0U) {
            I2C_GenerateSTOP(i2c, ENABLE);
            I2C_ScanBusRecover(i2c, apb1_periph);
            return -1;
        }
    }
}

/**
 * @brief Scan all valid 7-bit device addresses on one I2C bus.
 * @param i2c I2C instance.
 * @return Number of found devices.
 */
static int I2C_ScanOneBus(I2C_TypeDef *i2c, uint32_t apb1_periph, const char *name)
{
    uint8_t addr;
    int found = 0;
    int probe_status;

    I2C_GPIO_InitEx(i2c, 100000U, 0x00U);

    log_d("%s scanning...", name);

    for (addr = 0x08U; addr <= 0x77U; addr++) {
        probe_status = I2C_ProbeAddress(i2c, apb1_periph, addr);
        if (probe_status == 0) {
            log_d("%s found device at 0x%02X", name, addr);
            found++;
        } else if (probe_status < 0) {
            log_d("%s probe error at 0x%02X", name, addr);
        }
    }

    if (found == 0) {
        log_d("No I2C device acknowledged on %s.", name);
    } else {
        log_d("%s scan done, %d device(s) found.", name, found);
    }

    return found;
}

/**
 * @brief Scan all enabled I2C peripherals from sdkconfig.
 * @return 0 on completion.
 */
int case_i2cscan(void)
{
    int total_found = 0;
    int bus_count = 0;

#ifdef SDK_USING_I2C1
    total_found += I2C_ScanOneBus(SDK_USING_I2C1_DEVICE, RCC_APB1Periph_I2C1, "I2C1");
    bus_count++;
#endif
#ifdef SDK_USING_I2C2
    total_found += I2C_ScanOneBus(SDK_USING_I2C2_DEVICE, RCC_APB1Periph_I2C2, "I2C2");
    bus_count++;
#endif

    if (bus_count == 0) {
        log_d("No I2C peripheral enabled in sdkconfig.");
        return 0;
    }

    log_d("I2C scan complete on %d bus(es), total %d device(s) found.", bus_count, total_found);
    return 0;
}

SHELL_EXPORT_CMD(SHELL_CMD_PERMISSION(0) | SHELL_CMD_TYPE(SHELL_TYPE_CMD_FUNC),
                 case_i2cscan,
                 case_i2cscan,
                 test i2c scan);

#endif /* SDK_USING_TESTCASE_I2C_SCAN */
