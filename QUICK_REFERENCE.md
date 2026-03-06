# 🚀 SkillLedger Quick Reference

## Local Development

### Start Everything (Docker)
```bash
chmod +x setup.sh
./setup.sh
```

### Manual Start
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 10000
```

### Stop Everything
```bash
docker-compose down
```

## API Endpoints

### Base URL
- Local: `http://localhost:10000`
- Production: `https://skilledger-licenses-api.onrender.com`

### Authentication
All endpoints require API key in header:
```bash
-H "X-API-Key: sk_live_YOUR_KEY_HERE"
```

### Quick Test (No Auth)
```bash
curl http://localhost:10000/api/demo/verify?license_number=123456&state=AZ
```

## Core Endpoints

### 1. Verify Single License
```bash
curl -X POST "http://localhost:10000/api/verify/license" \
  -H "X-API-Key: sk_test_demo_key_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "license_number": "123456",
    "state_code": "AZ",
    "license_type": "RN"
  }'
```

### 2. Multi-State Search
```bash
curl -X POST "http://localhost:10000/api/verify/multi-state-search" \
  -H "X-API-Key: sk_test_demo_key_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Jane",
    "last_name": "Doe",
    "states": ["AZ", "CA", "TX"]
  }'
```

### 3. Subscribe to Monitoring
```bash
curl -X POST "http://localhost:10000/api/monitor/subscribe" \
  -H "X-API-Key: sk_test_demo_key_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "license_id": 1,
    "alert_at_days": [90, 60, 30, 7],
    "email": "recruiter@example.com"
  }'
```

### 4. Get Monitored Licenses
```bash
curl "http://localhost:10000/api/monitor/my-monitors" \
  -H "X-API-Key: sk_test_demo_key_12345"
```

### 5. Upload Bulk CSV
```bash
curl -X POST "http://localhost:10000/api/bulk/upload" \
  -H "X-API-Key: sk_test_demo_key_12345" \
  -F "file=@licenses.csv"
```

### 6. Compliance Dashboard
```bash
curl "http://localhost:10000/api/audit/compliance-dashboard" \
  -H "X-API-Key: sk_test_demo_key_12345"
```

## Database

### Connect to Local Database
```bash
docker-compose exec db psql -U skilledger -d skilledger_licenses
```

### Connect to Render Database
```bash
psql [paste connection string from Render dashboard]
```

### Create API Key Manually
```sql
-- Get user ID
SELECT id FROM users WHERE email = 'your@email.com';

-- Create API key
INSERT INTO api_keys (user_id, key, name, is_active, created_at)
VALUES (1, 'sk_live_YOUR_RANDOM_KEY', 'Production Key', true, NOW());
```

## Common Tasks

### View Logs (Docker)
```bash
docker-compose logs -f api
```

### View Logs (Render)
Dashboard → Your Service → Logs tab

### Restart Service (Docker)
```bash
docker-compose restart api
```

### Restart Service (Render)
Dashboard → Your Service → Manual Deploy → "Clear build cache & deploy"

### Check Health
```bash
curl http://localhost:10000/health
```

### Run Database Migrations
```bash
python -c "from app.database import init_db; init_db()"
```

## Sample CSV for Bulk Upload

Create `licenses.csv`:
```csv
license_number,state,candidate_name
123456,AZ,Jane Doe
789012,CA,John Smith
345678,TX,Mary Johnson
```

Upload:
```bash
curl -X POST "http://localhost:10000/api/bulk/upload" \
  -H "X-API-Key: sk_test_demo_key_12345" \
  -F "file=@licenses.csv"
```

## Environment Variables

### Required
```bash
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here
```

### Optional
```bash
NURSYS_API_KEY=your-nursys-key
SENDGRID_API_KEY=your-sendgrid-key
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
```

## Troubleshooting

### "Database connection failed"
- Check DATABASE_URL format
- Verify database is running: `docker-compose ps`
- Test connection: `docker-compose exec db pg_isready`

### "API key invalid"
- Check X-API-Key header is present
- Verify key exists in database
- Ensure key is active and not expired

### "Import errors"
- Install dependencies: `pip install -r requirements.txt`
- Check Python version: `python --version` (need 3.11+)

### "Port already in use"
- Change PORT in .env or docker-compose.yml
- Or stop conflicting service

## Performance

### Expected Response Times
- Single verification: 0.5-3 seconds
- Multi-state (5 states): 3-8 seconds
- Bulk (100 licenses): 2-3 minutes

### Rate Limits
- Default: 100 requests/minute per API key
- Upgrade plan for higher limits

## Security

### Generate Secret Key
```bash
openssl rand -hex 32
```

### Rotate API Keys
```sql
-- Deactivate old key
UPDATE api_keys SET is_active = false WHERE key = 'old_key';

-- Create new key
INSERT INTO api_keys (user_id, key, name, is_active)
VALUES (1, 'new_key', 'New Key', true);
```

## API Documentation

- Interactive Docs: http://localhost:10000/docs
- ReDoc: http://localhost:10000/redoc
- OpenAPI JSON: http://localhost:10000/openapi.json

## Support

- GitHub Issues: [your repo]/issues
- Email: support@skilledger.com
- Docs: https://docs.skilledger.com

## Quick Links

- Render Dashboard: https://dashboard.render.com
- API Docs: http://localhost:10000/docs
- Health Check: http://localhost:10000/health

---

**Pro Tip:** Bookmark this file for quick reference!
