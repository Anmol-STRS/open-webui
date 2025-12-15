# Docker Build Guide - Custom Open WebUI with React Preview

This guide shows you how to build a custom Docker image of Open WebUI that includes your React live preview feature.

---

## 📋 Prerequisites

### Install Docker Desktop

**Windows:**
1. Download Docker Desktop: https://www.docker.com/products/docker-desktop/
2. Install and restart your computer
3. Open Docker Desktop and ensure it's running

**Verify Installation:**
```bash
docker --version
docker compose --version
```

---

## 🏗️ Building Your Custom Image

### **Method 1: Simple Build (Recommended)**

Build the Docker image from your project directory:

```bash
# Navigate to your project
cd c:\Projects2025\open-webui

# Build the image (this will take 10-15 minutes)
docker build -t open-webui-react-preview:latest .
```

**What this does:**
- Uses the existing `Dockerfile` in your project
- Includes all your changes (React preview feature)
- Tags the image as `open-webui-react-preview:latest`
- Builds both frontend and backend

### **Method 2: Build with Docker Compose**

If you want to use docker-compose (easier management):

```bash
# Build with docker-compose
docker compose build

# Or build and start in one command
docker compose up --build -d
```

---

## 🚀 Running Your Custom Image

### **Quick Start:**

```bash
docker run -d \
  -p 3000:8080 \
  -v open-webui:/app/backend/data \
  --name open-webui-react \
  open-webui-react-preview:latest
```

**Access the app:**
- Open browser: http://localhost:3000

### **With Environment Variables:**

```bash
docker run -d \
  -p 3000:8080 \
  -v open-webui:/app/backend/data \
  -e OPENAI_API_KEY=your-api-key \
  -e WEBUI_AUTH=false \
  --name open-webui-react \
  open-webui-react-preview:latest
```

### **Using Docker Compose (Recommended):**

Create `docker-compose.yml` (or use existing):

```yaml
version: '3.8'

services:
  open-webui:
    build: .
    image: open-webui-react-preview:latest
    container_name: open-webui-react
    ports:
      - "3000:8080"
    volumes:
      - open-webui:/app/backend/data
    environment:
      - WEBUI_AUTH=false  # Disable auth for testing
      - OPENAI_API_KEY=${OPENAI_API_KEY}  # Set in .env file
    restart: unless-stopped

volumes:
  open-webui:
```

**Start with docker-compose:**
```bash
docker compose up -d
```

**Stop:**
```bash
docker compose down
```

**View logs:**
```bash
docker compose logs -f
```

---

## 🔧 Docker Commands Cheat Sheet

### **Build:**
```bash
# Build image
docker build -t open-webui-react-preview:latest .

# Build with no cache (fresh build)
docker build --no-cache -t open-webui-react-preview:latest .

# Build and tag with version
docker build -t open-webui-react-preview:1.0 -t open-webui-react-preview:latest .
```

### **Run:**
```bash
# Run container
docker run -d -p 3000:8080 --name open-webui-react open-webui-react-preview

# Run with auto-restart
docker run -d -p 3000:8080 --restart unless-stopped --name open-webui-react open-webui-react-preview

# Run with volume mount for data persistence
docker run -d -p 3000:8080 -v open-webui:/app/backend/data --name open-webui-react open-webui-react-preview
```

### **Manage:**
```bash
# List running containers
docker ps

# List all containers
docker ps -a

# View logs
docker logs open-webui-react

# Follow logs (live)
docker logs -f open-webui-react

# Stop container
docker stop open-webui-react

# Start container
docker start open-webui-react

# Restart container
docker restart open-webui-react

# Remove container
docker rm open-webui-react

# Remove container (force)
docker rm -f open-webui-react
```

### **Images:**
```bash
# List images
docker images

# Remove image
docker rmi open-webui-react-preview:latest

# Prune unused images
docker image prune
```

### **Cleanup:**
```bash
# Stop and remove container
docker stop open-webui-react && docker rm open-webui-react

# Remove everything (containers, images, volumes)
docker system prune -a --volumes
```

---

## 📦 Pushing to Docker Hub (Optional)

If you want to share your custom image:

### **1. Login to Docker Hub:**
```bash
docker login
```

### **2. Tag your image:**
```bash
docker tag open-webui-react-preview:latest yourusername/open-webui-react-preview:latest
```

### **3. Push to Docker Hub:**
```bash
docker push yourusername/open-webui-react-preview:latest
```

### **4. Others can pull it:**
```bash
docker pull yourusername/open-webui-react-preview:latest
docker run -d -p 3000:8080 yourusername/open-webui-react-preview:latest
```

---

## 🔍 Troubleshooting

### **Build fails with "npm install" errors:**
```bash
# Clear Docker cache and rebuild
docker builder prune
docker build --no-cache -t open-webui-react-preview:latest .
```

### **Container exits immediately:**
```bash
# Check logs
docker logs open-webui-react

# Run in interactive mode to see errors
docker run -it --rm open-webui-react-preview:latest
```

### **Port already in use:**
```bash
# Use a different port
docker run -d -p 3001:8080 --name open-webui-react open-webui-react-preview

# Or stop the conflicting container
docker ps
docker stop <container-name>
```

### **Need to access the container shell:**
```bash
# Access running container
docker exec -it open-webui-react /bin/bash

# Or start a new container with shell
docker run -it --rm open-webui-react-preview:latest /bin/bash
```

### **Build is very slow:**
This is normal for first build. The Dockerfile:
1. Installs Node.js dependencies (~5 minutes)
2. Builds frontend (~3 minutes)
3. Installs Python dependencies (~5 minutes)
4. Total: ~15 minutes

