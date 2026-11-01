@echo off
rem Demarre WebCognitive Engine puis ouvre l'interface dans le navigateur.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo L'installation n'a pas encore ete faite : double-cliquez d'abord sur installer.bat
  pause
  exit /b 1
)
rem Demarre Ollama s'il ne tourne pas, puis ouvre le navigateur quand le serveur est pret
start "" /min powershell -NoProfile -WindowStyle Hidden -Command "try { Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 3 | Out-Null } catch { Start-Process ollama -ArgumentList serve -WindowStyle Hidden }; Start-Sleep -Seconds 10; Start-Process 'http://127.0.0.1:8000/'"
echo Interface : http://127.0.0.1:8000/   (fermez cette fenetre ou Ctrl+C pour arreter)
".venv\Scripts\python.exe" scripts\serve_api.py
pause
