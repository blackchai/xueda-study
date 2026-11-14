# 学搭 StudyMate

**让自律不再孤单，让学习有人同行。**

学搭是面向大学生和自主学习者的目标管理、学习打卡、学习搭子与学习小组平台。

## 当前实现状态

公网网站：**[https://xueda-study.onrender.com](https://xueda-study.onrender.com)**。登录/注册：[进入学搭](https://xueda-study.onrender.com/auth)。

2026-11-14 已发布至 Render 新加坡区免费 Web 服务，Vue 与 FastAPI 在云端同源运行，业务数据保存到 Neon PostgreSQL。无需启动本机服务。Render 部署状态为 `live`，公网 HTTPS 就绪检查通过；云端验收结果、资源及免费套餐限制见[云端部署记录](docs/cloud-deployment.md)。

- 八个主要页面保持 Vue 3 + Element Plus 响应式设计。
- 注册、登录、刷新保持会话、退出已接入真实 FastAPI API。
- 认证只支持用户名/邮箱 + 密码，不使用微信或其他第三方登录。
- 密码用 Argon2id 哈希；原始会话令牌只存于 HttpOnly Cookie，数据库只存令牌哈希。
- 学习目标、目标任务和打卡已使用服务端持久化，后端按当前用户 ID 强制隔离。
- 学习档案、每周可用时段和匹配开关已保存到服务端；搭子推荐按真实用户计算，默认仅展示主动开启匹配的用户。
- 搭子页支持方向、时段、星期、共同空闲时间、公开关键词筛选和服务端分页，展示分项、重合分钟与推荐理由。
- 邀请发送、收件箱/发件箱、接受/拒绝/取消、我的搭子和解除关系已使用 PostgreSQL，刷新和重新登录后保留。
- 全站通知铃铛与通知中心支持搭子邀请/接受/拒绝/解除、小组申请/通过/拒绝/移除，共八类真实通知；分页、未读筛选、单条/全部已读和业务跳转均已接入 PostgreSQL。
- 学校、专业、个人简介和私人学习记录不进入公开匹配响应；接收邀请需本人主动开启。
- 小组发现、创建/编辑、直接加入/申请审核、成员移除、组长转让及解散已接入真实 PostgreSQL，组员私有内容由后端验证权限。
- 个人打卡默认私有，通过“分享到小组”逐组授权日期/时长，正文另行选择；可撤回，退出/移除自动撤回，不复制或删除个人记录。
- 今日/本周/本月时长榜与打卡天数榜使用真实 SQL 聚合，支持零记录成员；共同目标显示本人有效分享时长进度。
- 数据库结构由 Alembic 管理，正式环境不依赖启动时 `create_all`。
- 已修复应用入口只导入 Element Plus 样式、未注册组件的问题，登录表单和业务组件现在可真正交互。

## 本地访问地址

- 前端：[http://localhost:5173](http://localhost:5173)
- 登录/注册：[http://localhost:5173/auth](http://localhost:5173/auth)
- 学习小组：[http://localhost:5173/groups](http://localhost:5173/groups)
- 通知中心：[http://localhost:5173/notifications](http://localhost:5173/notifications)
- FastAPI 接口文档：[http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- 就绪检查：[http://localhost:8000/health/ready](http://localhost:8000/health/ready)

`xueda.study` 尚未购买或配置；当前使用上方 Render 分配的产品网址。没有使用本机隧道或旧静态原型承载本版系统。

## 技术栈

- 前端：Vue 3、TypeScript、Vite、Element Plus、Vue Router、Pinia、Vitest
- 后端：Python 3.10+、FastAPI、SQLAlchemy Async、Alembic
- 数据库：PostgreSQL + asyncpg；SQLite + aiosqlite 仅用于快速开发与自动化集成测试
- 安全：Argon2id、HttpOnly/Secure/SameSite Cookie、登录限流、Origin/CSRF 检查、资源所有权校验

## 本地启动

### 1. PostgreSQL

准备一个空数据库和专用用户，例如：

```text
postgresql+asyncpg://studymate:<password>@127.0.0.1:5432/studymate
```

可使用已安装的 PostgreSQL，或在本机支持 Docker 时使用根目录 `compose.yaml` 中的 `database` 服务。不要把真实密码写入仓库。

### 2. 后端与迁移

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
cp .env.example .env
```

把 `backend/.env` 中的 `STUDYMATE_DATABASE_URL` 改为上面的 PostgreSQL URL，并生成至少 32 字节的本地签名密钥，然后：

```bash
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

只需快速本地开发时，`.env.example` 的 SQLite URL 也可运行；验收跨设备持久化时必须换成 PostgreSQL。

### 3. 前端

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Vite 会把 `/api` 代理到 `127.0.0.1:8000`。默认 `VITE_BUSINESS_DATA_MODE=api`，真实业务不写 LocalStorage；显式设为 `mock` 时仅保留旧个人档案/目标/打卡演示，真实搭子推荐暂停展示。账号登录与小组始终调用真实 API，Mock 个人打卡不能分享到真实小组。不要把真实数据填入 Mock 模式。

## 创建两个测试账号

1. 在普通浏览器窗口打开 `/auth?mode=register`，注册 `user_a`。
2. 在无痕/隐私窗口打开同一地址，注册 `user_b`。
3. 两个窗口分别登录，创建不同目标和打卡；刷新后数据应保留且彼此不可见。
4. 退出后重新访问 `/dashboard`，应被导向登录页。

仓库不内置固定测试密码或生产账号。本地回归使用隔离测试数据库；本次公网验收仅创建带唯一测试前缀的新账号，未操作已有用户的数据。你可以在公网注册自己的账号；本机旧账号未自动导入云端。

## 三账号手动验收真实匹配

用三个独立浏览器配置文件，或不同浏览器/隐私会话注册 A、B、C（同一浏览器的多个无痕窗口可能共享 Cookie）。进入“个人中心 → 编辑资料”，均选择学习方式“共同讨论”、阶段“强化”，填写：

| 账号 | 方向 | 标签 | 周一时段 |
| --- | --- | --- | --- |
| A | 编程开发 | C++ | 19:00–22:00 |
| B | 编程开发 | C++ | 19:30–22:30 |
| C | 考研 | 考研英语 | 08:00–11:00 |

三个账号分别开启“允许被推荐”并保存。在 A 的搭子页刷新，应看到 B=94 分、C=25 分（若已有其他用户，可搜索测试昵称共同前缀）。A 不在自己的列表中。将 B 改为周一 08:00–11:00 后保存，A 刷新应看到 B=65 分；关闭 B 的“允许被推荐”并保存后，A 再刷新不应看到 B。刷新个人中心，资料和开关应保持。

推荐只展示匹配字段；邮箱、学校、专业、简介、私人目标详情和打卡不公开。新旧账号的“接收搭子邀请”默认关闭，推荐时显示是否可申请及当前关系。API 路径和完整参数见 [API 文档](docs/api-design.md)，评分规则见 [算法文档](docs/matching-algorithm.md)。

## 第四阶段：双浏览器手动验收邀请

1. 在两个独立浏览器或配置文件分别注册并登录 A、B。在“个人中心 → 编辑资料”填写方向、标签和作息，开启“允许被推荐”和“接收搭子邀请”，保存。
2. A 进入“学习搭子”，按 B 的公开昵称筛选，点击“申请成为搭子”，填写留言并发送。卡片应变为“等待接受”，发件箱出现一条 pending 记录。
3. B 打开搭子页的“通知”查看新邀请，可标为已读；在“收到的邀请”查看 A 的公开资料并接受。
4. 两人分别查看“我的搭子”，应看到对方；查看的是匹配目标标签和每周计划，不是对方的私人目标/打卡。刷新并退出重新登录，关系及通知应保留。
5. 任意一方点击“解除关系”并确认，双方的有效搭子列表移除，另一方收到解除通知。
6. 拒绝和取消流程可使用第三账号 C：C→B 后由 B 拒绝，不建立关系；A→C 后由 A 取消，C 无法再接受。C 无权操作 A/B 的请求或关系。

默认同一对账号重新发起有 300 秒冷却；每小时 10 次、24 小时 30 次、同时 pending 20 条。重复点击同方向 pending 请求返回原记录，不重复通知；不要用短时间反复取消重发来做手测。全站可见且在线时，每60秒查询轻量未读数；进入通知中心读取最新列表，可手动刷新。搭子页复用同一状态，不启动另一套轮询。

正式邀请、关系和通知不读写 LocalStorage。旧模拟邀请入口/服务/状态方法已移除，旧演示记录不自动导入真实账号。显式 Mock 模式仅保留个人学习演示，不能发送真实邀请。

## 第五阶段：三账号手动验收真实小组

使用三个真正隔离的浏览器配置文件/不同浏览器注册 A、B、C；多个普通标签页共享登录 Cookie，不能代表三个独立会话。自行设置密码，仓库不提供预置账号。

1. A 打开“学习小组 → 创建小组”，名称“C++ 晚间自习室”、方向“编程开发”，填写简介、人数上限，保持“需要组长审核”。创建后自动为组长，可编辑公告。
2. B 搜索小组，点击“申请加入”，应显示“等待审核”。A 在详情“加入申请”点击“同意”；B刷新后进入成员共学空间。C此时只能查看公开摘要，不能查看公告、名单、动态、目标或榜单；普通成员没有组长权限。
3. A、B分别在“学习打卡”记录今日180、120分钟。默认不显示到小组。对各自记录点击“分享到小组”，选择该组；A可勾选公开学习内容，B不勾选。组内应有两条动态，但B正文显示“未公开”；另一条未分享的私人记录完全不可见。
4. 刷新小组：今日人数2、累计300分钟；今日/本周/本月时长榜A在B之前，打卡天数均为1（同日多条只算一天）。切换周期可查看具体日期范围。
5. A设置覆盖今天的共同目标“每人学习 C++ 10小时”，600分钟；B看到120/600=20%，A为30%。刷新、退出重新登录后保持。
6. 在分享弹窗修改正文授权、撤回或重新分享：其他组员刷新后看到新授权，统计跟随撤回更新，个人记录不变。
7. B退出并确认，随后不能读取本组私有内容；B在本组的分享被撤回，A看到累计剩180分钟，B个人打卡仍存在。也可重新申请，旧分享不会自动恢复。
8. C申请后可取消；A可批准/拒绝。A在成员页可移除成员、将组长转让给现有成员。组长不能直接退出，须先转让，或点击“解散小组”并确认；解散保留个人记录并撤回全组分享。

统计统一北京时间 `Asia/Shanghai`（UTC+8），周一至周日和自然月。只计当前成员本次加入当地日期起的有效、主动分享记录；每人每天向同一组分享最多1440分钟。排行榜不读取未分享内容，也不使用前端提交分数。小组目标为时间目标，尚不自动识别打卡内容是否符合C++主题。所有有效小组公开发现摘要，组内内容仅成员可见；本版没有完全隐藏的小组。

完整接口、权限、数据约束及本机实测证据见 [API 文档](docs/api-design.md)、[数据库文档](docs/database-design.md)、[第五阶段验收记录](docs/stage5-verification.md)。

## 第六阶段：通知与全站验收

顶部铃铛可从任何业务页打开 `/notifications`。支持全部/未读筛选、服务端分页、单条已读、全部已读；点击“查看相关列表”会标记阅读并跳转搭子收件箱/发件箱/搭子列表或小组详情。标记已读不会代替接受邀请或审核申请。

小组申请通知由后端在业务事务中生成，审批结果发给申请者；移除成员时保存独立业务事件，再生成关联通知。重复操作不会重复发通知；取消/处理/解散会将对应待处理提醒标为已读，转让组长会交接未处理申请提醒。移除通知不会授予已退出成员访问组内私有数据的权限。

全站三账号验收已串联真实注册登录、各自目标创建/修改、任务完成、打卡、退出重登、匹配、邀请与接受、小组审核/共同打卡/排行榜、拒绝和移除通知，以及第三人越权、网络错误恢复和手机表单。完整证据、复验命令、剩余风险和 Render + Neon 下一阶段清单见 [第六阶段验收报告](docs/phase6-acceptance-report.md)。

## 检查与测试

```bash
cd frontend
npm run check
```

`npm run check` 依次运行 ESLint、TypeScript 检查、Vitest 和生产构建。

```bash
cd backend
.venv/bin/pytest -q
.venv/bin/python -m compileall -q app alembic tests
```

后端测试覆盖注册、重复邮箱、Argon2id 哈希、正确/错误密码、限流、Cookie 保持、退出失效、未登录访问、A/B 独立会话、目标/打卡隔离、越权拒绝和 CSRF 来源检查。

第三阶段新增算法、三账号匹配、资料校验、隐私白名单、方向/时间过滤、分页、撤回匹配同意和档案所有权测试。默认 SQLite 临时库；要运行真实 PostgreSQL 回归，指定专用测试库（URL 从本地环境提供）：

```bash
cd backend
export STUDYMATE_TEST_DATABASE_URL='postgresql+asyncpg://studymate:<test-password>@127.0.0.1:5432/studymate_test'
.venv/bin/pytest -q
```

PostgreSQL 每个测试创建并清理自己随机命名的 `studymate_test_*` schema，不清空已有业务表；测试数据库用户需有 CREATE SCHEMA 权限。只在隔离开发/测试库执行。

第六阶段完整 PostgreSQL 回归为 **96 passed**，前端为 **33 passed**。SQLite兼容回归为 **85 passed/11 skipped**，11项行锁并发测试仅在PostgreSQL执行。新增19项后端通知/安全用例，前端新增7项服务/状态/认证缓存用例。已验证空库→0005、带旧数据0004→0005、本机开发库无损升级及`alembic check`一致性；历史成绩保留在各阶段报告。

浏览器测试需先启动连接隔离 PostgreSQL 的后端和前端，再执行：

```bash
cd frontend
npx playwright install chromium
npm run test:e2e
```

如果本机已有 Chrome，可以不下载浏览器：

```bash
STUDYMATE_CHROMIUM_PATH=/usr/bin/google-chrome npm run test:e2e
```

浏览器测试只接受 localhost/127.0.0.1，四个完整场景（匹配、邀请、小组、全站通知）均通过。每个场景创建独立账号/Cookie会话，验证真实Vue表单、刷新/重登、隐私、权限和移动布局。截图位于 `frontend/test-results/`（Git忽略），不使用个人浏览器目录。**必须先连接独立测试数据库，不能指向现有开发数据或生产环境。** 测试默认访问5173；推荐 `STUDYMATE_E2E_BASE_URL=http://127.0.0.1:5174`，搭配8001测试后端及 `STUDYMATE_API_PROXY_TARGET=http://127.0.0.1:8001` 的5174前端。完整隔离命令见第六阶段报告。

## 项目结构

```text
.
├── backend/
│   ├── alembic/              # 版本化数据库迁移
│   ├── app/api/             # 认证、学习、匹配、邀请、通知、小组与分享API
│   ├── app/services/        # 算法、事务锁、安全投影、SQL统计与学习日历
│   ├── app/models.py        # SQLAlchemy 模型
│   └── tests/               # 算法、认证、三账号、并发与事务回滚测试
├── frontend/
│   ├── src/
│       ├── services/        # 独立 HTTP/API 层
│       ├── stores/          # Pinia 状态与 api/mock 切换
│       └── views/           # 八个主要页面与小组详情路由
│   └── e2e/                 # 三浏览器会话端到端验收
├── docs/                      # 需求、页面、数据库与 API 文档
├── compose.yaml
└── Dockerfile
```

## 文档

- [需求分析](docs/requirements.md)
- [页面与信息架构](docs/pages.md)
- [搭子匹配算法](docs/matching-algorithm.md)
- [数据库设计](docs/database-design.md)
- [API 设计](docs/api-design.md)
- [后续部署基线](docs/deployment.md)
- [第三阶段实际验收记录](docs/stage3-verification.md)
- [第四阶段实际验收记录](docs/stage4-verification.md)
- [第五阶段实际验收记录](docs/stage5-verification.md)
- [第六阶段全站验收报告](docs/phase6-acceptance-report.md)
- [云端部署记录与运行说明](docs/cloud-deployment.md)

## 已知边界

- 本轮已启动用户级隔离 PostgreSQL 14.24，实测 Alembic 从第一版保留旧账号升级，以及完整后端测试。该实例位于 `/tmp`，用于本地验收，不是正式数据库或备份方案。
- 当前匹配时间仅支持 UTC+8（Asia/Shanghai、Asia/Hong_Kong），跨时区/夏令时匹配尚未实现。
- 候选全量评分后排序分页，适合早期规模；大规模索引预筛、缓存与性能压测待后续。
- 实时聊天、独立组任务、打卡提醒、隐藏/邀请码小组尚未实现；基础小组事件通知已完成。
- 小组时长由用户自行记录，并非自动计时或防作弊系统；当前只保存一个共同目标，不保留目标版本。退出/被移除会撤回本组全部分享，榜单随之重算。
- Element Plus首包仍有超过500kB的构建提示，构建成功；未做大规模负载/长期运行压测。
- 未实现邮箱验证、密码找回、全设备退出、账号注销、审计告警和备份恢复。
- 已完成 Render + Neon 免费云部署；免费服务存在休眠及额度限制，备份恢复演练、长期负载测试和正式隐私/用户协议仍需完善。

## 下一阶段建议

- 增加组内独立任务及每成员完成记录、共同目标版本历史，继续复用现有打卡并严格区分私人数据和共享范围。
- 根据云端验收记录持续检查异地网络访问、性能和错误日志；使用免费环境试用后，再评估正式运营所需的资源和可用性。
- 增加小组举报/审核、账号级创建与申请配额、审计日志；根据实际规模再做排行榜缓存与一致性失效、索引及分页优化。
- 完成 Neon 数据导出与恢复演练、负载测试及隐私/用户协议；自定义域名需另行购买和授权，本轮未操作。
