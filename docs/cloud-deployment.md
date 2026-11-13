# 学搭云端部署记录与操作说明

日期：2026-11-13（香港时间）。目标为完全脱离个人电脑的Vue + FastAPI + PostgreSQL网站。

## 当前状态

- 用户已确认接受产品名加免费托管平台后缀，不包含ChatGPT或个人账号名称。优先服务名为`xueda-study`；实际公网URL以Render创建成功的返回值为准，本记录不把候选地址标成已上线。
- 已创建产品专属GitHub私有仓库`blackchai/xueda-study`，源码使用独立发布目录同步，原工作区的Git状态和现有数据保留。
- 首份源码已实际同步到私有仓库main分支并逐文件校验哈希；首份提交为`708dabcd395e4ab6230f1b0e572bf8f0451434b7`。后续配置/文档提交以仓库当前main为准，源码仓库不是网站访问地址。
- Render、Neon尚未连接授权，尚未创建云应用/云数据库、未写入真实云Secrets、未完成公网TLS或远程双账号验收。
- 已完成下述部署适配与本机回归；这不是已完成公网发布的声明。

## 部署结构

```text
浏览器 → Render托管HTTPS → 单个应用容器
                            ├─ Vue编译后的静态页面
                            ├─ /api/v1 FastAPI（同源Cookie）
                            └─ asyncpg + 证书校验TLS → Neon PostgreSQL

发布启动 → Neon直连 → Alembic迁移与迁移锁 → 启动应用
```

不使用本机反向隧道、本机端口转发或本机PostgreSQL作为公网依赖；构建和运行所需源码由私有GitHub仓库提供。Render实例本地文件系统不保存业务数据库。

## 已落地的配置改动

1. `render.yaml`改为免费Web实例，移除旧的付费数据库创建和未拥有的域名声明；自动部署显式关闭，由本轮部署操作选择发布，避免推送源码自动改动云端。
2. 同一Docker镜像构建Vue并提供FastAPI，不需要在云端运行Vite。运行时读取`PORT`；安装系统CA证书。
3. `python -m app.startup`先校验生产配置和前端产物，再执行Alembic，最后用当前Python解释器运行Uvicorn，避免虚拟环境PATH问题。
4. 自动读取Render的`RENDER_EXTERNAL_URL`作为明确的HTTPS来源。自定义部署可设置`STUDYMATE_PUBLIC_ORIGIN`覆盖。来源校验不再依赖外部传入的转发头；默认不信任X-Forwarded-*。
5. `STUDYMATE_MIGRATION_DATABASE_URL`支持独立直连；Neon的`-pooler`地址不用于迁移。PostgreSQL迁移使用会话级advisory lock，避免多个启动任务同时迁移。
6. 应用池最多3条常驻连接+2条溢出，启用pre-ping与连接回收；迁移使用NullPool。
7. libpq URL中的`sslmode`转为asyncpg支持的SSLContext；远程默认验证CA和主机名，TLS最低1.2。`require`也使用证书/主机名验证，不静默关闭校验。
8. `channel_binding=require`不是当前asyncpg支持的选项，程序会明确拒绝，不能直接把psql连接模板当成asyncpg模板。使用供应商的asyncpg兼容连接方式，并保留证书验证；不静默丢弃required安全要求。
9. Alembic不再把数据库URL放入ConfigParser插值，避免百分号编码的密码被破坏；URL在引擎中正确解码，SQL参数隐藏于错误信息。
10. SPA页面允许前端路由刷新；不存在的API、health或JavaScript资源返回404，不能用index.html伪装成功。HTML需重新验证缓存，构建后的assets可长期缓存。
11. Docker构建上下文排除旧Sites元数据、本地助手目录、环境文件、数据库、依赖缓存和测试结果；真实密钥不进入源码或镜像。
12. 后端constraints.txt固定为已通过本轮验收的依赖版本；Docker按该约束安装，避免云端构建无意升级到尚未测试的框架/驱动版本。

## 云端环境变量

以下变量通过云平台Secrets或配置设置，不提交真实值：

