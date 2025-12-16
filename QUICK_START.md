# Quick Start Guide - Open WebUI with React Preview

## 🚀 3 Ways to Run

### **Method 1: Windows Batch Script (Easiest for Windows)**

```bash
# Just double-click start.bat
# Or run from terminal:
start.bat
```

**What it does:**
- Opens 2 command windows (Backend & Frontend)
- Automatically opens browser
- Easy to see logs
- Easy to stop (close windows)

---

### **Method 2: Bash Script (Linux/Mac/Git Bash)**

```bash
# Make executable (first time only)
chmod +x start.sh

# Run
./start.sh

# Stop with Ctrl+C
```

**What it does:**
- Starts both servers in background
- Shows combined output
- Cleanup on Ctrl+C

---

### **Method 3: Python Script (Cross-platform)**

```bash
# Run
python start.py

# Stop with Ctrl+C
```

**What it does:**
- Checks prerequisites
- Installs dependencies if needed
- Manages both servers
- Clean shutdown

---

### **Method 4: Manual (For Development)**

**Terminal 1 - Backend:**
```bash
cd backend
python -m uvicorn open_webui.main:app --port 8080 --host 0.0.0.0 --reload
```

**Terminal 2 - Frontend:**
```bash
npm run dev
```

---

## 📋 Prerequisites

### **Required:**
- **Node.js** 18+ (https://nodejs.org/)
- **Python** 3.11+ (https://python.org/)
- **Git** (https://git-scm.com/)

### **Check Installation:**
```bash
node --version    # Should be v18+
python --version  # Should be 3.11+
npm --version     # Should be 6+
```

---

## ⚡ First Time Setup

### **1. Clone Repository**
```bash
git clone https://github.com/Anmol-STRS/open-webui.git
cd open-webui
```

### **2. Install Dependencies**

**Frontend:**
```bash
npm install
```

**Backend:**
```bash
cd backend
pip install -r requirements.txt
cd ..
```

### **3. Run Application**

**Windows:**
```bash
start.bat
```

**Linux/Mac:**
```bash
./start.sh
```

**Any OS:**
```bash
python start.py
```

---

## 🌐 Access Application

Once started, open your browser:

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8080
- **API Docs:** http://localhost:8080/docs

---

## 🎨 Test React Preview

### **1. Start a Chat**

First time users:
1. Create an account or skip authentication
2. Configure an LLM (OpenAI, Ollama, etc.)

### **2. Generate React Code**

Ask the AI:
```
Create a React counter component with + and - buttons
```

Or paste this code:
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

### **3. View Preview**

1. Click **"Preview"** button on code block
2. Artifacts panel opens on right
3. See live, interactive counter!
4. Click **"Open"** to view in new tab

---

## 🐛 Troubleshooting

### **Port Already in Use**

**Backend (8080) conflict:**
```bash
# Windows
netstat -ano | findstr :8080
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8080 | xargs kill -9
```

**Frontend (5173) conflict:**
```bash
# Windows
netstat -ano | findstr :5173
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:5173 | xargs kill -9
```

### **Dependencies Not Installed**

```bash
# Reinstall frontend
npm install

# Reinstall backend
cd backend
pip install -r requirements.txt
cd ..
```

### **Python Module Not Found**

```bash
# Use the correct Python
python -m pip install -r backend/requirements.txt

# Or with Python 3
python3 -m pip install -r backend/requirements.txt
```

### **npm Command Not Found**

Install Node.js from https://nodejs.org/

Verify:
```bash
node --version
npm --version
```

---

## 🛑 Stopping the Application

### **start.bat (Windows):**
Close the two command windows

### **start.sh (Linux/Mac):**
Press `Ctrl+C` in terminal

### **start.py:**
Press `Ctrl+C` in terminal

### **Manual:**
Press `Ctrl+C` in each terminal

---

## 🐳 Docker Alternative

If you prefer Docker:

```bash
# Build
docker build -t open-webui-react-preview .

# Run
docker run -d -p 3000:8080 -v open-webui:/app/backend/data --name open-webui open-webui-react-preview

# Access
open http://localhost:3000

# Stop
docker stop open-webui
docker rm open-webui
```

---

## 📚 Documentation

- **[REACT_PREVIEW_GUIDE.md](REACT_PREVIEW_GUIDE.md)** - Complete user guide
- **[ARCHITECTURE_OVERVIEW.md](ARCHITECTURE_OVERVIEW.md)** - System architecture
- **[DOCKER_BUILD_GUIDE.md](DOCKER_BUILD_GUIDE.md)** - Docker setup
- **[PUSH_TO_GITHUB.md](PUSH_TO_GITHUB.md)** - Git workflow

---

## ⚙️ Configuration

### **Environment Variables**

Create `.env` file:
```bash
# OpenAI
OPENAI_API_KEY=sk-your-key-here

# Ollama (local)
OLLAMA_API_BASE_URL=http://localhost:11434/api

# Authentication
WEBUI_AUTH=false  # Disable for testing

# Debug
WEBUI_DEBUG=true
```

---

## 🎯 Quick Commands Reference

```bash
# Start
start.bat         # Windows
./start.sh        # Linux/Mac
python start.py   # Any OS

# Install dependencies
npm install                           # Frontend
pip install -r backend/requirements.txt  # Backend

# Build for production
npm run build

# Run tests
npm test

# Check for updates
git pull myfork main

# Clean install
rm -rf node_modules
npm install
```

---

## ✅ Checklist

Before reporting issues:

- [ ] Node.js 18+ installed
- [ ] Python 3.11+ installed
- [ ] Dependencies installed (`npm install`)
- [ ] Backend dependencies installed
- [ ] Ports 5173 and 8080 available
- [ ] No firewall blocking
- [ ] Tried restarting

---

## 🆘 Getting Help

1. **Check documentation** in repository
2. **Search issues** on GitHub
3. **Create new issue** with:
   - OS and versions
   - Error messages
   - Steps to reproduce

---

## 🎉 You're Ready!

Your Open WebUI with React Live Preview is ready to use!

**Quick Test:**
1. Run `start.bat` (Windows) or `./start.sh` (Linux/Mac)
2. Open http://localhost:5173
3. Generate React code
4. Click Preview
5. Enjoy! 🚀
