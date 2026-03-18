#include "MultiTimer.h"
/**
 * @brief period task's tick.
 */
volatile uint32_t task_tick = 0;

/**
 * @brief Get period task's tick.
 */
uint64_t getPlatformTicks (void) 
{
    return (uint64_t)task_tick;
}
