@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

echo ============================================================
echo    MSPR ObRail - Demarrage complet du projet (Docker)
echo ============================================================
echo.

REM --- Verification de Docker ---
where docker >nul 2>nul
if errorlevel 1 (
    echo [ERREUR] Docker n'est pas installe ou absent du PATH.
    echo          Installez Docker Desktop puis relancez ce script.
    exit /b 1
)

docker info >nul 2>nul
if errorlevel 1 (
    echo [ERREUR] Le demon Docker ne repond pas. Demarrez Docker Desktop.
    exit /b 1
)

REM --- Fichier d'environnement API ---
if not exist "API\.env" (
    if exist ".env.example" (
        echo [INFO] API\.env manquant : creation depuis .env.example
        copy ".env.example" "API\.env" >nul
    )
)

echo [1/4] Construction des images...
docker compose build
if errorlevel 1 (
    echo [INFO] Echec de build - nouvelle tentative apres nettoyage des images du projet...
    docker rmi -f msprds-api msprds-frontend >nul 2>nul
    docker compose build
    if errorlevel 1 (
        echo [ERREUR] La construction des images a echoue.
        exit /b 1
    )
)

echo       Demarrage des conteneurs...
docker compose up -d
if errorlevel 1 (
    echo [ERREUR] "docker compose up" a echoue.
    exit /b 1
)

echo.
echo [2/4] Attente de l'API (http://localhost:8000)...
set /a n=0
:wait_api
curl -sf http://localhost:8000/monitoring/health >nul 2>nul
if not errorlevel 1 goto api_ready
set /a n+=1
if !n! geq 40 (
    echo [AVERTISSEMENT] API non joignable apres delai. Poursuite quand meme.
    goto after_api
)
timeout /t 3 >nul
goto wait_api
:api_ready
echo       API operationnelle.
:after_api

echo.
echo [3/4] Attente de MLflow (http://localhost:5000)...
set /a m=0
:wait_mlflow
curl -sf http://localhost:5000/health >nul 2>nul
if not errorlevel 1 goto mlflow_ready
set /a m+=1
if !m! geq 40 (
    echo [AVERTISSEMENT] MLflow non joignable. L'enregistrement du modele est ignore.
    goto after_register
)
timeout /t 3 >nul
goto wait_mlflow
:mlflow_ready
echo       MLflow operationnel.

echo.
echo [4/4] Enregistrement du modele XGBoost dans le Model Registry MLflow...
docker compose exec -T api python /model/register_mlflow.py
if errorlevel 1 echo [AVERTISSEMENT] Enregistrement MLflow en echec - l'API utilise le modele local .pkl
:after_register

echo.
echo ============================================================
echo    Stack demarree. Acces aux services :
echo ------------------------------------------------------------
echo    Frontend  (Streamlit) : http://localhost:8501
echo    API       (FastAPI)   : http://localhost:8000/docs
echo    Prometheus            : http://localhost:9090
echo    Grafana               : http://localhost:3000   (admin/admin)
echo    MLflow                : http://localhost:5000
echo ============================================================
echo.
echo    Astuce : pour servir le modele depuis MLflow plutot que le .pkl,
echo             relancez avec :  set USE_MLFLOW=true ^&^& docker compose up -d
echo.
echo    Logs en direct : docker compose logs -f
echo    Arret          : docker compose down
echo.

endlocal
