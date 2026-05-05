@echo off
cd /d "%~dp0"
"C:\Users\paulh\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -u app.py > server.out.log 2> server.err.log
