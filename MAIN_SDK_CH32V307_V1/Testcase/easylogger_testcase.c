/**
 * @file    easylogger_testcase.c
 * @brief   EasyLogger shell testcase.
 */

#include <stdint.h>

#include "debug.h"
#include "elog.h"
#include "shell.h"

#if defined(SDK_USING_TESTCASE_EASY_LOGGER)

static const char *k_easylogger_tag = "elog_tc";

int case_easylogger(int mode)
{
    static const uint8_t sample_data[] = {
        0x45, 0x61, 0x73, 0x79, 0x4C, 0x6F, 0x67, 0x67,
        0x65, 0x72, 0x2D, 0x43, 0x48, 0x33, 0x32, 0x56
    };

    if (!elog_get_output_enabled()) {
        printf("EasyLogger output is disabled.\r\n");
        return -1;
    }

    elog_set_filter(ELOG_LVL_VERBOSE, "", "");

    switch (mode) {
    case 0:
        elog_a(k_easylogger_tag, "assert level message");
        elog_e(k_easylogger_tag, "error level message");
        elog_w(k_easylogger_tag, "warn level message");
        elog_i(k_easylogger_tag, "info level message");
        elog_d(k_easylogger_tag, "debug level message");
        elog_v(k_easylogger_tag, "verbose level message");
        break;

    case 1:
        elog_i(k_easylogger_tag, "EasyLogger filter test start.");
        elog_set_filter(ELOG_LVL_INFO, k_easylogger_tag, "");
        elog_i(k_easylogger_tag, "this line should be visible");
        elog_d(k_easylogger_tag, "this line should be hidden by level filter");
        elog_i("other", "this line should be hidden by tag filter");
        elog_set_filter(ELOG_LVL_VERBOSE, "", "");
        elog_i(k_easylogger_tag, "EasyLogger filter test end.");
        break;

    case 2:
        elog_hexdump(k_easylogger_tag, 16, sample_data, sizeof(sample_data));
        break;

    case 3:
        elog_raw("easylogger raw output test\r\n");
        break;

    default:
        printf("Usage: easylogger_test [mode]\r\n");
        printf("  mode 0: output all colored log levels\r\n");
        printf("  mode 1: verify filter behavior\r\n");
        printf("  mode 2: output hexdump sample\r\n");
        printf("  mode 3: output raw sample without level color\r\n");
        return -1;
    }

    return 0;
}

SHELL_EXPORT_CMD(SHELL_CMD_PERMISSION(0) | SHELL_CMD_TYPE(SHELL_TYPE_CMD_FUNC),
                 case_easylogger,
                 case_easylogger,
                 easylogger test: mode(0=level,1=filter,2=hexdump,3=raw));

#endif /* SDK_USING_TESTCASE_EASY_LOGGER */
