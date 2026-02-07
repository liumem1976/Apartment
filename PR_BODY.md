## 简要说明

- 修复 CI 中 SQLite 数据库文件无法创建的问题，确保运行前创建 `data` 目录并将 `DATABASE_URL` 规范为仓库绝对路径。

## 测试

本地已运行 `pytest` 并通过