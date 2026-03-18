/**
 * @file vofa.h
 * @brief Command parser interface for VOFA UART frames.
 */

#ifndef VOFA_H
#define VOFA_H

#define CMD_BUFFER_SIZE 12
#define MAX_TYPE_LEN 8

/**
 * @brief Command callback type.
 * @param data Command payload string after ':'.
 */
typedef void (*CommandHandler)(const char*);

/**
 * @brief Command descriptor.
 * @var Command::type Command key between '#' and ':'.
 * @var Command::handler Callback for this command key.
 */
typedef struct{
    char type[MAX_TYPE_LEN];
    CommandHandler handler;
} Command;

/**
 * @brief Parse one pending command frame from ringbuffer and dispatch it.
 * @param commands Command descriptor table.
 * @param cmd_count Number of entries in @p commands.
 */
void parse_command(Command *commands, int cmd_count);

#endif // VOFA_H
