/**
 * @file sim_ladrc.c
 * @brief LADRC simulation command and task implementation.
 */

#include "sim_ladrc.h"
#include "MultiTimer.h"
#include "ladrc.h"
#include "../vofa.h"
#include "../usr_printf.h"
#include "elog.h"
#include <stdlib.h>

#ifdef LOG_TAG
#undef LOG_TAG
#endif /* LOG_TAG */

#define LOG_TAG "simulation/"
#define Simulation_Cycle 5

typedef enum {
    TD_MODE,
    LOOP_MODE,
    NULL_MODE
} simulation_mode_t;

typedef struct {
    simulation_mode_t mode;
    double init_val;
    double real_val;
    double expect_val;
} simulation_state_t;

/**
 * @brief Handle command `r`.
 * @param data ASCII numeric command payload.
 */
static void cmd_r_callback(const char *data);
/**
 * @brief Handle command `h`.
 * @param data ASCII numeric command payload.
 */
static void cmd_h_callback(const char *data);
/**
 * @brief Handle command `wo`.
 * @param data ASCII numeric command payload.
 */
static void cmd_wo_callback(const char *data);
/**
 * @brief Handle command `wc`.
 * @param data ASCII numeric command payload.
 */
static void cmd_wc_callback(const char *data);
/**
 * @brief Handle command `bo`.
 * @param data ASCII numeric command payload.
 */
static void cmd_bo_callback(const char *data);
/**
 * @brief Handle command `init`.
 * @param data ASCII numeric command payload.
 */
static void cmd_init_callback(const char *data);
/**
 * @brief Handle command `expe`.
 * @param data ASCII numeric command payload.
 */
static void cmd_expe_callback(const char *data);
/**
 * @brief Handle command `run`.
 * @param data ASCII numeric command payload.
 */
static void cmd_run_callback(const char *data);
/**
 * @brief Handle command `rst`.
 * @param data ASCII numeric command payload.
 */
static void cmd_rst_callback(const char *data);
/**
 * @brief TD mode periodic callback.
 * @param timer Timer instance.
 * @param user_data User data pointer, unused.
 */
static void simulation_td_callback(MultiTimer *timer, void *user_data);
/**
 * @brief LOOP mode periodic callback.
 * @param timer Timer instance.
 * @param user_data User data pointer, unused.
 */
static void simulation_loop_callback(MultiTimer *timer, void *user_data);

static simulation_state_t simulation_state;
static LADRC_TypeDef ladrc_mode;
static MultiTimer timer_td;
static MultiTimer timer_loop;

static Command ladrc_commands[] = {
    {"r",    cmd_r_callback},
    {"h",    cmd_h_callback},
    {"wo",   cmd_wo_callback},
    {"wc",   cmd_wc_callback},
    {"bo",   cmd_bo_callback},
    {"init", cmd_init_callback},
    {"expe", cmd_expe_callback},
    {"run",  cmd_run_callback},
    {"rst",  cmd_rst_callback},
};

static const int ladrc_cmd_count = sizeof(ladrc_commands) / sizeof(ladrc_commands[0]);

/**
 * @brief Convert command payload to integer.
 * @param data ASCII numeric payload.
 * @return Parsed integer value.
 */
static int cmd_to_int(const char *data) { return atoi(data); }

/**
 * @brief Parse integer payload and scale into target double.
 * @param data ASCII numeric payload.
 * @param scale Divisor used to convert integer to double.
 * @param target Output double pointer.
 * @return Parsed integer value before scaling.
 */
static int cmd_to_scaled_double(const char *data, double scale, double *target)
{
    int value = cmd_to_int(data);
    *target = (double)value / scale;
    return value;
}

/**
 * @brief Start or restart one simulation timer.
 * @param timer Timer object.
 * @param callback Timer callback.
 */
static void restart_timer(MultiTimer *timer, MultiTimerCallback_t callback)
{
    multiTimerStart(timer, Simulation_Cycle, callback, NULL);
}

/**
 * @brief Set simulation mode and synchronize mode-related state.
 * @param mode Target simulation mode.
 */
static void set_mode(simulation_mode_t mode)
{
    simulation_state.mode = mode;
    if (mode == LOOP_MODE) {
        simulation_state.real_val = simulation_state.init_val;
    }
}

