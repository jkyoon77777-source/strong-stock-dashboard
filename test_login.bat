@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
cmd /k "chcp 65001 >nul & python test_login.py"
