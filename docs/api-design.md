# 学搭 RESTful API 设计

> 基础路径：`/api/v1`  
> 当前实现：账号认证、学习目标/任务、打卡、档案、搭子匹配/邀请/关系/通知，以及真实学习小组
> 认证方式：只支持用户名/邮箱 + 密码，不接入第三方登录

## 1. 通用约定

- 浏览器只访问 FastAPI，不允许直接连接数据库。
- 用户身份只来自服务端会话；私有资源请求不接受客户端 `user_id`。
- JSON 字段与当前 Vue 类型保持 camelCase；日期使用 `YYYY-MM-DD`，时间使用 ISO 8601。
- 资源不存在、非成员读取小组私有内容返回 404；本组普通成员尝试组长操作返回 403。
- 删除成功返回 `204 No Content`；其他成功响应使用统一 envelope。

成功响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "requestId": "req_7f4a..."
}
```

错误响应：

```json
{
  "code": "UNAUTHENTICATED",
  "message": "请先登录",
  "data": null,
  "requestId": "req_7f4a..."
}
```

| HTTP | 业务 code | 说明 |
| ---: | --- | --- |
| 401 | `UNAUTHENTICATED` | 未登录、过期或已撤销 |
| 403 | `CSRF_ORIGIN_REJECTED` | Cookie 状态变更请求的 Origin 不可信 |
| 404 | `GOAL_NOT_FOUND` / `TASK_NOT_FOUND` / `CHECKIN_NOT_FOUND` | 不存在或不属于当前用户 |
| 409 | `ACCOUNT_ALREADY_EXISTS` | 用户名或邮箱已注册 |
| 422 | `VALIDATION_ERROR` | 请求字段不合法 |
| 429 | `LOGIN_RATE_LIMITED` | 登录失败超过限制 |

## 2. 认证与会话

| 方法 | 路径 | 认证 | 实现状态 |
| --- | --- | --- | --- |
| POST | `/auth/register` | 否 | 已实现 |
| POST | `/auth/login` | 否 | 已实现 |
| GET | `/auth/me` | Cookie | 已实现 |
| POST | `/auth/logout` | 可选 Cookie | 已实现，幂等撤销当前会话 |

### 2.1 注册

```http
POST /api/v1/auth/register
Content-Type: application/json
```

```json
{
  "username": "user_a",
  "email": "user_a@example.com",
  "password": "StudyMate2026!",
  "confirmPassword": "StudyMate2026!"
}
```

规则：

- 用户名 3–32 位，以字母开头，只允许字母、数字和下划线；存储时转小写。
- 邮箱进行格式校验并转小写；用户名和邮箱都具有数据库唯一约束。
- 密码 8–128 字符，至少包含一个字母和一个数字。
- 密码经 Argon2id 哈希后写库；响应、日志和数据库都不保存明文。
- 注册成功不自动建立会话，前端切回登录表单。

成功返回 201，`data` 为：

```json
{
  "userId": "uuid",
  "username": "user_a",
  "email": "user_a@example.com",
  "displayName": "user_a",
  "avatarUrl": null,
  "onboardingCompleted": false
}
```

### 2.2 登录

```json
{
  "account": "user_a@example.com",
  "password": "StudyMate2026!"
}
```

- `account` 可以是用户名或邮箱。
- 账号不存在、密码错误、账号不可用都统一返回 401 与“账号或密码错误”。
- 登录失败按“IP + 规范化账号”的哈希键记录在 `login_throttles`；默认 15 分钟内 5 次后锁定 15 分钟。
- 成功后生成高强度随机令牌，数据库只存 SHA-256 哈希。
- 本地开发 Cookie：`HttpOnly; SameSite=Lax`；生产配置强制 `Secure`。
- 会话默认有效期 30 天，浏览器刷新或重开后在有效期内仍可用。

### 2.3 身份与退出

- `GET /auth/me` 通过 Cookie 加载 `auth_sessions -> users -> profiles`。
- `POST /auth/logout` 写入 `revoked_at`并删除 Cookie；原 Cookie 后续请求返回 401。
- 前端不把密码、会话令牌或其他登录凭证写入 LocalStorage。

## 3. 目标与任务（已实现）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/goals` | 当前用户的目标与任务 |
| POST | `/goals` | 创建自己的目标 |
| GET | `/goals/{goal_id}` | 读取自己的目标 |
| PUT | `/goals/{goal_id}` | 全量更新自己的目标 |
| DELETE | `/goals/{goal_id}` | 删除自己的目标并级联删除任务 |
| POST | `/goals/{goal_id}/tasks` | 向自己的目标添加任务 |
| PUT | `/goals/{goal_id}/tasks/{task_id}` | 更新任务和完成状态 |
| DELETE | `/goals/{goal_id}/tasks/{task_id}` | 删除任务 |

