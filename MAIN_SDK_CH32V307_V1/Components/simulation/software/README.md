# 控制算法模拟器-by嵌入式新起点 软件说明

## 1. 文档说明

本文档为本软件的统一说明文件，已整合以下内容：

- 软件使用说明
- Python / EXE 运行依赖说明
- 仿真原理说明
- 上下位机串口通信协议说明
- 下位机 `printf` 输出示例

说明：

- `requirements_pyqt.txt` 仍保留在工程中，仅作为 `pip install -r` 的安装清单使用
- 原 `simulation_protocol_guide.md` 的内容已并入本文档，不再单独维护

---

## 2. 软件定位

本软件用于控制算法联调与被控对象仿真，典型用途如下：

- 下位机运行 `PID / LADRC / 开环` 等控制算法
- 下位机周期上传遥测数据
- 上位机根据下位机上传的 `u_cmd` 运行对象模型
- 上位机根据当前对接协议，仅在必要时向下位机下发控制命令与参数同步，并主动轮询状态
- 界面同时提供：
  - 实时波形
  - 3D 模型观察
  - 串口联调
  - 日志控制台
  - 参数设置与预设命令

可以简单理解为：

```text
上位机下发必要命令/状态查询 -> 下位机返回状态 -> 上位机显示/仿真 -> 按需继续同步
```

---

## 3. 运行环境与依赖

## 3.1 EXE 运行

如果你使用打包后的 `.exe` 文件，通常无需手动安装 Python 依赖，直接运行即可。

首次启动时软件会显示欢迎页，用户可以：

- 点击 `开始使用`
- 勾选或取消 `启动时显示欢迎页`
- 从欢迎页进入 `设备连接 / 控制参数 / 波形工作台 / 3D 视图`

## 3.2 Python 源码运行

建议环境：

- Python `3.9+`
- Windows 环境优先

安装方式：

```powershell
cd Components\simulation\software
pip install -r requirements_pyqt.txt
```

当前依赖如下：

| 依赖 | 版本要求 | 作用 |
|---|---:|---|
| `PyQt5` | `>=5.15` | 主界面与工作台 |
| `pyqtgraph` | `>=0.13` | 波形显示与 3D 基础可视化 |
| `pyserial` | `>=3.5` | 串口通信 |
| `PyOpenGL` | `>=3.1` | 3D 模型显示 |

启动方式：

```powershell
python run.py
```

---

## 4. 快速开始

建议按下面顺序使用软件：

1. 打开软件
2. 在左侧 `设备` 页选择串口和波特率
3. 点击 `连接`
4. 在左侧 `控制` 页选择算法、参考值、扰动等级、运行周期
5. 点击 `启动`
6. 中间查看实时波形
7. 右侧查看 3D 模型和运行状态
8. 需要保存调试数据时，点击 `开始录制`

如果没有连接下位机，也可以单独启动软件进行本地仿真观察。

---

## 5. 界面布局说明

当前软件采用工作台式布局，结构如下：

## 5.1 左侧工作区

### 设备

用于：

- 选择串口
- 选择波特率
- 连接 / 断开
- 切换是否使用二进制串口帧（兼容旧反馈链路）

当前串口下拉框支持的波特率为：`9600 / 115200 / 230400 / 460800 / 921600`。

### 控制

用于：

- 切换算法
- 设置参考值
- 设置环境扰动等级
- 设置上位机运行周期
- 启动 / 停止仿真
- 查询状态
- 发送自定义命令
- 使用预设命令

### 通道

用于：

- 选择波形显示通道
- 控制是否显示参考值、反馈值、控制输出、姿态量、垂向量等

## 5.2 中间主工作区

中间区域为波形工作台，支持：

- 实时波形显示
- 暂停 / 清空
- 一键聚焦
- 点击标记
- 回到最新
- 视图平移与缩放
- 双游标测量
- 小窗 / 全屏查看
- 导出图片
- 导出可见数据 CSV

## 5.3 右侧监视区

右侧包含：

- 3D 模型视图
- 运行状态

可用于观察：

- 姿态变化
- 垂向位置变化
- 运行状态
- 当前场景模式

## 5.4 底部控制台

控制台用于显示：

- 下位机上传的文本
- 下位机上传的遥测摘要
- 上位机下发的文本命令
- 兼容旧链路时的仿真反馈摘要
- 错误与异常提示

控制台默认自动跟随最新输出；如果用户手动滚动查看历史内容，自动跟随会暂停，滚回到底部后自动恢复。

