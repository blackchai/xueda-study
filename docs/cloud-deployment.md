# 学搭云端部署记录与操作说明

更新：2026-11-14（香港时间）。Vue + FastAPI + PostgreSQL 已部署到云端，运行不依赖个人电脑。

## 当前状态

- 实际公网网站：**[https://xueda-study.onrender.com](https://xueda-study.onrender.com)**；[登录/注册](https://xueda-study.onrender.com/auth)。该网址由 Render 实际创建返回，不含个人账号或 ChatGPT。
- Render 部署已为 `live`，云端 Docker 构建、五次 Alembic 迁移和 FastAPI 启动成功。公网 `/health/ready` 返回 HTTP 200 和 `status: ready`，HTTPS 证书校验开启。
- 源码为 `blackchai/xueda-study` 的 `main` 分支，本次运行代码提交为 `6ffae0f2417d553d492fcabbed1db67f5ab5ebf1`。后续文档提交不自动触发重新部署。
- Render 与 Neon 已授权；应用配置及数据库凭据只传入云环境变量，未写入源码、文档或命令行参数。
- 本机原工作区 Git 状态、已有本机数据和 Neon 原始 `production` 分支保留。本机旧账号不自动迁移；公网需自行注册。

## 实际云资源

| 资源 | 已创建配置 |
| --- | --- |
| Render 工作区 | `My Workspace` / `tea-dbrdc3lg1s2s7385tet0` |
| Web 服务 | `xueda-study` / `srv-dbs01b2fngtc73bbepng` |
| 服务套餐与地域 | `free` / `singapore`；未升级付费服务 |
| 部署 | `dep-dbs01bqfngtc73bbes20`；2026-11-14 14:35 香港时间成为 `live` |
| Neon 项目 | `summer-glade-88514655` / `aws-ap-southeast-1`；Free |
| 应用分支 | `xueda-study-live` / `br-snowy-math-ao1bu7zw` |
| 迁移验证分支 | `xueda-study-verification` / `br-green-dream-ao8q7492` |
| 数据库 | `studymate`，两个新分支均使用独立数据库 |
| 运行角色 | `studymate_app`，允许业务表读写，不能在 public 建表 |
| 迁移角色 | `neondb_owner`，独立直连 URL 仅供 Alembic |
| 迁移版本 | 验证分支与应用分支均已到 `20261113_0005` |

本次使用 MCP 直接创建单个 Web 服务，自动部署关闭。`render.yaml` 保留为重建配置模板，并非已创建 Blueprint。MCP 创建接口不支持设置 HTTP 探活路径，因此当前 Render 使用默认 TCP 检查；`/health/ready` 已单独通过公网请求验证。可在服务 Settings → Health Checks 将路径设置为 `/health/ready`，使平台也检查数据库就绪状态。

## 部署结构

```text
浏览器 → Render托管HTTPS → 单个应用容器
                            ├─ Vue编译后的静态页面
                            ├─ /api/v1 FastAPI（同源Cookie）
                            └─ asyncpg + 证书校验TLS → Neon PostgreSQL

发布启动 → Neon直连 → Alembic迁移与迁移锁 → 启动应用
```

不使用本机反向隧道、本机端口转发或本机 PostgreSQL 作为公网依赖；构建和运行所需源码由 GitHub 仓库提供。Render 实例本地文件系统不保存业务数据库。

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
| STUDYMATE_DATABASE_URL | Neon 受限应用角色的直连；应用池最多 5 条连接 |
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
- Docker 本机未安装，没有本机 Docker 运行结果；本次 Render 已实际完成多阶段 Docker 构建、镜像导出和容器启动。
- 应用使用 CA 和主机名校验的 TLS 连接 Neon；两条新分支均已迁移，受限角色的用户表读写权限及缺少建表权限已实查。公网 HTTPS 就绪请求通过，未关闭证书校验。
- 一体化编译版通过健康检查，独立PostgreSQL和本地5174端口直接提供Vue编译产物与FastAPI，不使用Vite；四个三账号浏览器场景全部通过（53.6秒）。

该路径的实际联调修复了虚拟环境启动命令定位，以及SPA兜底将不存在API的PUT误报405的问题；真实API路径仍保留405，未知API返回404。修复后的完整后端回归111项通过（43.57秒）。

历史第六阶段验收报告保留原阶段的96/33项结果；当前部署适配回归计数单独记录，不能把本机测试等同云端上线。

## 公网实际验收（2026-11-14）

所有下列请求均发往 `https://xueda-study.onrender.com`，没有转发至本机端口；数据库为上方 Neon 应用分支。测试仅创建本次新账号及其数据。

| 检查 | 实际结果 |
| --- | --- |
| Render 云端 Docker 构建与启动 | 成功；部署 `live`；监听 `0.0.0.0:10000` |
| 公网 HTTPS 就绪检查 | HTTP 200，`status: ready`；证书校验开启 |
| 三账号 Chrome 端到端全站用例 | **1 passed / 0 skipped / 0 flaky**，188.2 秒 |
| HTTP 页面及安全异常用例 | **24 passed** |
| Neon 迁移 | 验证分支与应用分支均为 `20261113_0005` |
| Neon 测试数据检查 | 3 个用户、3 个目标、3 条打卡、1 条有效搭子关系、2 个小组、7 条通知 |
| 本机发布前回归 | 后端 PostgreSQL **111 passed**；前端 **33 passed**、ESLint、TypeScript、生产构建通过 |

端到端用例复用 `frontend/e2e/phase6.e2e.ts`，通过只允许本产品网址的临时云端配置运行；未移除仓库原有 E2E 的 localhost 安全限制。三个独立浏览器上下文各自注册、登录，使用真实 Vue 表单创建/修改目标和打卡，退出后验证 401，再登录确认记录不丢失。还覆盖：

- A、B 的学习档案和时间匹配、推荐分数、发送与接受邀请、双向搭子关系。
- A 创建小组、B 申请、组长审核、双方逐组分享打卡、排行榜真实聚合（180 + 180 分钟）。
- C 无法读取 A 的目标、私人打卡、小组详情或排行榜；跨账号删除目标/打卡返回 404。
- 小组申请通过/拒绝、成员移除通知、单条与全部已读、刷新后通知保留、跨账号修改通知返回 404。
- 打卡正文不公开时不泄露，移除成员后组内分享撤回，个人打卡保留。
- 390 像素手机视口无横向溢出、手机端创建小组、真实网络请求失败后的提示与重试；无浏览器 JavaScript 未捕获异常。

24 项独立 HTTP 检查覆盖首页、登录页及各业务路由的 Vue 入口，7 类受保护接口未登录 401，错误密码 401、账号不存在时使用相同错误提示、重复邮箱 409、非法注册 422、外站 Origin 403、未知 API/静态资源真实 404。浏览器路由的服务器入口 200 不代表未登录可读取业务数据，身份保护仍由 Vue 路由和后端 API 分别执行。

本机默认代理及 DNS 在联调时失效；仅在本次测试进程内使用加密 DNS 返回的地址，保留原域名 SNI 与 TLS 证书验证，没有修改系统 DNS 或云端配置。首轮 HTTP 检查进程中断，改用持久 HTTPS 连接后完整 24 项通过。

本地证据位于 Git 忽略的 `frontend/test-results/cloud-20261114/`：`playwright-report.json`、`http-report.json`，以及通知桌面/手机、手机表单的三张截图。账号为 `whole_mwg1bavs_a/b/c`，密码由测试进程随机生成，未导出或公开；这些是真实测试账号，不是可供访客登录的演示凭据。云端目前保留少量带测试前缀的验收资料及小组。

未执行：真实手机/异地运营商网络验收、长期压测、恢复备份演练、空闲 15 分钟后的完整唤醒计时和云应用再次重启后的专门回归。本机没有 Docker；不把云端构建成功表述为本机 Docker 通过。免费套餐和默认 TCP 探活边界见本记录其他段落。

## 普通用户现在如何使用

1. 打开 [学搭注册页面](https://xueda-study.onrender.com/auth?mode=register)，填写自己的用户名、邮箱和密码；本机旧账号未导入。
2. 注册后按提示登录，在工作台创建目标、记录一次学习，再刷新或退出重登确认保存。
3. 在隐私/无痕窗口或另一台设备注册第二个账号；两个账号分别登录，私人目标和打卡相互隔离。
4. 在个人资料设置方向、目标标签、每周时段，并主动开启公开匹配/接收邀请，之后到学习搭子页筛选、发送和接受邀请。
5. 创建需要审核的小组，用第二账号申请，组长在通知中进入审核；成员把允许公开的个人打卡逐组分享，即可查看动态和排行榜。

## 本次发布方式与后续更新

1. 保留现有账号密码认证；使用 Neon 新应用分支及新数据库，不导入或清空原有数据。
2. 先在独立验证分支运行 Alembic，再将受限应用连接、迁移连接及独立随机签名密钥传入 Render 环境变量。
3. Render 从 GitHub `main` 的上述提交构建 Docker 镜像，启动时先迁移、后监听动态 `PORT`。
4. 确认部署为 `live`、公网就绪检查及页面资源正常，再运行新测试账号的完整联调。具体结果以本记录的云端验收段落为准。
5. 后续代码修改须先本地回归、同步源码，再从 Render 服务的 Manual Deploy 发布。自动部署已关闭，单独推送文档不会改动正在运行的版本。
6. 正式业务数据和账号保留在 Neon；关闭本机、重新部署容器或平台休眠不依赖本机磁盘。长期备份恢复仍需单独演练。

## 免费服务边界

Render免费Web服务有空闲休眠、构建/带宽与运行额度限制，超出限制或未授权付费时可能暂停，不能视为长期生产SLA。[Render免费服务说明](https://render.com/docs/free)

Neon池化连接与直连用途不同，迁移和备份使用直连；免费额度和供应商参数需在账号中核对。[Neon连接池说明](https://neon.com/docs/connect/connection-pooling)

当前网址已分配成功。免费套餐不等于持续可用性承诺；本次未购买自定义域名、未创建付费实例、未使用本机隧道。
