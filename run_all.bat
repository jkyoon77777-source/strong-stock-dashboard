@echo off
chcp 65001 > nul
REM Run after market close: fetch data -> rank -> build dashboard
cd /d %~dp0
set PYTHONUTF8=1
python fetch_data.py kr
python fetch_data.py us
python screener.py kr
python screener.py us
python build_dashboard.py
start dashboard.html
pause
