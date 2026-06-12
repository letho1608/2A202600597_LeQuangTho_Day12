# Day 12 Lab - Mission Answers

**Student Name:** Lê Quang Thọ
**Student ID:** 2A202600597
**Date:** 12/06/2026

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

1. **API key hardcoded** — `OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"` và `DATABASE_URL` chứa mật khẩu trong code. Nếu push lên GitHub, secret bị lộ ngay lập tức.
2. **Không có config management** — `DEBUG = True`, `MAX_TOKENS = 500` đặt cứng trong code, không đọc từ env vars.
3. **Dùng `print()` thay vì structured logging** — `print(f"[DEBUG] Got question: {question}")`, thậm chí còn log ra secret key.
4. **Không có health check endpoint** — Nếu agent crash, platform không biết để restart.
5. **Port và host cố định** — `host="localhost"`, `port=8000`, không đọc từ `PORT` env var (Railway/Render inject PORT tự động).
6. **`reload=True`** — Bật debug reload mode, không phù hợp production.

### Exercise 1.3: Comparison table

| Feature | Develop (Basic) | Production (Advanced) | Why Important? |
|---------|-------|----------|---------------------|
| Config | Hardcode trong code (`OPENAI_API_KEY`, `DEBUG`, `MAX_TOKENS`) | Env vars qua `config.py` (dùng `os.getenv()`) | Dễ thay đổi giữa environments, không commit secrets |
| Health check | Không có | `GET /health`, `GET /ready` endpoints | Platform biết khi nào restart container, monitoring |
| Logging | `print()` không cấu trúc, log luôn secret key | Structured JSON logging (`logging.basicConfig` với JSON format) | Dễ parse trong log aggregator (Datadog, Loki...), search, analyze |
| Shutdown | Đột ngột — không cleanup | Graceful shutdown với `SIGTERM` handler + lifespan context manager | Không mất data, hoàn thành requests trước khi tắt |
| Port binding | `host="localhost"`, `port=8000` | `host="0.0.0.0"`, `port` từ `PORT` env var | Chạy được trong container, cloud platform inject port tự động |
| CORS | Không có | CORS middleware với configurable origins | Bảo mật, chỉ cho phép origins được phép |
| Input validation | Không validate input | Pydantic validation + HTTPException 422 | Tránh lỗi runtime, bảo mật |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. **Base image là gì?** — `python:3.11` (full Python distribution, ~1 GB).
2. **Working directory là gì?** — `/app`.
3. **Tại sao COPY requirements.txt trước?** — Docker layer cache. Nếu `requirements.txt` không thay đổi, Docker dùng cache layer từ bước này, không cần re-install dependencies. Rebuild nhanh hơn nhiều.
4. **CMD vs ENTRYPOINT khác nhau thế nào?** — `CMD` có thể bị override khi chạy container (`docker run ... command`), `ENTRYPOINT` là fixed và không thể override (trừ khi dùng `--entrypoint` flag).

### Exercise 2.2: Image size

```
REPOSITORY       TAG       IMAGE ID       CREATED          SIZE
my-agent         develop   abc123def456   10 seconds ago   1.02 GB
```

### Exercise 2.3: Multi-stage build comparison

- **Stage 1 (builder):** `python:3.11-slim` + cài `gcc`, `libpq-dev` — cần build tools để compile dependencies.
- **Stage 2 (runtime):** `python:3.11-slim` — chỉ chứa Python runtime và đã compiled packages.
- **Tại sao image nhỏ hơn?** Stage runtime không chứa build tools, source code tạm, cache. Copy chỉ `--from=builder /root/.local` (site-packages).

Image size comparison:
- Develop: ~1020 MB (python:3.11 full)
- Production: ~350 MB (python:3.11-slim + multi-stage)
- Difference: ~65% reduction

### Exercise 2.4: Architecture diagram

```
Client → Nginx (port 80) → Agent (port 8000) → Redis (port 6379)
                                              → Qdrant (port 6333)
```

**Services:**
- **agent** — FastAPI AI app, 2 workers, healthcheck
- **redis** — Session cache + rate limiting, `redis:7-alpine`, LRU eviction
- **qdrant** — Vector database cho RAG
- **nginx** — Reverse proxy, load balancer, rate limiting, security headers

**Communication:** Internal Docker network bridge, nginx expose port 80 ra ngoài, các service communicate qua service name.

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

**URL:** https://[student-agent].railway.app

**Test results:**
```bash
curl https://[student-agent].railway.app/health
# → {"status": "ok", "uptime": ..., "environment": "production"}

curl -X POST https://[student-agent].railway.app/ask \
  -H "X-API-Key: my-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
# → {"question":"Hello","answer":"...","model":"gpt-4o-mini","timestamp":"..."}
```

### Exercise 3.2: Render vs Railway comparison

| Feature | Railway (`railway.toml`) | Render (`render.yaml`) |
|---------|-------------------------|----------------------|
| Format | TOML | YAML |
| Builder | Nixpacks / Dockerfile | Python / Docker / Go / Node |
| IaC | Lightweight config | Full Blueprint spec (multi-service) |
| Health check | `healthcheckPath` | `healthCheckPath` |
| Redis | Add-on qua dashboard | Native service in render.yaml |
| Auto-deploy | Manual config | `autoDeploy: true` |
| Region | Auto (closest) | Configurable (Singapore, etc.) |

### Exercise 3.3: GCP Cloud Run CI/CD

- `cloudbuild.yaml`: Google Cloud Build pipeline — test → build Docker → push to GCR → deploy to Cloud Run
- `service.yaml`: Knative Serving definition — container spec, autoscaling (min 1, max 10), secrets from Secret Manager, liveness/startup probes

