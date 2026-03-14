/**
 * @file    bmi160.c
 * @brief   BMI160 IMU driver over I2C2.
 */

#include "bmi160.h"
#include "debug.h"
#include "i2c.h"

#define BMI160_I2C_PORT                  I2C2
#define BMI160_I2C_CLOCK_HZ              100000U
#define BMI160_I2C_OWN_ADDRESS           0x00U
#define BMI160_I2C_TIMEOUT               0x20000UL

#define BMI160_REG_CHIP_ID               0x00U
#define BMI160_REG_GYRO_DATA             0x0CU
#define BMI160_REG_ACCEL_DATA            0x12U
#define BMI160_REG_ACCEL_CONF            0x40U
#define BMI160_REG_ACCEL_RANGE           0x41U
#define BMI160_REG_GYRO_CONF             0x42U
#define BMI160_REG_GYRO_RANGE            0x43U
#define BMI160_REG_CMD                   0x7EU
#define BMI160_REG_TEMP_DATA             0x20U

#define BMI160_CMD_SOFT_RESET            0xB6U
#define BMI160_CMD_ACCEL_NORMAL          0x11U
#define BMI160_CMD_GYRO_NORMAL           0x15U

#define BMI160_ACCEL_ODR_100HZ           0x08U
#define BMI160_ACCEL_BW_NORMAL_AVG4      0x02U
#define BMI160_ACCEL_RANGE_2G            0x03U

#define BMI160_GYRO_ODR_100HZ            0x08U
#define BMI160_GYRO_BW_NORMAL_MODE       0x02U
#define BMI160_GYRO_RANGE_2000_DPS       0x00U

#define BMI160_ACCEL_LSB_PER_G           16384.0f
#define BMI160_GYRO_LSB_PER_DPS          16.4f

#define BMI160_ACCEL_STARTUP_DELAY_MS    5U
#define BMI160_GYRO_STARTUP_DELAY_MS     81U
#define BMI160_SOFT_RESET_DELAY_MS       15U

static uint8_t bmi160_dev_addr = BMI160_I2C_ADDR_LOW;

static void BMI160_I2CBusRecover(void)
{
    RCC_APB1PeriphResetCmd(RCC_APB1Periph_I2C2, ENABLE);
    RCC_APB1PeriphResetCmd(RCC_APB1Periph_I2C2, DISABLE);
    I2C_SoftwareResetCmd(BMI160_I2C_PORT, ENABLE);
    I2C_SoftwareResetCmd(BMI160_I2C_PORT, DISABLE);
    I2C_Cmd(BMI160_I2C_PORT, ENABLE);
    I2C_AcknowledgeConfig(BMI160_I2C_PORT, ENABLE);
}

static int8_t BMI160_WaitEvent(uint32_t event)
{
    uint32_t timeout = BMI160_I2C_TIMEOUT;

    while (!I2C_CheckEvent(BMI160_I2C_PORT, event)) {
        if (timeout-- == 0U) {
            return BMI160_E_TIMEOUT;
        }
    }

    return BMI160_OK;
}

static int8_t BMI160_WaitBusyReset(void)
{
    uint32_t timeout = BMI160_I2C_TIMEOUT;

    while (I2C_GetFlagStatus(BMI160_I2C_PORT, I2C_FLAG_BUSY) != RESET) {
        if (timeout-- == 0U) {
            return BMI160_E_TIMEOUT;
        }
    }

    return BMI160_OK;
}

static int8_t BMI160_WriteRegs(uint8_t reg_addr, const uint8_t *data, uint16_t len)
{
    int8_t status;
    uint16_t index;

    status = BMI160_WaitBusyReset();
    if (status != BMI160_OK) {
        BMI160_I2CBusRecover();
        return status;
    }

    I2C_GenerateSTART(BMI160_I2C_PORT, ENABLE);
    status = BMI160_WaitEvent(I2C_EVENT_MASTER_MODE_SELECT);
    if (status != BMI160_OK) {
        return status;
    }

    I2C_Send7bitAddress(BMI160_I2C_PORT, bmi160_dev_addr, I2C_Direction_Transmitter);
    status = BMI160_WaitEvent(I2C_EVENT_MASTER_TRANSMITTER_MODE_SELECTED);
    if (status != BMI160_OK) {
        I2C_GenerateSTOP(BMI160_I2C_PORT, ENABLE);
        return status;
    }

    I2C_SendData(BMI160_I2C_PORT, reg_addr);
    status = BMI160_WaitEvent(I2C_EVENT_MASTER_BYTE_TRANSMITTED);
    if (status != BMI160_OK) {
        I2C_GenerateSTOP(BMI160_I2C_PORT, ENABLE);
        return status;
    }

    for (index = 0; index < len; index++) {
        I2C_SendData(BMI160_I2C_PORT, data[index]);
        status = BMI160_WaitEvent(I2C_EVENT_MASTER_BYTE_TRANSMITTED);
        if (status != BMI160_OK) {
            I2C_GenerateSTOP(BMI160_I2C_PORT, ENABLE);
            return status;
        }
    }

    I2C_GenerateSTOP(BMI160_I2C_PORT, ENABLE);
    return BMI160_OK;
}

