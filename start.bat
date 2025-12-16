@echo off
echo ============================================================
echo     Open WebUI - React Preview Edition
echo ============================================================
echo.

echo Starting Backend Server...
cd backend
start "Open WebUI Backend" cmd /k "python -m uvicorn open_webui.main:app --port 8080 --host 0.0.0.0 --reload"
cd ..

timeout /t 3 /nobreak > nul

echo.
echo Starting Frontend Server...
start "Open WebUI Frontend" cmd /k "npm run dev"

echo.
echo ============================================================
echo     Open WebUI is Starting!
echo ============================================================
echo.
echo Backend:  http://localhost:8080
echo Frontend: http://localhost:5173
echo.
echo React Preview Feature Included!
echo - Generate React code in chat
echo - Click 'Preview' button
echo - View live interactive components
echo.
echo Press any key to open the browser...
pause > nul

start http://localhost:5173

echo.
echo To stop servers, close the Backend and Frontend windows
echo.
