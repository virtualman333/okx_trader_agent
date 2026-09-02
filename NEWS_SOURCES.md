# 消息源实测清单 NEWS_SOURCES.md

> 记录每个数据源的**实测能力**，避免每轮重复试错。
> 首次实测：2026-09-01 ｜ 每次发现新的能力边界或失效情况，追加记录。

---

## ⚠️ 接入环境区分（重要，勿混用）

本文档各数据源实际由**两类不同环境**分别接入，调用方不同：

| 环境 | 接入的源 | 本 DSH 能否直连 |
|------|----------|----------------|
| **本 DSH 环境**（DeepSeek Harness，`E:\ai_project\okx_trader_agent`） | `jin10`（标准 MCP Streamable HTTP + Bearer，见 `scripts/jin10_client.py`） | ✅ 已直连 |
| **另一 agent 平台**（WorkBuddy 连接器注册表 `~/.workbuddy/connectors/.../mcp.json`） | `mx_finance_search_news` / `mx_macro_data` / `data_macro` / `westock-mcp` 等（OAuth 托管鉴权，注册表多为 `disabled` 或需平台票据） | ❌ 不能直连（独立脚本实测返回 `HTTP 401`） |
| 平台内置工具 | `WebSearch` / `WebFetch` | ⚠️ 本 DSH 端对应 `web_search` 工具，能力可替代但非同一 MCP |

- 标注「**由 WorkBuddy 连接器接入**」的源：**本 DSH 未直连**，调用需走那个 agent 平台，不要以为本环境有对应脚本/MCP。
- 标注「**本 DSH 直连**」的源：当前仅 `jin10` 一个，可用 `scripts/jin10_client.py` 直接调用。

---

## 一句话结论

| 场景 | 用哪个 |
|------|--------|
| 搜加密新闻 | `mx_finance_search_news`（东方财富）— **由 WorkBuddy 连接器接入，本 DSH 未直连** |
| 验证关键数字 / 防过期数据 | `WebSearch` — **由 WorkBuddy 平台提供；本 DSH 端对应 `web_search` 工具** |
| 读单条原文 | `WebFetch` — 同上，平台端工具 |
| 查美国宏观数据 | ⚠️ **不要用 `data_macro`**，改用 `mx_macro_data`（连接器）或 WebSearch |
| 查 A股/港股个股 | `westock-mcp` 全套（由 WorkBuddy 连接器接入，本 DSH 未直连，本项目不涉及） |
| 金十财经（快讯/资讯/行情/日历） | **`jin10` — 本 DSH 已直连**，用 `scripts/jin10_client.py` |

---

## 1. `mx_finance_search_news`（东方财富）— ★★★★☆ 主力源

**实测表现**：加密覆盖**意外地好**。虽然是股票数据库，但收录了大量加密媒体的中文站。

**已确认收录的信源**：
- **高质量**：Odaily 星球日报、ChainCatcher 链捕手、智通财经、FXStreet（中文站）、格隆汇
- **中质量**：币圈网(alibtc)、币圈子(120btc)、MoneyDJ
- **低质量（C级）**：搜狐 AI 生成栏目、币海财经(bihai123)

**时效**：可检索到**当天**发布的内容（2026-09-01 实测拿到 08:59 / 10:05 / 11:16 / 14:11 / 15:27 / 17:00 多个时点）。

**调用范式**：
```
query = "比特币 以太坊 加密货币 最新行情消息 2026年9月"
# 建议带上币种 + 关注点 + 时间范围，提高召回精度
```
返回结果含 `columns: [标题, 摘要, 发布时间, 来源, 跳转链接]`，摘要较长，适合直接研判。

**已知坑**：
- 同一事件会被多家媒体重复报道（如 BitMine 增持 ETH 一天内出现 6 条同质新闻），**依赖 `news_log.py` 的标题指纹去重**
- 低质站会产出 AI 生成的「点位喊单」文章，内部数据常自相矛盾 → 降 C 级

---

## 2. `WebSearch` — ★★★★☆ 交叉验证专用（不可替代）

**核心价值**：**唯一能识破"过期数据"的手段。**

### 案例（2026-09-01，已写入章程 §10.3）