| 变量 | 用途 |
| --- | --- |
| STUDYMATE_APP_ENV=production | 强制安全配置 |
| STUDYMATE_DATABASE_URL | Neon应用连接；可使用已验证的池化端点 |
| STUDYMATE_MIGRATION_DATABASE_URL | 相同数据库的直连端点，供Alembic使用 |
| STUDYMATE_AUTH_SIGNING_SECRET | 独立高熵随机值，不复制开发默认值 |
| STUDYMATE_AUTH_COOKIE_SECURE=true | 浏览器仅通过HTTPS发送会话 |
| STUDYMATE_AUTH_COOKIE_SAMESITE=lax | 当前已验收的同源方案 |
| STUDYMATE_AUTO_CREATE_SCHEMA=false | 仅使用版本化迁移 |
| STUDYMATE_FRONTEND_DIST_DIR=/srv/studymate/frontend | Docker中的前端构建产物 |
| STUDYMATE_CORS_ORIGINS | 同源部署保持空；不得使用星号 |
| STUDYMATE_PUBLIC_ORIGIN | Render可留空，由RENDER_EXTERNAL_URL提供；其他平台必须填实际HTTPS origin |

Neon连接示意（不是可用凭据）：

```text
postgresql://<role>:<percent-encoded-password>@<endpoint>/studymate?sslmode=verify-full
```

不要把签名密钥或数据库URL放入VITE_*变量、聊天消息、命令行历史、构建日志或Git仓库。

## 实际检查

- PostgreSQL独立测试库完整回归：111 passed；包含15项云端参数、启动、TLS配置、来源和静态路由测试。
- 前端33项单元测试、ESLint、TypeScript和生产构建通过；既有Element Plus首包体积提示保留。
- 修改后的独立迁移连接、迁移锁与`alembic check`已实际运行，没有结构漂移；没有修改现有开发用户数据。
- Docker本机未安装，不能声称镜像已在本机构建/运行；需待Render实际构建后检查部署日志与运行状态。
- SSLContext/证书强制配置已通过驱动边界测试；Neon网络、证书链、数据库角色与真实公网TLS尚待连接后验证。
- 一体化编译版通过健康检查，独立PostgreSQL和本地5174端口直接提供Vue编译产物与FastAPI，不使用Vite；四个三账号浏览器场景全部通过（53.6秒）。

该路径的实际联调修复了虚拟环境启动命令定位，以及SPA兜底将不存在API的PUT误报405的问题；真实API路径仍保留405，未知API返回404。修复后的完整后端回归111项通过（43.57秒）。

历史第六阶段验收报告保留原阶段的96/33项结果；当前部署适配回归计数单独记录，不能把本机测试等同云端上线。

## 连接授权后的实际发布步骤

1. 用户安装并连接Render、Neon，选择允许的免费资源；Render对GitHub仓库的读取授权只需覆盖本产品私有仓库。
2. 在Neon创建新的产品数据库，获取兼容asyncpg的应用/直连信息并验证TLS。已有真实云库必须先确认归属和备份，不能清空或覆盖。
3. 配置云端Secrets，创建服务名`xueda-study`；如名称占用，用其他产品相关名称，不加入个人账号或ChatGPT字样。
4. Render从私有仓库构建镜像；检查前端构建、迁移与应用启动日志。迁移成功、health/ready正常后才判定服务启动。
5. 使用Render实际返回的HTTPS URL检查首页、八个业务页和通知中心；两个以上独立浏览器账号验证注册、Secure/HttpOnly Cookie、重登、目标/打卡持久化与私有数据隔离。
6. 在Neon检查真实记录和关联约束，重启云应用后复验；确认没有localhost、个人电脑文件路径、旧静态站或本机数据库依赖。
7. 记录实际服务URL、代码提交、迁移版本、资源标识和验收结果；未通过时保留具体错误，不给出虚假的完成链接。

## 免费服务边界

Render免费Web服务有空闲休眠、构建/带宽与运行额度限制，超出限制或未授权付费时可能暂停，不能视为长期生产SLA。[Render免费服务说明](https://render.com/docs/free)

Neon池化连接与直连用途不同，迁移和备份使用直连；免费额度和供应商参数需在账号中核对。[Neon连接池说明](https://neon.com/docs/connect/connection-pooling)

目前不能承诺服务名一定可用，也不能把私有源码仓库地址当作已部署的网站地址。
