# 🚀 Deploy to Render - Step-by-Step Guide

Complete guide to deploy SkillLedger License Verification System to Render.com

## Prerequisites

- GitHub account
- Render account (sign up at https://render.com - free tier available)
- This codebase pushed to a GitHub repository

## Deployment Steps

### Step 1: Push Code to GitHub

```bash
# Initialize git repository (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: SkillLedger License Verification System"

# Add your GitHub repository as remote
git remote add origin https://github.com/YOUR_USERNAME/skilledger-licenses.git

# Push to GitHub
git push -u origin main
```

### Step 2: Sign Up for Render

1. Go to https://render.com
2. Click "Get Started"
3. Sign up with GitHub (recommended for easy deployment)
4. Authorize Render to access your repositories

### Step 3: Create PostgreSQL Database

1. From Render Dashboard, click "New +" → "PostgreSQL"
2. Configure:
   - **Name**: `skilledger-licenses-db`
   - **Database**: `skilledger_licenses`
   - **User**: `skilledger` (auto-generated)
   - **Region**: Choose closest to your users (e.g., Ohio)
   - **PostgreSQL Version**: 15
   - **Plan**: 
     - Free (for testing - limited to 90 days, 256MB RAM)
     - Starter ($7/mo - recommended for production)
     - Standard ($20/mo - for higher traffic)

3. Click "Create Database"
4. Wait ~2-3 minutes for database to provision
5. **IMPORTANT**: Copy the "Internal Database URL" - you'll need this
   - Format: `postgresql://user:password@hostname:5432/database`
   - Find it in the database dashboard under "Connections"

### Step 4: Create Redis Instance

1. Click "New +" → "Redis"
2. Configure:
   - **Name**: `skilledger-licenses-redis`
   - **Region**: Same as your database (e.g., Ohio)
   - **Plan**:
     - Free (for testing - limited features)
     - Starter ($10/mo - recommended)
   - **Maxmemory Policy**: `allkeys-lru` (recommended for caching)

3. Click "Create Redis"
4. Wait ~1-2 minutes for Redis to provision
5. **Copy the Redis URL** from the dashboard

### Step 5: Deploy Web Service

1. Click "New +" → "Web Service"
2. Click "Build and deploy from a Git repository"
3. Connect your GitHub repository:
   - If first time: Click "Connect Account" → Authorize Render
   - Select your repository from the list
   - If you don't see it, click "Configure account" to grant access

4. Configure the web service:

   **Basic Settings:**
   - **Name**: `skilledger-licenses-api`
   - **Region**: Same as database/Redis (e.g., Ohio)
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Docker`
   - **Dockerfile Path**: `./Dockerfile`

   **Instance Settings:**
   - **Instance Type**: 
     - Free (for testing - limited, spins down after inactivity)
     - Starter ($7/mo - **recommended for production**)
     - Standard ($20/mo - for higher traffic)

5. Click "Advanced" to add environment variables

### Step 6: Configure Environment Variables

Add these environment variables (click "Add Environment Variable" for each):

**Required Variables:**

```
DATABASE_URL = [Paste Internal Database URL from Step 3]
REDIS_URL = [Paste Redis URL from Step 4]
SECRET_KEY = [Generate random string - see below]
ENVIRONMENT = production
DEBUG = false
PORT = 10000
HOST = 0.0.0.0
```

**How to generate SECRET_KEY:**
```bash
# On Mac/Linux:
openssl rand -hex 32

# Or use any random 64-character string
```

**Optional Variables** (add these for full functionality):

```
NURSYS_API_KEY = your_nursys_api_key_when_you_get_it
SENDGRID_API_KEY = your_sendgrid_api_key_for_emails
FROM_EMAIL = noreply@yourdomain.com
AWS_ACCESS_KEY_ID = your_aws_key_for_screenshots
AWS_SECRET_ACCESS_KEY = your_aws_secret
S3_BUCKET_NAME = your-s3-bucket-name
```

### Step 7: Set Build Command (Optional)

Render will auto-detect the Dockerfile, but if you need to customize:

- **Docker Command**: `docker build -f ./Dockerfile -t skilledger .`
- **Docker Context**: `./backend`

### Step 8: Deploy

1. Review all settings
2. Click "Create Web Service"
3. Watch the deployment logs in real-time

**First deployment takes 5-10 minutes:**
- Render pulls code from GitHub
- Builds Docker image
- Starts the container
- Runs health checks

**You'll see logs like:**
```
Building...
Successfully built docker image
Deploying...
Starting service with 'uvicorn app.main:app --host 0.0.0.0 --port 10000'
✓ SkillLedger Licenses started successfully
✓ Listening on 0.0.0.0:10000
Service is live at https://skilledger-licenses-api.onrender.com
```

### Step 9: Initialize Database

Your database needs tables. You have two options:

**Option A: Automatic (on first request)**
The app will create tables automatically when it starts.

**Option B: Manual (recommended)**

1. Go to your PostgreSQL database dashboard on Render
2. Click "Connect" → Copy the connection command
3. In your terminal:

```bash
# Connect to database
psql [paste connection string]

# Run this SQL to create initial data
INSERT INTO subscription_plans (name, price_monthly, max_verifications_per_month, includes_alerts, includes_api_access)
VALUES 
  ('Free', 0.00, 10, false, true),
  ('Professional', 15.00, 100, true, true),
  ('Recruiter', 199.00, NULL, true, true),
  ('Enterprise', 999.00, NULL, true, true);

-- Create demo user
INSERT INTO users (email, full_name, organization, is_active, created_at)
VALUES ('demo@skilledger.com', 'Demo User', 'SkillLedger', true, NOW())
RETURNING id;

-- Create demo API key (use the id from above)
INSERT INTO api_keys (user_id, key, name, is_active, created_at)
VALUES (1, 'sk_live_demo_key_12345', 'Demo Key', true, NOW());

-- Create demo subscription
INSERT INTO user_subscriptions (user_id, plan_id, status, current_period_start, current_period_end)
VALUES (1, 4, 'active', CURRENT_DATE, CURRENT_DATE + INTERVAL '365 days');
```

### Step 10: Test Your Deployment

**Your API is now live at:**
```
https://skilledger-licenses-api.onrender.com
```

**Test the health endpoint:**
```bash
curl https://skilledger-licenses-api.onrender.com/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "database": "connected",
  "cache": "connected",
  "timestamp": "2026-03-05T12:00:00.000000"
}
```

**View API documentation:**
```
https://skilledger-licenses-api.onrender.com/docs
```

**Test verification endpoint:**
```bash
curl -X POST "https://skilledger-licenses-api.onrender.com/api/demo/verify?license_number=123456&state=AZ"
```

### Step 11: Set Up Custom Domain (Optional)

1. In your web service dashboard, click "Settings"
2. Scroll to "Custom Domains"
3. Click "Add Custom Domain"
4. Enter your domain (e.g., `api.skilledger.com`)
5. Follow DNS configuration instructions
6. Render will automatically provision SSL certificate

## Post-Deployment Configuration

### Enable Auto-Deploy

1. Go to your web service settings
2. Under "Build & Deploy" → Enable "Auto-Deploy"
3. Now every push to `main` branch auto-deploys

### Set Up Health Check Monitoring

Render automatically monitors `/health` endpoint. You can customize:

1. Settings → Health Check Path: `/health`
2. Expected Status Code: `200`
3. Check Interval: `30 seconds`

### View Logs

Real-time logs: Dashboard → your service → Logs tab

### Monitor Performance

Render provides metrics:
- CPU usage
- Memory usage
- Request count
- Response times

## Troubleshooting

### Service Won't Start

**Check logs for errors:**
```
Logs tab → look for error messages
```

**Common issues:**
- Wrong DATABASE_URL format
- Missing required environment variables
- Port mismatch (ensure PORT=10000)

### Database Connection Failed

**Verify DATABASE_URL:**
```bash
# It should look like:
postgresql://user:password@dpg-xxxxx:5432/database

