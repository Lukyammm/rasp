@echo off
rem RASP - Frontend estatico (a interface tambem fica disponivel em http://127.0.0.1:8000 pela propria API)
cd /d "%~dp0frontend"
"%~dp0backend\venv\Scripts\python.exe" "%~dp0frontend\serve.py" 8080
