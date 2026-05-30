# 特朗普喊单追踪 · Truth Alpha

一个本地运行的网站 + Mac 菜单栏插件，自动追踪特朗普在 Truth Social 上的发言、识别其中提到的
股票/加密货币，用真实行情计算「自他喊单以来的表现」，每天对前一交易日做复盘，并为每次喊单画出
**喊单后的 K 线（蜡烛图）走势**。

> ⚠️ **仅供信息追踪与历史复盘，不构成任何投资建议。** 喊单识别基于关键词匹配，可能有误差，
> 历史表现不代表未来。请务必点开原文自行核实再做判断。

---

## 一、推荐用法：装成 Mac 菜单栏插件（一劳永逸）

```bash
./setup.sh         # 1. 安装依赖（只需一次）
./install_app.sh   # 2. 装成菜单栏插件并启动
```

装好后：

- 屏幕右上角菜单栏出现 **📈** 图标，点它 →「**打开仪表盘**」随时查看；
- 后台常驻托管 **http://localhost:8000**，开机自动启动；
- **每天自动刷新一次**数据，也可菜单里「立即刷新数据」手动刷；
- 菜单里能看到「数据更新于…」的状态。

取消自启：`./install_app.sh uninstall`（或点菜单 📈 →「退出」临时关闭）。

> 插件已包含每日自动刷新，无需再单独设定时任务。

---

## 二、备用用法：手动启动（不想常驻时）

```bash
./setup.sh      # 安装依赖（只需一次）
./update.sh     # 刷新数据（抓取+复盘，约 1-2 分钟）
./start.sh      # 启动网站，自动打开浏览器；Ctrl+C 关闭
```

> ⚠️ 菜单栏插件和 `./start.sh` 都占用 8000 端口，**别同时开**。装了插件就用插件，
> 不用再跑 `start.sh`。`./install_daily.sh` 是给「只用命令行、不装插件」的人单独设每日刷新用的。

---

## ✦ 分享给朋友：公网版（已部署）

**公网地址（任何人可访问，直接发给朋友）：**

### 👉 https://face9533.github.io/trump-alpha/

- 托管在 GitHub Pages，源码仓库：https://github.com/face9533/trump-alpha
- 数据由**你 Mac 上的插件本地生成**，每天自动 `git push` 到 GitHub → 自动重新部署上线
- 手动发布：菜单栏 📈 →「**立即发布到网上**」，或命令行：
  ```bash
  ./publish.sh           # 发布现有数据
  ./publish.sh --fresh   # 先刷新再发布
  ```

> **为什么数据放本地生成**：yfinance 从云端服务器 IP 拉行情常被 Yahoo 限流，
> 所以让可靠的本地插件生成数据，只把静态结果发布到公网。只要你 Mac 开机、插件在跑，
> 公网版每天自动更新；Mac 关机时公网版停在最后一次发布的数据，不会报错。

---

## 三、它是怎么工作的

```
Truth Social 公开存档          关键词字典              Yahoo Finance
(trumpstruth.org)     ──►   识别喊单的股票    ──►    拉取真实行情    ──►   计算表现+复盘
   pipeline/scrape.py        pipeline/extract.py     pipeline/prices.py    pipeline/analyze.py
                                                                                  │
                                                                                  ▼
                                                                         web/data.json → 网站
```

