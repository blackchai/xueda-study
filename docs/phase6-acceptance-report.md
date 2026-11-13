# 学搭 StudyMate 第六阶段：站内通知与全站验收报告

验收日期：2026-11-13。工作区：`/home/martin/Tcamp个人项目`。

结论：本机真实PostgreSQL环境中，账号、目标/任务、打卡、匹配、搭子关系、小组和通知已形成完整业务闭环。以下测试均为本轮实际执行；Docker、Nginx运行、公网部署和真实多设备验收不在已通过范围。本轮不操作自定义域名、不修改生产环境，不重新引入第三方登录。

## 1. 已完成的功能

### 1.1 开发前检查

实际读取后端模型/API/迁移、前端Service/Pinia/路由/页面及测试，不依赖旧进度报告。开发前重新运行结果：PostgreSQL **77 passed**，前端 **26 passed**。既有注册登录、目标/任务、打卡、档案匹配、邀请关系及真实小组代码可用；通知仅有四类搭子事件、分页和单条已读，入口局限搭子页。

### 1.2 通知与业务事务

复用原notifications表和通知API，完整支持：

| 通知 | 接收者 | 持久化业务来源 |
| --- | --- | --- |
| 收到搭子邀请 | 被邀请者 | buddy_requests |
| 邀请被接受/拒绝 | 原发送者 | buddy_requests，接受另关联buddy_relations |
| 搭子关系解除 | 另一方搭子 | buddy_relations |
| 收到小组加入申请 | 当前组长 | group_join_requests |
| 小组申请通过/拒绝 | 申请者 | group_join_requests |
| 被移出学习小组 | 被移除者 | 新增group_member_events |

业务更新和通知同事务。数据库唯一event_key与既有业务行锁保证重复提交/并发不重复产生通知。移除成员后有效成员行会删除，因此新增最小持久事件表保留通知的真实来源；重新加入后再次被移除是新事件。

支持本人通知分页、全局未读数、未读筛选、单条已读及全部已读。全部已读为限定user_id和read_at IS NULL的原子UPDATE，保留已读时间，不影响他人或之后新到达的通知；不会代替接受邀请或审核申请。没有前端任意创建通知的API。

取消/处理/解散小组申请时，对应组长提醒标为已读；转让组长交接pending申请通知，旧组长提醒已读，已存在的相同接收者事件复用原行。通知跳转仍由目标API重新鉴权，不赋予被移除成员访问组内数据的权限。

### 1.3 全站前端

- 桌面和手机顶部铃铛、未读角标、新路由`/notifications`。
- 统一列表组件用于独立通知中心和原搭子页，提供分页、只看未读、单条/全部已读、刷新、状态和业务跳转。
- 通知链接定位搭子收件/发件/关系列表，或小组加入申请页；移除和解散通知返回小组发现页。
- 一个全站60秒未读查询轮询；隐藏/离线跳过，恢复后查询；合并并发请求，5秒抑制重复计数查询。进入通知中心读取最新列表。
- 未读数与通知仅在内存/API中管理，不写LocalStorage；账号切换或已读更新后，迟到的旧响应不会覆盖新状态。
- 加载、空状态、错误重试、会话失效重新登录、移动布局与表单保留现有蓝紫视觉风格。

### 1.4 验收中修复

1. 原Origin防护只比较hostname，忽略协议和端口，且仅对已有Cookie生效。现精确比较完整origin，注册/登录同样验证浏览器来源；null、非法端口、端口0伪装默认端口、路径或凭据形式来源均拒绝。
2. 携带会话而无Origin时，明确的Sec-Fetch-Site=cross-site请求也拒绝；同源、精确CORS及无浏览器来源标头的受信API客户端仍可使用。
3. 原`auth/me`异步缓存可能在退出后被迟到响应恢复。新增版本保护，旧响应不恢复旧账号或覆盖新用户。
4. 生产配置拒绝默认/占位密钥、SQLite和自动建表，保留Secure Cookie与32字节密钥要求。开发默认精确允许localhost:5173和127.0.0.1:5173。
5. 从旧小组申请通知进入页面后，如已不再是组长，回落到可访问的动态页签，避免落到不可见管理页签。

