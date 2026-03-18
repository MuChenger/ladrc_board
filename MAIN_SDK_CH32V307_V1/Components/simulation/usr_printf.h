/**
 * @file usr_printf.h
 * @brief Lightweight UART formatted output helper.
 */

#ifndef BOARD_COMPONENT_USR_PRINTF_USR_PRINTF_H_
#define BOARD_COMPONENT_USR_PRINTF_USR_PRINTF_H_

#include "ch32v30x.h"

/**
 * @brief Print formatted text to the target USART.
 * @param USARTx Target USART peripheral.
 * @param format printf-style format string.
 * @param ... Format arguments.
 */
void ladrc_printf(USART_TypeDef *USARTx, const char *format, ...);

#endif /* BOARD_COMPONENT_USR_PRINTF_USR_PRINTF_H_ */
