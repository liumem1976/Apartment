审查摘要：Task B — 域模型改进（`task-b-domain-models`）

变更概览：
- 修复 `assert_no_lease_overlap` 的边界行为，补充并通过多项边界测试（`tests/test_lease_overlap_extra.py`）。
- 在 `Meter` 模型上新增表级唯一约束 `uq_meter_unit_kind_slot`（`unit_id, kind, slot`），并通过 Alembic 新增索引/约束迁移 `alembic/versions/0004_add_meter_unique.py`。

关键文件：
- 模型：`app/models/domain.py`（包含 `UniqueConstraint("unit_id", "kind", "slot", name="uq_meter_unit_kind_slot")`）
- 迁移：`alembic/versions/0004_add_meter_unique.py`（创建索引 `uq_meter_unit_kind_slot`）
- 测试：`tests/test_lease_overlap_extra.py`（新增多项边界测试）

本地验证（已执行）：
- `pytest` -> 20 passed, 2 warnings（本地测试通过）。
- `alembic upgrade head` -> 本地开发 DB 迁移成功。
- 重复性检查：`python scripts/check_duplicate_meters.py ./data/app.db` -> `NO_DUPLICATES`（本地 DB）。
- GitHub Actions（PR #4 相关运行） -> 最近 workflow 运行状态为 `success`（多次成功）。

风险与注意点：
- 生产 DB 情况未知（你已指示跳过生产检查）。在生产环境应用迁移前，若将来有生产副本，务必先运行 `scripts/check_duplicate_meters.py <path_to_prod_db>`，并准备好数据清理的 fix-up migration（若发现重复）。
- 迁移涉及唯一约束，若生产存在重复会导致迁移失败。务必备份并在维护窗口执行。

建议审查点：
- 请检查 `assert_no_lease_overlap` 的逻辑是否满足所有业务场景（包含开始/结束相等、开放结束日期等）。
- 确认 `Meter` 的 `kind` 与 `slot` 在业务上确实应该与 `unit_id` 一起唯一（防止误判会影响旧数据）。
- CI 运行日志：请在 PR 的 Actions 页面查看完整 workflow 日志（目前最近一次已成功）。

下一步（待你确认）：
- 我已准备好将 PR 从 draft 标记为 ready（请求你确认后我会执行）。
- 如果需要，我可以把 PR 指定给某些审阅者或团队。