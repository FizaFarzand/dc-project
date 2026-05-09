@echo off
setlocal ENABLEEXTENSIONS
title Distributed E-Commerce - Windows Test Runner

echo ============================================================
echo  Distributed E-Commerce System - Windows CMD Test Runner
echo ============================================================
echo.
echo This script is made for Windows Command Prompt (cmd.exe).
echo It will:
echo   1) Start Docker services
echo   2) Run health checks
echo   3) Register users
echo   4) Ask you to paste tokens and product ID
echo   5) Create and list orders
echo.
pause

cd /d "%~dp0"

echo.
echo [1/8] Checking Docker...
docker --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Docker is not available in PATH.
  echo Open Docker Desktop and try again.
  goto :end
)

echo.
echo [2/8] Restarting stack...
docker compose down
if errorlevel 1 (
  echo WARNING: docker compose down returned an error. Continuing...
)
docker compose up --build -d
if errorlevel 1 (
  echo ERROR: Failed to start services.
  goto :end
)

echo.
echo [3/8] Waiting for services to warm up...
timeout /t 15 /nobreak >nul

echo.
echo [4/8] Container status:
docker compose ps

echo.
echo [5/8] Health checks:
set "ALL_HEALTHY=1"

call :check_health "Gateway" "http://localhost:8000/health"
call :check_health "User Service" "http://localhost:8001/health"
call :check_health "Product Service" "http://localhost:8002/health"
call :check_health "Order Service" "http://localhost:8003/health"
call :check_health "Payment Service" "http://localhost:8004/health"

if not "%ALL_HEALTHY%"=="1" (
  echo.
  echo ERROR: One or more services are unhealthy.
  echo Run these commands to inspect:
  echo   docker compose ps
  echo   docker compose logs --tail=200 user-service
  echo   docker compose logs --tail=200 order-service
  echo   docker compose logs --tail=200 api-gateway
  goto :end
)

echo.
echo [6/8] Registering sample users...
echo If users already exist, you may see "Email already exists" (this is okay).
curl -s -X POST "http://localhost:8000/api/users/register" ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Admin\",\"email\":\"admin@example.com\",\"password\":\"admin123\",\"role\":\"admin\"}"
echo.
curl -s -X POST "http://localhost:8000/api/users/register" ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Alice\",\"email\":\"alice@example.com\",\"password\":\"alice123\",\"role\":\"customer\"}"
echo.

echo.
echo [7/8] Login requests (copy access_token values from JSON output):
echo Admin login:
curl -s -X POST "http://localhost:8000/api/users/login" ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"admin@example.com\",\"password\":\"admin123\"}"
echo.
echo Customer login:
curl -s -X POST "http://localhost:8000/api/users/login" ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"alice@example.com\",\"password\":\"alice123\"}"
echo.

echo.
set /p ADMIN_TOKEN=Paste ADMIN access_token here: 
set /p USER_TOKEN=Paste CUSTOMER access_token here: 

if "%ADMIN_TOKEN%"=="" (
  echo ERROR: ADMIN token is empty.
  goto :end
)
if "%USER_TOKEN%"=="" (
  echo ERROR: USER token is empty.
  goto :end
)

echo.
echo Creating product as admin...
curl -s -X POST "http://localhost:8000/api/products" ^
  -H "Authorization: Bearer %ADMIN_TOKEN%" ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Laptop\",\"description\":\"Gaming laptop\",\"price\":1200,\"stock\":10,\"category\":\"Electronics\"}"
echo.

echo.
echo Listing products. Copy the product "id" from items[] in the JSON:
curl -s "http://localhost:8000/api/products?limit=20&page=1"
echo.
set /p PRODUCT_ID=Paste PRODUCT id here: 

if "%PRODUCT_ID%"=="" (
  echo ERROR: PRODUCT_ID is empty.
  goto :end
)

echo.
echo Creating order as customer...
curl -s -X POST "http://localhost:8000/api/orders" ^
  -H "Authorization: Bearer %USER_TOKEN%" ^
  -H "Content-Type: application/json" ^
  -d "{\"product_id\":\"%PRODUCT_ID%\",\"quantity\":1}"
echo.

echo.
echo [8/8] Fetching customer order history...
curl -s -X GET "http://localhost:8000/api/orders" ^
  -H "Authorization: Bearer %USER_TOKEN%"
echo.

echo.
echo ============================================================
echo Test flow completed.
echo If something failed, run:
echo   docker compose logs -f api-gateway
echo   docker compose logs -f user-service
echo   docker compose logs -f product-service
echo   docker compose logs -f order-service
echo   docker compose logs -f payment-service
echo ============================================================

:end
echo.
pause
endlocal
goto :eof

:check_health
set "SERVICE_NAME=%~1"
set "SERVICE_URL=%~2"
set "HTTP_CODE="
for /f %%i in ('curl -s -o NUL -w "%%{http_code}" "%SERVICE_URL%"') do set "HTTP_CODE=%%i"
echo %SERVICE_NAME%: %HTTP_CODE%
if not "%HTTP_CODE%"=="200" (
  set "ALL_HEALTHY=0"
)
goto :eof
