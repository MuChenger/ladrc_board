/**
 * @file    init.h
 * @brief   Automatic initialization items referenced by main.c.
 */

#ifndef USER_INIT_H_
#define USER_INIT_H_

#include "auto_init.h"
#include "ch32v30x.h"
#include "ch32v30x_it.h"
#include "chry_ringbuffer.h"
#include "debug.h"
#include "elog.h"
#include "imu/bmi160/bmi160.h"
#include "lshell_port.h"
#include "MultiTimer.h"
#include "simulation.h"
#include "tft_st7735s.h"
#include "timer.h"

#ifdef LOG_TAG
#undef LOG_TAG
#endif /* LOG_TAG */

#define LOG_TAG "Init"

static int easylogger_service_init(void);
static int shell_service_init(void);
/**
 * @brief   Shared ring buffer instance defined in main.c.
 */
extern chry_ringbuffer_t chry_rbuffer_tid;

/**
 * @brief   Backing storage for the UART receive ring buffer.
 */
static uint8_t rbuffer_pool[1024];

/**
 * @brief   Initialize the board core services and debug UART.
 *
 * @return  0 on success.
 */
static int board_startup_init(void)
{
    NVIC_PriorityGroupConfig(NVIC_PriorityGroup_2);
    Delay_Init();
    USART_Printf_Init(115200);
    shell_service_init();
    easylogger_service_init();
    log_i("USART Printf Init Success.");
    log_i("Shell Init Success.");
    return 0;
}
INIT_BOARD_EXPORT(board_startup_init);

/**
 * @brief   Initialize the EasyLogger service.
 *
 * @return  0 on success, -1 on failure.
 */
static int easylogger_service_init(void)
{
    uint8_t level;
    const size_t default_fmt = ELOG_FMT_LVL | ELOG_FMT_TAG | ELOG_FMT_TIME;

    if (elog_init() != ELOG_NO_ERR) {
        return -1;
    }

    for (level = ELOG_LVL_ASSERT; level <= ELOG_LVL_VERBOSE; level++) {
        elog_set_fmt(level, default_fmt);
    }

    elog_start();

    return 0;
}

/**
 * @brief   Initialize the shell service.
 *
 * @return  0 on success.
 */
static int shell_service_init(void)
{
    Shell_INIT();
    return 0;
}

/**
 * @brief   Initialize the BMI160 IMU on I2C2.
 *
 * This initialization is non-fatal. If the sensor is not populated on the
 * board, the system continues booting and prints the detected status.
 *
 * @return  0 on completion.
 */
static int bmi160_service_init(void)
{
#if defined(SDK_USING_I2C2)
    int8_t status;

    status = BMI160_InitAuto();
    if (status == BMI160_OK) {
        log_i("BMI160 init success.");
    } else {
        log_w("BMI160 init skipped, status=%d.", status);
    }
#endif /* SDK_USING_I2C2 */

    return 0;
}
INIT_DEVICE_EXPORT(bmi160_service_init);

/**
 * @brief   Initialize the communication ring buffer.
 *
 * @return  0 on success, -1 on failure.
 */
static int ringbuffer_service_init(void)
{
    if (0 == chry_ringbuffer_init(&chry_rbuffer_tid, rbuffer_pool, sizeof(rbuffer_pool))) {
        log_i("Ringbuffer init success.");
        return 0;
    }
    log_w("Ringbuffer init error.");
    return -1;
}
INIT_COMPONENT_EXPORT(ringbuffer_service_init);

#ifdef LDARC_COMPONENT_MULTITIMER
/**
 * @brief   Initialize the multitimer service.
 *
 * @return  0 on success.
 */
static int multitimer_service_init(void)
{
    multiTimerInstall(getPlatformTicks);
    log_i("Multitimer init success.");
    return 0;
}
INIT_COMPONENT_EXPORT(multitimer_service_init);
#endif /* LDARC_COMPONENT_MULTITIMER */

#ifdef LDARC_COMPONENT_TFT
/**
 * @brief   Initialize the TFT display module.
 *
 * @return  0 on success.
 */
static int tft_service_init(void)
{
    LCD_INIT();
    log_i("LCD init success.");
    return 0;
}
INIT_COMPONENT_EXPORT(tft_service_init);
#endif /* LDARC_COMPONENT_TFT */

#ifdef LDARC_COMPONENT_TFT_OFF
/**
 * @brief   Set the TFT display to the default off state.
 *
 * @return  0 on success.
 */
static int tft_off_service_init(void)
{
    LCD_OFF();
    log_i("LCD off success.");
    return 0;
}
INIT_APP_EXPORT(tft_off_service_init);
#endif /* LDARC_COMPONENT_TFT_OFF */

#if defined(SDK_USING_TIM2) || defined(SDK_USING_TIM6) || defined(SDK_USING_TIM7)
/**
 * @brief   Initialize timer-related GPIO resources.
 *
 * @return  0 on success.
 */
static int timer_gpio_init(void)
{
    TIM_GPIO_Init();
    log_i("TIM init success.");
    return 0;
}
INIT_DEVICE_EXPORT(timer_gpio_init);
#endif /* SDK_USING_TIM2 || SDK_USING_TIM6 || SDK_USING_TIM7 */

#ifdef LDARC_COMPONENT_SIMULATION
/**
 * @brief   Initialize the simulation module.
 *
 * @return  0 on success.
 */
static int simulation_service_init(void)
{
    SIMULATION_INIT();
    SIMULATION_DINIT();
    log_i("Simulation init success.");
    return 0;
}
INIT_APP_EXPORT(simulation_service_init);
#endif /* LDARC_COMPONENT_SIMULATION */

#endif /* USER_INIT_H_ */
