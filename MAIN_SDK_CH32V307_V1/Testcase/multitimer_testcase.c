/**
 * @file    multitimer_testcase.c
 * @brief   Simple MultiTimer shell testcase.
 */

#include <stdint.h>

#include "MultiTimer.h"
#include "shell.h"
#include "elog.h"

#ifdef LOG_TAG
#undef LOG_TAG
#endif /* LOG_TAG */

#define LOG_TAG "testcase/multitimer/"

#if defined(SDK_USING_TESTCASE_MULTITIMER)

static MultiTimer test_timer;

static void timer_callback(MultiTimer *timer, void *userData)
{
    log_d("multitimer timeout");
    multiTimerStart(timer, (uint32_t)(uintptr_t)userData, timer_callback, userData);
}

int case_multitimer(uint32_t period_ms)
{
    if (period_ms == 0U) {
        log_d("Usage: multitimer_test <period_ms>");
        return -1;
    }

    multiTimerStop(&test_timer);
    multiTimerStart(&test_timer, period_ms, timer_callback, (void *)(uintptr_t)period_ms);
    log_i("multitimer start: %lu ms", (unsigned long)period_ms);
    return 0;
}

SHELL_EXPORT_CMD(SHELL_CMD_PERMISSION(0) | SHELL_CMD_TYPE(SHELL_TYPE_CMD_FUNC),
                 case_multitimer,
                 case_multitimer,
                 test multitimer on timer6);

#endif /* SDK_USING_TESTCASE_MULTITIMER */