---

## 6. 常用功能说明

## 6.1 启动与停止

- 软件启动后，本地仿真默认不自动输出波形
- 只有点击 `启动` 后，上位机仿真定时器才会开始运行
- 点击 `停止` 后，上位机仿真输出停止

这更符合调试软件的常见操作习惯。

## 6.2 波形操作

波形区支持以下常用功能：

- `暂停`
- `清空`
- `一键聚焦`
- `点击标记`
- `回到最新`
- `适配 Y 轴`
- `时间放大 / 缩小`
- `左移 / 右移`
- `双游标测量`
- `导出图片`
- `导出 CSV`
- `波形悬浮窗`
- `波形全屏`

## 6.3 3D 视图

3D 区支持：

- 模型库切换
  - 水下机器人
  - 飞行器
  - 通用载体
- 场景模式切换
  - 姿态模式
  - 轨迹模式
  - 水下场景模式 / 空中场景模式
- 视角跟随
- 视角重置
- 轨迹清除
- 导入外部模型
- 调整外部模型姿态与外观

## 6.4 设置持久化

软件会自动保存用户的常用设置，下次启动恢复，主要包括：

- 工作台布局
- 主题
- 左侧控制参数
- 预设命令
- 波形常用设置
- 3D 模型与场景设置

菜单栏支持：

- `加载设置...`
- `导出设置...`
- `重置设置`

---

## 7. 上位机内部仿真原理

## 7.1 仿真目标

当前上位机内部仿真器并不是完整六自由度模型，而是一个单自由度垂向对象模型，用于联调垂向控制闭环。

核心目的：

- 让下位机只专注控制算法
- 让上位机模拟被控对象
- 形成“控制器在下位机，对象在上位机”的联调闭环

## 7.2 核心状态量

仿真器维护以下状态：

- `depth`
  - 当前垂向位置
  - 对水下机器人表示深度
  - 对飞行器界面显示为高度，但协议字段名仍然叫 `depth`
- `depth_rate`
  - 当前垂向速度
- `disturbance`
  - 当前环境扰动

## 7.3 仿真输入

仿真器每一步只使用一个控制输入：

- `u_cmd`

注意：

- `roll / pitch / yaw` 只用于界面显示
- 它们不参与对象动力学计算

## 7.4 仿真公式

当前软件使用的离散更新逻辑如下：

```text
disturb = disturb_amp * disturb_scale * sin(2π * disturb_freq_hz * t)

acc = (u_cmd + disturb - damping * depth_rate - buoyancy_bias) / mass

depth_rate = depth_rate + acc * dt
depth      = depth + depth_rate * dt

measured_depth = depth + noise
```

说明：

- `disturb`
  - 周期扰动
- `damping * depth_rate`
  - 速度阻尼项
- `buoyancy_bias`
  - 恒定偏置项
- `noise`
  - 测量噪声，只加到输出，不加到真实状态

最终返回给下位机的是带噪声的测量值：

- `depth = measured_depth`
- `depth_rate`
- `disturbance`

## 7.5 内置模型参数

### 水下机器人 ROV

| 参数 | 数值 |
|---|---:|
| `mass` | `8.0` |
| `damping` | `2.8` |
| `buoyancy_bias` | `-0.3` |
| `noise_std` | `0.005` |
| `disturb_amp` | `0.2` |
| `disturb_freq_hz` | `0.15` |

特性：

- 默认零输入时会有“下沉”趋势
- 正深度方向表示“更深”

### 飞行器

| 参数 | 数值 |
|---|---:|
| `mass` | `6.4` |
| `damping` | `3.4` |
| `buoyancy_bias` | `0.34` |
| `noise_std` | `0.003` |
| `disturb_amp` | `0.08` |
| `disturb_freq_hz` | `0.11` |

附加逻辑：

- 界面将 `depth` 显示为“高度”
- 高度下限为 `0`
- 高度到 `0` 后不会继续向地面以下运动

### 通用载体

| 参数 | 数值 |
|---|---:|
| `mass` | `7.2` |
| `damping` | `2.2` |
| `buoyancy_bias` | `0.0` |
| `noise_std` | `0.004` |
| `disturb_amp` | `0.12` |
| `disturb_freq_hz` | `0.08` |

## 7.6 扰动等级

界面中的环境扰动等级会改变 `disturb_scale`：

