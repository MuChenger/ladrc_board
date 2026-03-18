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
#include "gpio_pin.h"
#include "shell.h"
#include "elog.h"

#ifdef LOG_TAG
#undef LOG_TAG
#endif /* LOG_TAG */

#define LOG_TAG "testcase/motor/"

#if defined(SDK_USING_TESTCASE_MOTOR) 

void TIMERX_MOTOR_Dir_GPIO_Init(void);
static void motor_encoder_print_sample(TIM_TypeDef *tim, const char *label);
static void motor_pin_set(const char *pin_name);
static void motor_pin_reset(const char *pin_name);
static void motor_set_m1(uint8_t pin1_high, uint8_t pin2_high);
static void motor_set_m2(uint8_t pin1_high, uint8_t pin2_high);
static void motor_set_m3(uint8_t pin1_high, uint8_t pin2_high);
static void motor_set_m4(uint8_t pin1_high, uint8_t pin2_high);

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
int case_motor(int mode, int num)
{
    if (num <= 0) {
        num = 10;
    }

    TIMERX_MOTOR_Dir_GPIO_Init();
    TIMER_PWM_GPIO_Init();
    TIMER_ENCODER_GPIO_Init();

    motor_pin_set(SDK_USING_STOP_PIN1);
    motor_pin_set(SDK_USING_STOP_PIN2);

    switch (mode) {
    case 1:
        motor_set_m1(1, 0);
        motor_encoder_run(SDK_USING_TIM5_DEVICE, "TIM5", num);
        motor_set_m1(0, 0);
        log_d("\r\n");
        return 0;

    case 2:
        motor_set_m2(0, 1);
        motor_encoder_run(SDK_USING_TIM8_DEVICE, "TIM8", num);
        motor_set_m2(0, 0);
        log_d("\r\n");
        return 0;

    case 3:
        motor_set_m3(1, 0);
        motor_encoder_run(SDK_USING_TIM3_DEVICE, "TIM3", num);
        motor_set_m3(0, 0);
        log_d("\r\n");
        return 0;

    case 4:
        motor_set_m4(0, 1);
        motor_encoder_run(SDK_USING_TIM4_DEVICE, "TIM4", num);
        motor_set_m4(0, 0);
        log_d("\r\n");
        return 0;

    case 5:
        TIM_GPIO_Init();

        motor_set_m1(0, 1);
        motor_set_m2(1, 0);
        motor_set_m3(0, 1);
        motor_set_m4(0, 1);

        for (int i = 0; i < num; i++) {
            motor_encoder_print_sample(SDK_USING_TIM5_DEVICE, "TIM5");
            motor_encoder_print_sample(SDK_USING_TIM8_DEVICE, "TIM8");
            motor_encoder_print_sample(SDK_USING_TIM3_DEVICE, "TIM3");
            motor_encoder_print_sample(SDK_USING_TIM4_DEVICE, "TIM4");
            Delay_Ms(500);
        }

        log_d("\r\n");
        return 0;

    default:
        return 0;
    }
}

/**
 * @brief Initialize motor direction control GPIOs.
 */
void TIMERX_MOTOR_Dir_GPIO_Init(void)
{
    const char *pins[] = {
        SDK_USING_M1_PIN1, SDK_USING_M1_PIN2,
        SDK_USING_M2_PIN1, SDK_USING_M2_PIN2,
        SDK_USING_M3_PIN1, SDK_USING_M3_PIN2,
        SDK_USING_M4_PIN1, SDK_USING_M4_PIN2,
        SDK_USING_STOP_PIN1, SDK_USING_STOP_PIN2
    };
    GPIO_InitTypeDef GPIO_InitStructure = {0};
    uint8_t i;

    for (i = 0; i < (uint8_t)(sizeof(pins) / sizeof(pins[0])); i++) {
        RCC_APB2PeriphClockCmd(SDK_GetGPIORCC(pins[i]), ENABLE);
        GPIO_InitStructure.GPIO_Pin = SDK_GetPin(pins[i]);
        GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
        GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
        GPIO_Init(SDK_GetPort(pins[i]), &GPIO_InitStructure);
    }
}

static void motor_encoder_print_sample(TIM_TypeDef *tim, const char *label)
{
    uint16_t count = TIM_GetCounter(tim);
    const char *dir = (((tim->CTLR1) & TIM_DIR) == TIM_DIR) ? "REV" : "FWD";

    printf("%s count=%u dir=%s\r\n", label, count, dir);
}

static void motor_pin_set(const char *pin_name)
{
    GPIO_SetBits(SDK_GetPort(pin_name), SDK_GetPin(pin_name));
}

static void motor_pin_reset(const char *pin_name)
{
    GPIO_ResetBits(SDK_GetPort(pin_name), SDK_GetPin(pin_name));
}

static void motor_set_m1(uint8_t pin1_high, uint8_t pin2_high)
{
    if (pin1_high) motor_pin_set(SDK_USING_M1_PIN1); else motor_pin_reset(SDK_USING_M1_PIN1);
    if (pin2_high) motor_pin_set(SDK_USING_M1_PIN2); else motor_pin_reset(SDK_USING_M1_PIN2);
}

static void motor_set_m2(uint8_t pin1_high, uint8_t pin2_high)
{
    if (pin1_high) motor_pin_set(SDK_USING_M2_PIN1); else motor_pin_reset(SDK_USING_M2_PIN1);
    if (pin2_high) motor_pin_set(SDK_USING_M2_PIN2); else motor_pin_reset(SDK_USING_M2_PIN2);
}

static void motor_set_m3(uint8_t pin1_high, uint8_t pin2_high)
{
    if (pin1_high) motor_pin_set(SDK_USING_M3_PIN1); else motor_pin_reset(SDK_USING_M3_PIN1);
    if (pin2_high) motor_pin_set(SDK_USING_M3_PIN2); else motor_pin_reset(SDK_USING_M3_PIN2);
}

static void motor_set_m4(uint8_t pin1_high, uint8_t pin2_high)
{
    if (pin1_high) motor_pin_set(SDK_USING_M4_PIN1); else motor_pin_reset(SDK_USING_M4_PIN1);
    if (pin2_high) motor_pin_set(SDK_USING_M4_PIN2); else motor_pin_reset(SDK_USING_M4_PIN2);
}

SHELL_EXPORT_CMD(SHELL_CMD_PERMISSION(0) | SHELL_CMD_TYPE(SHELL_TYPE_CMD_FUNC),
                 case_motor,
                 case_motor,
                 test board encoder & motor);

#endif /* SDK_USING_TESTCASE_MOTOR */
