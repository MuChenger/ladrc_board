/**
 * @file    main.c
 * @brief   Application entry and main loop.
 */

#include "init.h"

/**
 * @brief   Run automatic initialization and the foreground task loop.
 *
 * @return  This function does not return.
 */
int main(void)
{
    auto_init_run();

    while (1)
    {
        sgl_task_handle();
#ifdef LDARC_COMPONENT_SIMULATION
        Simulation_parse_command();
#endif /* LDARC_COMPONENT_SIMULATION */

#ifdef SDK_USING_SIMULATION
        multiTimerYield();
#endif /* SDK_USING_SIMULATION */
    }
}

