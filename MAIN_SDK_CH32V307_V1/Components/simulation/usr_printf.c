/**
 * @file usr_printf.c
 * @brief UART formatted output helper implementation.
 */

#include "usr_printf.h"
#include <stdarg.h>
#include <string.h>

/**
 * @brief Print formatted text to USART by polling TXE.
 * @param USARTx Target USART peripheral.
 * @param format printf-style format string.
 * @param ... Format arguments.
 */
void ladrc_printf(USART_TypeDef *USARTx, const char *format, ...)
{
    va_list args;
    char buffer[256];

    va_start(args, format);
    int length = vsnprintf(buffer, sizeof(buffer), format, args);
    va_end(args);

    if (length <= 0) {
        return;
    }

    if (length >= (int)sizeof(buffer)) {
        length = (int)sizeof(buffer) - 1;
    }

    for (int i = 0; i < length; i++) {
        while (USART_GetFlagStatus(USARTx, USART_FLAG_TXE) == RESET);
        USART_SendData(USARTx, buffer[i]);
    }
}