# NOT like:
postgres://... (wrong protocol)
```

**Fix:** Use the "Internal Database URL" from Render dashboard

### Health Check Failing

**Ensure:**
- App is listening on `0.0.0.0:10000`
- `/health` endpoint exists and returns 200

### Out of Memory

**Upgrade instance:**
- Free tier: 512MB RAM (very limited)
- Starter: 512MB RAM (better)
- Standard: 2GB RAM (recommended for production)

## Costs

**Estimated monthly cost:**

| Component | Plan | Cost |
|-----------|------|------|
| PostgreSQL | Starter | $7/mo |
| Redis | Starter | $10/mo |
| Web Service | Starter | $7/mo |
| **Total** | | **$24/mo** |

**Free tier available:**
- 750 hours/month free web service
- Free PostgreSQL for 90 days
- No credit card required to start

## Scaling

### Horizontal Scaling
Add more instances:
1. Dashboard → your service → "Scale"
2. Increase instance count
3. Render auto-load-balances

### Vertical Scaling
Upgrade instance type:
1. Settings → Instance Type
2. Choose larger instance
3. Click "Save Changes"

## Security

### Environment Variables
- Never commit `.env` files
- Rotate API keys regularly
- Use Render's encrypted environment variables

### HTTPS
- Automatically enabled by Render
- Free SSL certificates
- Auto-renewal

### Database Security
- Private network (not publicly accessible)
- Encrypted connections
- Regular backups

## Backups

**Database backups (automatic):**
- Starter plan: Daily backups, 7-day retention
- Pro plan: Daily backups, 30-day retention

**Manual backup:**
```bash
# Download database dump
pg_dump [connection_string] > backup.sql
```

## Next Steps

1. ✅ Set up custom domain
2. ✅ Configure monitoring alerts
3. ✅ Add real Nursys API key
4. ✅ Set up SendGrid for email alerts
5. ✅ Configure AWS S3 for screenshots
6. ✅ Set up Sentry for error tracking

## Support

- Render Docs: https://render.com/docs
- Render Community: https://community.render.com
- SkillLedger Support: support@skilledger.com

---

**Congratulations! Your SkillLedger API is now live in production! 🎉**
