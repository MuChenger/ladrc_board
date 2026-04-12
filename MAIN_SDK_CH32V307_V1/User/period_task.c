#include "ch32v30x.h"
#include "MultiTimer.h"
#include "auto_init.h"
#include "ladrc/sim_ladrc.h"
#include "sdkconfig.h"
#include "sgl.h"
#include "elog.h"

#ifdef LOG_TAG
#undef LOG_TAG
#endif /* LOG_TAG */

#define LOG_TAG "task"

#define sgl_task_period 30        // 30ms
#define sgl_tick_period 1         // 1ms
#define simulation_tick_period 1  // 1ms

static MultiTimer sgl_tick_timer;
static MultiTimer sgl_task_timer;
static MultiTimer simulation_task_timer;

void simulation_task_timer_callback (MultiTimer *timer, void *userData) 
{
    SimLadrc_parse_command();
    multiTimerStart (timer, simulation_tick_period, simulation_task_timer_callback, NULL);
}

void sgl_tick_timer_callback (MultiTimer *timer, void *userData) 
{
    sgl_tick_inc (1);
    multiTimerStart (timer, sgl_tick_period, sgl_tick_timer_callback, NULL);
}

void sgl_task_timer_callback (MultiTimer *timer, void *userData) 
{
    sgl_task_handle();
    multiTimerStart (timer, sgl_task_period, sgl_task_timer_callback, NULL);
}

#ifdef SDK_USING_MULTI_TIMER
/**
 * @brief   Initialize the period task timer callback.
 *
 * @return  0 on success.
 */
static int period_task_init (void) 
{
    multiTimerStop (&simulation_task_timer);
    multiTimerStart (&simulation_task_timer, simulation_tick_period, simulation_task_timer_callback, NULL);

#if defined(SDK_USING_SGL)
    multiTimerStop (&sgl_tick_timer);
    multiTimerStart (&sgl_tick_timer, sgl_tick_period, sgl_tick_timer_callback, NULL);

    multiTimerStop (&sgl_task_timer);
    multiTimerStart (&sgl_task_timer, sgl_task_period, sgl_task_timer_callback, NULL);
#endif /* SDK_USING_SGL */

    log_i ("period task timer callback init success.");
    return 0;
}

INIT_APP_EXPORT (period_task_init);
#endif /* SDK_USING_MULTI_TIMER */
