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

## TDX云端验收完成与最终版本（2026-11-09）

- 固定上海时区后，云端全周期检查11/11成功，真实结果保存在D:/stock-dashboard-backups/tdx-signals-20261109/public-periods.json；原生5分23568根，源oficcejo/tdx-api，公网5分图表200响应约2.35MB压缩传输。
- 浏览器验证一买锚点可定位，六类入口和11周期矩阵正常。云端进程内存约193MB/512MB，TDX空闲连接45秒关闭以允许免费实例休眠。
- 最终版本2026.11.09.5同步页面升级脚本，并在健康接口分别列明可用视图与竞价确认缺证；全周期失败行明确失败且不误导航，0仍表示规则未形成。
- 0c9f190基础接入、b8e2382上海时区修复已在GitHub main；下一动作最终提交/发布→CI/部署→13个可用视图与11周期矩阵/点位/手机验收→保存最终备份与结果。准确性限于声明规则、复权和闭合K线检查，不能承诺未来盈利或原文唯一等价。

## 当前任务：精细笔级/线段方向 + 无线传媒与奥雅全周期真实回测（2026-11-10）

- 最新用户要求：截图明确为无线传媒301551；六类点位精准标注、全部K线运行回测；精细看笔，大方向看段。保留此前授权的GitHub备份/云发布；不得把预测箭头当成已发生信号，不承诺准确率或收益。
- 当前工作区D:/stock-dashboard，Git HEAD仍753ce8a（上一轮TDX完成），本轮源码修改尚未提交；运行时脏data日志不混入提交。
- 已做：chanmodel/stroke_signals.py独立笔级代理（Config loose，以实际高低价锚点、同向力度/两中枢趋势/首次回试门控）。StreamingStructure新增segments=False复用逐根因果笔；线段原文门控仍独立，不降低rank>1等证据条件来凑信号。
- 已做：web/precision_backtest.py后端串行全周期任务，11periods，逐根前缀产信号和事件、保留确认/失效/撤回与延迟，再使用causal_portfolio真实次根开盘/T+1/100股/费用/5bp滑点/涨跌停/前根量约束成交。粗周期事件映射到下一交易日开盘执行。修复原simulator用当前整根bar.volume判开盘资格的前视（现在只用前根成交量）。
- API新增POST /precision-backtests、GET /precision-backtests/{id}、GET /precision-backtests/{id}/{period}、GET /saved-replays/{code}/{resolution}；detail允许读取data/precision-replays已保存结果。需实际完成后复制结果并生成manifest，当前还没复制。
- UI新增精细笔级观察/线段大方向/叠加三按钮，stroke默认；实时panel附stroke_model，archive读取也附stroke_model；六类标签显示笔级代理口径；新增PrecisionBacktests表格、进度、11周期各类观察/确认数/交易/收益/回撤，可查看点位和导出。需修好replay detail的显示与portfolio_metrics使用，已基本接好待浏览器验收。
- 重要真结果：无线传媒日线511根，严格笔35，精细笔45，原段级没有信号；精细笔回放10个规则确认，包含二买锚2026-08-25/首次可知2026-09-09；不能说是原文严格确认。无线5m24000根精细回放386对象318规则确认（计数 first_buy44 second_buy24 third_buy119 first_sell29 second_sell13 third_sell157），耗时231s→PriceRanges sparse精确范围查询优化后126s，结果完全一致。
- 已测试：45项Python接口/新笔级prefix不重写、range直接对照、同bar总量不影响开盘成交等全部通过；前端类型与build通过。测试文件test_precision_backtest.py/test_stroke_signals.py已加入CI待发布。图表笔加粗/独立级别/当前状态标注，不把末端折线预测成1/2点。
- 服务：新本地完整验收8836，PID44012，tools exec session54326，LIANGCE_TDX_API=http://127.0.0.1:18083，LIANGCE_RUNTIME=D:/stock-dashboard/.runtime/precision-acceptance。服务是在本轮早段启动，后续源码部分不热重载；目前长任务进行中，先别重启。
- 真实全量runner：.runtime/run_all_precision.py正在exec session30664运行，依次等待4个后端job（无线stroke→奥雅stroke→无线segment→奥雅segment），每任务11周期。结果导出.runtime/precision-acceptance-export/*；runs.json完成摘要逐步保存。
- 任务1无线stroke id84b01be20c914a49b2a6778b9390aeab，11/11完成。任务2奥雅stroke ida8de951d27ec40159e7d4ad21054a5eb，上次进行5m，已过1m。任务3/4id待runner生成。用户需要实际全部跑完，不可用当前period-scan结果冒充回测。
- 第一真实成交结果：无线1m22320根笔级59笔，14胜，胜率23.7288%，净收益-1.0503%，最大回撤-3.1883%；真实结果差不可隐藏或调阈值迎合“精准”。
- 当前前端已构建，可用agent-browser sessionliangce-fine-test页面http://127.0.0.1:8836/?symbol=sz301551&period=day&data=live；pending tools exec session14919等待笔级二买显示。不要只等文本就称chart渲染成功；核验svg真实label+点位与确认日期。
- 问题/未完：优化原段回放较慢4任务约多分钟；等待runner时继续独立UI/测试/文档。服务器当前加载早版代码，最终等4任务全部完成再重启应用新validation/档读取。
- 下一动作：poll session30664与14919→完成UI/避免面板切周期清掉replayDetail（已移除fetch清除，activePanel按symbol/period/resolution匹配）→复制实际4job到data/precision-replays/{id}，manifest和每个detail输入hash/时间/数量验证→加入Docker COPY保存回测→重启8836验证已保存结果和笔段切换/手机→写真实回测报告CSV/JSON→版本2026.11.10.1提交备份发布Railway+Pages→云端真实图形/加载回测验收。
- 新增代码错误已纠正：precision模块在web不是chanmodel；去掉了无用rebase函数中错误构造；npm/pyscript工作目录错一轮已重跑成功。45通过后新增saved-replays需补针对读取验证。


## 最终精细笔级回放检查点（2026-11-10）
- 旧笔级v1数字作废；最终profile stroke_actual_extreme_center_first_retest_v2已在两股全部11周期重跑。无线最终id c91e98e2895a46e19aba467d5e593297；奥雅最终id95d4d8fe19154749923b5280ba8b089b。线段保留47bee78192614512831a3f2bb3e399de/0cb11d3770504cb19e08dcd30d16eb49。
- scripts/publish_replay_artifacts.py实际核验44输入哈希、1462确认极值和934成交时间，保存48份gzip约22.6MB及manifest于data/precision-replays。结构图层/MACD/ABCD随历史输入保存，防止当前窗口错配。详报artifacts/precision-backtest/README.md及CSV。
- 最终真实收益：无线日线-2.5376%、5分-24.0605%；奥雅日线+92.9327%（回撤-29.72%）、5分+18.4127%。代理规则确认不冒充原文全部等价，不声称盈利或准确率保证。
- 47项最小依赖Python测试通过，TS及构建通过；本地最新服务8836 PID3824 exec session88666。浏览器session liangce-precision-final已验精细笔级、加载日线历史、6确认与独立段模式；PNG图导出已实际生成。
- 下一动作：完成跨周期/手机/browser验收→提交只含任务代码与已核验结果→推送main→CI及Pages→既有Railway实际部署→公网回测与图表核验→备份/交付。长期授权用户指定Railway与GitHub未变；不混运行时data日志。


## 实时主图修复（2026-11-10，版本2026.11.10.2）
- 用户新要求“改实时获取”。已发现并移除PrecisionBacktests按相同输入哈希自动载入历史明细覆盖主图的effect。默认仅实时panel，历史明细须点击查看；返回实时/立即刷新/顶部和手机看盘入口清理回放并请求上游。
- 增加GET live-panel?refresh=true，跳过图表短缓存。自动15秒交易/300秒休市，报价原有10秒交易/300秒休市，页面隐藏暂停，回前台获取。回放时暂停主图轮询且状态明确固定时间。只用闭合K线确认结构。
- 48项Python检查通过（新增缓存内修改同根价格强制取数），TS和构建通过。本地浏览器8837实际验证默认没有自动明细请求、普通轮询发出、强制刷新03:34:34及返回实时03:35:13源取数时间前进，source_kind=live_market_panel；历史须显式打开且可退出。
- 备份基线D:/stock-dashboard-backups/realtime-default-20261110/BASELINE.zip；不提交无关data运行日志。下一动作手机/5m核验→提交并推送main→CI→既有Railway部署并公网核验。


## 当前在做：分享未归档股票/回测入口/分型大小/全部叠加（2026-11-10）
- 用户连续反馈其他人打开新华传媒5日K失败、其他股票回测不行、分型显示大小、三按钮同时全开。本轮统一实现，版本2026.11.10.3尚待最终提交发布。
- frontend/api旧7周期automaticPanel替换为统一live-panel，无归档自动实时取数并切mode。research_api.live_bars也接TDX。新增实时分享按钮canonical symbol/period/data=live，不含本地设置。截图600825实测TDX返回1550根5日K。
- 顶部/手机回测入口改为ref触发PrecisionBacktests当前周期任务，完成自动显示回测账户与交易；组件不再依赖panel存在。提供当前/全周期两个按钮，结果latest临时可供其他浏览器读；失败周期partial/failed正确。避免归档异步返回覆盖新任务。未认证公司行动添加回测局限。
- 本地浏览器8838新华传媒5日K顶部点击完成1/1、7平仓、42.9%胜率、-28.65%回撤、1324.55费用；8839奥雅日线实际顶部回测6平仓/-29.72%回撤；太极日线7830根已跑46平仓/-42.99%收益。sessionliangce-shared-stock/ li angce-all-scales分别测过；执行服务8838旧中期后台，8839较新后台。
- structureScale.ts按K线/笔端/段端分层，保留全分型及价格、原锚点、父结构证据时刻，不把大标记冒称跨周期级别。structureOverlay.ts合并fine笔/粗段/两套中枢信号，三按钮默认同时高亮，回测独立口径。ChartPane显示三开关、全部价格与幅度/根数，已截图D:/stock-dashboard-backups/share-backtest-20261110/all-structures.png。
- 51项Python通过，TS通过，structureScale/structureOverlay tests通过。当前少量末尾修改需最终lint/build和浏览器再确认→提交GitHub main→CI→既有Railway发布→公网新华5日K实际顶部回测→新浏览器分享/mobile验收→备份回滚/交付。
- 基线D:/stock-dashboard-backups/share-backtest-20261110/BASELINE.zip，Git当前HEAD57ba5ee。无关data运行日志别提交。


## 当前：手机独立唤醒后端/首次连接重试（2026-11-10版本.4）
- 用户问为什么电脑打开手机才连接，已查Railway现有部署sleepApplication=true；电脑可唤醒共享实例，但无用户手机日志不能排除网络问题。
- 已修wakeBackend原90秒后停止问题：backendConnection.ts可取消前台自动重连，早期1.5秒随后10秒，隐藏/离线暂停，401/403/404/身份错误不重试；ResearchApp连接成功且无主图时立即请求，唤醒状态清晰。
- 新backendConnection.test.ts通过，TS与构建通过。模拟服务8841脚本.runtime/test_mobile_wake.py health前7次503+panel首请求503，browser sessionliangce-phone-wake-retry手机390px等恢复。实际hosted服务未人为休眠，未更改免费套餐或保活。
- 基线备份D:/stock-dashboard-backups/mobile-wake-20261110/BASELINE.zip。当前Git基线b039de309e2147177cf8c58d6b523ff90007efae，线上真实仓库nnn256/LiangCe分支codex/hosted-chan-167，备份/Pages nnn256/liangce-v3 main，两边同步。
- 下一动作：查看模拟浏览器恢复证据→最后lint/build/test→提交双仓并等CI/Railway自动部署→手机公网核验→备份可逆验证→交付原因和新版链接。别提交无关data日志。


## 正在做：竞价实时快照 + 产品内监控提醒（2026-11-10 .5）
- 用户截图指竞价标签报422，要求实时获取，并加入价格/买卖信号监控。已新增web/auction_panel.py，由gateway真实L1报价/五档盘口，源时间只在实际竞价窗口且120秒内的当日采集才追加曲线，不补造历史或缠论信号；realtime_panel auction转该接口。Docker要带auction_panel已修改。
- 新GET /api/research/monitor-signals/{code}/{period}?resolution=stroke|segment，返回最小信号与当前规则确认。make_panel为fine附当前观察confirmations/records，保留stroke_rule_current_observation语义，非历史最早确认，仍只用闭合K线。ResearchApp/structureOverlay使用fine确认数据。
- 前端新增alertEngine.ts/useAlerts.ts/AlertsPanel.tsx/AuctionSnapshot.tsx/alerts.css。价格>=<=和涨跌幅，六买卖类可选择笔/段与确认Only；首次信号基线不补历史，价格新鲜度和跨越去重；20规则/4启用信号，localStorage规则/状态/200事件。页面toast、显式浏览器通知授权、用户启用音效，测试/暂停/删除/检查/记录。页面打开才运行，后台锁屏可暂停/关闭不保证，不伪称云推送。技能stock-monitor已读/宣布；无Codexautomation工具可用也无需，因为这是产品功能。
- 56 Python tests通过，alertEngine与TS检查及构建通过；版本constants/cache升级为2026.11.10.5。源码还未commit。CI加入auction tests和alertEngine test。
- 本地服务8843 exec64123，LIANGCE_TDX_BINARY=.runtime/tdx-api-build/liangce-tdx-shanghai.exe port18085可自动启动。真实竞价56.30 source_time11-09 16:14:42/五档；非竞价0快照；5分signal334/confirmed11，日line1/0。
- 浏览器agent-browser新Edge启动失败/Chromeqa renderer旧target卡住，用CDP关闭own page并新建成功。当前独立Chrome DevTools63094 sessionliangce-alerts-cdp --cdp63094，page127.0.0.1:8843；可继续用该CLI。QA旧sessionliangce-auction-alerts-qa有卡住daemon，别误动用户正常Edge。
- 页面新增价格rule60、signal5m已成功，模拟fresh59→61 priceevent1，重复不增；模拟新增三买confirm事件成功。全部在本地QA fetch override，不是市场事实；snapshot D:/stock-dashboard-backups/auction-alerts-20261110/monitor-mobile-test.png；390/390无溢出。接下来清理本地模拟state，build最后修改→重载浏览器查看真实竞价/规则持久化/通知及手机→提交双仓main与LiangCe codex/hosted-chan-167→CI+Railway→公网实际竞价和signal/提醒入口验收→备份回滚→最终准确说明关闭页无保证。
- 基线备份D:/stock-dashboard-backups/auction-alerts-20261110/BASELINE.zip。当前HEAD8f63810d0c5e0dd7c00138cff03fdd49e599e8f6。不要提交无关data日志。