目标请求示例：

```json
{
  "title": "计算机考研冲刺计划",
  "description": "完成 408 与高数二轮复习",
  "category": "考研",
  "tags": ["408", "高等数学"],
  "startDate": "2026-11-12",
  "targetDate": "2027-02-11",
  "status": "进行中",
  "color": "#5b5ce2"
}
```

任务请求示例：

```json
{
  "title": "完成一组数据结构习题",
  "dueDate": "2026-11-12",
  "estimatedMinutes": 60,
  "completed": false
}
```

目标、任务所有权在每个读写端点后端校验；前端传入其他用户的 UUID 不会绕过权限。

## 4. 学习打卡（已实现）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/checkins` | 当前用户的打卡列表 |
| POST | `/checkins` | 创建打卡 |
| GET | `/checkins/{checkin_id}` | 读取自己的打卡 |
| DELETE | `/checkins/{checkin_id}` | 删除自己的打卡 |

```json
{
  "date": "2026-11-12",
  "duration": 90,
  "content": "完成数据结构二叉树练习",
  "mood": "专注在线",
  "goalId": "uuid-or-null"
}
```

规则：日期不得晚于今天；时长 1–1440 分钟；`goalId` 有值时必须属于当前用户。

## 5. 浏览器安全策略

- 推荐前后端同源部署。
- CORS 只允许 `STUDYMATE_CORS_ORIGINS` 中的精确 origin，开启凭据时不使用 `*`。
- POST/PUT/PATCH/DELETE如含Origin（含未登录的注册/登录），必须精确匹配当前请求或显式CORS来源的协议、主机、端口；不再只比较hostname。null、非法端口、含凭据/路径的来源均拒绝。携带Cookie且无Origin的浏览器请求如Sec-Fetch-Site=cross-site也拒绝；无浏览器来源标头的受信API客户端仍按会话校验。
- 生产启动拒绝默认/占位密钥、少于32字节的密钥、未启用Secure、SQLite或自动建表。当前使用SameSite=Lax与同源部署；跨站Cookie及目标云代理配置仍需单独验收。

## 6. 学习档案（已实现）

`GET /profiles/me` 和 `PUT /profiles/me` 均要求登录。GET 只返回当前登录用户的完整档案；PUT 完整替换本人可编辑字段，不提供修改其他用户档案的路由。

PUT 请求示例：

```json
{
  "name": "晚间学 C++",
  "school": "",
  "major": "",
  "bio": "",
  "categories": ["编程开发"],
  "tags": ["C++", "算法"],
  "styles": ["独立学习", "共同讨论"],
  "stage": "强化",
  "timezone": "Asia/Shanghai",
  "timeSlots": [{"day": 1, "start": "19:00", "end": "22:00"}],
  "dailyTargetMinutes": 180,
  "publicProfile": true,
  "allowInvites": false
}
```

- `name` 必填，去空白后 1–50 字。建议昵称；邮箱和账号字段不能在这里修改。
- `categories` 为预设方向，最多 8 个；`tags` 最多 20 个、每项 1–32 字；`styles` 为预设方式，最多 8 个；`stage` 可为 null。
- 时段最多 42 个，`day` 为整数 1–7；时间必须是两位 `HH:mm`，end 可为 `24:00`，且严格晚于 start。完全重复时段拒绝，重叠时段保存后由算法合并。
- `publicProfile` 映射数据库 `matching_enabled`。新老账号都默认 false；关闭后仍可查看他人推荐，自己不成为候选。允许未完成档案的用户主动开启，但分数明确附缺失资料说明。
- `allowInvites` 为独立布尔字段（可在 PUT 中提供，默认 false），同样通过本人档案 API 保存；只有它和 publicProfile 同时为 true 才可接收新邀请。关闭不会取消历史申请或既有关系。
- 本阶段时区仅接受 `Asia/Shanghai`、`Asia/Hong_Kong`（UTC+8）。
- 非法字段（含 `id/userId`）返回 422；校验失败不覆盖现有档案。
- 返回本人档案，额外含 `id`、`avatar`、`updatedAt`；每个时段额外含服务端 `id`。前端保存时必须剔除只读字段。
- `school/major/bio/dailyTargetMinutes/publicProfile/updatedAt` 只出现在本人档案响应，不向其他用户公开。