- **数据来源**：[trumpstruth.org](https://trumpstruth.org) —— 特朗普 Truth Social 发言的公开存档。
- **只统计他本人原创帖**：转发别人的帖子（ReTruth）显示的是原作者和原始日期，日期不可靠，
  因此不计入股价基准，避免「用 3 月的价格算 5 月的喊单」这类错误。
- **行情**：用 `yfinance` 拉 Yahoo Finance 日线，免费、无需 API Key。
- **建仓基准**：以发言当日收盘价为基准；若是盘后（美东 16:00 后）发的，用次一交易日。
- **复盘基准日**：最新一个美股交易日（即「前一天」），周末/节假日自动顺延。

### 识别逻辑与已做的纠错

识别用关键词字典（`config/companies.json`），并已针对真实数据做了多道纠错：

| 问题 | 处理 |
|------|------|
| 他签名 "DJT" 被当成喊特朗普媒体股票 | 去掉裸缩写，只认公司名 / `$DJT` |
| "US intel"（情报）被当成英特尔 | 歧义词需附近出现行业语境（stock/chip/company…）|
| 公司名出现在链接域名里（amazon.com 买书链接）| 匹配前剥离 URL |
| 公司名藏在被空格拆断的 URL 路径里 | slug 守卫拦截 |
| "Boeing 757"（飞机）被当成喊波音 | 公司名后跟机型号则忽略 |

即便如此，关键词匹配仍可能把「顺带提到品牌但非投资信号」的发言算进来——所以表格里每行都给出
**命中公司附近的原文摘录**，并可一键点开原文，方便你自己判断。

---

## 四、自己扩展要追踪的股票

编辑 `config/companies.json`，照已有格式加一行即可，无需改代码：

```json
{ "ticker": "COIN", "name": "Coinbase", "type": "stock", "aliases": ["Coinbase"] }
```

- `ticker`：Yahoo Finance 代码（加密货币用 `BTC-USD` 这种带 `-USD` 的写法）。
- `aliases`：要匹配的公司名/人名/别名（不区分大小写、按词匹配）；`$XYZ` 形式表示 cashtag。
- 可选 `require_context`：歧义名才需要，命中词附近须出现这些词之一才算（参考 Intel 那条）。

改完重新 `./update.sh` 即可生效。

调整回溯天数：`./update.sh 90`（回溯 90 天）。

---

## 五、目录结构

```
特朗普喊单项目/
├── menubar_app.py            Mac 菜单栏插件（托管服务 + 每日刷新）
├── install_app.sh            装插件并开机自启
├── setup.sh / update.sh / start.sh / install_daily.sh   其它一键脚本
├── config/companies.json     喊单识别字典（可自行增删股票）
├── pipeline/                 数据流水线
│   ├── scrape.py   抓取 Truth Social
│   ├── extract.py  识别喊单 + 多道纠错
│   ├── prices.py   拉行情（OHLC，供画 K 线）
│   ├── analyze.py  计算表现 + 喊单后走势 + 生成复盘
│   └── update.py   主流程
├── web/                      本地网站（index.html / styles.css / app.js / data.json）
└── data/posts.json           抓取的发言缓存（增量）
```

网站内容：核心指标（含**跑赢大盘超额收益**）→ 每日复盘（含当天标普对照）→ **复盘历史**（每天
自动存一条，可回看）→ 标的总览（迷你走势图）→ **喊单后 K 线复盘**（每次喊单的蜡烛图 + 次日/3日/
一周/至今表现 + vs 大盘超额 + 文字解读）→ 全部喊单明细表。点标的卡片可看该股整段 K 线。

> **超额收益**：每次喊单都和同期标普 500（SPY）对比，算出"跑赢/跑输大盘多少"，区分"真本事"
> 和"大盘普涨带起来的"。**复盘历史**存在 `data/reviews.json`，每天累积，长期保留。
> 想追踪的股票已扩到 50+ 只，仍可在 `config/companies.json` 自行增删。

## 六、常见问题

- **网站打不开数据 / 一片空白**：要通过本地服务器访问（菜单栏 📈 →「打开仪表盘」，或 `./start.sh`），
  不能直接双击 `web/index.html`（浏览器安全策略会拦住读取本地 data.json）。
- **菜单栏没出现 📈**：确认已 `./setup.sh` 再 `./install_app.sh`；查看 `data/app.log` 有无报错。
- **抓取失败**：trumpstruth.org 偶尔不稳定或限流，过几分钟再 `./update.sh`。已抓到的会缓存，不会丢。
- **某只股票没数据**：检查 `config/companies.json` 里的 `ticker` 是否是正确的 Yahoo Finance 代码。
