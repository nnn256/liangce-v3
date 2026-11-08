# 量测 v3：运行、备份与发布

本项目基于 [lllaaa999/stock-dashboard](https://github.com/lllaaa999/stock-dashboard) 扩展，保留上游MIT许可和接口。默认主页为新的浅色缠论研究工作区；`?terminal=1`保留原行情终端。

## Windows本地完整前后端

在项目目录运行：

```powershell
./start-liangce.ps1
```

默认 `http://127.0.0.1:8810`。首次运行创建`.venv`、安装依赖和构建前端；数据及任务写入`.runtime/research/`。已有研究快照位于`data/research/`，不受上游接口短暂不可用影响。

如需同一Wi-Fi的手机访问，运行`./start-liangce.ps1 -Lan`，用这台电脑的局域网IP与8810端口打开；系统防火墙需要允许该端口。`-Lan`会监听0.0.0.0，默认不启用。

## GitHub公开网页

目标展示名“量测v3”，仓库地址使用`liangce-v3`。仓库工作流`.github/workflows/liangce-pages.yml`在main更新时构建、类型检查并发布到GitHub Pages。Pages设置选择GitHub Actions。

GitHub Pages只能运行前端和静态研究数据。公开网页带有奥雅股份15周期、原文条款确认与历史回测，可独立查看、缩放、查证据和导出。它不是后台Python计算服务。

后端已经有HTTPS地址时，在仓库变量设置`LIANGCE_API_BASE`后重新运行Pages工作流；也可以在网页“连接设置”中填写地址。后端设置`LIANGCE_ALLOWED_ORIGINS=https://你的账号.github.io`。访问令牌只在浏览器会话中保留，不进入GitHub。

## FastAPI后端容器

复制`.env.example`为本地`.env`并填写来源/可选访问令牌，然后：

```bash
docker compose up -d --build
```

默认容器端口仅映射到宿主127.0.0.1:8810；公网服务应通过宿主的HTTPS反向代理转发。公共模式屏蔽上游有状态的纸上交易管理路由，只开放研究接口与健康检查。`LIANGCE_READONLY=1`可禁止新计算；`LIANGCE_API_TOKEN`可限制计算请求；任务队列最多4个、工作线程2个、单次不超过30,000根K线。

Docker构建文件已提供。宿主未安装Docker时，不能把配置文件存在写成已运行容器。后端公网运行需要服务器或云平台，GitHub仓库本身不提供常驻FastAPI进程。

## 新接口

| 接口 | 用途 |
| --- | --- |
| GET `/api/research/health` | 运行状态、归档日期、是否允许计算 |
| GET `/api/research/catalog` | 数据清单与SHA-256 |
| GET `/api/research/symbols?q=` | 5580只沪深京个股的明确市场字典 |
| GET `/api/research/panel/{symbol}/{period}` | 已核验快照/最新研究结果，支持ETag |
| GET `/api/research/quote/{symbol}` | 使用上游行情网关取报价，和历史研究分列 |
| POST `/api/research/jobs` | 结构分析或逐根信号回放，可指定历史截止日 |
| GET `/api/research/jobs/{id}` | 任务进度、错误、结果地址 |
| GET `/api/research/jobs/{id}/result` | 真实任务结果 |

`source=archive`使用已核验奥雅股份数据。`source=live`使用原仓库行情网关，原生周期不支持时明确报错；未认证的复权/完整性只返回结构候选，不升级为严格确认。当前任务模式`backtest`重放信号确认与失效账本，成交收益页面显示前次已经核验的完整基准模拟，二者有明确文字。

## 定义与数据边界

全部分型、笔、线段、中枢、两种ABCD、特征序列、震荡监视器、走势分解、历史信号与证据可查看。分型不等于买卖点；确认不是盈利保证；整体严格原文等价尚未证明。样本行情截至2026-11-06，不能将其写为实时。

奥雅股份2026-05-29的10转4.5已处理：分析使用因果后复权，成交模拟按原价与实际股数记账。图中原价与分析价明确分列。历史竞价是每日09:25实际撮合结果，65日缺记录；没有09:15—09:25虚拟撮合过程。分时快照不冒充一分钟OHLC。

## 检查

```powershell
./.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
./.venv/Scripts/python.exe -m unittest discover -s tests -t .
cd frontend
npm ci
npm run lint
npm run build
```

浏览器验收脚本为`scripts/qa_liangce_browser.py`，使用已安装的agent-browser。截图和机器报告写入忽略的`artifacts/qa/`。API契约覆盖数据哈希、股票市场身份、真实历史截断、错误输入、认证/来源控制、队列和结果状态。