## 7. 搭子推荐（已实现）

```http
GET /api/v1/buddies/recommendations?category=编程开发&period=evening&day=1&page=1&pageSize=12
```

所有请求均要求 Cookie 登录；不接受指定其他评分用户的 ID，始终按当前用户档案评分。

| 参数 | 规则 |
| --- | --- |
| `category` | 可选，预设方向之一 |
| `q` | 最多 100 字，仅搜索公开昵称、方向、标签；`C++` 需 URL 编码为 `C%2B%2B` |
| `period` | 可选，morning=00–12，daytime=12–18，evening=18–24；按区间相交判断 |
| `day` | 可选，1–7，可独立或结合时间筛选 |
| `start/end` | 可选，必须成对提供，end 大于 start；不能与 period 同用 |
| `overlapOnly` | 默认 false；true 时仅保留与当前用户实际重合分钟大于 0 的用户 |
| `page/pageSize` | 默认 1/12；page 为 1–10000，pageSize 为 1–50 |

响应 `data` 示例：

```json
{
  "items": [{
    "id": "public-user-uuid",
    "name": "一起学 C++",
    "avatar": "一",
    "categories": ["编程开发"],
    "tags": ["C++"],
    "styles": ["共同讨论"],
    "stage": "强化",
    "timezone": "Asia/Shanghai",
    "timeSlots": [{"day": 1, "start": "19:30", "end": "22:30"}],
    "score": 94,
    "dimensions": {"goal": 100, "time": 83, "method": 100, "level": 100},
    "overlapMinutes": 150,
    "reasons": ["共同方向：编程开发", "目标标签契合：c++", "每周可共同学习 150 分钟", "都偏好共同讨论", "同处强化阶段"],
    "caveats": []
  }],
  "total": 1,
  "page": 1,
  "pageSize": 12,
  "timezone": "Asia/Shanghai",
  "algorithmVersion": "weighted-v1"
}
```

候选必须主动开启匹配、账号 active 且未禁用、时区受支持，并排除本人。排序按总分降序、同分 UUID 升序；先对所有符合筛选的候选评分排序，再分页，total 是筛选后总数。越界页返回空 items。接口不缓存推荐，用户修改或关闭匹配后下次请求立即使用数据库现状。

目标来源仅为主动填写的匹配方向和标签，不读取私人目标或打卡。所有推荐字段由白名单构造，不能返回邮箱、学校、专业、简介、密码、Cookie、在线状态或打卡统计。算法细节见 [matching-algorithm.md](matching-algorithm.md)。本阶段候选全量评分，适用于早期用户规模；规模增长后再增加索引预筛和候选预算。

## 8. 真实搭子邀请与关系（已实现）

