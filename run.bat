@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title MDO CHATBOT - MDO ESTC
echo ==================================================
echo   MDO CHATBOT - Assistant MDO / ESTC Casablanca
echo ==================================================
echo.

rem --- 1. Python ---
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY (
  where py >nul 2>nul && set "PY=py -3"
)
if not defined PY (
  echo [ERREUR] Python est introuvable.
  echo Installez Python 3.10 ou plus recent depuis https://www.python.org/downloads/
  echo IMPORTANT : cochez "Add python.exe to PATH" pendant l'installation.
  goto :fail
)
%PY% -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)"
if errorlevel 1 (
  echo [ERREUR] Python 3.10 ou plus recent est requis. Version detectee :
  %PY% --version
  goto :fail
)
echo [OK] Python detecte :
%PY% --version

rem --- 2. Environnement virtuel ---
if not exist ".venv\Scripts\python.exe" (
  echo [..] Creation de l'environnement virtuel...
  %PY% -m venv .venv
  if errorlevel 1 goto :fail
)
call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :fail

rem --- 3. Dependances ---
echo [..] Installation des dependances (la premiere fois, cela peut prendre une minute)...
python -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
  echo [ERREUR] L'installation des dependances a echoue. Verifiez votre connexion Internet.
  goto :fail
)

rem --- 4. .env + base de donnees ---
python -m app.setup
if errorlevel 1 goto :fail

rem --- 5. Lancement ---
echo.
echo [OK] Demarrage... L'application s'ouvre dans votre navigateur.
echo      Adresse : http://127.0.0.1:5000   (fermez cette fenetre pour arreter)
echo.
start "" /b cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:5000"
python -m app
if errorlevel 1 goto :fail
goto :end

:fail
echo.
echo *** Une erreur est survenue. Lisez le message ci-dessus. ***
pause
exit /b 1

:end
pause
