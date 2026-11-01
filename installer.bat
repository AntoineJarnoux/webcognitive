@echo off
rem Installation automatique de WebCognitive Engine : double-cliquez sur ce fichier.
rem Pour un modele plus leger : installer.bat -Modele llama3.2:3b
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer.ps1" %*
pause
