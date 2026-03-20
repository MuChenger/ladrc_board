# Testcase 使用文档

本文档说明 `Testcase` 目录下可通过 shell 调用的测试命令、参数含义与典型用法。

## 1. 使用前准备

1. 确认 `sdkconfig.h` 已开启对应测试宏（例如 `SDK_USING_TESTCASE_GPIO`、`SDK_USING_TESTCASE_W25Q16` 等）。
2. 下载程序并打开串口 shell（默认常见为 `115200 8N1`，以工程实际配置为准）。
3. 在 shell 输入命令执行测试。

## 2. 命令速查

| 命令 | 参数 | 说明 | 示例 |
| --- | --- | --- | --- |
| `case_gpio` | `cnt` | LED 翻转次数 | `case_gpio 10` |
| `case_adc` | `cnt` | ADC 采样输出次数（<=0 默认100） | `case_adc 50` |
| `case_ble` | `para` | UART2/BLE 回环处理字节数（<=0 默认100） | `case_ble 100` |
| `case_rs485` | `para` | UART6/RS485 回环处理字节数（<=0 默认100） | `case_rs485 100` |
| `case_i2cscan` | 无 | 扫描已启用 I2C 总线设备 | `case_i2cscan` |
| `i2c_mpu6050_dmp_func` | `cnt` | MPU6050 采样次数（<=0 默认100） | `i2c_mpu6050_dmp_func 100` |
| `case_bmi160` | `mode cnt` | BMI160 原始数据/Fusion 测试 | `case_bmi160 0 100` |
| `case_multitimer` | `period_ms` | 启动周期定时输出 | `case_multitimer 1000` |
| `case_easylogger` | `mode` | EasyLogger 功能测试 | `case_easylogger 2` |
| `case_lcd` | `mode` | ST7735S 屏幕功能测试 | `case_lcd 3` |
| `case_sgl` | `mode` | SGL 组件渲染测试 | `case_sgl 7` |
| `case_motor` | `mode num` | 电机与编码器测试 | `case_motor 1 20` |
| `case_flash` | `cnt` | W25Qxx 擦写读测试（参数未使用） | `case_flash 0` |
| `case_sfud` | `mode` | SFUD 快速自检（参数未使用） | `case_sfud 0` |
| `case_fdb` | `mode` | FlashDB KVDB 示例测试 | `case_fdb 4` |

## 3. 详细说明

### 3.1 GPIO

- 命令: `case_gpio <cnt>`
- 行为: 按次数循环点亮/熄灭 `sdkconfig.h` 中配置的 LED1/LED2。

### 3.2 ADC

- 命令: `case_adc <cnt>`
- 行为: 循环读取 6 路 ADC 值并打印转换结果。

### 3.3 BLE（UART2）

- 命令: `case_ble <para>`
- 行为: 从 UART2 收到数据后回发到 UART2，并镜像到 USART1。

### 3.4 RS485（UART6）

- 命令: `case_rs485 <para>`
- 行为: 从 UART6 收到数据后回发到 UART6，并镜像到 USART1。

### 3.5 I2C 扫描

- 命令: `case_i2cscan`
- 行为: 扫描 `sdkconfig.h` 中启用的 I2C 外设（I2C1/I2C2），打印应答地址。

### 3.6 MPU6050

- 命令: `i2c_mpu6050_dmp_func <cnt>`
- 行为:
  - 若编译启用 `DMP`，打印 `Yaw/Pitch/Roll`
  - 否则打印温度

### 3.7 BMI160

- 命令: `case_bmi160 <mode> <cnt>`
- `mode`:
  - `0`: 打印加速度、陀螺仪、温度
  - `1`: 运行 Fusion，打印欧拉角

### 3.8 MultiTimer

- 命令: `case_multitimer <period_ms>`
- 行为: 周期输出超时日志；`period_ms=0` 会提示用法并返回错误。

### 3.9 EasyLogger

- 命令: `case_easylogger <mode>`
- `mode`:
  - `0`: 输出各级别彩色日志
  - `1`: 过滤器行为测试
  - `2`: hexdump 示例
  - `3`: raw 输出示例

### 3.10 LCD（ST7735S）

- 命令: `case_lcd <mode>`
- `mode`:
  - `1`: 关屏
  - `2`: 开屏
  - `3`: 多颜色清屏测试
  - `4`: 画圆
  - `5`: 字符显示测试

### 3.11 SGL

- 命令: `case_sgl <mode>`
- `mode`:
  - `0`: label
  - `1`: button
  - `2`: slider
  - `3`: progress
  - `4`: switch + checkbox
  - `5`: led + ring
  - `6`: rect + line
  - `7`: 组合动画 demo

### 3.12 电机与编码器

- 命令: `case_motor <mode> <num>`
- `mode`:
  - `1`: M1 + TIM5
  - `2`: M2 + TIM8
  - `3`: M3 + TIM3
  - `4`: M4 + TIM4
  - `5`: 四路联合测试
- `num`: 采样打印次数（<=0 默认10）

### 3.13 W25Qxx 原始驱动测试

- 命令: `case_flash 0`
- 行为: 读取 ID、擦除扇区、写入测试字符串、再读回。

### 3.14 SFUD 快速自检

- 命令: `case_sfud 0`
- 行为: 初始化 SFUD，读取状态寄存器和起始地址数据头。

### 3.15 FlashDB KVDB 示例

- 命令: `case_fdb <mode>`
- `mode`:
  - `1`: 字符串 KV 写/读（`hello`）
  - `2`: Blob KV 写/读（`count_blob`）
  - `3`: 删除 KV 并验证
  - `4`: 迭代并打印全部 KV
  - 其它值: 打印帮助并输出当前 KV 列表

## 4. 常见问题

1. 命令找不到  
原因: 对应测试宏未启用或源文件未编入工程。  
建议: 检查 `sdkconfig.h` 与工程文件列表。

2. 传感器类测试无数据  
原因: 硬件未连接、引脚配置不一致、总线冲突。  
建议: 先执行 `case_i2cscan` 确认设备地址是否可见。

3. FlashDB/SFUD 初始化失败  
原因: SPI/CS 引脚配置错误或外部 Flash 不在线。  
建议: 先跑 `case_flash`、`case_sfud`，确认底层读写正常后再跑 `case_fdb`。
