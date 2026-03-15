/**
 * @file motor_encoder_testcase.c
 * @brief Motor direction and encoder test cases.
 */

#include "ch32v30x.h"
#include "sdkconfig.h"
#include "debug.h"
#include "timer.h"
#include "timer_encoder.h"
#include "timer_pwm.h"
#include "shell.h"

void TIMERX_MOTOR_Dir_GPIO_Init(void);
static void motor_encoder_print_sample(TIM_TypeDef *tim, const char *label);

static void motor_encoder_run(TIM_TypeDef *tim, const char *label, int num)
{
    for (int i = 0; i < num; i++) {
        motor_encoder_print_sample(tim, label);
        Delay_Ms(500);
    }
}

/**
 * @brief Run motor and encoder test with selected mode.
 *
 * @param mode Test mode.
 * @param num Loop count for encoder sampling.
 * @return 0 on completion.
 */
int motor_encoder_func(int mode, int num)
{
    if (num <= 0) {
        num = 10;
    }

    TIMERX_MOTOR_Dir_GPIO_Init();
    TIMER_PWM_GPIO_Init();
    TIMER_ENCODER_GPIO_Init();

    GPIO_SetBits(GPIOE, GPIO_Pin_8);
    GPIO_SetBits(GPIOE, GPIO_Pin_9);

    switch (mode) {
    case 1:
        GPIO_SetBits(GPIOE, GPIO_Pin_0);
        GPIO_ResetBits(GPIOE, GPIO_Pin_1);
        motor_encoder_run(SDK_USING_TIM5_DEVICE, "TIM5", num);
        GPIO_ResetBits(GPIOE, GPIO_Pin_0);
        GPIO_ResetBits(GPIOE, GPIO_Pin_1);
        printf("\r\n\r\n");
        return 0;

    case 2:
        GPIO_ResetBits(GPIOE, GPIO_Pin_2);
        GPIO_SetBits(GPIOE, GPIO_Pin_3);
        motor_encoder_run(SDK_USING_TIM8_DEVICE, "TIM8", num);
        GPIO_ResetBits(GPIOE, GPIO_Pin_2);
        GPIO_ResetBits(GPIOE, GPIO_Pin_3);
        printf("\r\n\r\n");
        return 0;

    case 3:
        GPIO_SetBits(GPIOE, GPIO_Pin_4);
        GPIO_ResetBits(GPIOE, GPIO_Pin_5);
        motor_encoder_run(SDK_USING_TIM3_DEVICE, "TIM3", num);
        GPIO_ResetBits(GPIOE, GPIO_Pin_4);
        GPIO_ResetBits(GPIOE, GPIO_Pin_5);
        printf("\r\n\r\n");
        return 0;

    case 4:
        GPIO_ResetBits(GPIOE, GPIO_Pin_6);
        GPIO_SetBits(GPIOE, GPIO_Pin_7);
        motor_encoder_run(SDK_USING_TIM4_DEVICE, "TIM4", num);
        GPIO_ResetBits(GPIOE, GPIO_Pin_6);
        GPIO_ResetBits(GPIOE, GPIO_Pin_7);
        printf("\r\n\r\n");
        return 0;

    case 5:
        TIM_GPIO_Init();

        GPIO_ResetBits(GPIOE, GPIO_Pin_0); /* M1 */
        GPIO_SetBits(GPIOE, GPIO_Pin_1);

        GPIO_SetBits(GPIOE, GPIO_Pin_2); /* M2 */
        GPIO_ResetBits(GPIOE, GPIO_Pin_3);

        GPIO_ResetBits(GPIOE, GPIO_Pin_6); /* M3 */
        GPIO_SetBits(GPIOE, GPIO_Pin_7);

        GPIO_ResetBits(GPIOE, GPIO_Pin_4); /* M4 */
        GPIO_SetBits(GPIOE, GPIO_Pin_5);

        for (int i = 0; i < num; i++) {
            motor_encoder_print_sample(SDK_USING_TIM5_DEVICE, "TIM5");
            motor_encoder_print_sample(SDK_USING_TIM8_DEVICE, "TIM8");
            motor_encoder_print_sample(SDK_USING_TIM3_DEVICE, "TIM3");
            motor_encoder_print_sample(SDK_USING_TIM4_DEVICE, "TIM4");
            Delay_Ms(500);
        }

        printf("\r\n\r\n");
        return 0;

    default:
        return 0;
    }
}

SHELL_EXPORT_CMD(SHELL_CMD_PERMISSION(0) | SHELL_CMD_TYPE(SHELL_TYPE_CMD_FUNC),
                 motor_encoder_func,
                 motor_encoder_func,
                 test board timer and motor func);

/**
 * @brief Initialize motor direction control GPIOs.
 */
void TIMERX_MOTOR_Dir_GPIO_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStructure = {0};

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOE, ENABLE);
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_0 | GPIO_Pin_1 |
                                  GPIO_Pin_2 | GPIO_Pin_3 |
                                  GPIO_Pin_4 | GPIO_Pin_5 |
                                  GPIO_Pin_6 | GPIO_Pin_7 |
                                  GPIO_Pin_8 | GPIO_Pin_9;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOE, &GPIO_InitStructure);
}

static void motor_encoder_print_sample(TIM_TypeDef *tim, const char *label)
{
    uint16_t count = TIM_GetCounter(tim);
    const char *dir = (((tim->CTLR1) & TIM_DIR) == TIM_DIR) ? "REV" : "FWD";

    printf("%s count=%u dir=%s\r\n", label, count, dir);
}
