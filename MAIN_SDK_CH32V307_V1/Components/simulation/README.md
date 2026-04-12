# Simulation 命令解析（`vofa.c`）

## 作用
- 解析串口命令帧：`#<type>:<data>`
- 根据 `Command` 表分发到对应回调
- 入口函数：`parse_command(commands, cmd_count)`

## 最小接入
1. 串口接收中断写入 `chry_rbuffer_tid`
2. 一帧接收完成后置位 `g_recvFinshFlag`
3. 定义命令表 `Command[]`
4. 在周期任务中调用 `parse_command(...)`

## 命令表示例
```c
static void cmd_run(const char *data);
static void cmd_rst(const char *data);

static Command cmds[] = {
    {"run", cmd_run},
    {"rst", cmd_rst},
};

parse_command(cmds, sizeof(cmds) / sizeof(cmds[0]));
```

## 解析规则
- 必须以 `#` 开头
- 必须包含 `:`
- `type` / `data` 不能为空
- 命令长度 `< CMD_BUFFER_SIZE`
- 自动裁剪末尾空白和 `\r\n`

出错会打印：`missing '#'`、`length overflow`、`empty command type`、`Unknown command type` 等信息。

## LADRC 命令速查（`sim_ladrc.c`）
- `#r:<value>` -> `r = value`
- `#h:<value>` -> `h = value`
- `#wo:<value>` -> `w0 = value`
- `#wc:<value>` -> `wc = value`
- `#bo:<value>` -> `b0 = value`
- `#init:<value>` -> `init_val = value`，并同步 `real_val`
- `#expe:<value>` -> `expect_val = value`
- `#run:0|1|other` -> `TD_MODE | LOOP_MODE | NULL_MODE`
- `#rst:1` -> 重置 LADRC 参数与仿真状态
- `#stat:1` -> 立即输出一帧当前 LADRC 状态

## 上位机联调输出
- 当前 LADRC 仿真采用“命令触发状态输出”模式，不做周期主动上报
- 上位机可通过 `#stat:1` 主动查询一帧结构化遥测文本；`#run` / `#rst` 也会立即返回当前状态
- 典型字段包括：`timestamp`、`algo_id`、`run_state`、`sim_mode`、`ref`、`feedback`、`u_cmd`、`v1`、`v2`、`z1`、`z2`、`z3`、`r`、`h`、`w0`、`wc`、`b0`、`init`
- 为兼容旧工具链，上位机仍保留对旧版 VOFA 风格 `2` 列 / `7` 列纯 CSV 输出的兜底解析
