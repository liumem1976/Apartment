# LAN 公寓收费系统 — 项目骨架

按照 `.vscode/settings.json` 的要求启动的最小骨架。

快速开始

1. 创建虚拟环境并安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. 启动服务：

```powershell
set "DATABASE_URL=sqlite:///./data/app.db"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

说明

- 数据库文件位于 `./data/app.db`，首次启动会创建表（WAL 已启用）。
- 下一步：实现认证、RBAC、中间件、账单生成 API、导入功能、Alembic 迁移脚本与前端模板。
