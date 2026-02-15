# PROJECT_CONTEXT.md
LAN 公寓收费系统（最终完整版）

本文件用于在任何新会话中恢复本项目完整上下文。请在新会话中输入：

**请读取 docs/PROJECT_CONTEXT.md 并恢复上下文。**

---
## 1. 项目简介
LAN 局域网收费系统，支持多公司、多小区、自然月计费...

## 2. 技术边界
Python 3.11.x, FastAPI, SQLModel, SQLite WAL, Alembic, Jinja2, HTMX, Tailwind...

## 3. 业务需求
- 多公司多小区
- 自然月计费
- 不按天拆账...

## 4. 领域模型
Company, Community, Building, Unit, Lease, Meter, Reading, Bill, BillLine...

## 5. 数据约束
- Bill 唯一键 (unit_id, period)
- Meter 唯一键 (unit_id, kind, slot)
- 租约不能重叠...

## 6. API 契约
- POST /api/v1/bills/generate
- POST /api/v1/bills/{id}/submit
...

## 7. 输出格式（七段式）
1) 任务假设与范围
2) 设计与决策
3) 代码与文件结构...

## 8. 当前进度（需人工维护）
- Task A 已完成
- 当前：进入 Task B（数据建模）
