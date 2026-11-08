# 量测 v3 · Render免费后端

已准备好[一键部署](https://render.com/deploy?repo=https://github.com/nnn256/liangce-v3)，使用仓库根目录的`render.yaml`。登录Render后可直接导入；服务计算套餐在文件中明确为`plan: free`。

## 已核对的免费条件

核对日期：2026-11-08；来源：[Render免费说明](https://render.com/docs/free)、[Blueprint字段](https://render.com/docs/blueprint-spec)、[FastAPI部署](https://render.com/docs/deploy-fastapi)。

- 免费Web Service提供HTTPS地址，0.1 CPU / 512MB内存。
- 连续15分钟无流量会休眠，下次访问唤醒约需一分钟。网页保留历史归档；设置中的连接检查等待最多90秒。
- 工作区每月750小时免费实例时间，多个免费服务共享。达到免费额度时可能暂停。
- 本地文件是临时存储，休眠、重启、部署后新任务结果可能丢失。GitHub随代码保存的研究快照可以重新加载；需要留存的新结果请导出JSON/CSV。
- 构建分钟和出站带宽另有工作区包含额度。若没有添加付款方式，超额后暂停服务/构建，而不是必须升级才能使用本项目。仅使用Free实例，无需在本部署配置中选择付费数据库或磁盘。

Hugging Face官方当前说明创建Docker/Gradio计算Space需要付费账户，因此本次不采用它，尽管CPU Basic硬件本身仍标为每小时免费。

## 本项目如何适配

`web.hosted_server:app`只在启动时导入FastAPI和研究路由。行情网关按实际请求延迟加载；启动不加载numpy、pandas、akshare、mootdx和原整套终端。

Render构建只安装`requirements-hosted.txt`。仓库已提交可用的前端构建与15周期研究快照，服务不需要重新下载Node和构建前端。

限制公开写入任务为1个工作线程、最多2个排队/执行任务、单次8,000根输入；超过时明确报错，不截断价格来冒充全历史。全部历史图和已有基准回测仍能查看。若要重放较长分钟历史，可在本地完整后端运行；免费机器的CPU和内存不适合同时重算全部市场。

`LIANGCE_ALLOWED_ORIGINS=https://nnn256.github.io`允许现有GitHub Pages调用。健康接口`/api/research/health`返回实际计算限制和临时存储属性。

## 部署后连接

部署成功后，Render会显示实际服务URL，例如`https://某个服务名.onrender.com`。先访问该地址的`/api/research/health`，必须实际返回`status: ok`。不能仅凭文件里服务名推定URL。

再在[量测v3网页](https://nnn256.github.io/liangce-v3/)的“连接设置”填入该HTTPS源地址，点击“保存并检查”。若要所有访客自动连接，用GitHub仓库变量`LIANGCE_API_BASE`设置该实际地址，再运行Pages工作流。无需在地址后添加`/api`。

如果Render要求邮箱验证、GitHub授权或账户安全验证，需要账户本人完成。GitHub CLI的授权不等于Render账号登录。服务创建与部署只使用已经准备好的Free配置。

## 已执行检查

`tests/test_hosted_server.py`检查最小启动、跨域预检、真实快照、超限不截断、历史前缀计算及临时存储说明；与研究接口测试共15项通过。创建好服务后还需检查远端健康、公开网页连接和实际任务完成，才能记为已上线。
