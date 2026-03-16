/**
 * @file    i2c.h
 * @brief   I2C driver interface.
 * @author  LADRC Board
 * @date    2026-03-12
 */

#ifndef USER_DRIVERS_I2C_H_
#define USER_DRIVERS_I2C_H_

#include "ch32v30x.h"
#include "sdkconfig.h"

/**
 * @brief Initialize selected I2C bus GPIO and peripheral.
 * @param i2c_device I2C device instance from sdkconfig (for example, SDK_USING_I2C1_DEVICE).
 * @param bound I2C bus clock in Hz.
 * @param address Local own address.
 */
void I2C_GPIO_InitEx(I2C_TypeDef *i2c_device, u32 bound, u16 address);

/**
 * @brief Initialize default I2C bus GPIO and peripheral.
 * @param bound I2C bus clock in Hz.
 * @param address Local own address.
 * @note  Defaults to SDK_USING_I2C2_DEVICE when enabled, otherwise SDK_USING_I2C1_DEVICE.
 */
void I2C_GPIO_Init(u32 bound, u16 address);

#endif /* USER_DRIVERS_I2C_H_ */
