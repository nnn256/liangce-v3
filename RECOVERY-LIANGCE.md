# 量测v3实施恢复点

- 工作目录D:/stock-dashboard，用户指定的新公开仓库名“量测v3”，拟slug liangce-v3。上游已克隆，分支codex/liangce-v3，基线bundle在D:/stock-dashboard-backups。
- 当前目标：图三主风格的响应式研究前端+上游行情API+原本已核验缠论确认与回测，测试、GitHub公开备份和网页发布。
- 已完成：读取repo与技能；迁入chanmodel 22文件和15快照（7.34MB gzip）；独立核对5580股票代码表；FastAPI research_api与research_server初版；frontend API/types；设计说明docs/LIANGCE-BRIEF.md。
- 依赖：.venv独立Python环境已装requirements+numpy/pandas/httpx/pytest；npm esbuild冲突已调整到^0.28.0，lightweight-charts@5.2.1安装完成。
- 未完成：React研究UI、图表/图层、API测试、响应式验收、部署配置、git提交与发布。
- 授权状态：用户授权创建公开仓库并部署；机器无gh、无GH/GITHUB_TOKEN。现有SSH钥匙只认证为nnn256/-的deploy key，不能据此假定有其他仓库创建权限。需使用官方GitHub设备登录完成发布。后端云运行环境未提供，先完成本地与容器可运行结果，再最后处理发布缺项。
- 用户已选图三风格并要求自行适配；不再询问常规设计确认。原有终端通过?terminal=1保留，新工作区默认入口。
