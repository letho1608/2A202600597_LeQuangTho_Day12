# Deployment Information

## Public URL
```
https://awake-wholeness-production-46aa.up.railway.app
```

## Platform
Railway / Render

## Test Commands

### Health Check
```bash
curl https://awake-wholeness-production-46aa.up.railway.app/health
# Expected: {"status":"ok","version":"1.0.0","environment":"production",...}
```

### Authentication Required (should return 401)
```bash
curl -X POST https://awake-wholeness-production-46aa.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
# Expected: 401 Unauthorized
```

### API Test (with authentication)
```bash
curl -X POST https://awake-wholeness-production-46aa.up.railway.app/ask \
  -H "X-API-Key: my-secret-key-prod" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"What is Docker?"}'
# Expected: 200 OK with question, answer, model, timestamp
```

### Rate Limiting Test
```bash
for i in {1..15}; do
  curl -X POST https://awake-wholeness-production-46aa.up.railway.app/ask \
    -H "X-API-Key: my-secret-key-prod" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":\"test\",\"question\":\"Request $i\"}"
  echo "---"
done
# Expected: Request 11+ should return 429 Too Many Requests
```

## Environment Variables Set

| Variable | Value | Secret? |
|----------|-------|---------|
| PORT | (auto-injected) | No |
| ENVIRONMENT | production | No |
| APP_VERSION | 1.0.0 | No |
| LOG_LEVEL | INFO | No |
| AGENT_API_KEY | (set manually) | Yes |
| JWT_SECRET | (generated) | Yes |
| REDIS_URL | (from Redis add-on) | Yes |
| DAILY_BUDGET_USD | 10.0 | No |
| RATE_LIMIT_PER_MINUTE | 10 | No |

## Screenshots

- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)

## Local Development

```bash
# Clone repo
git clone https://github.com/your-username/day12-agent-deployment.git
cd day12-agent-deployment

# Set up environment
cp .env.example .env
# Edit .env with your config

# Run locally
pip install -r requirements.txt
python -m app.main

# Or with Docker
docker compose up
```
