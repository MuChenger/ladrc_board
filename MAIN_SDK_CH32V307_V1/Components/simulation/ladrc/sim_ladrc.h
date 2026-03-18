/**
 * @file sim_ladrc.h
 * @brief Simulation module public APIs.
 */

#ifndef SIMULATION_H
#define SIMULATION_H

#include "sdkconfig.h"

#define SIMULATION_INTERFACE SDK_USING_BLE_INTERFACE_INSTANCE
/**
 * @brief Reset simulation runtime state to defaults.
 */
void SIMULATION_DINIT(void);

/**
 * @brief Initialize simulation runtime and periodic tasks.
 */
void SIMULATION_INIT(void);

/**
 * @brief Parse and dispatch one received LADRC simulation command.
 */
void SimLadrc_parse_command(void);

#endif // SIMULATION_H
