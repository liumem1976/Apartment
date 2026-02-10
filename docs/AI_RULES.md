AI 行为规范手册（专供 GitHub Copilot 使用）
从现在起，你（Copilot）在本仓库内进行的一切任务必须严格遵守以下规则。
这份手册是本项目的最高级别规范。

⚡ 【0. 总原则】


你必须自动读取并遵守：
docs/PROJECT_CONTEXT.md
和
docs/AI_RULES.md（即本手册）


你的所有行为必须符合：

本项目技术边界
业务规则
模型约束
输出格式规则（七段式）
安全红线
不引入不允许的框架（例如 SQLAlchemy Mapped 等）


你不得停下来等待可避免的用户确认。
若遇到确定性的问题（例如 forward ref 注解、lint 修复、测试失败），你必须自动修复。


用户是编程小白，任何需要技术判断的步骤，默认你代劳。



⚡ 【1. 自动加载项目上下文】
每次新对话，你必须自动执行：
读取 docs/PROJECT_CONTEXT.md，恢复整个项目上下文。

如果用户未说，你也必须主动提醒用户输入该指令。

⚡ 【2. 七段式输出规则（必须遵守）】
只要用户输入：
开始 任务 X

你必须输出以下七段结构：

任务假设与范围
设计与决策
代码与文件结构（列出修改文件和内容）
测试与验证（pytest 计划）
运行与维护
安全与一致性清单
后续迭代建议

不得省略、不得缩写。

⚡ 【3. 自动进行的行为（无需用户确认）】
以下操作不需要用户允许，你必须自动执行：
✔ 自动修复 forward reference
例如：
List[Community] → List["Community"]
Optional[Tenant] → Optional["Tenant"]

任何解析错误时，全部自动修复。

✔ 自动修复 lint（ruff / black / isort / flake8）
你必须自动：

运行 ruff check --fix
运行 isort
运行 black
修复未使用导入
修复重复定义
修复弱命名变量
修复模块级 import 位置
修复所有可自动修复项

你不得询问用户：“是否修复？”

✔ 自动运行 pytest 并修复失败
你必须自动：

重跑错误的测试
读取错误栈
自动定位受影响文件
自动生成 patch
再运行测试验证

不得要求用户“是否继续”。

✔ 自动提交、推送（若仓库可用）
只要：

所有测试通过
所有 lint 通过

你必须自动执行：
git add -A
git commit -m "<合适的信息>"
git push

但遇到 push 权限问题需提示用户。

✔ 自动更新 TODO
你必须维护你的 TODO 列表，不需要用户管理。

⚡ 【4. 不得再问用户的问题类型】
以下类型的问题禁止再询问：

“是否继续任务？”
“是否要应用最小变更？”
“我是否修复 lint？”
“是否运行测试？”
“是否修复 forward ref 注解？”
“是否提交？”
“是否推送？”
“是否继续 patch？”
“是否修复导入问题？”
“我是否应该继续根据 TODO 工作？”

这些必须 自动处理。

⚡ 【5. 你需要用户确认的唯一情况】
只有以下三种情况需要用户确认：
① 需要 GitHub 授权（push / PR / CI）
例如：

token 无效
push 被拒绝
PR 需要浏览器授权

这属于平台限制，必须请用户授权。

② 危险操作：rebase、force push、删除历史
必须提醒用户：
此操作可能不可逆，请确认。


③ 用户主动要求“非最小变更”
例如：
把 models.py 全部重构
把数据库迁移全部重写
加新框架

这类需要用户“明确发起”。

⚡ 【6. 禁止事项】

禁止私自更换框架
禁止引入 SQLAlchemy Mapped、DeclarativeBase
禁止在无必要时重构大量文件
禁止更改数据库结构（除非任务明确需要）
禁止删除用户代码
禁止擅自引入云服务


⚡ 【7. 持续任务行为】
你必须持续执行以下行为，无需用户重复：

跟踪 TODO
下一个任务自动接上
重跑 lint
重跑 pytest
自动提交
保持项目始终可运行


⚡ 【8. 用户输入分类规则】（你必须识别）

若用户说“继续” → 继续 TODO
若用户说“开始 任务 X” → 七段式输出
若用户说“修复” → 立刻执行 lint + pytest + patch
若用户说“生成文件” → 自动创建并提交
若用户说“出错了” → 自动重跑 pytest 并修复

⚡ 【9. 对编程小白的特别支持】
你必须默认：

用户不会 git
用户不会 pytest
用户不会看日志
用户不会看回溯
用户不会自己改代码
用户不会配置 Python 环境

因此你必须代劳所有技术性决策。

⚡ 【10. Pull Request 规范与合并检查清单（必须遵守）

本项目所有 PR 必须包含以下检查项，并由 AI 在创建 PR 时自动写入描述中：

一、模型（SQLModel）与数据一致性
 所有新增/修改字段已包含在 Alembic 迁移中
 未使用任何运行时 ALTER TABLE
 所有关系字段使用字符串前向引用（如 List["Community"]）
 未使用 SQLAlchemy 2.0 Mapped 或 DeclarativeBase
 模型字段符合 Decimal(18,4)、外键、非空约束等规则
二、迁移（Alembic）
 已生成对应的 migration 文件（如 000X_xxx.py）
 upgrade/downgrade 脚本完整且可执行
 含义清晰、无数据破坏风险
 迁移版本连续、无冲突
三、业务逻辑
 账单状态机逻辑符合：draft → submitted → approved → issued → void
 月度账单计算符合自然月规则，不按天拆账
 Import（rooms/leases）支持严格校验、全批次回滚、错误清单输出
 后台批处理（ImportBatch）逻辑正常
 所有受 RBAC 控制的接口已正确加权限装饰
四、测试（pytest）
 pytest 全部通过（0 failed）
 新增逻辑已添加单元测试
 无 skip 关键用例
 无临时日志/临时文件进入仓库
五、格式化与静态检查
 通过 ruff 检查
 通过 black 格式化检查
 通过 flake8 质量检查
 通过 isort 导入排序检查
 无未使用 import、无重复定义、无模糊变量名
六、Git 质量
 PR 不包含无关 diff
 .venv、data/*.db 等不应被跟踪
 commit message 清晰规范
 PR 描述完整并包含此 checklist
七、部署/运行环境（LAN）
 SQLite WAL 模式正常
 alembic upgrade head 可正常执行
 无硬编码路径
 .env 结构正确
 BackgroundTasks 可安全运行