## 2. 本阶段主要文件

| 范围 | 新增或修改的文件 |
| --- | --- |
| 通知模型/迁移 | backend/app/models.py；backend/alembic/versions/20261113_0005_group_notifications.py |
| 通知API/事务 | backend/app/api/notifications.py；backend/app/services/group_notifications.py；backend/app/api/groups.py |
| 安全/开发配置 | backend/app/main.py；backend/app/config.py；backend/.env.example |
| 后端测试 | backend/tests/test_notifications.py（19项，含参数化用例） |
| 前端API/类型 | frontend/src/services/buddyConnections.ts；frontend/src/types/buddies.ts |
| 全站状态/组件 | frontend/src/stores/notifications.ts；frontend/src/components/NotificationBell.vue；frontend/src/components/NotificationList.vue |
| 页面/路由接入 | frontend/src/layouts/AppLayout.vue；frontend/src/router/index.ts；frontend/src/views/NotificationsView.vue；frontend/src/views/BuddiesView.vue；frontend/src/components/BuddyConnections.vue；frontend/src/views/GroupDetailView.vue；frontend/src/components/GroupDetailPanel.vue |
| 认证与单元测试 | frontend/src/services/authSession.ts；authSession.spec.ts；buddyConnections.spec.ts；frontend/src/stores/notifications.spec.ts |
| 全站浏览器测试 | frontend/e2e/phase6.e2e.ts |
| 文档 | README.md；docs/api-design.md；docs/database-design.md；docs/deployment.md；docs/pages.md；docs/requirements.md；本报告 |

未重写登录、个人学习、匹配或小组模块。Dockerfile、compose.yaml、render.yaml没有在本阶段重构或推送到云端。之前阶段已有的工作区改动保留，没有清理用户文件。

## 3. 实际运行的测试

| 检查 | 实际结果 |
| --- | --- |
| PostgreSQL完整后端pytest | **96 passed**，全部PG并发用例实际执行 |
| SQLite兼容pytest | **85 passed，11 skipped**；11项依赖PG行锁的用例明确跳过 |
| 前端Vitest | **33 passed**，8个文件 |
| ESLint、TypeScript/vue-tsc | 通过，含端到端代码类型检查 |
| Vite生产构建 | 通过；既有Element Plus大于500kB首包提示保留 |
| Chrome/Playwright完整套件 | **4 passed**：搭子邀请、小组、匹配、第六阶段全站；最终完整轮次50.6秒 |
| Python compileall | app/alembic/tests通过 |
| Alembic/SQLAlchemy一致性 | PostgreSQL `alembic check` 无新增操作 |
| Compose检查 | YAML解析与结构性静态检查通过；实际Docker命令未运行 |

新增后端覆盖通知来源/隐私、分页和非法输入、单条/全部已读、未来通知保留、取消/归档/交接、重复事件唯一约束、组通知失败注入回滚、并发申请/审批/移除与已读、精确Origin（含端口0）、CORS、Secure/HttpOnly/SameSite/Max-Age、注销撤销、会话过期和生产配置。

前端新增7项单元测试：未读查询合并/节流、已读后的旧响应丢弃、账号切换隔离、网络失败保留已知计数、401过期、全部已读API和认证缓存竞争。既有目标、档案、算法与Service测试保留。

浏览器测试初轮修正了任务列表定位、等待退出完成和多条通知/重复测试小组文本的断言；截图等待加载完成并结束CSS动画，避免把中间状态当成最终页面。修正后四个完整场景实际通过，没有把失败轮次记录为通过。

补充端口0边界后，曾有一轮PostgreSQL回归被SIGTERM中断，未计为通过；随后单独重跑完整套件，实际结果96 passed（35.65秒）。

## 4. 前后端真实联调

独立测试服务：FastAPI8001、Vue/Vite5174，连接`studymate_phase6_test`，使用Chrome三个独立上下文。没有使用真实个人浏览器资料目录；测试密码随机生成，不作为交付账号公开。

全站场景顺序验证：

