@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

echo ============================================================
echo    MSPR ObRail - Tests et couverture
echo ============================================================
echo.
echo    Usage : run_tests.bat          (tests backend + couverture)
echo            run_tests.bat e2e      (ajoute les tests E2E Playwright)
echo            run_tests.bat all      (idem)
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERREUR] Python est introuvable dans le PATH.
    exit /b 1
)

echo [1/2] Installation des dependances de test...
python -m pip install -q -r API\requirements-dev.txt
if errorlevel 1 (
    echo [ERREUR] Echec de l'installation des dependances de test.
    exit /b 1
)

echo.
echo [2/2] Tests backend (unitaires + integration) avec couverture...
echo.
pushd API
python -m pytest --cov=. --cov-report=term-missing --cov-report=html
set BACK=!errorlevel!
popd

echo.
if !BACK! NEQ 0 (
    echo [ECHEC] Des tests backend ont echoue.
) else (
    echo [OK] Tous les tests backend sont passes.
)
echo Rapport HTML de couverture : API\htmlcov\index.html
if exist "API\htmlcov\index.html" start "" "API\htmlcov\index.html"

REM --- Tests E2E optionnels ---
if /i "%~1"=="e2e" goto e2e
if /i "%~1"=="all" goto e2e
goto end

:e2e
echo.
echo === Tests E2E (Playwright) ===
curl -sf http://localhost:8501/ >nul 2>nul
if errorlevel 1 (
    echo [INFO] Frontend non joignable sur http://localhost:8501
    echo        Lancez d'abord la stack avec start.bat, puis relancez run_tests.bat e2e
    goto end
)
echo Installation des dependances E2E + navigateur Chromium...
python -m pip install -q -r e2e\requirements.txt
python -m playwright install chromium
echo.
pushd e2e
python -m pytest
set FRONT=!errorlevel!
popd
echo.
if !FRONT! NEQ 0 (
    echo [ECHEC] Des tests E2E ont echoue.
) else (
    echo [OK] Tous les tests E2E sont passes.
)

:end
echo.
echo ============================================================
echo    Termine.
echo ============================================================
endlocal