以下接口全部要求 Cookie 登录。分页均默认 page=1/pageSize=12，上限 10000/50；返回 `{items,total,page,pageSize}`。私有资源和错误操作角色统一 404，身份仅来自 Cookie，不接受 senderId/userId 注入。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/buddy-requests` | 发送邀请，新建 201、同方向待处理重试 200 |
| GET | `/buddy-requests` | 本人收件箱或发件箱，额外返回 pendingCount |
| GET | `/buddy-requests/{id}` | 仅参与者可读的单条邀请 |
| POST | `/buddy-requests/{id}/accept` | 仅接收者接受 |
| POST | `/buddy-requests/{id}/reject` | 仅接收者拒绝 |
| POST | `/buddy-requests/{id}/cancel` | 仅发送者取消待处理申请 |
| GET | `/buddies` | 本人的有效搭子关系与对方匹配档案 |
| DELETE | `/buddies/{relationId}` | 任一参与者解除关系，204，重复解除幂等 |

POST 请求：

```json
{"recipientId":"user-uuid","message":"周一一起学习 C++ 吧"}
```

留言去首尾空白，最长 200 字，可空；禁止邀请自己（422），目标不存在、被禁用、未公开或未开启接收邀请时返回 404 `BUDDY_UNAVAILABLE`。已是搭子返回 409 `ALREADY_BUDDIES`；对方已发 pending 邀请时返回 409 `INCOMING_REQUEST_EXISTS`。同方向重复发起返回原 pending 记录，不更新其留言、时间或重复通知。

列表参数：`direction=incoming|outgoing`（默认 incoming）、可选 `status=pending|accepted|rejected|cancelled`。每条记录：

```json
{
  "id":"request-uuid","senderId":"a-uuid","recipientId":"b-uuid",
  "direction":"outgoing","status":"pending","message":"一起学习",
  "createdAt":"2026-11-13T08:00:00+00:00","updatedAt":"2026-11-13T08:00:00+00:00","resolvedAt":null,
  "peer":{"id":"b-uuid","name":"学习伙伴","avatar":"学","categories":["编程开发"],"tags":["C++"],"styles":["共同讨论"],"stage":"强化","timezone":"Asia/Shanghai","timeSlots":[{"day":1,"start":"19:00","end":"22:00"}],"allowInvites":true,"profileVisible":true},
  "connection":{"status":"outgoing_pending","requestId":"request-uuid"}
}
```

`peer` 使用白名单，不返回邮箱、学校、专业、简介、密码、私人目标或打卡。发出邀请意味着向接收者分享匹配档案；pending 期间、有效关系期间可看对应匹配字段。终态历史没有有效关系且对方未公开时，peer.profileVisible=false，方向/标签/方式/时段置空，只保留最小昵称信息。

`GET /buddies` 每条为 `{id,createdAt,peer}`，id 是关系 ID，不是对方用户 ID。解除关系软结束历史，双方私有学习数据不变。重新建立关系需要新邀请，旧 accepted 请求在其原关系结束后再次 accept 返回 409，不能复活关系。

同一终态重试 accept/reject/cancel 是幂等；试图把终态变成另一终态返回 409 `BUDDY_REQUEST_CLOSED`。接受时通知、状态、关系同事务提交，重复并发不会创建第二条关系或通知。处理已有邀请不要求接收开关仍开启，但禁用发送者不能被接受。

发送按数据库持久记录限流：滚动小时 10、24 小时 30、当前 pending 20，同一对用户冷却期默认 300 秒。超过配额返回 429 `BUDDY_INVITE_RATE_LIMITED`，冷却中返回 429 `BUDDY_PAIR_COOLDOWN`。取消或拒绝不会抹掉发送次数；重复 pending 请求不额外消耗配额。

推荐响应在原有字段上新增：

```json
{
  "allowInvites":true,
  "connection":{"status":"none"}
}
```

connection.status 为 none/outgoing_pending/incoming_pending/connected；pending 时附 requestId，connected 时附 relationId。元数据只描述当前登录用户与该候选的关系，不泄露其他人之间的邀请。原匹配公式和排序保持不变。

## 9. 站内通知（已实现）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/notifications` | 本人的通知分页，可用 unreadOnly=true，额外返回全局 unreadCount |
| GET | `/notifications/unread-count` | 当前用户轻量未读数量，不读取列表或他人资料 |
| PATCH | `/notifications/{id}/read` | 仅通知接收者标记已读，重复操作保持第一次 readAt |
| PATCH | `/notifications/read-all` | 原子标记当前用户当时可见的未读通知，返回updatedCount/unreadCount |

每条通知包含 `id/kind/title/actor/requestId/relationId/groupId/groupRequestId/groupEventId/groupName/href/createdAt/readAt`。不相关的关联字段为null；actor仅含公开ID和当前昵称，groupName为公开小组名称。不返回event_key、接收者账号资料、邮箱、学校、私人目标/打卡或邀请留言。

八种kind与接收者：

| kind | 接收者与来源 |
| --- | --- |
| buddy_request_received | 接收邀请者；buddy_requests |
| buddy_request_accepted / buddy_request_rejected | 原发送者；buddy_requests，接受另关联buddy_relations |
| buddy_relation_removed | 另一位搭子；buddy_relations |
| group_join_requested | 当前组长；group_join_requests |
| group_join_approved / group_join_rejected | 申请者；group_join_requests |
| group_member_removed | 被移除者；持久group_member_events，并关联group |