1. A/B/C均通过Vue注册/登录表单建立独立账号。
2. 三人分别用真实页面创建并修改自己的目标；A新增任务并勾选完成，目标进度变100%。
3. 三人分别通过真实打卡表单记录180分钟；退出后受保护API401，重新登录后自己的目标和打卡保持。
4. A/B填写相同C++方向/晚间作息，C填写考研英语/上午；A实际看到B为100分，并发送邀请。
5. B从顶部铃铛看到未读邀请，点击通知跳转收件箱，再接受；双方有效搭子关系为1。
6. A查看接受通知并标记已读；A创建真实小组，B申请，A从申请通知跳转指定小组审核页并批准。
7. B从通过通知进入小组；A/B对既有记录分别授权分享，B正文保持私有。今日人数2、累计360分钟，两人在排行榜均180分钟。
8. C对A目标/打卡/小组/榜单的读取，以及删除A/B私人记录均404；响应不含未授权正文或私人身份字段。
9. C申请小组，A全部已读后C仍未成为组员；A拒绝，C收到真实拒绝通知。A不能标记C的通知。
10. A移除B，B收到移除通知；B刷新后通知保留，但小组动态API404。B个人目标/打卡仍在，组内统计退回A的180分钟。
11. 1440px桌面、390px手机无页面水平溢出；手机通过真实表单创建另一小组。通知支持键盘原生按钮与表单控件。
12. 对实际通知请求注入网络失败，页面出现错误和重试入口；恢复网络后加载真实数据。浏览器无pageerror，未产生LocalStorage social业务记录。

截图在frontend/test-results/中（Git忽略）：phase6-notifications-desktop.png、phase6-notifications-mobile.png、phase6-mobile-form.png，以及其他三场景截图，均来自实际浏览器并已目视检查。

## 5. PostgreSQL与迁移检查

- 实际数据库为用户级PostgreSQL14.24，私有Unix Socket `/tmp/studymate-pg-socket-20261113`、端口号55432，未开放TCP；不是SQLite替代验收。
- pytest在独立`studymate_phase6_test`数据库中每例建立随机schema，结束只清理自身schema；浏览器账号只写该测试库public schema。
- 专用`studymate_phase6_migration_test`先建立0004，写入2个旧用户/档案、1个目标、1个任务、1个打卡、1条搭子申请及1条旧通知，再升级0005。逐表原列SHA-256摘要一致。
- 空库连续迁移至0005通过；SQLite独立临时文件的完整批处理迁移也通过。
- 本机原开发库`studymate_matching_dev`已0004→0005，原列内容摘要一致：users17、profiles17、auth_sessions16、profile_time_slots15，其他旧表保持原计数（本样本为空）。没有把验收账号写入开发库。
- 第六阶段新增group_member_events及通知三个可空FK，扩展kind检查；唯一事件键与原索引保留；`alembic check`通过。

最后一次全站场景结束后，使用新数据库连接直接核对测试前缀`whole_mweo6w8k`：

| 数据 | 直接SQL核对结果 |
| --- | --- |
| 三账号与密码 | 3个不同UUID，3个Argon2id哈希 |
| 目标/打卡 | 每人各1个目标、1条打卡 |
| 任务 | A有1个已完成任务 |
| A/B关系 | 1条有效关系 |
| 主小组成员/分享 | B移除后各剩1条（A） |
| 审核历史 | B approved、C rejected，各1条 |
| 成员移除事件 | 1条 |
| 通知 | 7条，event_key全部不同；2条未读 |

本轮没有重启共享PostgreSQL实例做故障恢复，避免中断其他本地开发会话；持久化证据为真实提交后的新连接查询、浏览器刷新/注销重登、独立迁移保留演练。备份恢复和真实云故障切换仍未验证。

## 6. 安全与异常检查

