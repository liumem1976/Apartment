# CHANGELOG

## v0.0.1-migration-20260219 — 2026-02-19

- 添加：生产迁移文档 `PRODUCTION_MIGRATION_STEPS.md`（仓库根目录），包含：备份步骤、预验证 SQL、应用 Alembic 迁移、回滚策略与迁移后验证要点。
- 功能：添加基于 cookie 的 HTML 登录/登出和仪表盘（见已合并 PR #6）。
- 数据库：新增 Alembic 迁移以支持 `user.is_active` 字段，并改进测试数据库初始化策略（在 CI/测试中通过运行 Alembic migrations 确保确定性）。
- 测试：新增针对 cookie 会话与 RBAC 的集成测试并修复测试中先前的命名冲突问题。

详细说明与迁移指南请参见：`PRODUCTION_MIGRATION_STEPS.md`（仓库根目录）或 Release：https://github.com/liumem1976/Apartment/releases/tag/v0.0.1-migration-20260219

---

（注）后续建议：优先在非高峰维护窗口执行迁移，生产环境若仍在使用 SQLite 请优先评估迁移到 PostgreSQL 的计划。有关从 SQLite 迁移到 PostgreSQL 的步骤已在迁移文档中列出。