业务变更与通知同事务，通知失败则一起回滚。事件键唯一约束和业务锁保证重复点击/并发只创建一条；没有客户端创建通知的API。直接加入与主动退出不生成本表未要求的提醒。取消/处理/解散会标记相关申请提醒已读；转让组长时给新组长交接pending提醒，旧组长提醒已读，若曾经接收过同一申请则复用原通知重新提示，不新增重复行。

href仅为站内业务路径：搭子→`/buddies?tab=incoming|outgoing|mine`，小组→`/groups/{id}`，加入申请→`/groups/{id}?tab=requests`；移除或已解散→`/groups`。访问仍由目标API按当前身份重新授权，通知不是访问凭证。

GET列表默认page=1/pageSize=12、最多50；未读统计始终针对本人全部通知，不限当前页/筛选。read-all不更改已读时间、不影响别人，也不把随后新到达的通知自动设为已读；与业务审批无关。401未登录、404他人/不存在通知、422分页/布尔参数非法。

顶部铃铛和独立`/notifications`中心在所有业务页可用；搭子页复用同一列表组件。仅布局启动一个60秒轮询，页面隐藏或离线时跳过，恢复时刷新；内存store合并并发请求、5秒抑制重复计数查询，列表结果更新计数。账号切换或已读更新后，较早响应不能覆盖新状态；不写LocalStorage。无WebSocket、邮件或短信。

## 10. 真实学习小组（第五阶段已实现）

以下路径均在 `/api/v1` 下，必须登录；修改操作沿用 Cookie 与 Origin/CSRF 防护。后端从会话读取当前用户，不接受 `userId/ownerId` 指定操作身份。

| 方法 | 路径 | 参数与权限 |
| --- | --- | --- |
| GET | `/groups` | 公开发现摘要；q 搜索名称/简介、category 预设方向、mine=false、page=1、pageSize=12（最多50） |
| POST | `/groups` | 创建，201；创建者与 owner 成员同事务入库 |
| GET | `/groups/{id}/preview` | 已登录即可查看的公开摘要，不含公告或成员资料 |
| GET | `/groups/{id}` | 仅本组成员：摘要、announcement、statistics、goal、myJoinedAt |
| PUT | `/groups/{id}` | 仅组长；完整更新，与创建使用同一 payload |
| DELETE | `/groups/{id}` | 仅组长明确解散，204；软归档、取消 pending、撤回成员分享，保留个人打卡 |
| POST | `/groups/{id}/join` | 无 body；直接加入或保存审核申请；重复点击返回原结果，不新增成员/申请 |
| GET | `/groups/{id}/join-requests` | 组长查看；status 默认 pending，可用 approved/rejected/cancelled；同样分页 |
| POST | `/groups/{id}/join-requests/{requestId}/approve` | 仅组长；检查容量，审批与成员创建同事务 |
| POST | `/groups/{id}/join-requests/{requestId}/reject` | 仅组长拒绝 |
| POST | `/groups/{id}/join-requests/{requestId}/cancel` | 仅申请者取消自己的 pending |
| GET | `/groups/{id}/members` | 仅成员；公开昵称、头像首字、角色、加入时间、isMe，不含邮箱和真实身份 |
| POST | `/groups/{id}/leave` | 普通成员退出，204；组长返回409，需先转让或解散 |
| DELETE | `/groups/{id}/members/{userId}` | 仅组长移除普通成员，204；不能移除组长 |
| POST | `/groups/{id}/transfer` | 仅组长，`{"newOwnerId":"现有成员UUID"}`；原组长降为成员 |
| PUT | `/groups/{id}/goal` | 仅组长设置或替换本组当前共同目标 |
| GET | `/groups/{id}/checkins` | 仅成员，分页获取主动分享的记录，默认12条、最多50 |
| GET | `/groups/{id}/rankings` | 仅成员，period=day/week/month/days；含零记录成员 |
| GET | `/checkins/{checkinId}/group-shares` | 仅个人打卡所有者查看自己的分享范围 |
| PUT | `/checkins/{checkinId}/groups/{groupId}` | 仅打卡所有者且为组员；显式分享或调整正文授权 |
| DELETE | `/checkins/{checkinId}/groups/{groupId}` | 同上，撤回分享，204；不删除原打卡 |

