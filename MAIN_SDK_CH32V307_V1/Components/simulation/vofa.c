/**
 * @file vofa.c
 * @brief VOFA command parser implementation.
 */

#include "vofa.h"
#include "chry_ringbuffer.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

chry_ringbuffer_t chry_rbuffer_tid;
uint8_t g_recvFinshFlag = 0;

/**
 * @brief Get pointer to UART frame-finished flag.
 * @return Pointer to receive-finished flag byte.
 */
uint8_t *IsUsart1RecvFinsh(void)
{
    return &g_recvFinshFlag;
}

static char cmd_buffer[CMD_BUFFER_SIZE];

/**
 * @brief Clear parse buffer and reset frame-finished flag.
 */
static void parse_command_cleanup(void)
{
    memset(cmd_buffer, 0, sizeof(cmd_buffer));
    *IsUsart1RecvFinsh() = 0;
}

/**
 * @brief Trim trailing blanks and line endings from a string.
 * @param str Mutable string to trim.
 */
static void trim_tail_blank(char *str)
{
    size_t length = strlen(str);
    while (length > 0) {
        char ch = str[length - 1];
        if (ch == '\r' || ch == '\n' || ch == ' ' || ch == '\t') {
            str[length - 1] = '\0';
            length--;
        } else {
            break;
        }
    }
}

/**
 * @brief Dispatch a parsed command to its callback.
 * @param cmd_type Parsed command key.
 * @param cmd_data Parsed command payload.
 * @param commands Command table.
 * @param cmd_count Command table size.
 */
static void process_command(const char *cmd_type,
                            const char *cmd_data,
                            const Command *commands,
                            int cmd_count)
{
    for (int index = 0; index < cmd_count; index++) {
        if (strcmp(cmd_type, commands[index].type) == 0 &&
            commands[index].handler != NULL) {
            commands[index].handler(cmd_data);
            return;
        }
    }
    printf("Unknown command type: %s\r\n", cmd_type);
}

/**
 * @brief Parse and dispatch one completed UART command frame.
 * @param commands Command table.
 * @param cmd_count Command table size.
 */
void parse_command(Command *commands, int cmd_count)
{
    if (commands == NULL || cmd_count <= 0) {
        return;
    }

    if (!*IsUsart1RecvFinsh()) {
        return;
    }

    uint32_t used_size = chry_ringbuffer_get_used(&chry_rbuffer_tid);
    if (used_size == 0) {
        *IsUsart1RecvFinsh() = 0;
        return;
    }

    if (used_size >= CMD_BUFFER_SIZE) {
        chry_ringbuffer_reset_read(&chry_rbuffer_tid);
        parse_command_cleanup();
        printf("Invalid command: length overflow\r\n");
        return;
    }

    chry_ringbuffer_read(&chry_rbuffer_tid, cmd_buffer, used_size);
    cmd_buffer[used_size] = '\0';

    if (cmd_buffer[0] != '#') {
        printf("Invalid command: missing '#'\r\n");
        parse_command_cleanup();
        return;
    }

    char cmd_type[MAX_TYPE_LEN] = {0};
    char cmd_data[CMD_BUFFER_SIZE] = {0};
    int index = 1;
    int type_index = 0;
    int data_index = 0;
    int colon_found = 0;

    while (cmd_buffer[index] != '\0' && index < CMD_BUFFER_SIZE - 1) {
        if (cmd_buffer[index] == ':') {
            colon_found = 1;
            index++;
            break;
        }
        if (type_index < MAX_TYPE_LEN - 1) {
            cmd_type[type_index++] = cmd_buffer[index];
        }
        index++;
    }

    if (colon_found) {
        while (cmd_buffer[index] != '\0' && index < CMD_BUFFER_SIZE - 1) {
            if (data_index < CMD_BUFFER_SIZE - 1) {
                cmd_data[data_index++] = cmd_buffer[index];
            }
            index++;
        }
    }

    trim_tail_blank(cmd_type);
    trim_tail_blank(cmd_data);

    if (cmd_type[0] == '\0') {
        printf("Invalid command: empty command type\r\n");
    } else if (!colon_found || cmd_data[0] == '\0') {
        printf("Invalid command: no data provided for %s\r\n", cmd_type);
    } else {
        process_command(cmd_type, cmd_data, commands, cmd_count);
    }

    parse_command_cleanup();
}