static int8_t BMI160_ReadRegs(uint8_t reg_addr, uint8_t *data, uint16_t len)
{
    int8_t status;
    uint16_t index;

    status = BMI160_WaitBusyReset();
    if (status != BMI160_OK) {
        BMI160_I2CBusRecover();
        return status;
    }

    I2C_GenerateSTART(BMI160_I2C_PORT, ENABLE);
    status = BMI160_WaitEvent(I2C_EVENT_MASTER_MODE_SELECT);
    if (status != BMI160_OK) {
        return status;
    }

    I2C_Send7bitAddress(BMI160_I2C_PORT, bmi160_dev_addr, I2C_Direction_Transmitter);
    status = BMI160_WaitEvent(I2C_EVENT_MASTER_TRANSMITTER_MODE_SELECTED);
    if (status != BMI160_OK) {
        I2C_GenerateSTOP(BMI160_I2C_PORT, ENABLE);
        return status;
    }

    I2C_SendData(BMI160_I2C_PORT, reg_addr);
    status = BMI160_WaitEvent(I2C_EVENT_MASTER_BYTE_TRANSMITTED);
    if (status != BMI160_OK) {
        I2C_GenerateSTOP(BMI160_I2C_PORT, ENABLE);
        return status;
    }

    I2C_GenerateSTART(BMI160_I2C_PORT, ENABLE);
    status = BMI160_WaitEvent(I2C_EVENT_MASTER_MODE_SELECT);
    if (status != BMI160_OK) {
        I2C_GenerateSTOP(BMI160_I2C_PORT, ENABLE);
        return status;
    }

    I2C_Send7bitAddress(BMI160_I2C_PORT, bmi160_dev_addr, I2C_Direction_Receiver);
    status = BMI160_WaitEvent(I2C_EVENT_MASTER_RECEIVER_MODE_SELECTED);
    if (status != BMI160_OK) {
        I2C_GenerateSTOP(BMI160_I2C_PORT, ENABLE);
        return status;
    }

    for (index = 0; index < len; index++) {
        if (index == (len - 1U)) {
            I2C_AcknowledgeConfig(BMI160_I2C_PORT, DISABLE);
            I2C_GenerateSTOP(BMI160_I2C_PORT, ENABLE);
        }

        status = BMI160_WaitEvent(I2C_EVENT_MASTER_BYTE_RECEIVED);
        if (status != BMI160_OK) {
            I2C_AcknowledgeConfig(BMI160_I2C_PORT, ENABLE);
            return status;
        }

        data[index] = I2C_ReceiveData(BMI160_I2C_PORT);
    }

    I2C_AcknowledgeConfig(BMI160_I2C_PORT, ENABLE);
    return BMI160_OK;
}

static int8_t BMI160_WriteByte(uint8_t reg_addr, uint8_t value)
{
    return BMI160_WriteRegs(reg_addr, &value, 1U);
}

static void BMI160_DecodeAxes(const uint8_t *raw, BMI160_Axes_t *axes)
{
    axes->x = (int16_t)(((uint16_t)raw[1] << 8) | raw[0]);
    axes->y = (int16_t)(((uint16_t)raw[3] << 8) | raw[2]);
    axes->z = (int16_t)(((uint16_t)raw[5] << 8) | raw[4]);
}

static void BMI160_ScaleAxes(const BMI160_Axes_t *raw_axes, BMI160_AxesF_t *scaled_axes, float lsb_per_unit)
{
    scaled_axes->x = (float)raw_axes->x / lsb_per_unit;
    scaled_axes->y = (float)raw_axes->y / lsb_per_unit;
    scaled_axes->z = (float)raw_axes->z / lsb_per_unit;
}

static int8_t BMI160_Configure(void)
{
    int8_t status;

    status = BMI160_WriteByte(BMI160_REG_ACCEL_CONF,
        (uint8_t)((BMI160_ACCEL_BW_NORMAL_AVG4 << 4) | BMI160_ACCEL_ODR_100HZ));
    if (status != BMI160_OK) return status;

    status = BMI160_WriteByte(BMI160_REG_ACCEL_RANGE, BMI160_ACCEL_RANGE_2G);
    if (status != BMI160_OK) return status;

    status = BMI160_WriteByte(BMI160_REG_GYRO_CONF,
        (uint8_t)((BMI160_GYRO_BW_NORMAL_MODE << 4) | BMI160_GYRO_ODR_100HZ));
    if (status != BMI160_OK) return status;

    status = BMI160_WriteByte(BMI160_REG_GYRO_RANGE, BMI160_GYRO_RANGE_2000_DPS);
    if (status != BMI160_OK) return status;

    status = BMI160_WriteByte(BMI160_REG_CMD, BMI160_CMD_ACCEL_NORMAL);
    if (status != BMI160_OK) return status;
    Delay_Ms(BMI160_ACCEL_STARTUP_DELAY_MS);

    status = BMI160_WriteByte(BMI160_REG_CMD, BMI160_CMD_GYRO_NORMAL);
    if (status != BMI160_OK) return status;
    Delay_Ms(BMI160_GYRO_STARTUP_DELAY_MS);

    return BMI160_OK;
}