| 信源 | 数据日期 | 9月加息概率 |
|------|----------|-------------|
| GO Markets（英文） | **8/26** | 36.1% |
| 汇通财经 / 中国基金报 / 格隆汇 / 新浪财经 | **9/1** | **65.4%** |

同一 CME FedWatch 指标，相隔 6 天，结论完全反转。转折点是 **8/27-8/31 Jackson Hole 全球央行年会**，美联储主席 **Kevin Warsh** 释放鹰派信号，2年期美债单日跳升 12bp。

若直接采信 8/26 的 36.1%，会把"大概率不加息"误判为基准情形 → 系统性低估紧缩风险。

**规则固化**：宏观预期类消息必须带 `published_at`，超过 48 小时强制重验。

**用法建议**：搜「指标名 + 具体数值 + 时间范围」最有效，如：
```
美联储 2026年9月 议息会议 加息概率 降息概率 CME FedWatch
```
配合 `freshness` 参数（d1 / d7 / m1）限制时效。

---

## 3. `data_macro`（腾讯自选股）— ★☆☆☆☆ **不推荐用于实时宏观**

### 实测问题

调用 `mode=indicator, area=us, names=us_inflation,us_employment,us_monetary` 返回：

```
美国截至1月31日当周续请失业金人数    OccurDate 20260205
美国第一季度劳工就业成本季率          OccurDate 20260430
美国截至11月3日当周续请失业金人数     OccurDate 20251120   ← 2025年的数据
美国5月挑战者企业裁员月率            OccurDate 20260604   ActualValue "未公布"
美国8月制造业就业人口变动            OccurDate 20250905   ← 2025年的数据
```

**三个致命问题**：
1. **日期乱序**：返回结果不按 OccurDate 排序，2025 与 2026 数据混杂
2. **无法取"最新值"**：`limit` 控制的是返回条数，不是"最近 N 条"，拿到的是随机采样
3. **大量"未公布"**：实际值为空，无信息量

**唯一可用场景**：查历史利率水平。实测拿到「美国7月联邦基金利率目标下限 3.50%」有效。

**替代方案**：`mx_macro_data`（东方财富）或 WebSearch。

**指标目录**（`mode=list, area=us` 返回）：
`us_employment` / `us_inflation` / `us_monetary` / `us_eco_growth` / `us_confidence` / `us_fiscal` / `us_energy` / `us_realestate`

---

## 4. `WebFetch` — 读原文用

用于核实单条关键新闻的原文表述，避免依赖二手摘要。注意：若遇到 host 跳转，需用新 URL 重新请求。

---

## 5. 未接入但可考虑的源

| 源 | 说明 | 状态 |
|----|------|------|
| 金十数据 | **本 DSH 已直连**（MCP Streamable HTTP + Bearer，见 `scripts/jin10_client.py`） | ✅ 本 DSH 已直连 |
| 腾讯新闻 | 用户提到过，无对应 MCP | 未接入 |
| OKX 官方公告 | 交易所有 `/api/v5/public/announcements` 公开接口 | **可直接用 urllib 接入**，待开发 |
| Coinglass 清算数据 | 清算地图/多空比，需第三方 | 未接入 |
| Alternative.me 恐惧贪婪指数 | 免费公开 API | **可直接接入**，待开发 |

**待开发优先级**：OKX 公告（交易所风险事件直接影响持仓安全）> 恐惧贪婪指数（情绪极值反向指标）> 清算数据。

---

## 5.5 `jin10` 金十数据财经 MCP — ★★★★★ **本 DSH 已直连（2026-09-02）**

> 这是本文档中**唯一一个本 DSH 环境真正直连**的数据源；其余"已接入"源均为 WorkBuddy 连接器接入（见顶部环境区分表）。

标准 MCP 客户端：`scripts/jin10_client.py`（Streamable HTTP + Bearer Token）。
严格流程 `initialize` → `notifications/initialized` → `tools/list`/`resources/list` → `tools/call`，
协议版本 `2025-11-25`（握手失败自动回退）。

| 场景 | 用哪个 |
|------|--------|
| 指定品种实时报价 / K线 | 先 `--quote-codes` 确认 code → `--quote <CODE>` / `--kline <CODE>` |
| 某主题最新快讯 | `--search-flash <关键词>`；顺序浏览最新流用 `--flash --all` |
| 某主题深度文章 | `--search-news <关键词>` / `--news --all` 拿 id → `--news-detail <id>` |
| 财经日历 / 本周数据 | `--calendar` |

