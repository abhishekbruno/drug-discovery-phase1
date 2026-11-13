@echo off
cd /d "%~dp0"
set "VINA_EXECUTABLE=%~dp0tools\vina.exe"
"%~dp0.venv\Scripts\dockpipe.exe" ui