int8_t BMI160_ReadChipId(uint8_t *chip_id)
{
    return BMI160_ReadRegs(BMI160_REG_CHIP_ID, chip_id, 1U);
}

int8_t BMI160_SoftReset(void)
{
    int8_t status = BMI160_WriteByte(BMI160_REG_CMD, BMI160_CMD_SOFT_RESET);
    if (status == BMI160_OK) Delay_Ms(BMI160_SOFT_RESET_DELAY_MS);
    return status;
}

int8_t BMI160_Init(uint8_t dev_addr)
{
    uint8_t chip_id;
    int8_t status;

    bmi160_dev_addr = dev_addr;
    I2C_GPIO_Init(BMI160_I2C_CLOCK_HZ, BMI160_I2C_OWN_ADDRESS);

    status = BMI160_ReadChipId(&chip_id);
    if (status != BMI160_OK) return status;

    if (chip_id != BMI160_CHIP_ID_VALUE) return BMI160_E_NOT_FOUND;

    status = BMI160_SoftReset();
    if (status != BMI160_OK) return status;

    return BMI160_Configure();
}

int8_t BMI160_InitAuto(void)
{
    int8_t status = BMI160_Init(BMI160_I2C_ADDR_LOW);
    return (status == BMI160_OK) ? BMI160_OK : BMI160_Init(BMI160_I2C_ADDR_HIGH);
}

int8_t BMI160_ReadAccel(BMI160_Axes_t *accel)
{
    uint8_t raw[6];
    int8_t status = BMI160_ReadRegs(BMI160_REG_ACCEL_DATA, raw, sizeof(raw));
    if (status == BMI160_OK) BMI160_DecodeAxes(raw, accel);
    return status;
}

int8_t BMI160_ReadGyro(BMI160_Axes_t *gyro)
{
    uint8_t raw[6];
    int8_t status = BMI160_ReadRegs(BMI160_REG_GYRO_DATA, raw, sizeof(raw));
    if (status == BMI160_OK) BMI160_DecodeAxes(raw, gyro);
    return status;
}

int8_t BMI160_ReadAccelGyro(BMI160_Axes_t *accel, BMI160_Axes_t *gyro)
{
    uint8_t raw[12];
    int8_t status = BMI160_ReadRegs(BMI160_REG_GYRO_DATA, raw, sizeof(raw));
    if (status == BMI160_OK) {
        BMI160_DecodeAxes(raw, gyro);
        BMI160_DecodeAxes(&raw[6], accel);
    }
    return status;
}

int8_t BMI160_ReadAccelG(BMI160_AxesF_t *accel_g)
{
    BMI160_Axes_t raw;
    int8_t status = BMI160_ReadAccel(&raw);
    if (status == BMI160_OK) BMI160_ScaleAxes(&raw, accel_g, BMI160_ACCEL_LSB_PER_G);
    return status;
}

int8_t BMI160_ReadGyroDps(BMI160_AxesF_t *gyro_dps)
{
    BMI160_Axes_t raw;
    int8_t status = BMI160_ReadGyro(&raw);
    if (status == BMI160_OK) BMI160_ScaleAxes(&raw, gyro_dps, BMI160_GYRO_LSB_PER_DPS);
    return status;
}

int8_t BMI160_ReadAccelGyroScaled(BMI160_AxesF_t *accel_g, BMI160_AxesF_t *gyro_dps)
{
    BMI160_Axes_t accel_raw, gyro_raw;
    int8_t status = BMI160_ReadAccelGyro(&accel_raw, &gyro_raw);
    if (status == BMI160_OK) {
        BMI160_ScaleAxes(&accel_raw, accel_g, BMI160_ACCEL_LSB_PER_G);
        BMI160_ScaleAxes(&gyro_raw, gyro_dps, BMI160_GYRO_LSB_PER_DPS);
    }
    return status;
}

int8_t BMI160_ReadTemperatureC(float *temperature_c)
{
    uint8_t raw[2];
    int8_t status = BMI160_ReadRegs(BMI160_REG_TEMP_DATA, raw, sizeof(raw));
    if (status == BMI160_OK) {
        int16_t raw_temp = (int16_t)(((uint16_t)raw[1] << 8) | raw[0]);
        *temperature_c = 23.0f + ((float)raw_temp / 512.0f);
    }
    return status;
}
