/**
 * @file    bmi160_testcase.c
 * @brief   BMI160 sensor and Fusion AHRS test.
 */

#include "ch32v30x.h"
#include "debug.h"
#include "imu/bmi160/bmi160_fusion.h"
#include "shell.h"
#include "elog.h"

#ifdef LOG_TAG
#undef LOG_TAG
#endif /* LOG_TAG */

#define LOG_TAG "testcase/bmi160/"

#if defined(SDK_USING_TESTCASE_IMU_BMI160)

#define SAMPLE_MS    10U
#define PRINT_DIV    10U

static int run_fusion(int cnt)
{
    BMI160_Fusion_t fusion;
    FusionEuler euler;
    int i;

    if (BMI160_FusionInit(&fusion) != BMI160_OK) {
        log_d("Fusion init failed");
        return -1;
    }

    log_d("Running...");
    for (i = 0; i < cnt; i++) {
        Delay_Ms(SAMPLE_MS);

        if (BMI160_FusionUpdate(&fusion) != BMI160_OK) {
            log_d("Read error");
            return -1;
        }

        if (i % PRINT_DIV == 0) {
            euler = BMI160_FusionGetEuler(&fusion);
            log_d("R %7.2f P %7.2f Y %7.2f",
                   euler.angle.roll, euler.angle.pitch, euler.angle.yaw);
        }
    }
    return 0;
}

int case_bmi160(int mode, int cnt)
{
    BMI160_Axes_t accel, gyro;
    float temp;
    int i;

    if (cnt <= 0) cnt = 100;

    if (BMI160_InitAuto() != BMI160_OK) {
        log_d("Init failed");
        return -1;
    }

    if (mode == 1) return run_fusion(cnt);

    for (i = 0; i < cnt; i++) {
        if (BMI160_ReadAccelGyro(&accel, &gyro) != BMI160_OK ||
            BMI160_ReadTemperatureC(&temp) != BMI160_OK) {
            log_d("Read error");
            return -1;
        }
        log_d("A[%6d %6d %6d] G[%6d %6d %6d] T:%.1f",
               accel.x, accel.y, accel.z, gyro.x, gyro.y, gyro.z, temp);
        Delay_Ms(100);
    }
    return 0;
}

SHELL_EXPORT_CMD(SHELL_CMD_PERMISSION(0) | SHELL_CMD_TYPE(SHELL_TYPE_CMD_FUNC),
                 case_bmi160, case_bmi160,
                 bmi160 test: mode(0=sensor,1=fusion) cnt);

#endif /* SDK_USING_TESTCASE_IMU_BMI160 */
