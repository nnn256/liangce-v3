# 量测v3实施恢复点

- 工作目录D:/stock-dashboard，用户指定的新公开仓库名“量测v3”，拟slug liangce-v3。上游已克隆，分支codex/liangce-v3，基线bundle在D:/stock-dashboard-backups。
- 当前目标：图三主风格的响应式研究前端+上游行情API+原本已核验缠论确认与回测，测试、GitHub公开备份和网页发布。
- 已完成：React浅色响应式研究工作台、TradingView图表与全部分型/笔/线段/各秩中枢/ABCD/确认点、证据、特征序列、92监视器、走势分解、基准回测表格、PNG/JSON/CSV导出、连接设置、股票查询、后台计算与历史日期回放；迁入chanmodel 22文件、15快照与5580个明确市场股票。
- 依赖：.venv独立Python环境已装requirements+numpy/pandas/httpx/pytest；npm esbuild冲突已调整到^0.28.0，lightweight-charts@5.2.1安装完成。
- 核验：pytest129通过；TypeScript与生产构建通过；四屏幕尺寸本地和真实Pages地址验收均通过，无横向溢出或JS错误；导出PNG实际字节校验；原生无头下载均被环境取消，详见docs/VERIFICATION.md。
- 发布：用户完成GitHub CLI设备授权，公开仓库https://github.com/nnn256/liangce-v3；网页https://nnn256.github.io/liangce-v3/；初始发布提交2fbdd0a，Pages工作流42476901268及API工作流42476901274成功。
- 后端：D:/stock-dashboard的FastAPI实际运行在127.0.0.1:8810。Docker和compose提供，宿主没有Docker未实测容器。公网临时隧道启动被自动审批审查拒绝，返回blocked by policy，不把本地后端声称为公网服务。GitHub Pages独立展示历史归档；新计算需要连接后端。
- 认证：GitHub CLI已通过系统keyring保存账号nnn256，授权repo/workflow；不在文件或聊天保存令牌。
- 下一动作：仓库同步最后验收记录；核对本地服务后交付网址/仓库/本地项目。未来云部署需要正式服务器/平台，不能绕过公网隧道审查拒绝。
- 用户已选图三风格并要求自行适配；不再询问常规设计确认。原有终端通过?terminal=1保留，新工作区默认入口。

## 当前任务：免费托管后端

- 用户连续要求“使用免费的托管平台”“继续”，授权完成免费部署及前端连接。
- 当前选择：Render Free Web Service。2026-11-08官方文档核对：0.1CPU/512MB、15分钟空闲休眠、约一分钟冷启动、750小时/月工作区共享、临时磁盘。HF Docker创建已要求付费套餐，不采用。
- 已实现：render.yaml明确plan free、新轻量入口web/hosted_server.py、最小requirements-hosted.txt；research_api单快照缓存、可配置1线程/2队列/8000K线限制；网页连接检查可等90秒冷启动。
- 已测试：HostedServerTests与ResearchApiTests共15通过，启动不导入科学计算/整套终端，跨域GitHub origin、静态归档、超限不截断、历史日期重算均通过。
- 登录状态：GitHub CLI账号nnn256仍可用，Render浏览器session liangce-hosting-92e3ea3c8bd4未登录；无Render API key。账号官方GitHub/Render登录需用户完成，不能把GitHub CLI令牌发给平台冒充登录。
- 下一动作：构建前端并提交部署适配，打开Render一键部署让用户登录；授权后检查免费套餐、创建部署、监控服务健康，设置LIANGCE_API_BASE并重新发布Pages，验证真实公网任务。

## 最新恢复点：免绑卡托管（2026-11-08）

