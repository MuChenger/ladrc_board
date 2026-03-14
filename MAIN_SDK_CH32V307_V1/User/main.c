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
#ifdef LDARC_COMPONENT_SIMULATION
        Simulation_parse_command();
#endif /* LDARC_COMPONENT_SIMULATION */

#ifdef LDARC_COMPONENT_MULTITIMER
        multiTimerYield();
#endif /* LDARC_COMPONENT_MULTITIMER */
    }
}

