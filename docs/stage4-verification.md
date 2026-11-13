# 第四阶段：真实搭子邀请、关系与通知验收

日期：2026-11-13。在原工作区增量开发，未新建项目、未操作生产环境或公网部署。第三阶段先实测回归，再开发本阶段。

## 1. 实现范围

- 独立接收邀请开关：新旧账号默认 false，需与允许推荐同时开启才可接收新申请。
- 真实发送/收取、接受/拒绝/取消，待处理重复请求幂等，反向申请提示处理原请求。
- 双方可见的有效搭子列表、公开学习目标标签/每周计划，以及任一方解除关系。
- PostgreSQL 持久化四类站内通知、未读数量、已读状态；普通 HTTP，无聊天或 WebSocket。
- Vue 推荐按钮按真实 connection 元数据变化；增加四个功能页签、通知入口、公开资料抽屉、加载/错误/空状态和解除确认。
- 移除旧模拟邀请服务和 Pinia 状态方法，LocalStorage 不保存真实邀请、关系或通知。小组 Mock 保留，未增加小组新业务。

## 2. 数据库与并发保证

迁移 `20261113_0003` 增加 profiles.allow_invites、buddy_requests、buddy_relations、notifications。规范化用户对 UUID、禁止自邀/非法状态、pending 对唯一、有效关系对唯一、来源邀请唯一、通知事件键唯一，由数据库兜底。

所有关系写操作先按 UUID 顺序锁定参与者 users，再处理邀请/关系；跨目标发送的账号配额也在同一用户锁内检查。接受、关系创建、通知一次提交。重复接受不创建重复关系/通知，原关系结束后旧邀请不能复活，即使随后已有新关系。异常通知写入会回滚整个接受事务。

默认配额：每小时 10、滚动 24 小时 30、同时 pending 20、同对用户 300 秒冷却。取消/拒绝仍计发送次数。只有参与者可读邀请，只有对应角色可处理；关系仅双方可读/解除；通知只有接收者可读和标记。错误角色或第三人请求返回 404。

## 3. 隔离实测环境

- 用户级 PostgreSQL 14.24 使用 `/tmp/studymate-pg-runtime` 与私有 Unix Socket `/tmp/studymate-pg-socket-20261113`，端口号 55432，不开放 TCP。
- 独立测试数据库为 **studymate_connections_test**；单元/接口测试再使用随机 `studymate_test_*` schema，结束只清理自身 schema。
- 浏览器联调服务为后端 8001、前端 5174；所有自动注册账号只写测试库。
- 原开发数据库 **studymate_matching_dev** 在测试后才增量升级。升级前后核验：17 个用户、17 个档案保留，用户与旧档案内容摘要一致，目标/任务/打卡表行数未变（本开发样本均为 0）。旧账号接收邀请全部为 false。
- 原本地 8000 后端已重启加载新版，5173 前端仍连接原开发库；保留原有账号。
- PostgreSQL 数据目录仍位于 `/tmp`，仅供本机开发验收，正式部署需独立持久化和备份。

## 4. 实际测试结果

| 检查 | 结果 |
| --- | --- |
| 开发前第三阶段 PostgreSQL 基线 | 43 passed |
| 开发前前端基线 | 17 passed，lint/type-check/build 通过 |
| 本阶段 PostgreSQL 全套 pytest | **60 passed**，没有跳过并发用例 |
| SQLite 兼容回归 | **55 passed, 5 skipped**；5 项 PostgreSQL 行锁并发用例明确跳过 |
| 前端 Vitest | **21 passed**，5 个文件 |
| ESLint、vue-tsc | 通过，含两个浏览器场景的类型检查 |
| Vite 生产构建 | 通过；原有 Element Plus 大首包告警仍存在 |
| Chrome 第四阶段三账号场景 | 通过，真实 Vue 表单和 API |
| Chrome 第三阶段匹配回归 | 通过 |
| Alembic 新库完整升级 | 测试库从空库连续升级至 0003，通过 |
| Alembic SQLite 兼容迁移 | 新临时库连续升级至 0003，通过 |
| Alembic 现有库升级 | 0002→0003，通过，并核对旧数据摘要 |

