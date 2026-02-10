from sqlmodel import Session, select

from app.db import engine
from app.models import ImportBatch

with Session(engine) as s:
    rows = s.exec(select(ImportBatch).order_by(ImportBatch.id.desc())).all()
    print("total", len(rows))
    for r in rows[:10]:
        print("ID", r.id, "status", r.status)
        print("result:", r.result)
        print("errors:", r.errors)
        print("---")