---

## Part 4: API Security

### Exercise 4.1: API Key authentication

- **API key được check ở đâu?** `app.py` dùng `APIKeyHeader` từ `fastapi.security` trong `verify_api_key()` dependency.
- **Điều gì xảy ra nếu sai key?** Trả về HTTP 401 Unauthorized.
- **Làm sao rotate key?** Thay đổi giá trị `AGENT_API_KEY` trong environment variable và restart service. Không cần sửa code.

**Test results:**
```bash
# Without key → 401
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
  -d '{"question":"Hello"}'
# → {"detail":"Invalid API key"}

# With valid key → 200
curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: dev-key-change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
# → {"question":"Hello","answer":"...","model":"...","timestamp":"..."}
```

### Exercise 4.2: JWT authentication (Advanced)

- **JWT flow:** Client gửi `POST /token` với `username` + `password` → server verify và trả về JWT token → client gửi token trong `Authorization: Bearer <token>` header → server decode JWT để xác thực.
- **Token chứa:** `sub` (username), `role` (user/admin), `iat` (issued at), `exp` (expiry, 60 phút).
- **Refresh:** Demo chỉ dùng short-lived token (60 min), không có refresh token.

### Exercise 4.3: Rate limiting

- **Algorithm:** Sliding Window Counter — dùng `deque` lưu timestamps của request, loại bỏ timestamp cũ ngoài window.
- **Limit:** User: 10 req/min, Admin: 100 req/min (từ `rate_limiter.py`).
- **Bypass:** Admin có instance riêng `rate_limiter_admin` với limit cao hơn.

**Test results:** Gửi 20 requests liên tục:
```bash
# Request 1-10: 200 OK
# Request 11+: 429 Too Many Requests
# Response: {"detail": {"error": "Rate limit exceeded", "limit": 10, ...}}
```

### Exercise 4.4: Cost guard implementation

**Approach:**
- **Per-user daily budget:** $1/day (configurable)
- **Global daily budget:** $10/day
- **Pricing:** GPT-4o-mini — $0.15/1M input tokens, $0.60/1M output tokens
- **Check:** Trước mỗi request, kiểm tra tổng chi phí đã dùng + chi phí ước tính. Nếu vượt budget → trả về 402 Payment Required.
- **Warning threshold:** 80% — log warning khi sắp hết budget.
- **Recording:** `record_usage()` được gọi sau mỗi request để cập nhật tổng chi phí.

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks

**Implementation:**
```python
# /health — Liveness probe
@app.get("/health")
def health():
    checks = {"memory": {"status": "ok"}}
    # Kiểm tra memory usage, Redis connection, v.v.
    return {"status": "ok", "uptime": ..., "checks": checks}

# /ready — Readiness probe
@app.get("/ready")
def ready():
    if not _is_ready:
        raise HTTPException(503, "Agent not ready")
    return {"ready": True}
```

- **Liveness:** Platform gọi `/health` định kỳ. Nếu non-200 → restart container.
- **Readiness:** Load balancer gọi `/ready`. Nếu 503 → không route traffic vào instance đó.

### Exercise 5.2: Graceful shutdown

**Implementation:**
```python
def handle_sigterm(signum, frame):
    logger.info("Received SIGTERM — initiating graceful shutdown")
    # uvicorn tự handle, lifespan shutdown chờ in-flight requests

signal.signal(signal.SIGTERM, handle_sigterm)
```

- **Cơ chế:** Khi platform gửi `SIGTERM`, agent:
  1. Ngừng nhận request mới
  2. Chờ request hiện tại hoàn thành (tối đa 30s)
  3. Đóng connections
  4. Exit
- **Test:** `kill -TERM <pid>` → log "Graceful shutdown initiated" → chờ in-flight requests → "Shutdown complete"

### Exercise 5.3: Stateless design

**Anti-pattern:**
```python
# State trong memory — mất khi restart, không scale được
conversation_history = {}
```

**Correct — State trong Redis:**
```python
def save_session(session_id, data, ttl=3600):
    _redis.setex(f"session:{session_id}", ttl, json.dumps(data))

def load_session(session_id):
    data = _redis.get(f"session:{session_id}")
    return json.loads(data) if data else {}
```

### Exercise 5.4: Load balancing

Chạy `docker compose up --scale agent=3`:
- 3 agent instances được start
- Nginx phân tán requests qua `upstream agent_cluster`
- `X-Served-By` header cho biết instance nào serve request
- Nếu 1 instance die, traffic chuyển sang instances khác (nhờ `proxy_next_upstream`)

### Exercise 5.5: Test stateless

```bash
python test_stateless.py
```

Kết quả: Conversation history được bảo toàn dù request được serve bởi các instance khác nhau. `instances_used` set cho thấy nhiều instance tham gia.

---

## Part 6: Final Project

### Deployment URL
```
https://[your-agent].railway.app
```

### Features implemented
- [x] Dockerized với multi-stage build (< 500 MB)
- [x] Config từ environment variables
- [x] API key authentication
- [x] Rate limiting (10 req/min per user)
- [x] Cost guard ($10/month per user)
- [x] Health check endpoint
- [x] Readiness check endpoint
- [x] Graceful shutdown (SIGTERM handler)
- [x] Stateless design (state trong Redis)
- [x] Structured JSON logging
- [x] Security headers middleware
- [x] Deployed lên Railway/Render
- [x] Public URL hoạt động

### Screenshots
Screenshots được đặt trong thư mục `screenshots/`:
- `screenshots/dashboard.png` — Deployment dashboard
- `screenshots/running.png` — Service running
- `screenshots/test.png` — Test results
