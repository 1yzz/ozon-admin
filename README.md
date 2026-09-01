# Ozon 卖家后台

FBS 单店本地后台：商品管理、一键复刊、只读订单（含取消原因）、只读仓库。

后端 FastAPI + `ozonapi-async` + SQLite，前端 React / TypeScript。虚拟环境用 **uv**。

## 启动

```bash
# 后端
cd backend
uv sync
# 在 .env 或设置页填写 Client-Id；Api-Key 可先写在 .env
# 本机需有 Redis：127.0.0.1:6379
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 前端
cd frontend
npm install
npm run dev
```

打开 http://localhost:5173

翻译、同步、复制、复刊走本地 Redis 队列（默认 `redis://127.0.0.1:6379/0`）。后端启动时会嵌入 worker；也可单独跑：

```bash
cd backend
uv run python -m app.worker
```

Ozon 鉴权需要 **Client-Id + Api-Key**。只有密钥不够，请到卖家后台「设置 → API 密钥」把数字 Client-Id 填进设置页。

## 注意

- `.env` 和 SQLite 不会提交到 git
- 聊天里发过的 Api-Key 建议在卖家后台轮换
- 复刊会新建卡片或恢复归档，不能撤销平台举报
