@echo off
setlocal

echo ===================================================
echo   ClipCompass Docker Image Publisher
echo ===================================================

REM Check if user is logged in
docker login
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker login failed. Please login and try again.
    exit /b 1
)

REM Ask for Docker Hub username
set /p DOCKER_USER="Enter your Docker Hub username: "

if "%DOCKER_USER%"=="" (
    echo [ERROR] Username is required.
    exit /b 1
)

echo.
echo Tagging images for user: %DOCKER_USER%...

REM Tag Backend
docker tag clipcompass-backend:latest %DOCKER_USER%/clipcompass-backend:latest
echo [OK] Tagged backend

REM Tag Frontend
docker tag clipcompass-frontend:latest %DOCKER_USER%/clipcompass-frontend:latest
echo [OK] Tagged frontend

REM Tag Celery Worker
docker tag clipcompass-celery-worker:latest %DOCKER_USER%/clipcompass-celery-worker:latest
echo [OK] Tagged celery-worker

echo.
echo Pushing images to Docker Hub...
echo This might take a while depending on your upload speed.

echo.
echo [1/3] Pushing backend...
docker push %DOCKER_USER%/clipcompass-backend:latest

echo.
echo [2/3] Pushing frontend...
docker push %DOCKER_USER%/clipcompass-frontend:latest

echo.
echo [3/3] Pushing celery-worker...
docker push %DOCKER_USER%/clipcompass-celery-worker:latest

echo.
echo ===================================================
echo   SUCCESS! All images pushed to Docker Hub
echo ===================================================
echo.
pause
