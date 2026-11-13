# 第五阶段：真实学习小组验收记录

日期：2026-11-13。直接增量修改原工作区；未新建项目、未操作生产数据、域名或云服务器。

## 1. 开发前实际检查

检查认证、模型、迁移、学习业务、档案/推荐、邀请/关系/通知、小组页面与现有测试。既有第三、四阶段代码存在且可运行：开发前 PostgreSQL 后端60项、前端21项通过，lint/type-check/build通过。原小组页使用 `useSocialStore` 和LocalStorage，申请加入会模拟通过，没有真实小组表/API。本次替换该路径，没有重写认证或个人学习业务。

## 2. 实现内容与边界

- 原 `/groups` 页面保留蓝紫卡片设计，使用真实发现/搜索/方向过滤/我加入的/分页和创建表单。新增 `/groups/:groupId` 共学详情路由。
- 组长/成员两种角色；创建者自动成为组长。支持直接加入、审核申请、批准/拒绝/取消、普通成员退出、组长移除、转让和明确解散。后端校验角色、当前成员资格及容量。
- 个人打卡页“分享到小组”逐组授权，默认只分享昵称、日期、时长；学习正文单独选择，可调整或撤回。不复制现有checkins，不公开心情、私人目标、邮箱/学校/专业。
- 成员可查看真实公开动态、今日人数、本周足迹/时长和累计时长，四类排行榜包括零分享成员。组长设置当前共同时间目标，成员查看自己的进度。
- 所有小组业务调用独立 `services/groups.ts`；移除 `stores/social.ts` 的假多人互动。旧浏览器演示数据不删除、不自动迁入真实账号；显式Mock仅保留个人学习演示。
- 既有通知仍仅支持搭子事件；本阶段小组需手动刷新，没有聊天/WebSocket、隐藏小组或小组事件通知。

## 3. PostgreSQL结构与一致性

Alembic `20261113_0004` 从0003增量增加 `groups/group_members/group_join_requests/group_goals/group_checkin_shares` 和checkins复合唯一约束。迁移不清空旧表，不覆盖用户或打卡，不依赖正式环境自动建表。降级明确拒绝自动丢弃小组历史。

数据库约束：成员复合主键、每组一个owner的部分唯一索引、每组/人一个pending申请、同组长有效小组名唯一、审核来源唯一、每组/打卡一个分享、分享必须同时属于原记录所有者和本组成员的两个复合外键。所有组状态修改首先锁定group行；个人记录分享再锁定checkin。接受申请、创建成员一次提交，owner转让先降旧角色再升新角色；成员私有读取持有共享锁与撤权串行。

退出/移除级联撤回该成员在本组的分享；删除原打卡撤回其全部小组分享；撤回分享不删除个人打卡；重新加入不恢复旧分享。组长不可直接退出，转让对象必须是现有有效成员。解散为软归档，撤回成员和分享、取消待处理申请，保留归档/目标/审核历史和个人记录。旧申请即使approved也不能在成员退出后重新创建成员。

排行榜统一北京时间 `Asia/Shanghai` UTC+8，day当天、week周一至周日、month自然月、days建组以来。SQL仅关联当前成员/有效用户、本次入组当地日期起且不晚于今天的授权记录，入组当天的早些记录可分享。每人每天分享到同一组总时长<=1440分钟；不同组独立计数，个人记录不重复创建。时长降序、天数降序、UUID升序；天数榜天数降序后按时长/UUID稳定排序。天数DISTINCT日期，一条分享每组只累计一次。撤回/退出后实时重算，不保留未经同意的历史排名快照。

共同目标周期含首尾，最多366天，最多525600分钟且不得超过周期天数×1440。只保存当前目标；进度只计本人在该组该周期有效分享，目标主题由成员自律遵守，不进行语义判断或防作弊识别。

## 4. 实际隔离环境与迁移

