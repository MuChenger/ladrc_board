/**
 * @file sfud_testcase.c
 * @brief SFUD minimal self-check testcase.
 */

#include "sdkconfig.h"
#include "sfud.h"
#include "shell.h"
#include "elog.h"

#ifdef LOG_TAG
#undef LOG_TAG
#endif /* LOG_TAG */

#define LOG_TAG "testcase/sfud/"

#if defined(SDK_USING_TESTCASE_W25Q16)

/**
 * @brief Run SFUD minimal self-check.
 *
 * @param mode Unused.
 * @return 0 on success, -1 on failure.
 */
int case_sfud(int mode)
{
    static uint8_t sfud_inited = 0;
    sfud_err result;
    sfud_flash *flash;
    uint8_t status = 0;
    uint8_t data[16] = {0};

    (void)mode;

    if (!sfud_inited) {
        result = sfud_init();
        if (result != SFUD_SUCCESS) {
            log_e("sfud_init failed, err=%d.", result);
            return -1;
        }
        sfud_inited = 1;
    }

    flash = sfud_get_device(0);
    if (flash == NULL || !flash->init_ok) {
        log_e("sfud_get_device failed.");
        return -1;
    }

    log_i("SFUD device: %s", flash->name ? flash->name : "unknown");

    result = sfud_read_status(flash, &status);
    if (result != SFUD_SUCCESS) {
        log_e("sfud_read_status failed, err=%d.", result);
        return -1;
    }
    log_i("status=0x%02X", status);

    result = sfud_read(flash, 0x0, sizeof(data), data);
    if (result != SFUD_SUCCESS) {
        log_e("sfud_read failed, err=%d.", result);
        return -1;
    }
    log_i("head=%02X %02X %02X %02X", data[0], data[1], data[2], data[3]);

    return 0;
}

SHELL_EXPORT_CMD(SHELL_CMD_PERMISSION(0) | SHELL_CMD_TYPE(SHELL_TYPE_CMD_FUNC),
                 case_sfud,
                 case_sfud,
                 sfud quick self-check);

#endif /* SDK_USING_TESTCASE_W25Q16 */
