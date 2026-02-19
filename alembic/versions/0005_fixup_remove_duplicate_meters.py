"""fix-up migration template to remove duplicate meters (if any)

CAUTION: This is a template intended for manual review and testing on a copy
of your production DB before applying to production. By default it will NOT
execute the deduplication logic unless `RUN_DEDUPE = True` is set here.

Usage:
- Set `RUN_DEDUPE = True` only after you have tested the SQL on a copy of the
  production DB and confirmed the intended rows will be removed.
- Prefer running the dedupe SQL manually on a DB copy and keep the migration as
  an audited record of the change.

Revision ID and down_revision must be adjusted if your migrations differ.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0005_fixup_remove_duplicate_meters"
down_revision = "0004_add_meter_unique"
branch_labels = None
depends_on = None

# Safety flag — do NOT enable by default.
RUN_DEDUPE = False


def upgrade() -> None:
    """Remove duplicate `meter` rows keeping the row with the smallest id.

    The SQL below removes any rows in `meter` where another row exists with
    the same (unit_id, kind, slot) and a smaller id. This is a destructive
    operation — test thoroughly on a copy of production before enabling.
    """
    if not RUN_DEDUPE:
        # Avoid calling into engine internals during automated runs — just skip.
        print("Fix-up migration skipped because RUN_DEDUPE=False")
        return

    # The following DELETE is intentionally simple and compatible with SQLite
    # and PostgreSQL. It deletes rows whose id is NOT the minimum id for the
    # (unit_id, kind, slot) group.
    op.execute("""
        DELETE FROM meter
        WHERE id NOT IN (
            SELECT MIN(id) FROM meter GROUP BY unit_id, kind, slot
        )
        """)


def downgrade() -> None:
    # Downgrade is not implemented because deleting rows is destructive.
    # If you need to reverse, restore from backup.
    pass