- 本机用户级 PostgreSQL **14.24**，私有Unix Socket `/tmp/studymate-pg-socket-20261113`，端口号55432，未开放TCP。
- 本阶段独立测试库 **studymate_groups_test**。pytest每项再使用随机 `studymate_test_*` schema，结束只清理自身schema；浏览器测试账号仅写入该测试库。
- 浏览器联调服务为8001/5174，三账号使用独立Chrome上下文、随机密码，没有使用个人浏览器目录。
- 测试库从空库连续迁移至0004通过；`alembic check` 无新增操作。SQLite独立临时文件也从空库连续迁移成功。
- 既有开发库 **studymate_matching_dev** 0003→0004成功。迁移前后逐表JSON内容SHA-256摘要一致：users17、profiles17、auth_sessions16、profile_time_slots15，goals/tasks/checkins/buddy_requests/buddy_relations/notifications/login_throttles均0（开发样本原状）。只输出计数，不输出凭据或私人数据。新小组表为空，不把验收账号写入开发库。
- 原本机8000开发后端已重启加载新版，并保留原环境/认证配置；5173前端继续连接该开发库。可自行注册并创建小组。

## 5. 实际自动化结果

| 检查 | 实际结果 |
| --- | --- |
| PostgreSQL完整pytest | **77 passed**，包含17项新增小组测试；并发用例无跳过 |
| SQLite兼容pytest | **67 passed，10 skipped**；10项依赖PostgreSQL行锁的用例明确跳过 |
| 前端Vitest | **26 passed**，6个文件；含6项真实小组服务测试，移除旧Mock小组测试 |
| ESLint、vue-tsc | 通过，含三个端到端场景类型检查 |
| Vite生产构建 | 通过；既有Element Plus首包大于500kB提示保留 |
| Chrome/Playwright完整场景 | **3 passed**：搭子邀请、学习小组、真实匹配，最终全套32.1秒 |
| Python compileall | app/alembic/tests通过 |
| PostgreSQL Alembic | 空库→0004、旧库0003→0004通过，模型check无漂移 |
| SQLite Alembic | 空临时文件→0004通过 |
| git diff --check | 通过 |

小组后端覆盖：A/B/C正常闭环、未登录、非组员404、成员越权403、他人申请/打卡404、非法方向/日期/容量/未知字段、重复加入/申请/批准幂等、容量缩小拒绝、取消/拒绝、组长退出规则、转让/解散、撤回/成员移除/删除原记录、重登持久化、零数据成员、同日多条去重、跨组独立分享、外键直接插入拒绝、UTC+8入组日期边界和跨周/月SQL统计，以及创建中途故障整笔回滚。

新增5项PostgreSQL并发测试实际执行：抢最后一个名额与重复加入；并行批准只允许一个占用最后名额；分享与成员撤权竞争；两条900分钟记录并发分享只有一条成功；六次重复申请只有一条pending、批准与取消竞争最终状态一致。现有搭子并发测试也通过。

`alembic check`首次发现已有认证模型把第一版迁移的命名唯一索引描述为匿名唯一约束。已将模型声明对齐实际命名索引，唯一性与认证机制不变，再次check通过。SQLite迁移曾在受限沙盒的线程环境挂起；结束该临时进程，在允许运行线程的环境重跑成功，没有把挂起算作通过。

## 6. 浏览器实际闭环

`frontend/e2e/groups.e2e.ts` 使用A/B/C三个真实注册登录会话，执行：

1. A通过Vue表单创建C++组，创建者为owner；公告仅成员可见。
2. B在发现页搜索并申请，按钮等待审核，详情API404。C不能审批他人申请；A从申请页同意，B刷新后可进入。
3. A通过真实打卡表单记录180分钟，B通过真实打卡API记录120分钟，另有45分钟私人记录。不分享时组动态为0。
4. A在分享弹窗勾选正文，B保持默认不公开；组内只有两条记录，不含B正文、未分享记录、心情或身份字段。C不能读取动态/名单/分享他人打卡，B不能移除A。
5. B通过弹窗公开正文、关闭正文授权、撤回、重新分享，另一个会话的响应随之更新；原个人记录保持。
6. 今日人数2、300分钟，A排第一180分钟、B120分钟；目标600分钟，A30%、B20%。B刷新、退出重登后仍为20%。
7. B退出后API404，分享撤回，A统计变为180分钟，B两条个人打卡仍在。
8. C申请后取消，再申请获A批准；A通过成员页转让给C；C移除A，A私有访问404，组内累计变0。C通过表单编辑并明确解散，小组预览404。
9. 桌面1440px和移动390px截图已目视检查，移动页面无水平溢出；浏览器无pageerror，LocalStorage无真实social记录。修复全局主按钮样式覆盖文字/朴素按钮导致的低对比度问题。

