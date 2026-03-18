/**
 * @file uart6_rs485_testcase.c
 * @brief UART6 RS485 loopback test case.
 */

#include "ch32v30x.h"
#include "sdkconfig.h"
#include "debug.h"
#include "shell.h"
#include "elog.h"

#ifdef LOG_TAG
#undef LOG_TAG
#endif /* LOG_TAG */

#define LOG_TAG "testcase/rs485/"
#if defined(SDK_USING_TESTCASE_RS485)

/**
 * @brief Loopback UART6 data and mirror to USART1.
 *
 * @param para Number of bytes to process before returning.
 * @return 0 on completion.
 */
int case_rs485(int para)
{
    uint16_t data = 0;
    int cnt = 0;

    if (para <= 0) {
        para = 100;
    }

    while (1) {
        while (USART_GetFlagStatus(SDK_USING_UART6_DEVICE, USART_FLAG_RXNE) == SET) {
            cnt++;
            data = USART_ReceiveData(SDK_USING_UART6_DEVICE);
            USART_SendData(SDK_USING_UART6_DEVICE, data);
            USART_SendData(SDK_USING_USART1_DEVICE, data);

            if (cnt >= para) {
                log_d("\r");
                return 0;
            }
        }

        Delay_Ms(1);
    }
}

SHELL_EXPORT_CMD(SHELL_CMD_PERMISSION(0) | SHELL_CMD_TYPE(SHELL_TYPE_CMD_FUNC),
                 case_rs485,
                 case_rs485,
                 test  rs485 on uart6);

#endif /* SDK_USING_TESTCASE_RS485 */
