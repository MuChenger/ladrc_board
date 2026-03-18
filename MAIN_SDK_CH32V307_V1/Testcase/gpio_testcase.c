/**
 * @file gpio_testcase.c
 * @brief GPIO LED test case.
 */

#include "ch32v30x.h"
#include "sdkconfig.h"
#include "debug.h"
#include "gpio.h"
#include "gpio_pin.h"
#include "shell.h"
#include "elog.h"

#ifdef LOG_TAG
#undef LOG_TAG
#endif /* LOG_TAG */

#define LOG_TAG "testcase/gpio/"
#if defined(SDK_USING_TESTCASE_GPIO)

/**
 * @brief Toggle LED GPIOs for a given cycle count.
 *
 * @param cnt Toggle count.
 * @return 0 on completion.
 */
int case_gpio(int cnt)
{
    GPIO_TypeDef *led1_port = SDK_GetPort(SDK_USING_LED_LED1);
    GPIO_TypeDef *led2_port = SDK_GetPort(SDK_USING_LED_LED2);
    uint16_t led1_pin = SDK_GetPin(SDK_USING_LED_LED1);
    uint16_t led2_pin = SDK_GetPin(SDK_USING_LED_LED2);

    LED_GPIO_INIT();

    for (int i = 0; i < cnt; i++) {
        Delay_Ms(500);
        GPIO_SetBits(led1_port, led1_pin);
        GPIO_SetBits(led2_port, led2_pin);

        Delay_Ms(500);
        GPIO_ResetBits(led1_port, led1_pin);
        GPIO_ResetBits(led2_port, led2_pin);
    }

    return 0;
}

SHELL_EXPORT_CMD(SHELL_CMD_PERMISSION(0) | SHELL_CMD_TYPE(SHELL_TYPE_CMD_FUNC),
                 case_gpio,
                 case_gpio,
                 test board gpio);

#endif /* SDK_USING_TESTCASE_GPIO */
