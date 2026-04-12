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
#include <math.h>
#include <stdlib.h>

#ifdef SDK_USING_FLASHDB
#include <flashdb.h>
#endif

#ifdef LOG_TAG
#undef LOG_TAG
#endif /* LOG_TAG */

#define LOG_TAG "simulation/"
#define Simulation_Cycle_Default 20U
#define Simulation_Plant_Mass 8.0
#define Simulation_Plant_Damping 2.8

typedef enum {
    TD_MODE,
    LOOP_MODE,
    NULL_MODE
} simulation_mode_t;

typedef struct {
    simulation_mode_t mode;
    double init_val;
    double real_val;
    double real_rate;
    double expect_val;
    uint64_t last_step_tick;
} simulation_state_t;

typedef struct {
    uint32_t magic;
    uint32_t version;
    double r;
    double h;
    double w0;
    double wc;
    double b0;
    double init;
    double expect;
} simulation_flash_config_t;

#define SIMULATION_FLASH_KEY "sim_ladrc"
#define SIMULATION_FLASH_MAGIC 0x4C445243UL
#define SIMULATION_FLASH_VERSION 1UL

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
 * @brief Handle command `stat`.
 * @param data ASCII numeric command payload.
 */
static void cmd_stat_callback(const char *data);
/**
 * @brief Handle command `save`.
 * @param data ASCII numeric command payload.
 */
static void cmd_save_callback(const char *data);
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
/**
 * @brief Emit one structured LADRC telemetry line for the upper computer.
 */
static void emit_ladrc_status_line(void);
/**
 * @brief Convert current simulation mode to generic run state.
 * @return 1 when TD/LOOP mode is active, otherwise 0.
 */
static int simulation_run_state(void);
/**
 * @brief Compute current simulation period from `h`.
 * @return Timer period in milliseconds.
 */
static unsigned int simulation_cycle_ms(void);
/**
 * @brief Get current integration step in seconds.
 * @return Positive step size in seconds.
 */
static double simulation_dt_seconds(void);
/**
 * @brief Advance TD runtime by one controller step.
 */
static void simulation_step_td(void);
/**
 * @brief Advance LOOP runtime by one controller step.
 */
static void simulation_step_loop(void);
/**
 * @brief Catch up simulation state to current platform tick.
 */
static void simulation_catch_up(void);
/**
 * @brief Reset controller runtime states for TD mode.
 */
static void reset_td_runtime_states(void);
/**
 * @brief Reset controller runtime states for LOOP mode.
 */
static void reset_loop_runtime_states(void);
/**
 * @brief Check whether runtime values are finite and usable.
 * @return 1 when valid, otherwise 0.
 */
static int runtime_state_is_valid(void);
/**
 * @brief Recover from a divergent runtime state.
 */
static void recover_invalid_runtime(void);
/**
 * @brief Normalize known-unsafe high-gain presets to the practical simulation preset.
 */
static void normalize_runtime_params(void);
/**
 * @brief Convert a value to a safe printable number.
 * @param value Input value.
 * @return `value` when finite, otherwise `0.0`.
 */
static double safe_status_value(double value);
/**
 * @brief Get current feedback value exposed to the upper computer.
 * @return TD mode returns tracked output `v1`, LOOP mode returns plant output.
 */
static double current_feedback_output(void);
/**
 * @brief Restore persisted LADRC configuration for the first reset after boot.
 */
static void restore_saved_config_on_boot(void);
/**
 * @brief Save current LADRC configuration to persistent storage.
 * @return 1 on success, otherwise 0.
 */
static int save_runtime_config(void);

static simulation_state_t simulation_state;
static LADRC_TypeDef ladrc_mode;
static MultiTimer timer_td;
static MultiTimer timer_loop;
static simulation_flash_config_t g_saved_flash_config;
static int g_saved_flash_config_valid = 0;
static int g_boot_restore_pending = 0;

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
    {"stat", cmd_stat_callback},
    {"save", cmd_save_callback},
};

static const int ladrc_cmd_count = sizeof(ladrc_commands) / sizeof(ladrc_commands[0]);

/**
 * @brief Parse command payload as a direct double value.
 * @param data ASCII numeric payload.
 * @param target Output double pointer.
 * @return 1 when parsing succeeded, otherwise 0.
 */