| 项目 | 证据与结果 |
| --- | --- |
| 身份与所有权 | 每个私人API使用require_auth，身份来自Cookie会话；A/B/C目标、任务、打卡与通知按拥有者限制，小组按成员/组长限制 |
| 未登录与注销/过期 | API401；注销旧Cookie与过期会话均不能继续访问；三浏览器独立登录 |
| 通知隔离 | 他人通知标记404；全部已读只限定本人；无任意创建通知API |
| 密码/会话 | Argon2id、会话数据库仅哈希；前端无明文登录凭证LocalStorage；Secure属性通过HTTPS ASGI客户端验证 |
| Origin/CORS | 错误协议/端口/端口0、恶意或null来源拒绝；精确允许的预检通过，非可信预检不获CORS允许 |
| 幂等与并发 | 重复搭子发送/接受、小组申请/批准/移除只有一个有效转换/事件；唯一约束和PG行锁用例实际通过 |
| 回滚 | 搭子及小组通知失败注入，业务关系/成员/审核/移除事件共同回滚 |
| 学习统计 | 继承并回归UTC+8日/周/月边界、加入日期、去重日期/记录、24小时上限、撤回与移除后重算 |
| 网络与刷新 | 失败提示、重试恢复、旧响应不覆盖新账号/已读数、刷新及重登保留 |

这不是渗透测试或生产安全认证。当前已验证同源/SameSite=Lax方案，尚未验证真实云TLS终止、可信代理、跨站SameSite=None与CSRF token方案。

## 7. 未通过或未执行的检查

- 最终已执行的功能、单元、集成与浏览器套件没有遗留失败。
- SQLite的11项PG行锁并发测试明确跳过，不能用SQLite分数替代；对应PG用例均执行。
- 本机无docker可执行程序，未执行docker compose config/build/up或镜像启动；Compose仅做静态解析/关键关系核对。
- 本机无nginx程序，未执行nginx -t或TLS终止验收。
- 未连接Render/Neon、未发布公网、未操作域名或生产数据。
- 未做真实手机硬件/不同设备、Firefox/Safari、长时间运行、高负载、云数据库TLS/连接池、备份恢复或故障切换实测。

## 8. 剩余问题与上线风险

1. PostgreSQL当前在/tmp，仅开发验证用途，需要正式持久数据库和可验证备份。
2. Element Plus首包仍超过500kB，生产构建成功，但低带宽首屏和加载性能未压测。
3. 现有render.yaml为早期Render数据库方案，不是已验证的Render + Neon免费配置；下阶段需改造后再部署，不能直接创建其中资源。
4. Neon复制的连接参数需按asyncpg适配并真实验证TLS；当前仅转换PostgreSQL协议前缀，未连接外部数据库。
5. DockerCMD当前信任所有转发来源的配置必须在目标云代理策略下收窄并实测，以免影响Origin/IP限流；本地服务仅绑定loopback，本阶段没有暴露该容器到公网。
6. 尚未实现邮箱验证/密码找回、全设备退出、举报审核、完整审计告警和生产反滥用体系；账号数据保留策略与法律文案需上线前确认。
7. 通知采用HTTP查询，有轮询延迟；标记已读不代表处理业务。主动退出/直接加入不额外发未要求的通知，短信/邮件/WebSocket不在本阶段。

## 9. 普通用户手动验收