截图（测试运行时生成，Git忽略）位于 `frontend/test-results/`，有 `group-desktop.png/group-mobile.png` 及匹配/搭子截图。完整端到端重跑后均通过，不以失败轮次代替最终结果。

## 7. 复验与本地运行命令

当前本机实例已运行。如本机实例仍存在但已停止，可执行（不要对其他数据目录运行initdb）：

```bash
mkdir -p /tmp/studymate-pg-socket-20261113
chmod 700 /tmp/studymate-pg-socket-20261113
LD_LIBRARY_PATH=/tmp/studymate-pg-runtime/usr/lib/x86_64-linux-gnu \
  /tmp/studymate-pg-runtime/usr/lib/postgresql/14/bin/pg_ctl \
  -D /tmp/studymate-pg-data-20261113 -l /tmp/studymate-pg-stage5.log \
  -o '-p 55432 -h "" -k /tmp/studymate-pg-socket-20261113' start
```

此路径仅适用本机开发实例；`/tmp`会被清理，不是正式持久化方案。其他机器按README准备PostgreSQL、环境变量与专用数据库，不能直接复用此URL或验收账号。

正常开发启动（分别开终端；已运行时不重复占用端口）：

```bash
cd backend
export STUDYMATE_DATABASE_URL='postgresql+asyncpg://martin@/studymate_matching_dev?host=/tmp/studymate-pg-socket-20261113&port=55432'
.venv/bin/alembic upgrade head
STUDYMATE_AUTO_CREATE_SCHEMA=false .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

浏览器：[注册登录](http://127.0.0.1:5173/auth)、[小组发现](http://127.0.0.1:5173/groups)、[学习打卡](http://127.0.0.1:5173/checkins)、[接口文档](http://127.0.0.1:8000/api/docs)。仅本机可访问，本阶段不发布公网链接。

隔离后端回归：

```bash
cd backend
STUDYMATE_TEST_DATABASE_URL='postgresql+asyncpg://martin@/studymate_groups_test?host=/tmp/studymate-pg-socket-20261113&port=55432' .venv/bin/pytest -q
env -u STUDYMATE_TEST_DATABASE_URL .venv/bin/pytest -q
.venv/bin/python -m compileall -q app alembic tests
```

隔离浏览器联调分别启动（测试库需提前创建，不能替换为生产URL）：

```bash
cd backend
export STUDYMATE_DATABASE_URL='postgresql+asyncpg://martin@/studymate_groups_test?host=/tmp/studymate-pg-socket-20261113&port=55432'
.venv/bin/alembic upgrade head
STUDYMATE_APP_ENV=test STUDYMATE_AUTO_CREATE_SCHEMA=false STUDYMATE_CORS_ORIGINS=http://127.0.0.1:5174 .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001
```

```bash
cd frontend
VITE_BUSINESS_DATA_MODE=api STUDYMATE_API_PROXY_TARGET=http://127.0.0.1:8001 npm run dev -- --host 127.0.0.1 --port 5174 --strictPort
```

再执行：

```bash
cd frontend
npm run check
STUDYMATE_E2E_BASE_URL=http://127.0.0.1:5174 STUDYMATE_CHROMIUM_PATH=/usr/bin/google-chrome npm run test:e2e
```

其他机器没有Chrome时可`npx playwright install chromium`。手动三账号步骤见README；无固定密码、不显示自动化密码，重新运行会创建独立测试账号。

## 8. 未验证和后续事项

本机没有Docker可执行程序，本次不依赖或声称容器运行验证。未进行云部署、域名操作、负载/长期运行压测或生产备份恢复演练。当前仅HTTP手动刷新共享结果，不提供推送通知。时长为自报记录，尚非防作弊系统。

最终交付前，8000后端已显示成功启动日志，5173原开发前端保留。最后一次针对这两个端口的curl就绪/链接复核因自动审批服务的额度限制被拒绝执行（不是操作被判定不安全）；因此不把该次HTTP复核列为通过。此前连接独立PostgreSQL的8001/5174完整浏览器验收实际通过，随后已正常停止这两个隔离验收服务；保留8000/5173供本机使用。

后续建议按顺序补齐持久数据库/备份恢复和运行监控；组内任务与目标历史；带幂等事件键的小组通知；账号级创建/申请配额、举报审核与审计；规模增长后优化查询/缓存并压测。上线另行完成HTTPS、安全Cookie、生产密钥和迁移预演。
