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
- `#r:<n>` -> `r = n / 10.0`
- `#h:<n>` -> `h = n / 1000.0`
- `#wo:<n>` -> `w0 = n`
- `#wc:<n>` -> `wc = n`
- `#bo:<n>` -> `b0 = n / 10.0`
- `#init:<n>` -> `init_val = n / 10.0`，并同步 `real_val`
- `#expe:<n>` -> `expect_val = n / 10.0`
- `#run:0|1|other` -> `TD_MODE | LOOP_MODE | NULL_MODE`
- `#rst:1` -> 重置 LADRC 参数与仿真状态
