import re
import sys
from pathlib import Path

p = Path("app/models/domain.py")
s = p.read_text(encoding="utf-8")

# collect class names defined as SQLModel, table=True
class_pattern = re.compile(r"class\s+(\w+)\s*\(([^)]*)\)\s*:", re.S)
classes = []
for m in class_pattern.finditer(s):
    name = m.group(1)
    params = m.group(2)
    if "SQLModel" in params:
        classes.append(name)
classes = set(classes)
class_table_names = {c: c.lower() for c in classes}

fk_pattern = re.compile(r'foreign_key\s*=\s*"([\w_]+)\.([\w_]+)"')

errors = []
for m in fk_pattern.finditer(s):
    left, right = m.group(1), m.group(2)
    # check if left matches any class table name
    if left not in class_table_names.values():
        # try to map to a class
        candidate = None
        # if left contains underscore, try to remove
        left_no_underscore = left.replace("_", "")
        for c, tbl in class_table_names.items():
            if tbl == left or tbl.replace("_", "") == left_no_underscore:
                candidate = (c, tbl)
                break
        if not candidate:
            errors.append((m.group(0), left, right))

if not errors:
    print("No foreign_key left-side mismatches found. Classes:", sorted(classes))
else:
    print("Found mismatches:")
    for raw, left, right in errors:
        print(raw, "left not matching any class tables")

# exit code

sys.exit(0 if not errors else 2)
