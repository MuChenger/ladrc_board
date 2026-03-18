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
#ifdef SDK_USING_MULTI_TIMER
        multiTimerYield();
#endif /* SDK_USING_MULTI_TIMER */
    }
}