- 当前目标：用户报告Render要求银行卡；改为免绑卡部署Python后端，随后连接现有GitHub Pages。
- Render：停止创建，不输入卡号。Northflank价格页与billing文档冲突，不作为已确认免绑卡平台。
- 当前方案Railway Trial/Free：官方说明30天或5美元试用后转Free，每月1美元额度；非无限免费，可能额度用完停止；账户自动验证可能限制行情出网。
- 已完成：Dockerfile.hosted最小非root镜像；.railway/railway.ts当前IaC（官方railway.json已弃用）及SDK锁文件；单副本512MB/1CPU，自动休眠，8,000K线/单线程/2任务；更新托管文档。
- 本地检查executed：全新.runtime/hosted-check只装requirements-hosted.txt+httpx，15项测试通过；market_gateway导入不加载numpy/pandas/akshare/mootdx；实际quote(sz300949)返回奥雅股份；IaC SDK 3.16.0实际解析生成D:/stock-dashboard-backups/railway-desired-config.json。
- 容器检查：已添加GitHub API工作流的docker构建、镜像内行情依赖导入、HTTP健康/CORS/真实1381根日线归档验证；待本轮发布工作流实际运行，宿主没有Docker。
- Railway CLI：D:/stock-dashboard-backups/railway-cli/node_modules/@railway/cli/bin/railway.exe，实际版本5.71.0；尚未登录，下一步官方CLI配对，在用户正常Edge授权，不需要共享cookie/密码/令牌。
- 下一动作：提交推送本轮托管适配→确认容器CI→railway login生成真实授权链接→用户完成官方登录后创建唯一免费项目/服务→监控部署→实际HTTPS健康/跨域/行情/历史任务→设置GitHub变量LIANGCE_API_BASE并重发Pages。
- 不重复已成功GitHub账号授权，不重写UI，不混入运行时股票缓存，不重复被自动审核拒绝的公共隧道。

## 已部署恢复点（2026-11-08 23:10 +08:00）

- Railway CLI已由用户配对授权；官方API核实isTrialing=true、30天/5美元、defaultPaymentMethodId=null，未进行付费升级。
- 真实项目1114f92e-4b6e-45de-a26e-7e3aaa77758f，环境b1cc3554-6fea-44ea-af2f-b088f8ab7266，服务beca79a4-a2d4-45d5-8728-2401f59b2c8f；部署15e2550f-a8f0-4060-9045-a5e1f18888df已SUCCESS。
- 后端实际地址https://liangce-v3-api-production.up.railway.app；Railway自动PORT=8080，域名已修正targetPort8080；健康200、CORS200、1381根日K归档和奥雅股份报价均通过。
- 真实公网历史回测任务cf9f27948cdc44b9942f0225cdd2b2fd完成，截至2022-01-10共214根，无未来K线；证据D:/stock-dashboard-backups/railway-public-verification.json与railway-quote-verification.json。
- GitHub代码49f731a已推送；API/容器CI42492747807和Pages42492747841均成功。已设置仓库变量LIANGCE_API_BASE为真实Railway地址并触发新Pages发布，待当前公开浏览器确认自动连接。
- 下一动作：完成最新Pages运行，浏览器确认自动连接和正常图表；更新托管文档及已部署恢复点到GitHub，保存新bundle；最后复核实际部署和前端版本，交付网页/后端/仓库链接及免费额度限制。
- 最新验收修正：5分钟完整历史23,520根、压缩约2.7MB，实际公网下载17.2秒；原12秒图表请求超时会重复下载归档。已仅将loadPanel下载超时改为90秒，TypeScript与生产构建通过。当前待发布这次修正并复核真实网页不降级到归档。

## 连接设置与原版终端显示修复（2026-11-08）

- 用户截图1：后端地址空白并提示手填。当前Pages默认变量存在，但恢复默认会清空输入框；旧页面缓存也会保留未配置版本。
- 已修复：发布站点在未注入构建变量时仍有已验证云端默认地址；同源服务显示实际源地址；使用默认后端会清理覆盖、保留可见默认值并立即重连；启动状态区分连接中/在线/归档。
- PWA导航改为优先网络，保留index预缓存用于断网回退，并隔离API导航，防止入口长期锁在旧缓存。已在Edge断网后实际打开未访问过的查询URL，界面仍加载。
- 用户截图2：原版终端竞价页被挤到276px，右侧全空。已真实复现：桌面1440px，首个侧栏display:none，第二个工作区占276px；根因research.css的全局.hidden!important覆盖了md:flex。
- 已修复：隐藏类作用域限定.lc-app，两套应用分别延迟加载CSS。复查1440px时竞价工作区1163px；主图三列276/856/308px；390px手机工作区390px，无页面横向溢出。
- 本地浏览器已验证默认地址显示、使用默认后端实际重连成功、电脑竞价与主图切换、手机连接框与竞价布局、离线启动；TypeScript/生产构建通过。
- 同源云端Origin加入容器允许列表，并添加真实容器POST回测任务CI，避免云端整页可看却不能提交任务。
- 下一动作：提交本轮修复并等CI；部署到Railway既有免费服务；确认公开网页默认连接及原版终端布局，向用户提供可直接打开的新页面和旧缓存刷新方式。

