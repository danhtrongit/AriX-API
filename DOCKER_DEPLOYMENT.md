# 🐳 Docker Deployment Guide - AriX API

## Quick Start with Docker

### 1. Clone Repository
```bash
git clone https://github.com/danhtrongit/AriX-API.git
cd AriX-API
```

### 2. Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your API keys
nano .env  # or use your preferred editor
```

**Required Environment Variables:**
```env
GEMINI_API_KEY=your_gemini_api_key_here
VNSTOCK_DEFAULT_SOURCE=VCI
FLASK_ENV=production
DEBUG=False
LOG_LEVEL=INFO
```

### 3. Build and Run with Docker Compose
```bash
# Build and start the container
docker-compose up --build -d

# Check logs
docker-compose logs -f arix-api

# Check status
docker-compose ps
```

### 4. Test the API
```bash
# Health check
curl http://localhost:5005/

# Test chat endpoint
curl -X POST http://localhost:5005/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Phân tích VCB hiện tại"}'
```

## Docker Commands

### Management Commands
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up --build -d

# View logs
docker-compose logs arix-api

# Follow logs in real-time
docker-compose logs -f arix-api

# Check container status
docker-compose ps

# Execute commands in container
docker-compose exec arix-api bash
```

### Production Deployment

#### Using Docker Build
```bash
# Build image
docker build -t arix-api:latest .

# Run container
docker run -d \
  --name arix-backend \
  -p 5005:5005 \
  --env-file .env \
  arix-api:latest
```

#### Health Monitoring
```bash
# Check container health
docker ps

# View container stats
docker stats arix-backend

# Check container logs
docker logs arix-backend -f
```

## Troubleshooting

### Common Issues

**1. Port already in use**
```bash
# Check what's using port 5005
lsof -i :5005

# Change port in docker-compose.yml
ports:
  - "5006:5005"  # Change external port
```

**2. Environment variables not loading**
```bash
# Verify .env file exists
ls -la .env

# Check env vars in container
docker-compose exec arix-api env | grep GEMINI
```

**3. API key issues**
```bash
# Check logs for API key errors
docker-compose logs arix-api | grep -i "api key\|gemini\|error"

# Verify env file format (no spaces around =)
GEMINI_API_KEY=your_key_here  # ✅ Correct
GEMINI_API_KEY = your_key_here  # ❌ Wrong
```

### Performance Optimization

**1. Resource Limits**
```yaml
# Add to docker-compose.yml
services:
  arix-api:
    # ... other config
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
```

**2. Volume Mounting for Logs**
```yaml
# Add to docker-compose.yml
volumes:
  - ./logs:/app/logs:rw
```

## Production Checklist

- [ ] Environment variables configured
- [ ] API keys valid and working
- [ ] Health check endpoint responding
- [ ] Logs directory permissions correct
- [ ] Firewall rules configured (if needed)
- [ ] SSL/HTTPS setup (reverse proxy)
- [ ] Backup strategy in place
- [ ] Monitoring alerts configured

## Support

For issues with deployment, please check:
1. [GitHub Issues](https://github.com/danhtrongit/AriX-API/issues)
2. Container logs: `docker-compose logs arix-api`
3. API documentation in main README.md