| 扰动等级 | 缩放系数 |
|---|---:|
| 关闭 | `0.0` |
| 低 | `0.5` |
| 中 | `1.0` |
| 高 | `1.6` |
| 极高 | `2.4` |

实际扰动幅值：

```text
实际扰动幅值 = disturb_amp * disturb_scale
```

## 7.7 运行周期

当前软件支持手动设置上位机仿真运行周期，单位为 `ms`。

常见相关周期如下：

- 上位机仿真运行周期
  - 用户可调
- UI 刷新频率
  - 默认约 `30 Hz`
- 上位机反馈发送频率
  - 仿真运行时约 `25 Hz`

---

## 8. 数据流总览

当前联调链路如下：

1. 下位机运行控制算法或 LADRC 仿真任务
2. 下位机上传遥测数据给上位机
3. 上位机从遥测中取出：
   - 姿态量
   - `u_cmd`
   - `ref`
   - `feedback`
4. 上位机刷新波形、状态面板和 3D 视图，并在需要时本地推进对象模型
5. 用户执行操作或需要参数同步时，上位机仅下发必要命令
6. 在真实 LADRC 串口联调时，上位机通过 `#stat:1` 主动轮询状态，下位机按查询返回最新状态

可以简单写成：

```text
PC command/status poll -> MCU state response -> PC display/simulator -> PC command sync when needed
```

---

## 9. 下位机上传给上位机的数据

下位机到上位机支持三类内容：

- 文本遥测
- 二进制遥测
- 普通文本应答

推荐优先级：

1. 文本遥测
2. 扩展二进制遥测
3. 旧版二进制遥测

最推荐的方式仍然是：

- 下位机用 `printf` 周期输出文本遥测

原因：

- 最容易联调
- 最容易抓包
- 最容易和 `GET STATUS` 共用
- 对 `feedback` 支持最完整

## 9.1 推荐下位机必传字段

建议下位机至少发送以下字段：

| 字段名 | 是否建议必传 | 作用 |
|---|---|---|
| `timestamp_ms` / `timestamp` | 是 | 标识遥测生成时刻 |
| `roll` | 是 | 波形与 3D 显示 |
| `pitch` | 是 | 波形与 3D 显示 |
| `yaw` | 是 | 波形与 3D 显示 |
| `u_cmd` | 是 | 驱动上位机对象模型 |
| `ref` | 是 | 显示当前目标值 |
| `feedback` | 是 | 显示当前反馈值，并用于分析闭环 |
| `algo_id` | 是 | 显示当前控制算法 |
| `run_state` | 是 | 显示当前运行状态 |

其中最关键的两个字段是：

- `u_cmd`
- `feedback`

## 9.2 每个字段的含义与来源

### `timestamp_ms`

推荐来源：

- `HAL_GetTick()`
- RTOS tick
- 自己维护的毫秒计数器

作用：

- 估算链路延迟
- 判断新旧遥测

### `roll / pitch / yaw`

推荐来源：

- IMU
- AHRS
- 姿态融合算法

推荐单位：

- 角度制 `°`

### `u_cmd`

推荐来源：

- 下位机当前周期的最终控制输出

注意：

- 必须发送“最终执行值”
- 不要发送误差
- 不要发送 PID 单项中间量
- 不要直接发送某个推进器原始 PWM

### `ref`

推荐来源：

- 当前目标值变量
- `SET REF` 命令设置结果

### `feedback`

推荐来源：

- 控制器当前真正使用的反馈量

建议定义：

```text
feedback = 控制器本周期实际使用的反馈值
```

例如：

- 仿真模式下：`feedback = sim_feedback.depth`
- 真实传感器模式下：`feedback = sensor_depth`

### `algo_id`

建议映射：

| 数值 | 算法 |
|---:|---|
| `0` | `PID` |
| `1` | `LADRC` |
| `2` | `OPEN_LOOP` |

### `run_state`

建议映射：

| 数值 | 含义 |
|---:|---|
| `0` | 空闲 |
| `1` | 运行中 |

## 9.3 推荐文本遥测格式

最推荐下位机使用这种一行一帧的 `key=value` 文本格式：

```text
timestamp=1710000123,roll=0.10,pitch=-0.05,yaw=1.57,u_cmd=0.80,ref=2.00,feedback=1.86,algo_id=0,run_state=1
```

要求：

- 一行一帧
- 结尾带 `\n` 或 `\r\n`
- 键名大小写不敏感
- 建议固定字段顺序

## 9.4 推荐 JSON 遥测格式