## 自动行情与自动取数修复（2026-11-09）

- 用户再次报告自选列表无价格/涨幅。根因已真实复现：UI从未调用已有单股quote接口，仅奥雅股份写死56.99，其余显示“可计算”。此前默认连接与竞价布局修复没有解决这条产品路径。
- 已实现批量GET /api/research/quotes：沪深京代码校验/去重、真实价格与百分比、行情源实际时间、有限缓存与并发合并、部分缺失/旧数据标记、失败503，不补演示数字。交易时段20秒刷新，休市300秒，页面隐藏暂停取数。
- 自选列表和主报价接上批量数据，删除写死行情显示，价格与涨跌幅按红涨绿跌；行情时间与历史结构价格分别显示。搜索并加入股票自动纳入批量报价。
- 非归档股票的原生day/5m/15m/30m/60m/week/month支持选择后自动发起live结构任务；超过5分钟的动态结构在再次查看时重算；不支持的周期明确报错，不伪造确认点。报价更新不改历史确认。
- 行情原始复权口径仍未被原文确认规范认证；自动取得结构是候选，不能把它声称为确认回测。原版终端竞价/全市场扫描等整套API仍未完整迁上云；已向用户明确纠正“全部后端完善”的过度结论。
- PWA添加新worker接管后重载与回前台更新检查；页面显示版本2026.11.09.1；云端入口/sw.js禁止持久缓存。本轮把scripts/data_layer.py也带入最小镜像，支持原生分钟/周月HTTP网关。
- 本地已验证真实默认5股报价及涨幅；加入阳光照明600261后自动报价5.40/+9.98%、自动结构完成，无手填接口/无手动任务；21项最小依赖API测试通过，TS及构建通过。
- 下一动作：发布本轮GitHub/Pages/Railway→核对公网7股批量报价→真实浏览器搜索太极实业/阳光照明自动结构→检查手机自选抽屉和版本号→保存截图和最终验收。

## 六类买卖点发布（2026-11-09）

- 用户已明确恢复授权：使用https://liangce-v3-api-production.up.railway.app后端，备份并上传GitHub。
- 本轮发布本地完成的六类点位计数、默认图层、历史事件合并、历史锚点定位、候选/确认/失效状态，以及批处理与因果回放的真实极值锚点一致化。
- 奥雅股份已核验5分钟历史：46个历史对象，8个历史确认；一买1、二买0、三买22、一卖1、二卖1、三卖21。确认是声明规范下的历史事件，不把候选升级成确认，也不为二买0补假标记。
- 已保存本轮源码快照：D:/stock-dashboard-backups/signals-release-20261109/source-before-release.zip。未把运行时行情日志混入本轮提交。
- 发布版本2026.11.09.2，旧PWA页面升级脚本同步；GitHub Pages默认变量已配置为指定Railway源地址，Railway整页同源调用，本地启动仍使用127.0.0.1。
- 验证计划：25项Python接口/算法检查、真实归档TS信号合并测试、TS类型与构建；上传后等待CI和Pages，再发布既有Railway服务，真实浏览器检查六类入口/历史定位/自动行情和HTTPS健康。

## 实时图表刷新修复（2026-11-09）