新增后端测试覆盖：三账号收发、默认开关与目标资格、自邀/未知用户/非法输入、角色越权、通知隔离和已读幂等、分页筛选、拒绝/取消不创建关系、双方解除、关闭公开后的历史资料隐藏、禁用发送者不能接受、持久配额及重登。

5 项 PostgreSQL 并发用例实际执行：8 次同向发送和 8 次接受只产生一个请求/关系/通知；正反向同时申请只保留一条 pending；同发送者并发不同目标共享配额；接受与取消竞争；接受与拒绝竞争。另有通知失败注入回滚和数据库重复 pending 唯一约束测试。

## 5. 浏览器实测过程

Chrome 使用独立上下文和随机密码，不使用个人浏览器资料目录。A/B/C 实际通过注册登录页面创建账号，测试包含：

1. B 在个人中心手动开启接收邀请，保存并刷新验证。
2. A 从真实推荐卡发送留言，显示等待接受，发件箱保留；重复 POST 返回原请求，C 无权操作。
3. B 查看新通知并标记已读，查看 A 的公开资料，点击接受。
4. A/B 均看到同一关系；刷新、退出重登后保留，通知已读状态也保留。
5. 推荐卡变为已成为搭子；关系响应不含邮箱、学校、专业、简介、私人记录。
6. C→B 邀请被拒绝，C 可见 rejected，没有关系；A→C 被取消，状态 cancelled。
7. B 解除 A/B 关系，A 收到解除通知，双方列表移除；旧接受请求返回 409。
8. 390px 移动视口无水平溢出；正式邀请没有写入 LocalStorage social 记录。

截图在 `frontend/test-results/`（Git 忽略），包含我的搭子、桌面通知、移动通知及第三阶段推荐。两个场景最终均通过。

## 6. 本次修复的测试基础问题

第三阶段测试 fixture 在 connect 事件中执行 SET search_path，却未脱离事务。并发新增池连接遇到只读请求回滚后会恢复默认 schema，导致“表不存在”，并非业务表缺失。现使用事务外设置并恢复原 autocommit，符合 [SQLAlchemy 的连接 search_path 说明](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#setting-alternate-search-paths-on-connect)，多连接并发回归已通过。

## 7. 复验命令

当前本机 PostgreSQL 测试库：

```bash
cd backend
STUDYMATE_TEST_DATABASE_URL='postgresql+asyncpg://martin@/studymate_connections_test?host=/tmp/studymate-pg-socket-20261113&port=55432' .venv/bin/pytest -q
```

复现隔离浏览器联调，分别在两个终端启动：

```bash
cd backend
export STUDYMATE_DATABASE_URL='postgresql+asyncpg://martin@/studymate_connections_test?host=/tmp/studymate-pg-socket-20261113&port=55432'
.venv/bin/alembic upgrade head
STUDYMATE_APP_ENV=test STUDYMATE_CORS_ORIGINS=http://127.0.0.1:5174 .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001
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

Socket URL 和 Chrome 路径只适用于本机；其他环境按 README 准备自己的隔离测试库和浏览器。不要把测试指向生产环境。

## 8. 手测与后续

两个独立浏览器分别使用 A/B，完成开启匹配/邀请、A 申请、B 查看通知并接受、双方刷新/重登、任一方解除。拒绝/取消和第三人越权可加 C；同一对用户重新申请受 300 秒冷却影响。详细步骤见 README。

下一阶段实现真实小组的成员唯一约束、角色权限、容量事务锁、个人组任务完成记录和服务端排行榜；复用通知时同步迁移 kind 检查约束。当前未开发聊天、真实小组、打卡提醒或公网部署；未运行容器构建或高并发压力测试。当前配额是账号级基础保护，不等于完成生产反滥用系统。
