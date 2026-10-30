@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -c "import streamlit,pymupdf,jieba,sklearn" >nul 2>&1
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m streamlit run app.py
pause
exit /b
:failed
echo 启动失败，请保留上方错误信息。请确认已安装 Python 3.11 或 3.12，首次安装需要网络。
pause
