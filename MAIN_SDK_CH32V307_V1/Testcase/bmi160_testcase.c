/**
 * @file    bmi160_testcase.c
 * @brief   BMI160 test case on I2C2.
 */

#include "ch32v30x.h"
#include "sdkconfig.h"
#include "debug.h"
#include "imu/bmi160/bmi160.h"
#include "shell.h"

/**
 * @brief   Initialize BMI160 and print sampled sensor data.
 *
 * @param   cnt Number of samples to print.
 * @return  0 on success, -1 on failure.
 */
int bmi160_func(int cnt)
{
#if defined(SDK_USING_I2C2)
    BMI160_Axes_t accel;
    BMI160_Axes_t gyro;
    uint8_t chip_id;
    float temperature_c;
    int8_t status;
    int i;

    status = BMI160_InitAuto();
    if (status != BMI160_OK) {
        printf("BMI160 init failed, status=%d.\r\n", status);
        return -1;
    }

    status = BMI160_ReadChipId(&chip_id);
    if (status != BMI160_OK) {
        printf("BMI160 read chip id failed, status=%d.\r\n", status);
        return -1;
    }

    printf("BMI160 chip id: 0x%02X\r\n", chip_id);

    for (i = 0; i < cnt; i++) {
        status = BMI160_ReadAccelGyro(&accel, &gyro);
        if (status != BMI160_OK) {
            printf("BMI160 read accel/gyro failed, status=%d.\r\n", status);
            return -1;
        }

        status = BMI160_ReadTemperatureC(&temperature_c);
        if (status != BMI160_OK) {
            printf("BMI160 read temperature failed, status=%d.\r\n", status);
            return -1;
        }

        printf("ACC[%6d %6d %6d] GYR[%6d %6d %6d] TEMP[%.2fC]\r\n",
               accel.x,
               accel.y,
               accel.z,
               gyro.x,
               gyro.y,
               gyro.z,
               temperature_c);
        Delay_Ms(100);
    }

    return 0;
#else
    (void)cnt;
    printf("BMI160 testcase disabled: I2C2 is not enabled.\r\n");
    return -1;
#endif /* SDK_USING_I2C2 */
}

SHELL_EXPORT_CMD(SHELL_CMD_PERMISSION(0) | SHELL_CMD_TYPE(SHELL_TYPE_CMD_FUNC),
                 bmi160_func,
                 bmi160_func,
                 test i2c2 and board bmi160);
