/**
 * @file    bmi160_fusion.c
 * @brief   Fusion adaptation layer for BMI160.
 */

#include "bmi160_fusion.h"

#define BMI160_FUSION_GAIN            0.5f
#define BMI160_FUSION_GYRO_RANGE_DPS  2000.0f
#define BMI160_FUSION_ACCEL_REJECTION 10.0f

int8_t BMI160_FusionInit(BMI160_Fusion_t *fusion)
{
    FusionAhrsSettings settings = fusionAhrsDefaultSettings;

    FusionBiasInitialise(&fusion->bias, BMI160_FUSION_SAMPLE_RATE_HZ);
    FusionAhrsInitialise(&fusion->ahrs);

    settings.convention = FusionConventionNwu;
    settings.gain = BMI160_FUSION_GAIN;
    settings.gyroscopeRange = BMI160_FUSION_GYRO_RANGE_DPS;
    settings.accelerationRejection = BMI160_FUSION_ACCEL_REJECTION;
    settings.recoveryTriggerPeriod = 5U * BMI160_FUSION_SAMPLE_RATE_HZ;
    FusionAhrsSetSettings(&fusion->ahrs, &settings);

    fusion->alignment = FusionRemapAlignmentPXPYPZ;
    return BMI160_OK;
}

int8_t BMI160_FusionUpdate(BMI160_Fusion_t *fusion)
{
    BMI160_AxesF_t accel_g, gyro_dps;
    FusionVector gyro, accel;

    if (BMI160_ReadAccelGyroScaled(&accel_g, &gyro_dps) != BMI160_OK)
        return BMI160_E_COMM;

    gyro = FusionRemap((FusionVector){{gyro_dps.x, gyro_dps.y, gyro_dps.z}}, fusion->alignment);
    accel = FusionRemap((FusionVector){{accel_g.x, accel_g.y, accel_g.z}}, fusion->alignment);
    gyro = FusionBiasUpdate(&fusion->bias, gyro);

    FusionAhrsUpdateNoMagnetometer(&fusion->ahrs, gyro, accel, BMI160_FUSION_SAMPLE_PERIOD_S);
    return BMI160_OK;
}

FusionEuler BMI160_FusionGetEuler(const BMI160_Fusion_t *fusion)
{
    return FusionQuaternionToEuler(FusionAhrsGetQuaternion(&fusion->ahrs));
}