static int cmd_to_double(const char *data, double *target)
{
    char *end_ptr = NULL;
    double value;

    if (data == NULL || target == NULL || *data == '\0') {
        return 0;
    }

    value = strtod(data, &end_ptr);
    if (end_ptr == data) {
        return 0;
    }

    while (*end_ptr == ' ' || *end_ptr == '\t') {
        end_ptr++;
    }

    if (*end_ptr != '\0') {
        return 0;
    }

    *target = value;
    return 1;
}

/**
 * @brief Parse command payload as an integer.
 * @param data ASCII numeric payload.
 * @return Parsed integer value.
 */
static int cmd_to_int(const char *data)
{
    double value = 0.0;

    if (!cmd_to_double(data, &value)) {
        return 0;
    }
    return (int)lround(value);
}

/**
 * @brief Start or restart one simulation timer.
 * @param timer Timer object.
 * @param callback Timer callback.
 */
static void restart_timer(MultiTimer *timer, MultiTimerCallback_t callback)
{
    multiTimerStart(timer, simulation_cycle_ms(), callback, NULL);
}

/**
 * @brief Set simulation mode and synchronize mode-related state.
 * @param mode Target simulation mode.
 */
static void set_mode(simulation_mode_t mode)
{
    simulation_state.mode = mode;
    simulation_state.real_rate = 0.0;
    if (mode == LOOP_MODE) {
        simulation_state.real_val = simulation_state.init_val;
        reset_loop_runtime_states();
    } else if (mode == TD_MODE) {
        reset_td_runtime_states();
    } else {
        ladrc_mode.u = 0.0;
    }
    simulation_state.last_step_tick = getPlatformTicks();
}

static int simulation_run_state(void)
{
    return (simulation_state.mode == NULL_MODE) ? 0 : 1;
}

static unsigned int simulation_cycle_ms(void)
{
    double h = ladrc_mode.h;

    if (!isfinite(h) || h <= 0.0) {
        return Simulation_Cycle_Default;
    }

    h *= 1000.0;
    if (h < 1.0) {
        return 1U;
    }
    if (h > 1000.0) {
        return 1000U;
    }
    return (unsigned int)(h + 0.5);
}

static double simulation_dt_seconds(void)
{
    double h = ladrc_mode.h;

    if (!isfinite(h) || h <= 0.0) {
        return (double)Simulation_Cycle_Default / 1000.0;
    }
    return h;
}

static void simulation_step_td(void)
{
    if (simulation_state.mode == TD_MODE) {
        LADRC_TD(&ladrc_mode, simulation_state.expect_val);
    }
}

static void simulation_step_loop(void)
{
    if (simulation_state.mode == LOOP_MODE) {
        double dt = simulation_dt_seconds();
        double acc = (ladrc_mode.u - Simulation_Plant_Damping * simulation_state.real_rate) / Simulation_Plant_Mass;

        simulation_state.real_rate += acc * dt;
        simulation_state.real_val += simulation_state.real_rate * dt;
        LADRC_Loop(&ladrc_mode, &simulation_state.expect_val, &simulation_state.real_val);
        if (!runtime_state_is_valid()) {
            recover_invalid_runtime();
        }
    }
}

static void simulation_catch_up(void)
{
    uint64_t now_tick;
    uint64_t cycle_ms;
    uint64_t steps;

    if (simulation_state.mode == NULL_MODE) {
        simulation_state.last_step_tick = getPlatformTicks();
        return;
    }

    now_tick = getPlatformTicks();
    cycle_ms = simulation_cycle_ms();
    if (cycle_ms == 0U) {
        cycle_ms = Simulation_Cycle_Default;
    }

    if (simulation_state.last_step_tick == 0U || now_tick < simulation_state.last_step_tick) {
        simulation_state.last_step_tick = now_tick;
        return;
    }

    steps = (now_tick - simulation_state.last_step_tick) / cycle_ms;
    if (steps > 1000U) {
        steps = 1000U;
        simulation_state.last_step_tick = now_tick - cycle_ms * steps;
    }

    while (steps > 0U) {
        if (simulation_state.mode == TD_MODE) {
            simulation_step_td();
        } else if (simulation_state.mode == LOOP_MODE) {
            simulation_step_loop();
        }
        simulation_state.last_step_tick += cycle_ms;
        steps--;
    }
}

