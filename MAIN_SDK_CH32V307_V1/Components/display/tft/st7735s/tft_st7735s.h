/**
 * @file tft_st7735s.h
 * @brief ST7735S TFT display driver interface.
 */

#ifndef USER_PERIPHERAL_DRIVER_TFT_ST7735S_TFT_ST7735S_H_
#define USER_PERIPHERAL_DRIVER_TFT_ST7735S_TFT_ST7735S_H_

#include "spi.h"
#include "gpio_pin.h"
#include "sdkconfig.h"

#define X_MAX_PIXEL         128
#define Y_MAX_PIXEL         128

#define RED     0xf800
#define GREEN   0x07e0
#define BLUE    0x001f
#define WHITE   0xffff
#define BLACK   0x0000
#define YELLOW  0xFFE0
#define GRAY0   0xEF7D // cleaned legacy comment
#define GRAY1   0x8410 // cleaned legacy comment
#define GRAY2   0x4208 // cleaned legacy comment

#define LCD_LED_SET
#define LCD_LED_CLR

#ifndef SDK_USING_LCD_INTERFACE_INSTANCE
#define SDK_USING_LCD_INTERFACE_INSTANCE SDK_USING_SPI3_DEVICE
#endif

const char *LCD_InterfaceGetCsPin(void);

#define LCD_CS_CLR  GPIO_ResetBits(SDK_GetPort(LCD_InterfaceGetCsPin()), SDK_GetPin(LCD_InterfaceGetCsPin())) // CS
#define LCD_CS_SET  GPIO_SetBits(SDK_GetPort(LCD_InterfaceGetCsPin()), SDK_GetPin(LCD_InterfaceGetCsPin()))

#define LCD_RS_CLR  GPIO_ResetBits(SDK_GetPort(SDK_USING_LCD_DC), SDK_GetPin(SDK_USING_LCD_DC))   // DC
#define LCD_RS_SET  GPIO_SetBits(SDK_GetPort(SDK_USING_LCD_DC), SDK_GetPin(SDK_USING_LCD_DC))

#define LCD_RST_CLR GPIO_ResetBits(SDK_GetPort(SDK_USING_LCD_RST), SDK_GetPin(SDK_USING_LCD_RST)) // RES
#define LCD_RST_SET GPIO_SetBits(SDK_GetPort(SDK_USING_LCD_RST), SDK_GetPin(SDK_USING_LCD_RST))


void LCD_GPIO_Init(void);
void LCD_ON(void);
void LCD_OFF(void);
void Lcd_WriteIndex(u8 Index);
void Lcd_WriteData(u8 Data);
void Lcd_WriteReg(u8 Index, u8 Data);
u16 Lcd_ReadReg(u8 LCD_Reg);
void Lcd_Reset(void);
void LCD_INIT(void);
void Lcd_Clear(u16 Color);
void Lcd_SetXY(u16 x, u16 y);
void Gui_DrawPoint(u16 x, u16 y, u16 Data);
void Gui_FillRectangle(u16 x1, u16 y1, u16 x2, u16 y2, u16 color);
unsigned int Lcd_ReadPoint(u16 x, u16 y);
void Lcd_SetRegion(u16 x_start, u16 y_start, u16 x_end, u16 y_end);
void LCD_WriteData_16Bit(u16 Data);
#endif /* USER_PERIPHERAL_DRIVER_TFT_ST7735S_TFT_ST7735S_H_ */


