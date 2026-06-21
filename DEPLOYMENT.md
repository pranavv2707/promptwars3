# DEPLOYMENT GUIDE - Karbon.io

## Pre-Deployment Checklist

- [ ] All tests pass (`pytest` in backend/)
- [ ] Security fixes applied (CORS, XSS, input validation)
- [ ] Environment variables configured (.env files)
- [ ] Firebase credentials secure (never commit keys)
- [ ] HTTPS enabled on production
- [ ] Rate limiting configured
- [ ] Monitoring/logging enabled

## Environment Setup

### Backend (.env)

```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your values:
FIREBASE_CREDENTIALS_PATH=/secure/path/firebase-key.json
GEMINI_API_KEY=your_key
GOOGLE_MAPS_API_KEY=your_key
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### Frontend (.env.local)

```bash
cp .env.example .env.local
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_ENVIRONMENT=production
```

## Building for Production

### Backend

```bash
cd backend
python -m pip install -r requirements.txt
python -m pytest  # Run all tests
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend

```bash
npm install
npm run build
# Output: dist/
# Deploy dist/ to CDN or static hosting
```

## Docker Deployment (Recommended)

### Backend Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Security Hardening

1. **HTTPS Only**: Redirect all HTTP to HTTPS
2. **Security Headers**: Add to server config
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `Strict-Transport-Security: max-age=31536000`

3. **API Rate Limiting**: Use Redis + redis-rate-limiter in FastAPI

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

4. **CORS**: Keep origins restrictive

5. **Authentication**: Implement JWT for production

## Monitoring & Logging

- **Backend**: Use Sentry for error tracking
- **Frontend**: Use Datadog or CloudWatch
- **Logs**: Stream to ELK or CloudWatch

## Deployment Targets

### AWS
- **Frontend**: S3 + CloudFront
- **Backend**: ECS + ALB or Lambda
- **Database**: Firestore (managed)

### Heroku
```bash
heroku create karbon-app
heroku config:set FIREBASE_CREDENTIALS_PATH=/app/firebase-key.json
git push heroku main
```

### Vercel (Frontend only)
```bash
npm install -g vercel
vercel
```

## Post-Deployment

1. Run smoke tests
2. Monitor error rates
3. Test critical user flows
4. Verify API connectivity
5. Check performance metrics

## Rollback

If issues detected:
```bash
# Revert to previous deployment
heroku releases:rollback
# Or redeploy from git
git push heroku [previous_commit]:main
```
