# AI Production Agent - Day 12 Final Project

Production-ready AI agent with authentication, rate limiting, cost guard, health checks, graceful shutdown, and Docker deployment.

## Features

| Feature | Status |
|---------|--------|
| Multi-stage Docker build (< 500 MB) | ✅ |
| Environment variable configuration | ✅ |
| API Key authentication | ✅ |
| Rate limiting (10 req/min) | ✅ |
| Cost guard ($10/month) | ✅ |
| Health check endpoint | ✅ |
| Readiness check endpoint | ✅ |
| Graceful shutdown | ✅ |
| Stateless design (Redis) | ✅ |
| Structured JSON logging | ✅ |
| Security headers | ✅ |
| Railway / Render deployment | ✅ |

## Quick Start

```bash
# Clone
git clone <your-repo-url>
cd my-production-agent

# Copy env
cp .env.example .env

# Run locally
pip install -r requirements.txt
python -m app.main

# Test
curl http://localhost:8000/health
curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: dev-key-change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
```

## Docker

```bash
# Build and run
docker compose up

# Test
curl http://localhost:8000/health
```

## Project Structure

```
my-production-agent/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # pydantic-settings config
│   ├── auth.py              # API Key authentication
│   ├── rate_limiter.py      # Sliding window rate limiter
│   └── cost_guard.py        # Monthly budget tracking
├── utils/
│   └── mock_llm.py          # Mock LLM (no API key needed)
├── Dockerfile               # Multi-stage build
├── docker-compose.yml       # Agent + Redis stack
├── requirements.txt         # Python dependencies
├── .env.example             # Environment template
├── .dockerignore            # Docker ignore rules
├── railway.toml             # Railway deployment config
├── render.yaml              # Render deployment config
├── MISSION_ANSWERS.md       # Lab exercise answers
└── DEPLOYMENT.md            # Deployment information
```
