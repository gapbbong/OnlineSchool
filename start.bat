@echo off
chcp 65001 > nul
echo ========================================================
echo   🏫 온라인 교무실 (Online Faculty Hub) 실행 중...
echo ========================================================
echo.

start "온라인 교무실 - Backend API" cmd /k "cd /d %~dp0backend && .\venv\Scripts\uvicorn app.main:app --reload --port 8000"
timeout /t 2 > nul
start "온라인 교무실 - Frontend UI" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo [안내] 
echo - 교무실 메인 대시보드 : http://localhost:3000
echo - 신규 교사 등록 페이지: http://localhost:3000/teachers/onboarding
echo - 백엔드 API 문서(Swagger): http://localhost:8000/docs
echo ========================================================
