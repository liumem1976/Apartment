## Task B — 数据建模计划

目标：完成并稳定项目的领域模型（Company、Community、Building、Unit、Lease、Meter、Reading、Bill、BillLine 等），确保模型与 Alembic 迁移一致、通过格式化与测试，并准备下一步业务实现。

步骤：
1. 审查 `app/models/domain.py`，列出缺失或不一致字段。
2. 为每个变更编写最小化的 SQLModel 模型更新（使用字符串前向引用），避免引入 SQLAlchemy Mapped/DeclarativeBase。
3. 为每个模型变更生成 Alembic migration（例如 `000X_add_xxx.py`）。
4. 在本地运行 `pytest` 与 `ruff/isort/black`，修复失败并提交。
5. 推送分支并通过 CI 验证（GitHub Actions 已配置）。

验收条件：
- `pytest` 全部通过（0 failed）
- `ruff`/`isort`/`black` 在 CI 通过
- 所有新增/修改字段有对应 Alembic migration
- 未在运行时做 ALTER 操作（所有 schema 变更由 Alembic 管理）

短期计划（下 3 步，我将自动执行）：
- 1) 在 `app/models/domain.py` 中扫描并报告不一致字段（自动收集）。
- 2) 生成一个小的移植性修复补丁（如果发现缺失字段，例如 `Unit.remark`），并将其放入新 migration（若已有 migration，跳过）。
- 3) 运行 `pytest` 验证现状，提交并推送任何修复。

注意：本地自动格式化/修复在当前环境中偶发被 Alembic 导入副作用中断；已将格式检查加入 CI，必要时会在隔离环境中完成自动修复并提交。
