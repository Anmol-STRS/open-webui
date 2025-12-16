#!/bin/bash

echo "============================================================"
echo "    Open WebUI - React Preview Edition"
echo "============================================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Backend Server...${NC}"
cd backend
python -m uvicorn open_webui.main:app --port 8080 --host 0.0.0.0 --reload &
BACKEND_PID=$!
cd ..

sleep 3

echo ""
echo -e "${BLUE}Starting Frontend Server...${NC}"
npm run dev &
FRONTEND_PID=$!

sleep 2

echo ""
echo "============================================================"
echo "    Open WebUI is Running!"
echo "============================================================"
echo ""
echo -e "${GREEN}✓ Backend:  http://localhost:8080${NC}"
echo -e "${GREEN}✓ Frontend: http://localhost:5173${NC}"
echo ""
echo -e "${YELLOW}React Preview Feature Included!${NC}"
echo "- Generate React code in chat"
echo "- Click 'Preview' button"
echo "- View live interactive components"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all servers${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "All servers stopped"
    exit 0
}

# Trap Ctrl+C
trap cleanup INT TERM

# Wait for processes
wait