当前本机入口：[注册登录](http://127.0.0.1:5173/auth)、[工作台](http://127.0.0.1:5173/dashboard)、[通知中心](http://127.0.0.1:5173/notifications)、[学习小组](http://127.0.0.1:5173/groups)。已有5173/8000开发服务已保留，本轮实际HTTP检查通知页面200、后端health/ready为ready。

1. 用三个不同浏览器或真正独立的浏览器配置文件注册A/B/C，自设密码；同一浏览器多个普通标签页共享Cookie，不代表独立账号。
2. 每人创建一个目标、修改标题、添加任务并打卡；退出再登录，确认仅见自己的数据且仍存在。
3. A/B在个人中心填写相同C++方向、标签、晚间时段，开启允许推荐和接收邀请。C填写英语和上午时段。A搜索B，查看得分和理由并发邀请。
4. B点击顶部铃铛刷新通知，查看新邀请并进入收件箱接受；A查看接受通知，双方“我的搭子”出现对方。
5. A创建需要审核的小组，B申请；A从申请通知进入审核页同意，B从通过通知进入小组。
6. A/B在个人打卡记录选择“分享到小组”；正文默认不公开，可另行授权。刷新小组检查人数、时长、排行榜与个人隐私。
7. C申请加入；A先“全部标为已读”，确认C仍未入组，再拒绝。C应收到拒绝通知，A不能替C读通知。
8. A移除B，B收到通知；B个人记录仍在，但不能再读取组内内容。A统计只剩自己的分享。
9. 测试通知“只看未读”、单条/全部已读、分页和刷新；点击通知不会自动批准申请或接受邀请。网络失败时应显示错误，恢复后点击重试。
10. 在手机或窄窗口检查铃铛、列表和创建小组表单。手动验收不要尝试使用自动化随机密码，直接注册自己的账号。

复验命令（本机专用测试库，不能改为生产库）：

```bash
cd backend
STUDYMATE_TEST_DATABASE_URL='postgresql+asyncpg://martin@/studymate_phase6_test?host=/tmp/studymate-pg-socket-20261113&port=55432' .venv/bin/pytest -q
env -u STUDYMATE_TEST_DATABASE_URL .venv/bin/pytest -q
.venv/bin/python -m compileall -q app alembic tests
```

需要重启本机开发后端时，在项目backend目录执行（已运行时不要重复占端口）：

```bash
export STUDYMATE_DATABASE_URL='postgresql+asyncpg://martin@/studymate_matching_dev?host=/tmp/studymate-pg-socket-20261113&port=55432'
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

前端在frontend目录执行`npm run dev -- --host 127.0.0.1 --port 5173 --strictPort`。其他机器先按README安装依赖并准备自己的PostgreSQL，/tmp Socket路径只适用本机。

隔离浏览器联调，分别启动测试后端和前端：

```bash
cd backend
export STUDYMATE_DATABASE_URL='postgresql+asyncpg://martin@/studymate_phase6_test?host=/tmp/studymate-pg-socket-20261113&port=55432'
.venv/bin/alembic upgrade head
STUDYMATE_APP_ENV=test STUDYMATE_CORS_ORIGINS=http://127.0.0.1:5174 .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001
```

```bash
cd frontend
VITE_BUSINESS_DATA_MODE=api STUDYMATE_API_PROXY_TARGET=http://127.0.0.1:8001 npm run dev -- --host 127.0.0.1 --port 5174 --strictPort
```

再运行：

```bash
cd frontend
npm run check
STUDYMATE_E2E_BASE_URL=http://127.0.0.1:5174 STUDYMATE_CHROMIUM_PATH=/usr/bin/google-chrome npm run test:e2e
```

浏览器和数据库工具必须可用；本机隔离测试服务在验收后停止，不影响保留的8000/5173服务。准备新的测试库时先CREATE DATABASE，不能清空现有库。

## 10. 下一阶段Render + Neon准备清单

1. 同步包含0001–0005所有迁移的完整源码到受控GitHub仓库，先检查密钥与本地测试资料排除。当前没有Git远程，不声称已推送。
2. 由用户登录并连接Render/Neon，核对免费额度、休眠、存储/连接限制与超额策略；不自动创建付费套餐。
3. 准备独立Neon预发数据库/分支和最小权限角色，区分应用连接与Alembic迁移直连；数据库URL仅放Secret，不放VITE变量或仓库。
4. 实测asyncpg对Neon sslmode/channel_binding参数的兼容与TLS；必要时调整连接参数/SSLContext，不能只看URL字符串就宣称连通。
5. 改造早期render.yaml为外部Neon数据库Secret和确认后的资源配置，不自动创建旧数据库或处理域名；核对容器PORT及可信代理转发策略。
6. 先在预发迁移、检查约束、执行本报告全套测试并做备份恢复，确认不丢数据后再连接正式数据库。
7. 同源HTTPS提供Vue和FastAPI，生产Secure/HttpOnly/SameSite=Lax、精确Origin/CORS；通过不同设备真实注册/登录、刷新和注销验证。
8. 增加运行监控、日志脱敏、资源上限和负载测试；验证免费服务休眠后的重新连接与错误提示，最后才报告已部署的真实公网链接。

平台限制以[Render免费服务文档](https://render.com/docs/free)和[Neon SQLAlchemy连接文档](https://neon.com/docs/guides/sqlalchemy)为准。云端准备详情另见[部署文档](deployment.md)。本轮仅准备清单，不执行正式部署。