也支持 JSON 行：

```json
{"timestamp":1710000123,"roll":0.10,"pitch":-0.05,"yaw":1.57,"u_cmd":0.80,"ref":2.00,"feedback":1.86,"algo_id":0,"run_state":1}
```

同样要求每行一帧并带换行。

## 9.5 二进制遥测格式

二进制协议帧结构：

```text
AA 55 | msg_id | len | seq(2B) | payload | crc16(2B)
```

说明：

- 帧头：`0xAA 0x55`
- 遥测 `msg_id`：`0x01`
- 仿真反馈 `msg_id`：`0x10`
- ACK `msg_id`：`0x20`
- CRC：`CRC16-CCITT`

### 旧版二进制遥测 payload

格式：

```text
<IfffffBB
```

字段顺序：

1. `timestamp_ms`
2. `roll`
3. `pitch`
4. `yaw`
5. `u_cmd`
6. `ref`
7. `algo_id`
8. `run_state`

### 扩展二进制遥测 payload

格式：

```text
<IffffffBB
```

字段顺序：

1. `timestamp_ms`
2. `roll`
3. `pitch`
4. `yaw`
5. `u_cmd`
6. `ref`
7. `feedback`
8. `algo_id`
9. `run_state`

说明：

- 当前软件同时兼容旧版和扩展版
- 若使用旧版格式，不包含 `feedback`
- 软件会临时沿用上一反馈值或当前仿真反馈，避免界面掉回 `0`
- 若想界面显示完全准确，仍建议发送文本遥测或扩展二进制遥测

## 9.6 普通文本应答

下位机也可以发送普通文本，例如：

```text
OK
ERR PARAM
ERR CRC
```

这类内容只会进入控制台，不会更新波形和状态。

---

## 10. 上位机发送给下位机的数据

当前 LADRC 对接模式下，上位机到下位机只发送必要的文本命令，并周期性发送 `#stat:1` 做轻量状态轮询。
旧版“周期回传仿真反馈”链路仅保留兼容说明，不再作为当前固件的实用默认方案。

## 10.1 文本命令

用户命令始终为文本行，UTF-8 编码，结尾带换行。

当前仓库下位机实际需要的命令为：

- `#r:<value>`
- `#h:<value>`
- `#wo:<value>`
- `#wc:<value>`
- `#bo:<value>`
- `#init:<value>`
- `#expe:<value>`
- `#run:0|1|2`
- `#rst:1`
- `#stat:1`

其中上位机界面的通用操作会自动转换为当前固件真正需要的命令：

- `SET REF <value>` -> `#expe:<value>`
- `RUN 1` -> 同步当前 LADRC 参数与目标后发送 `#run:1`
- `RUN 0` -> `#run:2`
- `GET STATUS` -> `#stat:1`

软件在“已连接串口 + 当前算法为 LADRC”时，还会静默周期发送 `#stat:1`，以适配“下位机不主动周期上传”的实际场景。

## 10.2 兼容旧反馈链路（非当前 LADRC 固件必需）

以下内容仅用于兼容旧版“下位机控制器 + 上位机对象仿真”方案。
对于当前仓库中的 LADRC 下位机，不建议再周期性发送这些反馈，否则只会增加串口负担，甚至触发下位机命令缓冲异常。

反馈字段固定为：

- `timestamp_ms`
- `depth`
- `depth_rate`
- `disturbance`

### 文本反馈格式

```text
timestamp=1710000999,depth=1.23456,depth_rate=0.01234,disturbance=0.10000
```

### 二进制反馈格式

`msg_id = 0x10`

payload 格式：

```text
<Ifff
```

字段顺序：

1. `timestamp_ms`
2. `depth`
3. `depth_rate`
4. `disturbance`

---

## 11. 下位机如何使用上位机反馈

如果当前是“下位机控制器 + 上位机对象仿真”的闭环联调，推荐这样使用：

```text
feedback     = sim_feedback.depth
feedback_dot = sim_feedback.depth_rate
error        = ref - feedback
```

推荐用途：

- `depth`
  - 作为主反馈量
- `depth_rate`
  - 用作速度反馈或微分辅助
- `disturbance`
  - 用于观测、记录和验证，不建议直接硬灌进控制律

下位机接收到反馈后的推荐处理：

1. 更新 `depth`
2. 更新 `depth_rate`
3. 更新 `disturbance`
4. 置位反馈有效标志
5. 把 `depth` 写入控制器 `feedback`
6. 把 `depth_rate` 写入控制器 `feedback_rate`

