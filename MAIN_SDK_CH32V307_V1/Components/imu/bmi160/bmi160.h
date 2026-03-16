/**
 * @file    bmi160.h
 * @brief   BMI160 IMU driver over SDK-configured I2C bus.
 */

#ifndef COMPONENTS_IMU_BMI160_BMI160_H_
#define COMPONENTS_IMU_BMI160_BMI160_H_

#include "ch32v30x.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief   BMI160 driver return codes.
 */
typedef enum
{
    BMI160_OK = 0,
    BMI160_E_NULL_PTR = -1,
    BMI160_E_COMM = -2,
    BMI160_E_NOT_FOUND = -3,
    BMI160_E_TIMEOUT = -4
} BMI160_Status_t;

/**
 * @brief   Raw 3-axis sensor sample.
 */
typedef struct
{
    int16_t x;
    int16_t y;
    int16_t z;
} BMI160_Axes_t;

/**
 * @brief   Floating-point 3-axis sensor sample.
 */
typedef struct
{
    float x;
    float y;
    float z;
} BMI160_AxesF_t;

/**
 * @brief   Default BMI160 I2C address with SDIO tied low.
 */
#define BMI160_I2C_ADDR_LOW      (0x68U << 1)

/**
 * @brief   Alternate BMI160 I2C address with SDIO tied high.
 */
#define BMI160_I2C_ADDR_HIGH     (0x69U << 1)

/**
 * @brief   Expected BMI160 chip identifier.
 */
#define BMI160_CHIP_ID_VALUE     0xD1U

int8_t BMI160_Init(uint8_t dev_addr);
int8_t BMI160_InitAuto(void);
int8_t BMI160_SoftReset(void);
int8_t BMI160_ReadChipId(uint8_t *chip_id);
int8_t BMI160_ReadAccel(BMI160_Axes_t *accel);
int8_t BMI160_ReadGyro(BMI160_Axes_t *gyro);
int8_t BMI160_ReadAccelGyro(BMI160_Axes_t *accel, BMI160_Axes_t *gyro);
int8_t BMI160_ReadAccelG(BMI160_AxesF_t *accel_g);
int8_t BMI160_ReadGyroDps(BMI160_AxesF_t *gyro_dps);
int8_t BMI160_ReadAccelGyroScaled(BMI160_AxesF_t *accel_g, BMI160_AxesF_t *gyro_dps);
int8_t BMI160_ReadTemperatureC(float *temperature_c);

#ifdef __cplusplus
}
#endif

#endif /* COMPONENTS_IMU_BMI160_BMI160_H_ */
