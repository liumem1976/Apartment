## 变更说明

- 增加依赖：`python-jose`，以修复测试导入 `from jose import ...` 的缺失模块错误。
- 修复测试：移除 `tests/test_imports.py` 顶部未使用的导入。

## 测试

- 本地测试: `pytest` 通过

详细说明：已在 CI 中触发新运行以验证更改。