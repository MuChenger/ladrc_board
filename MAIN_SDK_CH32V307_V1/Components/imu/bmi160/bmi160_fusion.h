/**
 * @file    bmi160_fusion.h
 * @brief   Fusion adaptation layer for BMI160.
 */

#ifndef BMI160_FUSION_H_
#define BMI160_FUSION_H_

#include "Fusion.h"
#include "bmi160.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    FusionBias bias;
    FusionAhrs ahrs;
    FusionRemapAlignment alignment;
} BMI160_Fusion_t;

#define BMI160_FUSION_SAMPLE_RATE_HZ    100U
#define BMI160_FUSION_SAMPLE_PERIOD_S   (1.0f / BMI160_FUSION_SAMPLE_RATE_HZ)

int8_t BMI160_FusionInit(BMI160_Fusion_t *fusion);
int8_t BMI160_FusionUpdate(BMI160_Fusion_t *fusion);
FusionEuler BMI160_FusionGetEuler(const BMI160_Fusion_t *fusion);

#ifdef __cplusplus
}
#endif

#endif /* BMI160_FUSION_H_ */
