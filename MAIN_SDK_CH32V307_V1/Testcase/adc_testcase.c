/**
 * @file adc_testcase.c
 * @brief ADC test case.
 */

#include "ch32v30x.h"
#include "sdkconfig.h"
#include "adc.h"
#include "debug.h"
#include "shell.h"
#include "elog.h"

#ifdef LOG_TAG
#undef LOG_TAG
#endif /* LOG_TAG */

#define LOG_TAG "testcase/adc/"
#if defined(SDK_USING_TESTCASE_ADC)

/**
 * @brief Read ADC channels and print converted values.
 *
 * @param cnt Unused.
 * @return Never returns during normal operation.
 */
int case_adc(int cnt)
{
    if (cnt <= 0) {
        cnt = 100;
    }

    ADC_GPIO_Init();

    for (int i = 0; i < cnt; i++) {
        u16 adc_val[6];

        adc_val[0] = Get_ADC_Val(ADC_Channel_4);
        adc_val[1] = Get_ADC_Val(ADC_Channel_5);
        adc_val[2] = Get_ADC_Val(ADC_Channel_12);
        adc_val[3] = Get_ADC_Val(ADC_Channel_13);
        adc_val[4] = Get_ADC_Val(ADC_Channel_14);
        adc_val[5] = Get_ADC_Val(ADC_Channel_15);

        Delay_Ms(100);

        log_i("CH1:%04d CH2:%04d CH3:%04d CH4:%04d CH5:%04d CH6:%04d",
               Get_ConversionVal(adc_val[0]), Get_ConversionVal(adc_val[1]),
               Get_ConversionVal(adc_val[2]), Get_ConversionVal(adc_val[3]),
               Get_ConversionVal(adc_val[4]), Get_ConversionVal(adc_val[5]));
    }

    return 0;
}

SHELL_EXPORT_CMD(SHELL_CMD_PERMISSION(0) | SHELL_CMD_TYPE(SHELL_TYPE_CMD_FUNC),
                 case_adc,
                 case_adc,
                 test board adc);

#endif /* SDK_USING_TESTCASE_ADC */