static void reset_td_runtime_states(void)
{
    ladrc_mode.v1 = simulation_state.real_val;
    ladrc_mode.v2 = 0.0;
    ladrc_mode.z1 = simulation_state.real_val;
    ladrc_mode.z2 = 0.0;
    ladrc_mode.z3 = 0.0;
    ladrc_mode.u = 0.0;
}

static void reset_loop_runtime_states(void)
{
    ladrc_mode.v1 = simulation_state.expect_val;
    ladrc_mode.v2 = 0.0;
    ladrc_mode.z1 = simulation_state.real_val;
    ladrc_mode.z2 = 0.0;
    ladrc_mode.z3 = 0.0;
    ladrc_mode.u = 0.0;
}

static int runtime_state_is_valid(void)
{
    if (!isfinite(simulation_state.init_val) ||
        !isfinite(simulation_state.expect_val) ||
        !isfinite(simulation_state.real_val) ||
        !isfinite(simulation_state.real_rate)) {
        return 0;
    }

    if (!isfinite(ladrc_mode.v1) ||
        !isfinite(ladrc_mode.v2) ||
        !isfinite(ladrc_mode.z1) ||
        !isfinite(ladrc_mode.z2) ||
        !isfinite(ladrc_mode.z3) ||
        !isfinite(ladrc_mode.u) ||
        !isfinite(ladrc_mode.r) ||
        !isfinite(ladrc_mode.h) ||
        !isfinite(ladrc_mode.w0) ||
        !isfinite(ladrc_mode.wc) ||
        !isfinite(ladrc_mode.b0)) {
        return 0;
    }

    return (ladrc_mode.h > 0.0 && ladrc_mode.b0 > 0.0);
}

static void recover_invalid_runtime(void)
{
    log_e("LADRC simulation diverged, reset to idle");
    simulation_state.mode = NULL_MODE;
    simulation_state.real_val = simulation_state.init_val;
    simulation_state.real_rate = 0.0;
    reset_loop_runtime_states();
}

static void normalize_runtime_params(void)
{
    int use_safe_profile = 0;

    if (!isfinite(ladrc_mode.r) || ladrc_mode.r <= 0.0 ||
        !isfinite(ladrc_mode.h) || ladrc_mode.h <= 0.0 ||
        !isfinite(ladrc_mode.w0) || ladrc_mode.w0 <= 0.0 ||
        !isfinite(ladrc_mode.wc) || ladrc_mode.wc <= 0.0 ||
        !isfinite(ladrc_mode.b0) || ladrc_mode.b0 <= 0.0) {
        use_safe_profile = 1;
    }

    if (!use_safe_profile &&
        ladrc_mode.h >= 0.045 &&
        ladrc_mode.w0 >= 80.0 &&
        ladrc_mode.wc >= 20.0 &&
        ladrc_mode.b0 >= 4.0) {
        use_safe_profile = 1;
    }

    if (!use_safe_profile) {
        return;
    }

    log_w("unsafe LADRC preset detected, switching to practical simulation preset");
    ladrc_mode.r = 20.0;
    ladrc_mode.h = 0.02;
    ladrc_mode.w0 = 40.0;
    ladrc_mode.wc = 2.0;
    ladrc_mode.b0 = 0.5;
}

static double safe_status_value(double value)
{
    return isfinite(value) ? value : 0.0;
}

static double current_feedback_output(void)
{
    if (simulation_state.mode == TD_MODE) {
        return safe_status_value(ladrc_mode.v1);
    }
    return safe_status_value(simulation_state.real_val);
}

