# 量测 v3 · 免绑卡后端托管

目前网页已发布：[量测 v3](https://nnn256.github.io/liangce-v3/)。云后端仍待平台账户授权；配置和本地检查完成不等于公网部署完成。

## 选择 Railway Free / Trial

核对日期：2026-11-08。官方来源：[免费试用](https://docs.railway.com/pricing/free-trial)、[套餐与资源计费](https://docs.railway.com/pricing/plans)、[Serverless休眠](https://docs.railway.com/deployments/serverless)。

- 新账户可免绑卡使用30天或5美元试用额度，以先达到的为准。试用结束后自动转为Free，每月1美元资源额度，不结转。
- 这不是无限免费服务器。内存、CPU、出站流量按实际用量消耗额度；频繁计算、长时间运行可能提前耗尽额度并停止服务。不选择Hobby或Pro付费订阅。
- Free最多1个副本、0.5GB内存、1vCPU。项目只部署一个轻量API，不创建数据库、持久盘或其他付费资源。
- 已在配置中启用Serverless，连续无出站流量约5–10分钟后休眠。首次访问可能短暂返回502；网页连接检查会重试等待唤醒。不要添加定时保活或第三方监控来阻止休眠。
- GitHub账户的自动验证决定Full或Limited Trial；Limited可能限制访问行情源。已有归档与重算可独立使用，实际远端行情请求仍须部署后验证，不能承诺平台一定通过账户验证。
- 新任务保存在临时磁盘，休眠、重启和部署后可能丢失。GitHub中的已核验快照随镜像保留；需要保存的新结果请导出JSON/CSV。

Render在本账户创建服务时要求银行卡验证，因此本次停止使用。Northflank价格页写着无需卡，但其billing帮助文档又要求所有用户添加付款方式，官方资料不一致，暂不作为免绑卡方案。此前“Free即可直接部署”的描述不能用于证明本账户无需卡。

## 已准备的部署文件

- `Dockerfile.hosted`：只安装`requirements-hosted.txt`，只复制研究引擎、行情网关及其依赖、已构建前端和真实归档。以非root用户运行，使用平台`PORT`。
- `.railway/railway.ts`：Railway当前IaC配置，固定仓库`nnn256/liangce-v3`和`main`分支、轻量Dockerfile、健康检查、单副本、512MB上限及自动休眠。
- `.railway/package-lock.json`：锁定IaC SDK。平台已弃用旧`railway.json`，本次不新增该格式。

研究API保留1个计算线程、最多2个排队/执行任务和单次8,000根输入限制。超过限制会明确报错，绝不截断历史冒充全量结果。完整归档仍可查看。

## 官方账号授权后部署

先执行`railway login --browserless`，在Edge打开该次CLI实际生成的官方链接完成配对。登录或注册由账户本人完成；GitHub CLI授权不能代替Railway授权，不需要在聊天发送密码、令牌或银行卡。

```powershell
npm ci --prefix .railway
railway init --name liangce-v3
railway config plan
railway config apply --yes
railway domain --service liangce-v3-api --port 8810
```

部署前确认账户仍为Trial或Free、计划只新增一个API，启用Serverless且未添加付款方式。若GitHub仓库源需要额外安装Railway GitHub App，由官方授权页完成。部署后从CLI实际输出获取HTTPS域名，不按服务名猜测地址。

## 连接现有网页

远端`/api/research/health`必须实际返回`status: ok`；随后检查跨域、归档、历史前缀任务完成和真实行情请求。全部通过后，把实际HTTPS源地址写入GitHub仓库变量`LIANGCE_API_BASE`，触发`liangce-pages.yml`，再验证公开页面。URL不带`/api`。

本地最小依赖环境已检查15项研究API与托管入口契约，并实际请求到奥雅股份报价。容器构建、平台账户验证、远端任务和网页自动连接分别记录实际结果；尚未执行的项目不得标为成功。
