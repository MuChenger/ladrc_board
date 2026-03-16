/**
 * @file uart6_rs485_testcase.c
 * @brief UART6 RS485 loopback test case.
 */

#include "ch32v30x.h"
#include "sdkconfig.h"
#include "debug.h"
#include "shell.h"

#if defined(SDK_USING_TESTCASE_RS485)

/**
 * @brief Loopback UART6 data and mirror to USART1.
 *
 * @param para Number of bytes to process before returning.
 * @return 0 on completion.
 */
int uart6_rs485_func(int para)
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
                printf("\r\r\n");
                return 0;
            }
        }

        Delay_Ms(1);
    }
}

SHELL_EXPORT_CMD(SHELL_CMD_PERMISSION(0) | SHELL_CMD_TYPE(SHELL_TYPE_CMD_FUNC),
                 uart6_rs485_func,
                 uart6_rs485_func,
                 test uart6 and rs485);

#endif /* SDK_USING_TESTCASE_RS485 */
