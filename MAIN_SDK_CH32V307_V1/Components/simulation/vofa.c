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
 * @brief Check whether a byte is a line delimiter.
 * @param ch Input byte.
 * @return 1 for CR/LF, otherwise 0.
 */
static int is_line_delimiter(uint8_t ch)
{
    return (ch == '\r' || ch == '\n');
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
 * @brief Parse one complete command frame already isolated from the stream.
 * @param frame One command line without trailing CR/LF.
 * @param commands Command table.
 * @param cmd_count Command table size.
 */
static void process_command_frame(char *frame, const Command *commands, int cmd_count)
{
    char cmd_type[MAX_TYPE_LEN] = {0};
    char cmd_data[CMD_BUFFER_SIZE] = {0};
    int index = 1;
    int type_index = 0;
    int data_index = 0;
    int colon_found = 0;

    trim_tail_blank(frame);

    if (frame[0] == '\0') {
        return;
    }

    if (frame[0] != '#') {
        printf("Invalid command: missing '#'\r\n");
        return;
    }

    while (frame[index] != '\0' && index < CMD_BUFFER_SIZE - 1) {
        if (frame[index] == ':') {
            colon_found = 1;
            index++;
            break;
        }
        if (type_index < MAX_TYPE_LEN - 1) {
            cmd_type[type_index++] = frame[index];
        }
        index++;
    }

    if (colon_found) {
        while (frame[index] != '\0' && index < CMD_BUFFER_SIZE - 1) {
            if (data_index < CMD_BUFFER_SIZE - 1) {
                cmd_data[data_index++] = frame[index];
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
}

/**
 * @brief Parse and dispatch one completed UART command frame.
 * @param commands Command table.
 * @param cmd_count Command table size.
 */
void parse_command(Command *commands, int cmd_count)
{
    uint8_t byte = 0;
    uint32_t used_size = 0;
    int frame_length = 0;
    int frame_overflow = 0;

    if (commands == NULL || cmd_count <= 0) {
        return;
    }

    if (!*IsUsart1RecvFinsh()) {
        return;
    }

    used_size = chry_ringbuffer_get_used(&chry_rbuffer_tid);
    if (used_size == 0) {
        *IsUsart1RecvFinsh() = 0;
        return;
    }

    while (chry_ringbuffer_read_byte(&chry_rbuffer_tid, &byte)) {
        if (is_line_delimiter(byte)) {
            if (frame_overflow) {
                printf("Invalid command: length overflow\r\n");
                frame_overflow = 0;
            } else if (frame_length > 0) {
                cmd_buffer[frame_length] = '\0';
                process_command_frame(cmd_buffer, commands, cmd_count);
            }
            frame_length = 0;
            continue;
        }

        if (frame_overflow) {
            continue;
        }

        if (frame_length >= CMD_BUFFER_SIZE - 1) {
            frame_overflow = 1;
            continue;
        }

        cmd_buffer[frame_length++] = (char)byte;
    }

    if (frame_overflow) {
        printf("Invalid command: length overflow\r\n");
    } else if (frame_length > 0) {
        cmd_buffer[frame_length] = '\0';
        process_command_frame(cmd_buffer, commands, cmd_count);
    }

    parse_command_cleanup();
}
