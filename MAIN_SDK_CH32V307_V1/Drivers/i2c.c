/**
 * @file    i2c.c
 * @brief   I2C driver implementation by sdkconfig.
 * @author  LADRC Board
 * @date    2026-03-12
 */

#include "i2c.h"
#include "gpio_pin.h"

#if defined(SDK_USING_I2C1) || defined(SDK_USING_I2C2)

static int I2C_GetBusConfig(I2C_TypeDef *i2c_device,
                            const char **scl_pin,
                            const char **sda_pin,
                            uint32_t *apb1_periph)
{
#ifdef SDK_USING_I2C1
    if (i2c_device == SDK_USING_I2C1_DEVICE) {
        *scl_pin = SDK_USING_I2C1_SCL;
        *sda_pin = SDK_USING_I2C1_SDA;
        *apb1_periph = RCC_APB1Periph_I2C1;
        return 1;
    }
#endif

#ifdef SDK_USING_I2C2
    if (i2c_device == SDK_USING_I2C2_DEVICE) {
        *scl_pin = SDK_USING_I2C2_SCL;
        *sda_pin = SDK_USING_I2C2_SDA;
        *apb1_periph = RCC_APB1Periph_I2C2;
        return 1;
    }
#endif

    return 0;
}

/**
 * @brief Configure selected I2C pins and peripheral from sdkconfig.
 * @param i2c_device I2C device instance from sdkconfig.
 * @param bound I2C bus clock in Hz.
 * @param address Local own address.
 */
void I2C_GPIO_InitEx(I2C_TypeDef *i2c_device, u32 bound, u16 address)
{
    GPIO_InitTypeDef GPIO_InitStructure = {0};
    I2C_InitTypeDef I2C_InitTSturcture = {0};
    const char *scl_pin = 0;
    const char *sda_pin = 0;
    uint32_t apb1_periph = 0;

    if (!I2C_GetBusConfig(i2c_device, &scl_pin, &sda_pin, &apb1_periph)) {
        return;
    }

    /* Enable clocks for selected GPIO ports and I2C peripheral. */
    RCC_APB2PeriphClockCmd(SDK_GetGPIORCC(scl_pin), ENABLE);
    RCC_APB2PeriphClockCmd(SDK_GetGPIORCC(sda_pin), ENABLE);
    RCC_APB1PeriphClockCmd(apb1_periph, ENABLE);

    /* Configure SCL and SDA as open-drain alternate function. */
    GPIO_InitStructure.GPIO_Pin = SDK_GetPin(scl_pin);
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AF_OD;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(SDK_GetPort(scl_pin), &GPIO_InitStructure);

    GPIO_InitStructure.GPIO_Pin = SDK_GetPin(sda_pin);
    GPIO_Init(SDK_GetPort(sda_pin), &GPIO_InitStructure);

    /* Configure I2C timing and addressing mode. */
    I2C_InitTSturcture.I2C_ClockSpeed = bound;
    I2C_InitTSturcture.I2C_Mode = I2C_Mode_I2C;
    I2C_InitTSturcture.I2C_DutyCycle = I2C_DutyCycle_2;
    I2C_InitTSturcture.I2C_OwnAddress1 = address;
    I2C_InitTSturcture.I2C_Ack = I2C_Ack_Enable;
    I2C_InitTSturcture.I2C_AcknowledgedAddress = I2C_AcknowledgedAddress_7bit;
    I2C_Init(i2c_device, &I2C_InitTSturcture);

    I2C_Cmd(i2c_device, ENABLE);
    I2C_AcknowledgeConfig(i2c_device, ENABLE);

    Delay_Ms(50);
}

void I2C_GPIO_Init(u32 bound, u16 address)
{
#ifdef SDK_USING_I2C2
    I2C_GPIO_InitEx(SDK_USING_I2C2_DEVICE, bound, address);
#elif defined(SDK_USING_I2C1)
    I2C_GPIO_InitEx(SDK_USING_I2C1_DEVICE, bound, address);
#endif
}

#endif // SDK_USING_I2C1 || SDK_USING_I2C2