字段约定（与金十一致）：
- 报价：`data.{code,name,time,open,close,high,low,volume,ups_price,ups_percent}`
- K线：`data.{code,name,klines:[{close,high,low,open,time,volume}]}`
- 快讯/资讯列表：`data.{items,next_cursor,has_more}`（**分页只传 `cursor`，不要传 `offset`**）
- 文章详情：`data.{id,title,introduction,time,url,content}`
- 财经日历：`data:[{pub_time,star,title,previous,consensus,actual,revised,affect_txt}]`

常用 code：`XAUUSD` 现货黄金 / `XAGUSD` 现货白银 / `USOIL` WTI / `UKOIL` 布伦特 / `COPPER` 铜 / `USDJPY` / `EURUSD` / `USDCNH`。
结果**优先取 `result.structuredContent`**，`content` 仅作可读文本补充。该服务按用户×工具每日限流 1500 次（北京自然日），超限返回「今日该工具调用次数已达上限，请明日再试」，客户端会置 `rate_limited=true`。

---

## 5.8 双源交叉验证通道（2026-09-02 用户建议 + 实测）

> **用户建议原文（2026-09-02）**：「你可以使用其他新闻资源，或使用 playwright 主动搜索等」。
> 本系统采纳并实测落地。判断依据见下方"为什么这条建议必须采纳"。

### 为什么这条建议必须采纳（不是优化，是补合规缺口）

章程 **§10.3 强制**：关键数字（宏观数据、加息概率、资金流等）必须 **≥2 独立信源**交叉验证才定 **A 级**。
而 §10.2 规定：**只有 A 级才具备否决权**，B 级（单源）「可作参考，无单独否决权」。

**关键矛盾**：2026-09-02 之前，本 DSH 环境**只有 `jin10` 一个可用源**
（`mx_finance_search_news` / `WebSearch` 均属 WorkBuddy 连接器，本环境未直连）。
→ 所有消息**永远只能定 B 级**，消息面的最高价值（否决权）结构性不可用。

因此补充第二信源**不是锦上添花，而是补齐 §10.3 的合规缺口**。

### 实测结论（2026-09-02）

| 通道 | 实测结果 | 用途 |
|------|----------|------|
| `jin10`（`scripts/jin10_client.py`） | ✅ 可用，无需 token，实时到当天 | **主源**（采集） |
| OKX MCP `news_*` 模块 | ❌ **不可用**：demo 下 `ConfigError: News features are not available in demo/simulated trading mode`；live 又 `No credentials found` | 弃用（待配 live 凭据后重试） |
| DSH 内置 `web_search` 工具 | ❌ 不可用：`DEEPSEEK_API_KEY` 未配置 | 不可用（若日后配置则优先用） |
| BrowserSkill `bsk` CLI | ❌ 未安装（提示 `bsk not found`） | 不可用（可安装后启用） |
| **Playwright（python）** | ✅ **可用**（见下） | **第二信源（交叉验证专用）** |

### Playwright 通道（第二信源）

- 安装：`pip install playwright` + `python -m playwright install chromium`
- **重要**：本机 `C:\Users\15155\AppData\Local\ms-playwright` 目录**已预置 chromium 浏览器**
  （`chromium-1237` 等），是历史遗留。但**版本号须与 playwright 包匹配**——
  实测 playwright 1.62 要求 `chromium-1234`，与已有的 `1237` 不匹配，
  必须执行 `python -m playwright install chromium` 下载对应版本。
- chromium 下载约 150MB，**网络慢时会超时**，应放到后台任务执行（`run_in_background`），
  不要在前台阻塞。
- 用法：headless 启动 → `goto(搜索URL)` → `inner_text("body")` 抽取文本 → 正则/关键词匹配目标数字。

### 落地脚本

- `scripts/news_fetch.py`：采集 + 过滤 + 自动分级，输出 `_cross_validated` / `_needs_review`。
- `scripts/news_verify.py`：**双源交叉验证专用**（本脚本）。用 playwright 抓搜索引擎，
  比对关键数字，输出 `verified` / `suggested_credibility`（A 或 B）。

