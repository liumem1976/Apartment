PRODUCTION 迁移步骤（生产就绪）

说明：本文件以可执行、最小化风险的步骤描述如何在生产环境中应用 Alembic 迁移、校验数据一致性与回滚策略。请在执行前把本文件作为运行清单（checklist）逐项核对。

1. 准备与前置条件
- 计划维护窗口并通知相关方（预估 15–60 分钟，视迁移复杂度）
- 确认拥有数据库管理员权限和服务器 SSH/控制台访问
- 确认当前应用版本已被标记（git tag / release）并备份当前运行配置
- 确认 `alembic.ini` 和 `DATABASE_URL` 指向正确的生产实例

2. 备份（强制执行）
- PostgreSQL（推荐）

```bash
PGPASSWORD=yourpwd pg_dump -Fc -h <host> -U <user> -d <db> -f backup-$(date +%Y%m%d%H%M).dump
```

- SQLite（局域网部署情形）

```powershell
Stop-Process -Name YourAppProcessName -ErrorAction SilentlyContinue
Copy-Item .\path\to\production.db .\backups\production.db.$((Get-Date).ToString('yyyyMMddHHmmss'))
```

- 备份校验：
  - PostgreSQL: `pg_restore --list backup.dump` 能列出条目
  - SQLite: `PRAGMA integrity_check;` 在恢复后运行

3. 将应用置于维护模式
- 停止或将流量引导到备用实例；确保没有并发写操作（尽量在低峰期操作）

4. 预验证（在生产 DB 上执行，只读）
- 唯一性/去重检查（示例查询）：

```sql
-- 检查 meter 唯一列（例如 meter_id 或 serial）
SELECT COUNT(*) AS total, COUNT(DISTINCT meter_serial) AS unique FROM meters;

-- 若 total != unique，请在迁移前解决重复数据
```

- 用户与角色完整性检查（示例）：

```sql
-- 确保至少有 1 个管理员
SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1;

-- 检查重复用户名/邮箱
SELECT email, COUNT(*) FROM users GROUP BY email HAVING COUNT(*) > 1;
```

- 记录 `alembic current` 与当前 schema 版本（以便核对）：

```bash
alembic -c alembic.ini current
```

5. 应用迁移（推荐在一台受控跳板机上运行）
- 设置环境变量并在受控会话下运行（示例：Linux/Bash）：

```bash
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
alembic -c alembic.ini upgrade head
```

- Windows PowerShell 示例：

```powershell
$env:DATABASE_URL = 'sqlite:///C:/path/production.db'  # 或指向 PostgreSQL
alembic -c alembic.ini upgrade head
```

- 注意：若使用 SQLite 并发写锁风险高，请确保应用已停止且文件备份完成。

6. 每个迁移阶段的回滚策略
- 通用原则：
  - 优先考虑从备份恢复（最安全、最可靠），特别是当迁移包含不可逆的数据迁移或删除时
  - 若迁移是可逆的并且在 Alembic 中明确实现 downgrade，则可使用 `alembic downgrade <rev>` 回退

- 示例命令：

```bash
# 回退到上一个迁移（仅当 downgrade 可用时）
alembic -c alembic.ini downgrade -1

# 或回退到指定修订
alembic -c alembic.ini downgrade <revision_id>
```

- SQLite 特例回滚：
  - SQLite 的某些 DDL 无法在事务中回滚；因此对 SQLite 的回滚策略以“替换备份文件”为主：

```powershell
Stop-Process -Name YourAppProcessName -ErrorAction SilentlyContinue
Copy-Item .\backups\production.db.YYYYMMDDHHMMSS .\path\to\production.db -Force
# 重启应用并验证
```

- 若迁移失败且无法 downgrade：
  - 立即恢复备份文件或使用 `pg_restore` 恢复 PostgreSQL
  - 将故障原因写入事件日志并通知运维与开发

7. 迁移后的验证步骤（强制执行）
- 检查 Alembic 版本：

```bash
alembic -c alembic.ini current
```

- 数据一致性快速检查：执行在“预验证”中列出的核心 SELECT 语句确认计数/唯一性无异常
- 健康检查：调用应用健康端点（示例）：

```bash
curl -fS --retry 3 https://your.app/health || echo 'HEALTH CHECK FAILED'
```

- 登录/登出（会话、RBAC）验证：
  - 使用一个已知的管理员账号执行登录（或发起一个仿真请求），确认成功并能访问受限接口（例如 `/dashboard`）
  - 使用普通账号测试受限接口应返回 403/401

- 事务/应用功能抽样测试：
  - 执行 5–10 条写操作（若可在维护窗口内）并验证回写一致性

8. 监控与回归观察期
- 将应用移出维护模式并逐步恢复流量
- 打开 30–60 分钟的回归观察期，关注错误率、响应时间与数据库连接数

9. SQLite（局域网部署）特别说明
- SQLite 适合轻量或单节点部署，但存在限制：
  - 文件级锁定会影响并发写入性能
  - 某些 DDL 在 SQLite 上不可回滚或行为与 Postgres 不同
  - 不建议在有大量并发写入或多实例读取的生产环境长期使用

