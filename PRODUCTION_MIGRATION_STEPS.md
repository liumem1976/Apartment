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