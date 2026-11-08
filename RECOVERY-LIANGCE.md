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
