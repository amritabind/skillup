# Deployment Guide for SkillUp

This guide covers deploying your FastAPI application on various cloud platforms using GitHub.

## Files Included

- `.github/workflows/python-app.yml` - GitHub Actions CI/CD pipeline
- `Dockerfile` - Container configuration for deployment
- `docker-compose.yml` - Local Docker testing
- `.dockerignore` - Files to exclude from Docker builds

---

## Option 1: Deploy to Render (Recommended - FREE tier available)

### Steps:

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Add deployment files"
   git push origin main
   ```

2. **Create Render Account**
   - Go to [render.com](https://render.com)
   - Sign up with GitHub (easier integration)

3. **Connect Repository**
   - Dashboard → New → Web Service
   - Connect your GitHub repo
   - Select repository and branch

4. **Configure Service**
   - **Name**: `skillup-api` (or your choice)
   - **Runtime**: `Docker`
   - **Build Command**: (leave default)
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

5. **Environment Variables**
   - Click "Advanced" → "Add Environment Variable"
   - Add: `GOOGLE_API_KEY` = your actual API key
   - Add: `PORT` = `8000`

6. **Deploy**
   - Click "Create Web Service"
   - Wait 5-10 minutes for deployment to complete
   - Your app will be live at: `https://skillup-api.onrender.com`

---

## Option 2: Deploy to Railway (FREE credits included)

### Steps:

1. **Create Railway Account**
   - Go to [railway.app](https://railway.app)
   - Sign up with GitHub

2. **Create New Project**
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository

3. **Add Service**
   - Rail will auto-detect Python
   - Set start command in `Procfile` (create this file):
     ```
     web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```

4. **Add Environment Variables**
   - Project settings → Variables
   - Add: `GOOGLE_API_KEY` = your API key

5. **Deploy**
   - Auto-deploys on main branch push
   - Access at provided Railway domain

---

## Option 3: Deploy to Heroku (deprecated Free tier, paid plans)

### Steps:

1. **Create Procfile**
   ```
   web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

2. **Create `runtime.txt`**
   ```
   python-3.11.0
   ```

3. **Heroku CLI Setup**
   ```bash
   npm install -g heroku
   heroku login
   heroku create your-app-name
   heroku config:set GOOGLE_API_KEY=your_actual_key
   git push heroku main
   ```

---

## Option 4: Deploy to Google Cloud Run (FREE tier - 2M requests/month)

### Steps:

1. **Install Google Cloud CLI**
   ```bash
   # Windows
   # Download from: https://cloud.google.com/sdk/docs/install
   ```

2. **Authenticate**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **Deploy**
   ```bash
   gcloud run deploy skillup-api \
     --source . \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars GOOGLE_API_KEY=your_actual_key
   ```

---

## Option 5: Deploy to Azure Container Instances

### Steps:

1. **Create Azure Container Registry**
   ```bash
   az acr create --resource-group myResourceGroup --name skillupregistry --sku Basic
   ```

2. **Push Image**
   ```bash
   docker build -t skillup-api .
   az acr build --registry skillupregistry --image skillup-api:latest .
   ```

3. **Deploy Container**
   ```bash
   az container create \
     --resource-group myResourceGroup \
     --name skillup-app \
     --image skillupregistry.azurecr.io/skillup-api:latest \
     --environment-variables GOOGLE_API_KEY=your_api_key \
     --ports 8000
   ```

---

## Local Docker Testing (Before Deployment)

Test your deployment locally first:

```bash
# Build Docker image
docker build -t skillup-api .

# Run with environment
docker run -e GOOGLE_API_KEY=your_actual_key -p 8000:8000 skillup-api

# OR use docker-compose
docker-compose up
```

Visit: `http://localhost:8000`

---

## GitHub Actions CI/CD

Your workflow file automatically:

✅ Runs on every push to `main` and `develop` branches  
✅ Tests against Python 3.9, 3.10, 3.11  
✅ Lints code with flake8  
✅ Caches dependencies for faster builds  

View results in: GitHub Actions tab → Workflow runs

---

## Environment Variables Setup

Before deployment, ensure `.env` file has:

```env
GOOGLE_API_KEY=your_actual_google_api_key_here
```

⚠️ **Never commit `.env` file to GitHub!** It's in `.gitignore`

---

## Troubleshooting

### Port Issues
- Change port in service configuration (default: 8000)
- Render/Railway auto-bind to platform port

### API Key Issues
- Verify `GOOGLE_API_KEY` environment variable is set
- Check Google Generative AI API is enabled in your project

### Build Failures
- Check GitHub Actions logs for errors
- Verify `requirements.txt` has all dependencies
- Ensure Python version compatibility (3.9+)

---

## Monitoring & Logs

**Render**: Dashboard → Logs  
**Railway**: Project page → Logs  
**Google Cloud Run**: Cloud Console → Cloud Run → Logs  
**Heroku**: `heroku logs --tail`

---

## Quick Start Summary

```bash
# 1. Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit with deployment files"
git remote add origin https://github.com/yourusername/jarvis.git
git push -u origin main

# 2. Choose platform and follow relevant section above

# 3. Your app is live! 🚀
```

---

Questions? Check the specific platform's documentation:
- [Render Docs](https://docs.render.com)
- [Railway Docs](https://docs.railway.app)
- [Google Cloud Run Docs](https://cloud.google.com/run/docs)
