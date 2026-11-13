# 第三阶段验收记录

> 此文记录第三阶段历史验收（迁移版本 0002）。第四阶段邀请/关系/通知的当前状态见 [stage4-verification.md](stage4-verification.md)。

日期：2026-11-13。代码在现有工作区继续修改，保留上一阶段未提交的变更，未操作生产环境或公网部署。

## 实测环境

- PostgreSQL 14.24：下载 Ubuntu 仓库二进制至 `/tmp/studymate-pg-runtime`，用户级实例数据在 `/tmp/studymate-pg-data-20261113`。
- 数据库 `studymate_matching_dev` 使用当前用户私有 Unix Socket `/tmp/studymate-pg-socket-20261113`，端口号 55432，不开放 TCP 或公网端口。
- FastAPI：`http://127.0.0.1:8000`，Vite：`http://127.0.0.1:5173`，API 模式。
- Playwright 使用 `/usr/bin/google-chrome` 创建独立无头上下文，不读取用户的 Chrome 配置文件。
- 该实例用于本地验收，位于临时目录，不能作为正式持久化/备份部署。标准 PostgreSQL 配置见 README。

## 已执行检查

| 检查 | 实际结果 |
| --- | --- |
| PostgreSQL 后端全套 pytest | 43 passed，含原有认证、目标、任务、打卡回归 |
| SQLite 后端全套 pytest | 43 passed |
| 前端 ESLint、vue-tsc | 通过，包含浏览器测试源码类型检查 |
| 前端 Vitest | 4 个文件，17 项通过 |
| Vite 生产构建 | 通过；存在 Element Plus 全量注册后的大 chunk 提醒，首包拆分仍可优化 |
| Python compileall、git diff --check | 通过 |
| Chrome 三账号完整场景 | 1 场景通过，包含真实 Vue 表单与独立 Cookie 会话 |
| Alembic PostgreSQL 升级 | 从空库建第一版，加入旧账号后升至 20261113_0002，原昵称/账号保留，matching_enabled=false、categories=[] |
| Alembic SQLite 升级 | 新临时库连续升级至 20261113_0002 成功 |

PostgreSQL 测试的每个用例创建并清理自己随机命名的 schema；没有清空开发库的 public 表。浏览器测试通过注册 API 创建随机独立测试账号，密码运行时随机生成，不写仓库。

## 三账号关键断言

账号 A：编程开发/C++，周一 19:00–22:00；B：相同方向/标签，周一 19:30–22:30；C：考研/考研英语，周一 08:00–11:00。三者方式为共同讨论、阶段为强化。

- A→B：G=100、T=83、M=100、L=100，S=94；每周重合 150 分钟。
- A→C：G=0、T=0、M=100、L=100，S=25。
- B 在实际前端时间选择器改为 08:00–11:00，保存后 A 刷新，A→B=65。
- B 在实际前端关闭“允许被推荐”并保存，A 刷新后不再看到 B。
- 本人不在候选列表；默认未开启匹配、禁用账号不在候选列表。
- 刷新个人中心保持已保存昵称、时间和匹配开关。
- 推荐字段白名单不含邮箱、学校、专业、简介、私人目标、打卡或会话凭证。
- 修改其他用户档案路径返回 404；往 `/profiles/me` 注入 userId 返回 422；未登录接口返回 401。
- 方向、星期、跨时段交集、共同空闲、关键词和分页均已测试；非法输入失败时旧档案不变。
- 390×844 移动视口无水平溢出；桌面/移动截图由浏览器测试生成在 `frontend/test-results/`（Git 忽略）。

## 发现并修复的原有缺陷

浏览器首轮发现所有 Element Plus 表单只有样式文件、没有注册组件，导致原生输入框和按钮实际不渲染。已在 `frontend/src/main.ts` 注册组件库及中文语言包。该问题不能由原先只测 store/算法和编译的测试发现，现增加真实浏览器回归覆盖。

同时增加账号切换时的档案/学习数据内存清理与请求代次检查，避免旧账号的延迟响应覆盖新账号页面。正式 API 模式不读写旧 LocalStorage Mock 档案；也不会自动把不明归属的演示数据导入真实账号。

## 复验命令

```bash
cd backend
STUDYMATE_TEST_DATABASE_URL='postgresql+asyncpg://martin@/studymate_matching_dev?host=/tmp/studymate-pg-socket-20261113&port=55432' .venv/bin/pytest -q
```

```bash
cd frontend
npm run check
STUDYMATE_CHROMIUM_PATH=/usr/bin/google-chrome npm run test:e2e
```

浏览器测试运行前需启动本地前后端；详情见 README。此处 Socket URL 只适用于本次本机临时实例；其他环境需更换为自己的隔离 PostgreSQL 测试库。

## 本阶段未验收项目

Docker 未安装，未执行容器构建。未做公网部署、人工跨设备访问或目标云平台验证。跨时区/夏令时匹配、真实邀请/聊天/小组、线上通知及大规模推荐压测留待后续。当前推荐全量评分后分页，不能据此声称已通过高并发验收。
