@echo off
rem RASP - Backend (API FastAPI/Uvicorn). Logs detalhados em backend\logs\rasp.log
cd /d "%~dp0backend"
set PYTHONUNBUFFERED=1
rem Para liberar acesso a outras maquinas da rede, troque 127.0.0.1 por 0.0.0.0 (e ajuste RASP_HOST)
"%~dp0backend\venv\Scripts\python.exe" -X utf8 -m uvicorn main:app --host 127.0.0.1 --port 8000 --no-access-log