### 实战案例（2026-09-02，已验证有效）

验证对象：美国 8 月 ADP 就业人数。

| 项 | 源1 金十 | 源2 搜狗聚合 | 结论 |
|----|----------|--------------|------|
| ADP 8月新增就业 | 3.8 万人 | 38,000 人 | ✅ **一致** → §10.3 满足，**升 A 级（具备否决权）** |
| 市场预期 | 4.8 万人 | **47,000 人（4.7万）** | ⚠️ **金十口径有误** |
| 前值 | （未明确） | 增加 4.4 万 | 补充信息 |

**这条案例的价值**：第二信源不只是"再确认一遍"，它**纠出了单一信源的口径偏差**
（预期值 4.8万 vs 4.7万）。若只看金十，会带着一个错误的预期基准去判断"爆冷程度"。

**搜索引擎可用性实测**：

| 引擎 | 结果 |
|------|------|
| **搜狗** `sogou.com` | ✅ **最佳**（中文结果准、无需等待 JS、直接可抓） |
| Bing `bing.com` | ⚠️ 可用但需 `wait_for_timeout(2500~3000)` 等 JS 渲染，否则 body 仅 45 字符 |
| DuckDuckGo `duckduckgo.com/html` | ❌ 返回错误页（"If this persists, please email us"） |

**实操要点**（踩过的坑，勿重复）：
1. 必须 `wait_until="domcontentloaded"` + `wait_for_timeout(2500~3000)`，
   直接取 `inner_text("body")` 会拿到空/极短内容。
2. 必须设置真实 `user_agent`，否则被反爬。
3. 页面文本长度 < 200 基本等于抓取失败，应换引擎而不是硬解析。
4. 数字比对要**归一化**：`3.8万` ↔ `38,000` ↔ `38000` 视为同一值
   （`news_verify.py` 的 `normalize_num()` 已实现）。

---

## 5.9 关于「用户建议」的处理规则（2026-09-02 用户指示）

> **用户原话**：「我告诉你的东西，你要判断是否合适，如果合适要持久记忆。」

**本系统的处理规则（已固化为长期机制）**：

1. **判断，不是照做。** 用户建议进入后，先评估：是否有实证支撑？是否符合章程目标
   （§0 长期稳定盈利）？是否补上了某个已识别的缺口？**判断不合适的，要说明理由。**
2. **合适的必须持久化。** 光"记住"没用——下次会话上下文清空就丢了。
   落地位置按性质分：
   | 建议性质 | 落到哪里 |
   |---|---|
   | 数据源能力/边界 | `NEWS_SOURCES.md`（本文件） |
   | 交易规则/风控 | `AGENT_TRADING_RULES.md` + §13 变更记录 |
   | 已发生的教训/归因 | `EVOLUTION.md` |
   | 待批准的新规则 | `PLAYBOOK.md` 待批准区 |
3. **持久化要带"为什么"。** 只写结论的规则，日后无法判断它是否还成立。
   须同时记录判断依据与**可证伪条件**（与 §0.3 的 `falsifier` 同源思路）。

**本条建议的处理结果**：采纳。因为它补的是 §10.3 的**合规缺口**
（单源 → 永远 B 级 → 消息面否决权结构性不可用），而非锦上添花。已落地为
`scripts/news_verify.py` 并写入本文件。

---

## 6. 重大事实更正记录

| 日期 | 更正内容 |
|------|----------|
| 2026-09-01 | **美联储主席是 Kevin Warsh（凯文·沃什），不是鲍威尔**。此前决策笔记中的"鲍威尔讲话"表述已全面过时。Warsh 在 2026 Jackson Hole 重申抗通胀决心，暗示不排除加息，是 9月加息概率从 36% 跳至 65% 的直接原因。 |
| 2026-09-01 | 当前联邦基金利率目标下限 **3.50%**；10年期美债 **4.75%**（2025年1月以来新高）、30年期 **5.243%**、2年期 **4.339%**。 |
| 2026-09-01 | 7月非农 **−2.3万**（意外负增长），失业率 **4.1%**，前值下修。就业走弱与通胀黏性并存，形成政策两难。 |
