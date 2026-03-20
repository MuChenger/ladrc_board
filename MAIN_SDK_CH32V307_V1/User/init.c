/**
 * @file    init.h
 * @brief   Automatic initialization items referenced by main.c.
 */

#ifndef USER_INIT_H_
#define USER_INIT_H_
#include "init.h"

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
    USART_Printf_Init(SDK_USING_USART1_BAUDRATE);
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

#ifdef SDK_USING_BMI160
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
#endif /* SDK_USING_BMI160 */

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

#ifdef SDK_USING_MULTI_TIMER
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
#endif /* SDK_USING_MULTI_TIMER */

#ifdef SDK_USING_LCD
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
#endif /* SDK_USING_LCD */

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

#ifdef SDK_USING_SIMULATION
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
#endif /* SDK_USING_SIMULATION */

#if defined(SDK_USING_SGL)
/**
 * @brief   Initialize the SGL GUI.
 *
 * @return  0 on success.
 */
#define PANEL_WIDTH     128
#define PANEL_HEIGHT    128

static sgl_color_t panel_buffer[PANEL_WIDTH * 10];
static void panel_flush_area(sgl_area_t *area, sgl_color_t *src)
{
    uint16_t width = area->x2 - area->x1 + 1;
    uint16_t height = area->y2 - area->y1 + 1;
    uint32_t pixel_count = (uint32_t)width * height;

    Lcd_SetRegion(area->x1, area->y1, area->x2, area->y2);
    for (uint32_t index = 0; index < pixel_count; index++) {
        LCD_WriteData_16Bit(src[index].full);
    }

    sgl_fbdev_flush_ready();
}

static int sgl_gui_service_init(void)
{
    sgl_fbinfo_t fbinfo = {
        .xres = PANEL_WIDTH,
        .yres = PANEL_HEIGHT,
        .flush_area = panel_flush_area,
        .buffer[0] = panel_buffer,
        .buffer_size = SGL_ARRAY_SIZE(panel_buffer), 
    };

    if (sgl_fbdev_register(&fbinfo) != 0) {
        log_e("sgl fbdev register failed.");
        return -1;
    }
    if (sgl_init() != 0) {
        log_e("sgl init failed.");
        return -1;
    }

    sgl_obj_t *label = sgl_label_create(NULL);
    if (label == NULL) {
        log_e("sgl label create failed.");
        return -1;
    }
    sgl_obj_set_size(label, PANEL_WIDTH, 30);
    sgl_obj_set_pos_align(label, SGL_ALIGN_CENTER);
    sgl_label_set_font(label, &consolas24);
    sgl_label_set_text(label, "Hello!");
    log_i("sgl gui init success.");
    return 0;
}
INIT_ENV_EXPORT(sgl_gui_service_init);

#ifdef SDK_USING_FLASHDB
/**
 * @brief   Initialize the flashdb.
 *
 * @return  0 on success.
 */

struct fdb_kvdb default_kvdb = {0};

static int flashdb_service_init(void)
{
    extern volatile uint8_t kvdb_inited;

    fdb_err_t result;
    struct fdb_default_kv default_kv;

    result = fdb_kvdb_init(&default_kvdb, "default", "fdb_kvdb1", &default_kv, NULL);
    if (result != FDB_NO_ERR) {
        log_e("fdb_kvdb_init failed, err=%d.", (int)result);
        return -1;
    }
    log_d("fdb_kvdb_init success.");
    return 0;
}
INIT_APP_EXPORT(flashdb_service_init);
#endif /* SDK_USING_FLASHDB */

#endif /* SDK_USING_SGL */
#endif /* USER_INIT_H_ */