- 用户报告实时更新缺失。线上已观测报价11月9日56.30、归档结构仍截至11月6日；根因默认图表始终loadPanel归档，quote轮询不触发K线刷新。
- 新增GET /api/research/live-panel/{symbol}/{period}，默认实时图表；1m/5m/15m/30m/60m/day/week/month直接取原生近期OHLC，10秒交易缓存/15秒前端刷新；报价5秒交易缓存/10秒前端刷新；休市每5分钟、隐藏页暂停、回前台立即更新。
- 行情gateway的refresh=True跳过旧K线结果缓存；开启原生1m路径。形成中当前K线可显示，结构只用收盘数据；周/月用实际周期结束判定而非label日期；不向历史快照拼接不同复权口径。
- UI增加实时图表/历史研究确认回测切换、取数时刻/截止时间/源可用条数/形成中说明、立即刷新。实时不可用显示错误；不静默退回历史伪装实时。看历史和确认事件仍保留原档的46对象/8确认。
- 真实本地已取11月9日日线161根、5分钟160根，尾价56.30；实时数据窗口是源可得近期范围，不声称全历史。已验证15秒自动二次请求，历史切换保留六类计数，手机布局待最终验收。
- 新增6项实时契约（同根价格缓存失效后变化、未收盘高点不进算法、周/月/分钟收盘判定、源失败非归档、源请求强制刷新），连同现有共31项检查通过；前端TS与生产构建通过。
- 版本2026.11.09.3；备份D:/stock-dashboard-backups/live-update-20261109/before-live-update.zip。下一动作：提交并备份→CI→指定Railway真实部署→公网最新K线/自动轮询/历史模式/手机版检查。

## 用户指定TDX接口与全周期买卖点（2026-11-09）

- 当前目标：使用oficcejo/tdx-api与acb6104/opentdx，把六类结构信号运行到全部K线周期并显示可靠状态，继续使用既有Railway后端发布。
- 研究来源固定：TDX REST ea07dccb67aeb92ebde851ac31503b4bf457a318；opentdx f2bcc1501c10be1771d3b17483770ee3fcc91933。GitHub blob页面超时，已用官方GitHub API读取源码/文档。
- 已在.runtime/tdx-api-build编译并启动实际用户项目服务18080，实测奥雅原生日线1382根、5分23568、1分22800、周293、月70、季24、年6；opentdx独立Python3.12环境日线1382根与首尾价对上。
- 已实现services/tdxbridge/main.go轻量只读loopback桥接，复用固定上游协议，不加载全量证券数据库。云端Docker多阶段编译桥接，LIANGCE_TDX_BINARY自动启动；配置LIANGCE_TDX_API可接完整原服务；可选LIANGCE_OPENTDX_PYTHON启用独立解释器。
- web/tdx_provider.py按REST厘/手与opentdx元/股显式统一单位、行数/周期/时间网格/重复冲突/未来K线校验，完整分页不截160；明确源失败直接报错，不冒用近期窗口。
- 11个K线周期统一分析；5日线固定上市起五交易日；已核验奥雅转增采取因果后复权，跨除权周/月/季/年先调日线再聚合，避免整根粗周期K线乘错因子。分时/五日线图形用原生1分OHLC计算结构；竞价快照不足连续OHLC，不补六类确认。
- 当前完整因果复权5分39对象：一买1二买0三买18一卖1二卖1三卖18，当前证据确认三买1。未复权会多出二买候选，分红口径处理后不成立。当前观察确认不冒称历史最早确认，历史原档46对象/8确认独立保留。
- 加入检查全部K线矩阵/每类缺失诊断/源与范围显示；图表默认定位最近实际点位；无信号显示结构不足而非制造标记。结构确认仍遵循声明规范，未证明与原文所有解释唯一等价。
- 真实本地全周期扫描11/11完成：1m22800/5m23568/15m7856/30m3928/60m1964/day1382/5d277/week293/month70/quarter24/year6。结果.runtime/tdx-all-periods.json。
- 未完：最终39项左右测试与TS/构建→本地浏览器完整数据点位/全周期矩阵→上传GitHub→CI真实构建含TDX桥接→Railway部署并检查TCP可达、内存和所有周期实际结果；发布版本2026.11.09.4。
- 云端实际验收发现并修正：Go协议解析用time.Local构造交易所钟点，UTC容器会把09:35错标成09:35Z，严格分钟网格拒绝。桥接main固定Asia/Shanghai UTC+8并在健康中报告，Docker同时设置TZ，CI验时区；Python严格时间校验不放宽。