/**
 * @brief Reset runtime state to default values.
 */
void SIMULATION_DINIT(void)
{
    simulation_state.init_val = 0;
    simulation_state.expect_val = 0;
    simulation_state.real_val = 0;
    set_mode(NULL_MODE);
}

/**
 * @brief Initialize LADRC parameters and start simulation timers.
 */
void SIMULATION_INIT(void)
{
    LADRC_INIT(&ladrc_mode);
    restart_timer(&timer_td, simulation_td_callback);
    restart_timer(&timer_loop, simulation_loop_callback);
}

/**
 * @brief TD mode periodic task body.
 * @param timer Timer object.
 * @param user_data User data pointer, unused.
 */
static void simulation_td_callback(MultiTimer *timer, void *user_data)
{
    (void)user_data;
    if (simulation_state.mode == TD_MODE) {
        LADRC_TD(&ladrc_mode, simulation_state.expect_val);
        ladrc_printf(SIMULATION_INTERFACE, "%.2f,%.2f\n", ladrc_mode.v1, ladrc_mode.v2);
    }
    restart_timer(timer, simulation_td_callback);
}

/**
 * @brief LOOP mode periodic task body.
 * @param timer Timer object.
 * @param user_data User data pointer, unused.
 */
static void simulation_loop_callback(MultiTimer *timer, void *user_data)
{
    (void)user_data;
    simulation_state.real_val += ladrc_mode.u;

    if (simulation_state.mode == LOOP_MODE) {
        LADRC_Loop(&ladrc_mode, &simulation_state.expect_val, &simulation_state.real_val);
        ladrc_printf(SIMULATION_INTERFACE, "%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f\n",
                     ladrc_mode.v1, ladrc_mode.v2, ladrc_mode.z1, ladrc_mode.z2,
                     ladrc_mode.z3, simulation_state.expect_val, simulation_state.real_val);
    }
    restart_timer(timer, simulation_loop_callback);
}

static void cmd_r_callback(const char *data)   { int value = cmd_to_scaled_double(data, 10.0, &ladrc_mode.r); log_d("R:%d,r:%f", value, ladrc_mode.r); }
static void cmd_h_callback(const char *data)   { int value = cmd_to_scaled_double(data, 1000.0, &ladrc_mode.h); log_d("H:%d,h:%f", value, ladrc_mode.h); }
static void cmd_wo_callback(const char *data)  { int value = cmd_to_scaled_double(data, 1.0, &ladrc_mode.w0); log_d("W0:%d,w0:%f", value, ladrc_mode.w0); }
static void cmd_wc_callback(const char *data)  { int value = cmd_to_scaled_double(data, 1.0, &ladrc_mode.wc); log_d("WC:%d,wc:%f", value, ladrc_mode.wc); }
static void cmd_bo_callback(const char *data)  { int value = cmd_to_scaled_double(data, 10.0, &ladrc_mode.b0); log_d("B0:%d,b0:%f", value, ladrc_mode.b0); }

static void cmd_init_callback(const char *data)
{
    int value = cmd_to_scaled_double(data, 10.0, &simulation_state.init_val);
    simulation_state.real_val = simulation_state.init_val;
    log_d("INIT:%d,init:%f", value, simulation_state.init_val);
}

static void cmd_expe_callback(const char *data)
{
    int value = cmd_to_scaled_double(data, 10.0, &simulation_state.expect_val);
    log_d("EXPE:%d,expe:%f", value, simulation_state.expect_val);
}

static void cmd_run_callback(const char *data)
{
    int value = cmd_to_int(data);
    set_mode((value == 0) ? TD_MODE : (value == 1) ? LOOP_MODE : NULL_MODE);
    log_d("run val:%d", value);
}

static void cmd_rst_callback(const char *data)
{
    int value = cmd_to_int(data);
    if (value) {
        LADRC_INIT(&ladrc_mode);
        SIMULATION_DINIT();
    }
    log_d("res val:%d", value);
}

/**
 * @brief Parse and dispatch pending LADRC simulation command from UART buffer.
 */
void SimLadrc_parse_command(void)
{
    parse_command(ladrc_commands, ladrc_cmd_count);
}