---

## 12. `u_cmd` 的详细说明

## 12.1 `u_cmd` 是什么

最重要的一点：

```text
u_cmd 不是上位机计算的，而是下位机控制器自己计算后再上传给上位机。
```

上位机只做两件事：

1. 接收下位机上传的 `u_cmd`
2. 用 `u_cmd` 推进对象模型

因此：

- `u_cmd` 是否正确
- 直接决定仿真趋势是否正确

## 12.2 `u_cmd` 的本质

建议把 `u_cmd` 定义成：

- 控制器当前输出给垂向对象模型的最终标量控制量

它应该满足：

- 是一个标量
- 有明确正负方向
- 体现控制作用强弱

## 12.3 推荐符号约定

建议始终遵守下面这条：

```text
如果 feedback 增大表示目标量增大，那么正 u_cmd 也应推动 feedback 增大。
```

例如：

- 深度控制时
  - 正 `u_cmd` 应推动“更深”
- 高度控制时
  - 正 `u_cmd` 应推动“更高”

## 12.4 推荐计算流程

推荐控制周期：

1. 读取 `ref`
2. 读取 `feedback`
3. 计算误差
4. 得到原始控制量 `u_cmd_raw`
5. 做限幅 / 保护 / 死区处理
6. 得到最终 `u_cmd`
7. 上传 `telemetry.u_cmd = u_cmd`

推荐代码结构：

```c
controller.error = controller.ref - controller.feedback;
controller.u_cmd_raw = controller_calculate(&controller);
controller.u_cmd = limit(controller.u_cmd_raw, U_MIN, U_MAX);
telemetry.u_cmd = controller.u_cmd;
```

## 12.5 PID 情况下的推荐计算

推荐公式：

```text
e  = ref - feedback
ed = -feedback_rate
ei = ei + e * dt

u_cmd_raw = Kp * e + Ki * ei + Kd * ed
u_cmd     = clamp(u_cmd_raw, U_MIN, U_MAX)
```

### PID 数值实例

假设：

- `ref = 2.000`
- `feedback = 1.620`
- `feedback_rate = 0.080`
- `dt = 0.01`
- `Kp = 1.5`
- `Ki = 0.2`
- `Kd = 0.6`
- `ei_old = 0.500`

则：

```text
e = 2.000 - 1.620 = 0.380
ei = 0.500 + 0.380 * 0.01 = 0.5038
ed = -0.080
u_cmd_raw = 1.5*0.380 + 0.2*0.5038 + 0.6*(-0.080)
          = 0.62276
u_cmd ≈ 0.623
```

此时建议上传：

```text
u_cmd=0.623
```

## 12.6 OPEN_LOOP 情况

开环时，`u_cmd` 可以来自：

- 固定测试值
- 手动给定
- 脚本输出

示例：

```c
controller.u_cmd_raw = controller.manual_output;
controller.u_cmd = limit(controller.u_cmd_raw, U_MIN, U_MAX);
```

## 12.7 LADRC 情况

LADRC 的具体公式取决于实现，但通常可理解为：

```text
e  = ref - z1
u0 = Kp * e - Kd * z2
u_cmd_raw = (u0 - z3) / b0
u_cmd = clamp(u_cmd_raw, U_MIN, U_MAX)
```

其中：

- `z1`
  - 状态估计
- `z2`
  - 速度估计
- `z3`
  - 总扰动估计
- `b0`
  - 名义控制增益

## 12.8 多推进器系统如何得到 `u_cmd`

如果你的系统最终输出多个推进器命令，不建议把每个推进器值直接作为 `u_cmd` 上传。

推荐做法：

### 方式一

直接上传混控前的垂向通道输出：

```text
u_cmd = vertical_channel_output_after_limit
```

### 方式二

从多个执行器命令合成等效垂向量：

```text
u_cmd = Σ(执行器输出 × 垂向方向权重)
```

例如 4 个纯垂向推进器：

```text
u_cmd = (m1 + m2 + m3 + m4) / 4
```

---

## 13. 推荐 `printf` 输出方式

## 13.1 推荐下位机遥测模板

最推荐的输出格式：

```c
printf("timestamp=%lu,roll=%.2f,pitch=%.2f,yaw=%.2f,u_cmd=%.3f,ref=%.3f,feedback=%.3f,algo_id=%u,run_state=%u\r\n",
       (unsigned long)timestamp_ms,
       roll,
       pitch,
       yaw,
       u_cmd,
       ref,
       feedback,
       (unsigned int)algo_id,
       (unsigned int)run_state);
```

