## 简要说明

- 增加依赖：`python-jose[cryptography]`，以修复测试与运行时对 `jose` 的依赖并确保加密支持。
- 修复测试：移除 `tests/test_imports.py` 中未使用的导入，解决 ruff 报错。

## 测试

- 已在本地运行 `pytest` 并通过（在提交前确认）。

## 本地运行 pytest 并通过

- 本次改动为最小修复，主要修改依赖与测试导入，CI 将验证其余用例。