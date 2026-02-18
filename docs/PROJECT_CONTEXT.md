PROJECT_CONTEXT.md
LAN 公寓收费系统（多公司/多小区/合同周期计费）AI 驱动开发 — 项目上下文总说明
0. 文件作用（极重要）
本文件用于在 任何新的 AI 会话中恢复完整项目上下文。
每次开始新会话，请先输入：

请读取 docs/PROJECT_CONTEXT.md，并根据此恢复全部上下文。

AI 将自动理解：

项目背景
技术栈
业务需求
安全约束
开发流程
当前进度
下一步任务

你无需重复任何说明。

1. 项目简介
本系统为：

本地局域网运行的公寓收费系统
不依赖外网、需在本地服务器/Windows 运行
主要用户：管理员 / 财务 / 销售（或 clerk）
管理多公司、多小区、多房间、多租约
支持水表抄表（2 冷 + 2 热）、账单生成、审核、导入、报表、审计追踪
使用 AI 驱动开发方式（任务化推动 + PR + CI）

系统特点：

合同起始日定义计费周期（非自然月）
不按天拆账，采用负项调整（Adjustment）
审计日志覆盖关键变动
Excel 导入支持严格校验与整批回滚
报表支持 xlsx/csv 导出


2. 技术栈与技术边界
（来自你上传的提示词） [提示词-英文 | Txt]

Python 3.11.x
FastAPI
SQLModel（基于 SQLAlchemy）
Pydantic v2
SQLite（WAL 模式，短事务）
Alembic（迁移）
Jinja2
HTMX
TailwindCSS
APScheduler（周期任务）
本地局域网部署，10 并发以内
Locale: Asia/Shanghai, zh-CN, CNY
Decimal：存储 18,4，展示两位
RBAC（admin / finance / clerk）
审计日志
严格 CORS
禁止外部云服务
依赖文件：requirements.txt / requirements‑dev.txt / requirements‑lock.txt（已建立）


3. 业务需求（摘要）
（来自你上传的提示词） [提示词-中文ASC版 | Txt]

多公司、多社区、多楼栋、多单元、多房间
水费：每房 2 冷 2 热
租金、押金、宽带、保洁、维修等
电费模型预留（暂不启用）
计费周期基于租约 start_date 自动推算
不按天拆账 → 调整使用负项 BillLine
账单生成方式：单房 / 批量
流程：clerk 提交 → 财务审核 → 出具（冻结关键字段）
报表：周期总览、欠费、房间历史等
导入：rooms.csv & leases.csv（幂等、校验、整批回滚）


4. 领域模型（摘要）
（来自提示词） [提示词-英文 | Txt]

Company, Community, Building, Unit
Tenant, Lease（含租金/押金/起止日期）
Meter（cold/hot, slot 1/2）
MeterReading（period, reading, read_at）
TariffWater（可按公司/小区覆盖）
ChargeItem（rent/deposit/cleaning/repair/broadband/water/other）
Bill（cycle_start, cycle_end, state=draft→submitted→approved→issued→void）
BillLine（qty, unit_price, amount，可负值）
Adjustment
User（role）
AuditLog（before/after/actor/ip/trace_id）
AppConfig
预留：电费模型 MeterElec / TariffElec


5. 模型约束（摘要）
（来自提示词） [提示词-中文ASC版 | Txt]

Lease 不可重叠
MeterReading 唯一 (meter_id + period)
Bill 唯一 (unit_id + cycle_start)
Meter 唯一 (unit_id + kind + slot)
计量必须递增（错误通过 Adjustment 修正）
Decimal(18,4)
SQLite 仅允许命名参数
导入失败必须整批回滚


6. AI 输出格式要求（严格遵守）
当你在 VS Code 对 GitHub AI 输入“开始 任务 X”时，它必须按以下格式输出： [提示词-中文ASC版 | Txt]

《任务假设与范围》
《设计与决策》
《代码与文件结构》
《测试与验证》
《运行与维护》
《安全与一致性清单》
《后续迭代建议》

所有输出必须符合此结构。

7. 开发工作流（AI 驱动方式）
✔ 采用 Git Flow + PR 模式

所有代码均由 GitHub AI 生成
每次改动走 PR → CI → Merge
你只需审核 PR 描述是否合理（AI 会写）
CI 自动跑：pytest、ruff、flake8、isort、black —check

✔ 已启用的 CI 项目

.github/workflows/ci.yml（已生成）
包含：

pip install
pytest
ruff
flake8
isort
black —check
PR 模板检查（AI 已启用）



✔ 已启用的 Git 辅助文件

CONTRIBUTING.md（已自动生成）
CODEOWNERS（占位符版，尚未绑定真实用户）
PULL_REQUEST_TEMPLATE.md（已建立）
.gitignore（已清理并生效）


8. 当前开发状态（来自你整个会话过程）
这一部分是你最关心的，因为将用于恢复当前进度。
✔ Git / GitHub 部分

当前分支：squash-by-module
本地提交已推送到远端
.gitignore 已清理并从 Git 跟踪中移除 .venv/, .logs/, *.db
分支已准备创建 PR（AI 将负责）

✔ 文件 & 配置状态

requirements.txt → 已建立
requirements-dev.txt → 已建立
requirements-lock.txt → 已建立
CI workflow → 已建立
PR 模板 → 已建立
CODEOWNERS → 仅占位，未绑定
CONTRIBUTING.md → 已生成
pytest 测试可运行（8 passed, warnings 可忽略）

✔ AI 的下一步将做什么？
根据你的会话进度：

下一步是：创建 PR → 触发 CI → 等待 CI 结果。

你只需要让 AI 执行这一步。

9. 下一阶段路线图（建议顺序）


Task A
项目骨架、基础目录、启动脚本（你已完成）


Task B
SQLModel 数据建模 + Alembic 迁移


Task C
鉴权 + RBAC + Cookie 登录


Task D
房间/租约 CRUD 页面


Task E
2 冷/2 热水表抄表 + 校验规则


Task F
账单生成（自然周期、冻结策略、负项调整）


Task G
审核流 + 审计日志


Task H
Excel 导入 rooms.csv / leases.csv


Task I
报表模块（欠费、周期、房间历史）


Task J
备份脚本（SQLite WAL + APScheduler）


Task K
性能优化 & 安全回归



10. 新会话的使用方法（最关键）
每次你开启一个新会话，只需：
第 1 句（恢复项目上下文）

请读取 docs/PROJECT_CONTEXT.md 并恢复上下文。

第 2 句（继续开发）
例如：

“继续创建 PR”
“开始 任务 B”
“继续开发账单模块”
“修复 CI 错误”

AI 就能完全接上你当前的工程进度。