## 13.2 推荐封装函数

```c
void telemetry_printf_line(uint32_t timestamp_ms,
                           float roll,
                           float pitch,
                           float yaw,
                           float u_cmd,
                           float ref,
                           float feedback,
                           uint8_t algo_id,
                           uint8_t run_state)
{
    printf("timestamp=%lu,roll=%.2f,pitch=%.2f,yaw=%.2f,u_cmd=%.3f,ref=%.3f,feedback=%.3f,algo_id=%u,run_state=%u\r\n",
           (unsigned long)timestamp_ms,
           roll,
           pitch,
           yaw,
           u_cmd,
           ref,
           feedback,
           (unsigned int)algo_id,
           (unsigned int)run_state);
}
```

## 13.3 `GET STATUS` 推荐响应方式

收到：

```text
GET STATUS
```

推荐直接回一条完整遥测，而不是仅仅回 `OK`：

```c
if (strcmp(rx_cmd, "GET STATUS") == 0)
{
    telemetry_printf_line(millis(),
                          imu_roll_deg,
                          imu_pitch_deg,
                          imu_yaw_deg,
                          controller.u_cmd,
                          controller.ref,
                          controller.feedback,
                          controller.algo_id,
                          controller.run_state);
}
```

## 13.4 使用 `printf` 时的注意事项

1. 一条遥测必须独占一行
2. 遥测结尾必须带换行
3. 普通调试日志尽量不要包含 `=`
4. 若必须共用串口，普通日志建议写成：
   - `LOG motor start`
   - `OK`
   - `ERR PARAM`
5. 如果 MCU 默认未启用浮点 `printf`，需要开启浮点输出支持

---

## 14. 推荐下位机最小对接方案

如果你要尽快和本软件跑通，建议最低实现以下内容。

## 14.1 下位机接收

如果对接当前仓库中的 LADRC 下位机，建议直接处理以下命令即可：

- `#r:<value>`
- `#h:<value>`
- `#wo:<value>`
- `#wc:<value>`
- `#bo:<value>`
- `#init:<value>`
- `#expe:<value>`
- `#run:0|1|2`
- `#rst:1`
- `#stat:1`

当前实用方案下，无需再解析上位机周期发送的 `depth / depth_rate / disturbance` 仿真反馈；只需正确响应上位机的 `#stat:1` 状态查询。

## 14.2 下位机发送

建议周期发送文本遥测，至少包含：

- `timestamp`
- `roll`
- `pitch`
- `yaw`
- `u_cmd`
- `ref`
- `feedback`
- `algo_id`
- `run_state`

推荐示例：

```text
timestamp=1710001200,roll=0.00,pitch=0.00,yaw=0.00,u_cmd=0.75,ref=2.00,feedback=1.62,algo_id=0,run_state=1
```

---

## 15. 常见问题

## 15.1 没有波形输出

请先确认：

- 已点击 `启动`
- 波形通道已勾选
- 下位机正在上传遥测

## 15.2 能连串口但没有正确刷新状态

请检查：

- 下位机是否按约定输出遥测
- 是否包含 `u_cmd / ref / feedback / run_state`
- 是否每条遥测都带换行

## 15.3 `printf` 输出正常但上位机不识别

请检查：

- 是否一行一帧
- 是否字段名正确
- 是否使用了带 `=` 的普通日志混在同一串口

## 15.4 飞行器为什么界面显示“高度”，协议字段仍叫 `depth`

这是当前实现的兼容策略：

- 界面语义按“高度”显示
- 协议字段仍统一保留 `depth`

这样更利于与现有仿真器和协议保持一致。

## 15.5 为什么推荐文本遥测优先于二进制

因为：

- 联调最简单
- 能最快定位问题
- 最容易直接看出 `u_cmd / feedback` 是否正确

---

## 16. 结论

当前软件的核心协作关系是：

- 下位机负责控制器
- 上位机负责对象模型
- 双方通过串口完成“状态查询/应答 + 必要命令下行”的联调

对接时最关键的两点是：

1. 下位机必须稳定上传 `u_cmd / ref / feedback / run_state`
2. 下位机必须正确接收并执行必要的 `#...` 控制命令，并能对 `#stat:1` 返回当前状态

如果这两条链路打通，波形、3D、日志和联调工作台就都会稳定工作。