**Speed up rebuilds:**
- Docker caches layers, so subsequent builds are faster
- Only changed layers are rebuilt

---

## 🎯 Testing Your React Preview Feature

Once the container is running:

### **1. Access the app:**
```
http://localhost:3000
```

### **2. Test React Preview:**

Paste this React code in chat or ask AI to generate it:

````markdown
```jsx
import React, { useState } from 'react';

function Counter() {
  const [count, setCount] = useState(0);

  return (
    <div style={{ padding: '20px', textAlign: 'center' }}>
      <h1>Count: {count}</h1>
      <button onClick={() => setCount(count - 1)}>-</button>
      <button onClick={() => setCount(count + 1)}>+</button>
    </div>
  );
}

export default Counter;
```
````

### **3. Expected Result:**
- ✅ Code block with syntax highlighting
- ✅ "Preview" button visible
- ✅ Artifacts panel opens on right
- ✅ Live interactive counter!

---

## 🌐 Environment Variables

Configure Open WebUI with environment variables:

### **Common Settings:**

```bash
# Disable authentication (for testing)
-e WEBUI_AUTH=false

# Set OpenAI API key
-e OPENAI_API_KEY=sk-...

# Set custom port
-e PORT=8080

# Enable debug mode
-e WEBUI_DEBUG=true

# Set database URL
-e DATABASE_URL=postgresql://user:pass@host/db

# Allow origins for CORS
-e CORS_ALLOW_ORIGIN=http://localhost:3000
```

### **Example with multiple variables:**
```bash
docker run -d \
  -p 3000:8080 \
  -v open-webui:/app/backend/data \
  -e WEBUI_AUTH=false \
  -e OPENAI_API_KEY=sk-your-key \
  -e WEBUI_DEBUG=true \
  --name open-webui-react \
  open-webui-react-preview:latest
```

---

## 📝 Multi-Stage Build Explained

The Dockerfile uses multi-stage builds for efficiency:

### **Stage 1: Frontend Build**
```dockerfile
FROM node:20-alpine AS frontend-builder
# Builds the Svelte frontend
# Includes your React preview feature
```

### **Stage 2: Python Backend**
```dockerfile
FROM python:3.11-slim
# Installs Python dependencies
# Copies built frontend from Stage 1
# Sets up backend server
```

**Benefits:**
- Final image only contains what's needed to run
- Smaller image size (~1.5GB vs 3GB+)
- Faster deployment

---

## 🔐 Security Notes

### **Production Deployment:**

1. **Enable Authentication:**
   ```bash
   -e WEBUI_AUTH=true
   ```

2. **Use Secrets for API Keys:**
   ```bash
   docker secret create openai_key your-key-file
   ```

3. **Use HTTPS:**
   - Set up reverse proxy (nginx, Traefik)
   - Use Let's Encrypt for SSL

4. **Limit Ports:**
   ```bash
   -p 127.0.0.1:3000:8080  # Only localhost access
   ```

5. **Regular Updates:**
   ```bash
   docker pull open-webui-react-preview:latest
   docker compose up -d
   ```

---

## 📊 Resource Usage

**Typical resource usage:**
- **CPU:** 1-2 cores
- **RAM:** 1-2 GB
- **Disk:** 2-3 GB (image) + data volume
- **Build time:** 10-15 minutes (first time)

**Adjust resources in Docker Desktop:**
- Settings → Resources → Advanced
- Allocate: 4GB RAM, 2 CPUs minimum

---

## 🎓 Next Steps

After building and running:

1. **Configure LLM Backend:**
   - Add OpenAI API key
   - Or use Ollama locally
   - Or configure other providers

2. **Test Features:**
   - Test React preview with different components
   - Try TypeScript examples
   - Test with complex state management

3. **Customize:**
   - Modify ReactPreview props in Artifacts.svelte
   - Enable code editing in preview
   - Add custom Sandpack templates

4. **Deploy:**
   - Push to cloud (AWS, GCP, Azure)
   - Or use docker-compose on VPS
   - Set up domain and SSL

---

## 📚 Additional Resources

- **Docker Documentation:** https://docs.docker.com
- **Docker Compose:** https://docs.docker.com/compose/
- **Open WebUI Docs:** https://docs.openwebui.com
- **Your Implementation Docs:**
  - [REACT_PREVIEW_GUIDE.md](REACT_PREVIEW_GUIDE.md)
  - [ARCHITECTURE_OVERVIEW.md](ARCHITECTURE_OVERVIEW.md)
  - [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

---

## ✅ Quick Reference

### **Build and Run (One Command):**
```bash
docker build -t open-webui-react-preview . && \
docker run -d -p 3000:8080 \
  -v open-webui:/app/backend/data \
  -e WEBUI_AUTH=false \
  --name open-webui-react \
  open-webui-react-preview:latest
```

### **Check Status:**
```bash
docker ps
docker logs -f open-webui-react
```

### **Stop and Clean:**
```bash
docker stop open-webui-react
docker rm open-webui-react
```

### **Rebuild After Changes:**
```bash
docker build --no-cache -t open-webui-react-preview .
docker stop open-webui-react
docker rm open-webui-react
docker run -d -p 3000:8080 -v open-webui:/app/backend/data --name open-webui-react open-webui-react-preview
```

---

## 🎉 Summary

**Your custom Docker image includes:**
- ✅ React live preview with Sandpack
- ✅ TypeScript support
- ✅ Smart code detection
- ✅ Artifacts panel integration
- ✅ Theme awareness
- ✅ All Open WebUI features

**Ready to share, deploy, or use anywhere Docker runs!** 🚀
