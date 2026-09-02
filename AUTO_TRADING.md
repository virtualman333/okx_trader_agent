# 自动交易轮（5 分钟定时任务）

> 本文件说明 `scripts/trade_round.py` 的运行方式与安全边界。
> 由用户 2026-09-02 要求：开启一个 5 分钟的定时任务，执行量化交易（仅模拟盘 okx-demo）。

## 调度方式

DSH 环境没有内置调度器，且 README 提到的"最小 1 小时"是**原部署平台**的限制，不适用于本机。
这里用**一个常驻后台进程**充当 5 分钟定时任务：

```bash
python scripts/trade_round.py --loop --interval 300
```

由 DSH 的 background job 托管（单进程 = 天然不重叠）。进程内也已做单实例保护。

## 运行模式（安全开关）

| 模式 | 命令 | 行为 |
|------|------|------|
| **监控评估（默认）** | `python scripts/trade_round.py --once` | 取数→按 §4 评估→写 `state/decision_R*.md` 与面板。**不下单、不挂单。** 安全首跑用此。 |
| 联机只读预演 | `--dry-run` | 只读取数，拟执行动作只记录不发网络写请求。 |
| **自动下单** | `--auto-trade` | 评估通过（或已留 §0.3 偏离）后，经 `mcp_call.py --allow-write` 在 **demo** 下单 + 同轮挂 OCO 止损 + 回查确认。 |

> `--auto-trade` 默认**关闭**。首次挂载只跑监控评估轮，确认无误后由用户显式开启 `--auto-trade`。

## 强制安全边界（硬编码，不可被参数绕过）

1. **仅 okx-demo**：任何写操作都走 `mcp_call.py --profile demo --allow-write`；`okx-live` 写操作被 `mcp_call.py` 代码级拒绝（返回 REFUSED）。
2. **L1-4 止损必挂**：`--auto-trade` 下每笔下单一律同轮内挂 OCO 止损，并回查 `swap_get_algo_orders(status=pending)` 确认；失败按章程处理。
3. **L1-8 幂等 clOrdId**：下单必须带由 `order_id.py` 生成的合规 `clOrdId`（格式 `^[A-Za-z][A-Za-z0-9]{0,31}$`，禁 `_`/`-`），超时复用同一 ID 重试。
4. **L1-5 / L1-2 硬顶**：单笔风险 ≤ 2.5%、杠杆 ≤ 5x，超限直接拒绝该笔。
5. **L1-7 只追加**：归档经 `archive_round.py` 唯一写入口，历史日志/台账绝不改写。

## 启动步骤（由父 agent 执行）

1. 手动跑一次监控评估轮，确认决策文件/面板正常、无真实下单：
   `python scripts/trade_round.py --once`
2. 用 DSH 后台 job 启动常驻 5 分钟轮（先不开 auto-trade）：
   `python scripts/trade_round.py --loop --interval 300`
3. 用户确认后，停止该 job，改用带 `--auto-trade` 的命令重启。

## 状态与日志

- 每轮：写 `state/decision_R<id>.md`、`logs/YYYY-MM/YYYY-MM-DD.md`、`logs/rounds.jsonl`（仅追加）。
- 调度器输出：`logs/trade_round.log`（常驻进程 stdout/stderr）。
- 运行态：`state/runtime.json`（轮次号、当日止损计数、熔断状态）。