static void restore_saved_config_on_boot(void)
{
    if (!g_boot_restore_pending) {
        return;
    }

    g_boot_restore_pending = 0;
    if (!g_saved_flash_config_valid) {
        return;
    }

    if (!isfinite(g_saved_flash_config.r) ||
        !isfinite(g_saved_flash_config.h) ||
        !isfinite(g_saved_flash_config.w0) ||
        !isfinite(g_saved_flash_config.wc) ||
        !isfinite(g_saved_flash_config.b0) ||
        !isfinite(g_saved_flash_config.init) ||
        !isfinite(g_saved_flash_config.expect)) {
        g_saved_flash_config_valid = 0;
        return;
    }

    ladrc_mode.r = g_saved_flash_config.r;
    ladrc_mode.h = g_saved_flash_config.h;
    ladrc_mode.w0 = g_saved_flash_config.w0;
    ladrc_mode.wc = g_saved_flash_config.wc;
    ladrc_mode.b0 = g_saved_flash_config.b0;
    simulation_state.init_val = g_saved_flash_config.init;
    simulation_state.expect_val = g_saved_flash_config.expect;
    simulation_state.real_val = simulation_state.init_val;
    simulation_state.real_rate = 0.0;
    normalize_runtime_params();
}

static int save_runtime_config(void)
{
#ifdef SDK_USING_FLASHDB
    extern struct fdb_kvdb default_kvdb;
    struct fdb_blob blob;
    simulation_flash_config_t config;
    fdb_err_t result;

    if (!default_kvdb.parent.init_ok) {
        log_w("FlashDB not initialized, skip persisting LADRC config");
        return 0;
    }

    config.magic = SIMULATION_FLASH_MAGIC;
    config.version = SIMULATION_FLASH_VERSION;
    config.r = ladrc_mode.r;
    config.h = ladrc_mode.h;
    config.w0 = ladrc_mode.w0;
    config.wc = ladrc_mode.wc;
    config.b0 = ladrc_mode.b0;
    config.init = simulation_state.init_val;
    config.expect = simulation_state.expect_val;

    result = fdb_kv_set_blob(&default_kvdb,
                             SIMULATION_FLASH_KEY,
                             fdb_blob_make(&blob, &config, sizeof(config)));
    if (result != FDB_NO_ERR) {
        log_e("persist LADRC config failed, err=%d", (int)result);
        return 0;
    }

    g_saved_flash_config = config;
    g_saved_flash_config_valid = 1;
    log_i("LADRC config written to flash");
    return 1;
#else
    log_w("flash persistence disabled, ignore save request");
    return 0;
#endif
}

static void emit_ladrc_status_line(void)
{
    simulation_catch_up();

    if (!runtime_state_is_valid()) {
        recover_invalid_runtime();
    }

    ladrc_printf(
        SIMULATION_INTERFACE,
        "timestamp=%lu,algo_id=1,run_state=%d,sim_mode=%d,ref=%.3f,feedback=%.3f,u_cmd=%.3f,"
        "v1=%.3f,v2=%.3f,z1=%.3f,z2=%.3f,z3=%.3f,r=%.3f,h=%.3f,w0=%.3f,wc=%.3f,b0=%.3f,init=%.3f\r\n",
        (unsigned long)getPlatformTicks(),
        simulation_run_state(),
        (int)simulation_state.mode,
        safe_status_value(simulation_state.expect_val),
        current_feedback_output(),
        safe_status_value(ladrc_mode.u),
        safe_status_value(ladrc_mode.v1),
        safe_status_value(ladrc_mode.v2),
        safe_status_value(ladrc_mode.z1),
        safe_status_value(ladrc_mode.z2),
        safe_status_value(ladrc_mode.z3),
        safe_status_value(ladrc_mode.r),
        safe_status_value(ladrc_mode.h),
        safe_status_value(ladrc_mode.w0),
        safe_status_value(ladrc_mode.wc),
        safe_status_value(ladrc_mode.b0),
        safe_status_value(simulation_state.init_val)
    );
}

/**
 * @brief Reset runtime state to default values.
 */
void SIMULATION_DINIT(void)
{
    simulation_state.init_val = 0;
    simulation_state.expect_val = 0;
    simulation_state.real_val = 0;
    simulation_state.real_rate = 0;
    simulation_state.last_step_tick = getPlatformTicks();
    restore_saved_config_on_boot();
    set_mode(NULL_MODE);
}

/**
 * @brief Initialize LADRC parameters and start simulation timers.
 */
