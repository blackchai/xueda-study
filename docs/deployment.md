# 部署准备与第六阶段验收边界

## 1. 当前状态

后续云部署任务已获授权，最新适配与未完成事项见[云端部署记录](cloud-deployment.md)。下文保留第六阶段当时的验收边界；Render配置、迁移连接和代理策略的最新实现以云端部署记录及当前源码为准。

第六阶段已完成站内通知和本机全站验收。本轮按最新需求不操作域名/DNS、不注册或修改云资源、不执行正式公网部署，也没有把旧静态原型冒充为当前全栈版本。

当前交付入口为本机前端5173、后端8000。下一阶段按Render + Neon准备独立预发环境；正式网址只在真实部署、HTTPS和多人验收完成后报告。本阶段不处理自定义域名。

## 2. 推荐拓扑

```text
浏览器
   │ HTTPS / 云平台分配的产品服务地址
   ▼
TLS 终止 + Nginx/云负载均衡
   │
   ├─ /            -> Vue dist
   ├─ /api/v1/*   -> FastAPI
   └─ /health/*   -> FastAPI
                         │ asyncpg + TLS/内网
                         ▼
                   Neon PostgreSQL（下一阶段待联调）
```

优先同源部署，这样 Cookie 使用 `Secure; HttpOnly; SameSite=Lax`，不需要为认证引入额外跨站复杂性。如果前后端必须跨站，需要单独评审 `SameSite=None`、Secure、精确 CORS 和 CSRF token，不可直接开放 `*`。

## 3. 生产变量

从 `.env.production.example` 复制本地、不进入 Git 的 `.env.production`：

- `STUDYMATE_DATABASE_URL`：PostgreSQL asyncpg URL，优先使用云平台 Secret。
- `STUDYMATE_AUTH_SIGNING_SECRET`：至少 32 字节高熵随机值。
- `STUDYMATE_AUTH_COOKIE_SECURE=true`。
- `STUDYMATE_AUTH_COOKIE_SAMESITE=lax`。
- `STUDYMATE_AUTO_CREATE_SCHEMA=false`，由 Alembic 迁移。
- `STUDYMATE_CORS_ORIGINS`：同源部署可留空；跨源时仅填精确 HTTPS origin。

第六阶段Origin校验精确比较协议、主机、端口，注册/登录也校验浏览器Origin；本地默认只允许localhost:5173与127.0.0.1:5173。生产配置拒绝占位密钥、SQLite和自动建表。原始Cookie仍为不透明随机会话令牌，数据库只存哈希，不使用前端LocalStorage保存敏感认证凭证。

不得把数据库密码、签名密钥、会话令牌或用户密码写入镜像、仓库、构建日志或前端 `VITE_*` 变量。

## 4. 发布步骤

1. 为生产 PostgreSQL 创建最小权限应用用户，启用备份与连接加密。
2. 在预发数据库执行 `alembic upgrade head`，完成数量、约束和回滚方案审核。
3. 构建前端，确保 `VITE_BUSINESS_DATA_MODE=api`。
4. 部署后端和前端静态文件，运行数据库迁移，再启动 Uvicorn/Gunicorn 工作进程。
5. 先使用云平台分配的服务地址完成同源HTTPS/Cookie验收，自定义域名另行处理。
6. 运行发布验收与恢复演练，通过后再切换正式流量。

根目录Dockerfile、compose.yaml、render.yaml保留。已用PyYAML解析Compose并静态核对依赖健康检查、loopback映射、独立数据库卷、数据库不暴露端口和env_file引用；这不等于`docker compose config`或实际构建/启动成功。本机没有Docker或Nginx，相关运行检查未执行。

现有render.yaml是较早的“Render Web + Render托管数据库”方案，包含资源套餐和域名配置，**不是已验证的Render + Neon一键方案**。下一阶段应先改为外部Neon连接Secret、删除不需要的数据库/域名自动创建声明，并核对免费套餐与账户限制，才能执行部署。当前没有修改或同步该Blueprint到云端。

## 5. 生产验收清单

- 两个全新账号可注册，数据库中只看到 Argon2id 哈希。
- 用户名、邮箱登录都可用；错误密码、重复邮箱与限流结果正确。
- 刷新和重开浏览器在会话有效期内保持登录；退出后原 Cookie 失效。
- 普通窗口与隐私窗口分别登录 A/B，目标与打卡隔离，越权 UUID 返回 404。
- 应用到 PostgreSQL 的数据在重启、换浏览器和换设备后仍一致。
- Cookie 具有 Secure/HttpOnly/SameSite，HTTPS 无混合内容，CORS/Origin 拒绝非可信来源。
- 日志不包含密码、Cookie、数据库 URL 或密钥；告警、备份和恢复演练有记录。

## 6. 本环境未完成的验证

2026-11-13本机实际结果：PostgreSQL96项、前端33项通过，四个Chrome完整场景通过；SQLite85项通过、11项PG并发测试跳过。Alembic空库→0005、带旧用户/目标/任务/打卡/通知的0004→0005、现有开发库无损升级及模型一致性均通过。通知桌面/手机、手机创建表单与网络错误重试已联调。详见[第六阶段验收报告](phase6-acceptance-report.md)。

这些是本机独立数据库与浏览器上下文证据，不代表公网TLS、真实跨设备、长期负载、容器或云服务验收。当前PostgreSQL在/tmp，仅作开发验证，不能当作正式持久化或备份方案。

## 7. 下一阶段Render + Neon准备清单

1. 确认GitHub源码仓库与完整源文件（含所有迁移）已同步，密钥/会话/测试数据库不入库；当前工作区未配置Git远程，不把本地未提交文件误认成已上传。
2. 登录并连接Render与Neon账号，选择允许的免费资源/地域，核对休眠、连接、存储和超额策略；不自动创建付费服务。
3. 用独立Neon数据库/分支做预发，创建最小权限角色；应用连接与Alembic直连分别核对，生成的数据库URL仅存Secret。
4. 先适配并实际验证SQLAlchemy asyncpg的TLS参数。现有协议转换只处理postgres/postgresql前缀，不能假设Neon复制出的sslmode/channel_binding参数能直接传给asyncpg；本阶段未连接Neon。
5. 明确容器PORT与云平台端口、反向代理TLS转发和真实客户端IP。DockerCMD现有`forwarded-allow-ips '*'`必须结合目标平台可信代理策略收窄/验证，防止伪造转发头影响来源判断和限流；当前未验证云代理拓扑。
6. 先在预发跑0005迁移、alembic check和三账号端到端测试，再执行备份恢复演练。对已有真实数据库先备份，不执行create_all或清空表。
7. 保持Vue与FastAPI同源：VITE_BUSINESS_DATA_MODE=api、VITE_API_BASE_URL=/api/v1；保持HttpOnly/Secure/SameSite=Lax，精确CORS/Origin；验证浏览器刷新/重开、注销和多个设备账号隔离。
8. 验证监控、健康检查、错误日志脱敏和资源上限；本次96项测试不代替负载测试/生产安全审查。最后才能将经验证的HTTPS地址作为新版本公网链接。

免费Render有空闲休眠和配额限制，不能把本机测试成绩当作长期生产可用性保证；使用前按[Render免费服务说明](https://render.com/docs/free)核对账户当前条件。Neon连接方式按[官方SQLAlchemy文档](https://neon.com/docs/guides/sqlalchemy)及所用asyncpg驱动版本验证。本阶段仅整理准备项，未创建这些资源。