- 建议：
  - 若继续使用 SQLite：确保定期文件备份、限制并发写入、并把 DB 文件放在稳定的网络文件系统（注意锁问题）
  - 更好做法是尽快切换到 PostgreSQL 或其它服务器型 DB

10. 从 SQLite 迁移到 PostgreSQL 的指南要点
- 准备 PostgreSQL 实例并创建目标库与角色
- 导出数据（可选工具：`pgloader`、`csv` 导出/导入）：

```bash
# 使用 sqlite3 导出为 CSV（每个表）
sqlite3 production.db \
  -header -csv "select * from users;" > users.csv

# 通过 psql 导入（示例）
psql postgresql://user:pass@host:5432/dbname -c "\copy users FROM 'users.csv' CSV HEADER"
```

- 在 PostgreSQL 上运行 `alembic -c alembic.ini upgrade head`（`DATABASE_URL` 指向 PostgreSQL）以施加 schema 与约束
- 逐表校验行数与关键约束（外键、唯一索引）是否匹配

11. 回归记录与审计
- 在迁移完成后，把以下信息归档到变更记录：
  - 迁移执行人、开始/结束时间、备份文件名与位置
  - `alembic current` 输出与 `alembic history --verbose` 的相关段落
  - 任意手动修复脚本与数据修改记录

12. 快速故障处理清单（紧急恢复）
- 如果严重故障且无法快速修复：
  1. 将服务下线（防止更多写入）
  2. 从最近备份恢复数据库（Postgres 用 `pg_restore`，SQLite 直接替换文件）
  3. 回退应用至上一个已知良好版本（git checkout + 重启）
  4. 组织事后复盘，评估迁移脚本与数据约束问题

附录：常用命令速查

```bash
# 查看当前 alembic 版本
alembic -c alembic.ini current

# 应用所有迁移
alembic -c alembic.ini upgrade head

# 回退一步（仅当 downgrade 可用）
alembic -c alembic.ini downgrade -1

# PostgreSQL 备份
pg_dump -Fc -h <host> -U <user> -d <db> -f backup.dump

# SQLite 备份（PowerShell）
Copy-Item .\path\to\production.db .\backups\production.db.YYYYMMDDHHMMSS
```

结束语：务必把“备份并验证备份”视为不可选步骤；对于任何包含数据迁移或删除的 Alembic 脚本，优先准备可以快速恢复的备份与回滚路径。
生产迁移步骤（Task B: meter 唯一索引迁移）

目的
- 在生产环境安全地应用 `alembic` 迁移以添加 `meter(unit_id, kind, slot)` 的唯一约束。

前提（强制）
- 在生产环境执行迁移前，必须有最近的数据库备份且已验证可以恢复。
- 如果有生产数据库副本，请先在副本上运行重复检测脚本：

  ```bash
  python scripts/check_duplicate_meters.py /path/to/prod_db
  ```

  若输出 `NO_DUPLICATES` 则可继续；若返回重复记录（或其他输出），请不要直接执行迁移，先走数据清理流程（见下方 fix-up migration）。

步骤（概览）
1. 选择维护窗口并通知相关人员（开发/运维/产品）。
2. 备份数据库并把备份存放到安全位置（示例命令）：

   - SQLite：
     ```bash
     cp /path/to/prod_db /path/to/backup/prod_db_$(date +%F_%T).db
     ```

   - PostgreSQL：
     ```bash
     pg_dump -Fc -h <host> -U <user> -f prod_db_$(date +%F_%T).dump <dbname>
     ```

3. 在备份/副本上运行重复检测：

   ```bash
   python scripts/check_duplicate_meters.py /path/to/prod_db
   ```

   - 若输出 `NO_DUPLICATES`：继续下一步。
   - 若发现重复：不要执行迁移。请参考 `alembic/versions/0005_fixup_remove_duplicate_meters.py`（模板）来清理重复数据，测试并在副本上运行，确认无误后再返回本步骤。

4. 将服务切换到只读/维护模式（根据实际应用）。

5. 在生产环境（或运维主机）运行 Alembic 迁移：

   ```bash
   alembic upgrade head
   ```

6. 验证迁移：
   - 检查 `meter` 表上是否存在索引/约束 `uq_meter_unit_kind_slot`。
   - 运行应用端常见读取/写入场景（或 smoke tests）。

7. 恢复服务并监控错误/日志 15-60 分钟，确认没有异常。

回滚（若需要）
- 如果迁移导致问题并必须回退，使用 alembic 回退（注意：如果迁移已删除或更改了数据，回滚可能不会恢复数据到原始状态）：

  ```bash
  alembic downgrade -1
  ```

- 若发生数据丢失，请从备份恢复（恢复步骤与数据库类型相关，谨慎操作）。

补充说明
- 迁移会添加唯一约束；若存在重复数据，迁移会失败并回报错误。请务必按照上文先检测并清理重复。 
- `scripts/check_duplicate_meters.py` 是用于检测重复的脚本。若你需要，我可以把脚本输出示例和在生产上运行的安全校验命令扩展成一份运维手册。

联系/审计
- 执行迁移的人员：
  - 开发负责人：@your-dev
  - 运维负责人：@your-ops
- 审计日志：保留备份与操作步骤记录以便复核。

---
（此文档由自动化助手生成为操作参考，请在执行前与团队确认并按公司变更管理流程批准。）