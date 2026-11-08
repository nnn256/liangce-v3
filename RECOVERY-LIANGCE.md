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