void SIMULATION_INIT(void)
{
    LADRC_INIT(&ladrc_mode);
#ifdef SDK_USING_FLASHDB
    {
        extern struct fdb_kvdb default_kvdb;
        struct fdb_blob blob;
        simulation_flash_config_t config = {0};
        size_t read_len = 0;

        g_saved_flash_config_valid = 0;
        if (default_kvdb.parent.init_ok) {
            read_len = fdb_kv_get_blob(&default_kvdb,
                                       SIMULATION_FLASH_KEY,
                                       fdb_blob_make(&blob, &config, sizeof(config)));
        }
        if (read_len == sizeof(config) &&
            config.magic == SIMULATION_FLASH_MAGIC &&
            config.version == SIMULATION_FLASH_VERSION) {
            g_saved_flash_config = config;
            g_saved_flash_config_valid = 1;
        }
    }
#else
    g_saved_flash_config_valid = 0;
#endif
    g_boot_restore_pending = 1;
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
    simulation_step_td();
    simulation_state.last_step_tick = getPlatformTicks();
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
    simulation_step_loop();
    simulation_state.last_step_tick = getPlatformTicks();
    restart_timer(timer, simulation_loop_callback);
}

static void cmd_r_callback(const char *data)
{
    simulation_catch_up();
    if (cmd_to_double(data, &ladrc_mode.r)) {
        log_d("R:%f", ladrc_mode.r);
    }
}

static void cmd_h_callback(const char *data)
{
    simulation_catch_up();
    if (cmd_to_double(data, &ladrc_mode.h)) {
        restart_timer(&timer_td, simulation_td_callback);
        restart_timer(&timer_loop, simulation_loop_callback);
        simulation_state.last_step_tick = getPlatformTicks();
        log_d("H:%f", ladrc_mode.h);
    }
}

static void cmd_wo_callback(const char *data)
{
    simulation_catch_up();
    if (cmd_to_double(data, &ladrc_mode.w0)) {
        log_d("W0:%f", ladrc_mode.w0);
    }
}

static void cmd_wc_callback(const char *data)
{
    simulation_catch_up();
    if (cmd_to_double(data, &ladrc_mode.wc)) {
        log_d("WC:%f", ladrc_mode.wc);
    }
}

static void cmd_bo_callback(const char *data)
{
    simulation_catch_up();
    if (cmd_to_double(data, &ladrc_mode.b0)) {
        log_d("B0:%f", ladrc_mode.b0);
    }
}

static void cmd_init_callback(const char *data)
{
    simulation_catch_up();
    if (!cmd_to_double(data, &simulation_state.init_val)) {
        return;
    }
    simulation_state.real_val = simulation_state.init_val;
    simulation_state.real_rate = 0.0;
    if (simulation_state.mode == LOOP_MODE) {
        reset_loop_runtime_states();
    } else if (simulation_state.mode == TD_MODE) {
        reset_td_runtime_states();
    }
    log_d("INIT:%f", simulation_state.init_val);
}

static void cmd_expe_callback(const char *data)
{
    simulation_catch_up();
    if (cmd_to_double(data, &simulation_state.expect_val)) {
        log_d("EXPE:%f", simulation_state.expect_val);
    }
}

static void cmd_run_callback(const char *data)
{
    int value = cmd_to_int(data);
    normalize_runtime_params();
    set_mode((value == 0) ? TD_MODE : (value == 1) ? LOOP_MODE : NULL_MODE);
    log_d("run val:%d", value);
    emit_ladrc_status_line();
}

static void cmd_rst_callback(const char *data)
{
    int value = cmd_to_int(data);
    if (value) {
        LADRC_INIT(&ladrc_mode);
        SIMULATION_DINIT();
    }
    log_d("res val:%d", value);
    emit_ladrc_status_line();
}

static void cmd_stat_callback(const char *data)
{
    int value = cmd_to_int(data);
    if (value) {
        emit_ladrc_status_line();
    }
}

static void cmd_save_callback(const char *data)
{
    int value = cmd_to_int(data);

    if (value) {
        (void)save_runtime_config();
    }
    emit_ladrc_status_line();
}

/**
 * @brief Parse and dispatch pending LADRC simulation command from UART buffer.
 */
void SimLadrc_parse_command(void)
{
    parse_command(ladrc_commands, ladrc_cmd_count);
}