### 10.1 请求示例

创建或更新小组（未知字段拒绝，422）：

```json
{"name":"C++ 晚间自习室","category":"编程开发","description":"每晚一起学习与复盘","tags":["C++"],"maxMembers":30,"requiresApproval":true,"announcement":"仅成员可见的约定"}
```

name 2–50 字，description 1–500 字，maxMembers 严格整数 2–200；标签最多10项，每项1–32字；announcement 最多500字。同一组长的有效小组名称唯一，避免重复提交创建；不同组长可使用相同名称。缩小容量不能低于当前成员数。转让时新组长已有同名有效小组将返回409，需先改名。

加入响应 `data`：`{"state":"pending","requestId":"UUID"}` 或 `{"state":"joined","requestId":null}`。新请求/成员201，幂等重复200。申请状态 pending→approved/rejected/cancelled；终态不能反向修改。重复 approve 只在对应原成员关系仍存在时幂等，退出后不能用旧批准记录重新加入。

共同目标请求：

```json
{"title":"本周每人 C++ 至少10小时","startDate":"2026-11-09","endDate":"2026-11-15","targetMinutes":600}
```

周期含首尾，1–366天，targetMinutes 为正整数且不能超过周期天数×1440。返回 id、上述字段、myMinutes、myDays、progress（0–100）、updatedAt；只返回当前查看者进度，不泄露其他成员的私人记录。

分享请求：`{"shareContent":false}`。默认 false，只公开昵称、日期与时长。true 额外授权本条学习正文；不公开 mood、goalId、邮箱、学校等。幂等更新不重复记录或累计时长，保留首次 sharedAt。

### 10.2 安全响应与统计口径

`GET /groups` 返回 `data={items,total,joinedTotal,page,pageSize}`；summary 只有 id、name、category、description、tags、memberCount、maxMembers、requiresApproval、ownerName、myRole、isJoined、本人 joinRequest(id/status)、createdAt。所有有效小组的此摘要可供发现；本阶段没有完全隐藏/邀请码小组。

成员详情的 statistics 包含 todayMembers、totalMinutes、weekMinutes、weekMembers、weekStart/weekEnd、weekDays（date/minutes/memberCount/recordCount）、asOfDate、timezone。小组内容为成员私有，不是个人所有者私有；退出/移除立即失去后续 API 访问权限。

动态 items 每项只含 checkinId、date、duration、content（未授权为 null）、shareContent、sharedAt 和 user(id/name/avatar)。仅查询当前有效组员主动分享、打卡日期不早于本次入组当地日期且不晚于今天的记录；入组当日可分享当天早些时间的学习。每人每天向同一组分享最多1440分钟。个人多条记录仍保留，一条记录可独立授权多个组。

排行返回 `data={items,period,startDate,endDate,asOfDate,timezone}`；items 含 rank、userId、name、avatar、role、minutes、days、records、isMe。北京时间 Asia/Shanghai（UTC+8）：day 当天、week 周一至周日、month 自然月、days 建组至今。时长榜按 minutes 降序、days 降序、UUID升序；天数榜按 days 降序、minutes 降序、UUID升序，天数使用 DISTINCT 学习日期。范围含首尾，未来日期不计入；无分享成员显示0。累计统计和目标也只计本组被授权的有效分享，撤回/退出/移除/删除原打卡后立即重算。

主要错误：401 未登录；404 不存在/非成员/他人打卡或申请；403 GROUP_OWNER_REQUIRED；409 GROUP_FULL、GROUP_NAME_EXISTS、OWNER_MUST_TRANSFER、JOIN_REQUEST_CLOSED、GROUP_DAILY_DURATION_EXCEEDED；422 字段或日期范围不合法。组长操作、成员变更及分享按同一 group 行锁串行，接受与建成员在同一事务，数据库唯一约束和复合外键兜底。

## 11. 待实现 API

以下仍是设计契约，本次不伪装为已完成：

- 组内独立任务、隐藏/邀请码小组和举报/审核。
- 密码找回、邮箱验证、全设备退出、账号注销。
- 统计聚合、目标/打卡列表分页、通用幂等键、审计日志；打卡提醒及实时聊天。
