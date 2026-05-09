@echo off
REM Windows Batch script to run load tests with Locust

setlocal enabledelayedexpansion

echo Loading E-Commerce Load Testing Suite...
echo.

cd load-tests

REM Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install/upgrade Locust in virtual environment
echo Installing/upgrading Locust in virtual environment...
pip install --upgrade -r requirements.txt

cd ..

cd load-tests

echo.
echo ============================================
echo E-Commerce Load Testing Options:
echo ============================================
echo.
echo 1) GUI Mode (interactive, no rate limiting)
echo 2) 50 users, 2m duration (light test)
echo 3) 100 users, 5m duration (medium test)
echo.
set /p choice="Select option (1-3): "

REM Activate virtual environment for running Locust
call venv\Scripts\activate.bat

if "%choice%"=="1" (
    echo Starting Locust GUI at http://localhost:8089
    echo Press Ctrl+C to stop
    locust -f locustfile.py --host=http://localhost:8000
) else if "%choice%"=="2" (
    echo Running light load test: 50 users...
    locust -f locustfile.py --host=http://localhost:8000 ^
      --users 50 --spawn-rate 5 --run-time 2m --headless --csv=results_light
    echo Results saved to results_light_stats.csv
) else if "%choice%"=="3" (
    echo Running medium load test: 100 users...
    locust -f locustfile.py --host=http://localhost:8000 ^
      --users 100 --spawn-rate 10 --run-time 5m --headless --csv=results_medium
    echo Results saved to results_medium_stats.csv
) else (
    echo Invalid choice. Exiting.
    exit /b 1
)

cd ..

echo.
echo ============================================
echo Load test completed!
echo ============================================
echo.
echo To verify async communication is working:
echo 1. Create an order: CREATE ORDER IN GATEWAY
echo 2. Check RabbitMQ: http://localhost:15672 (guest/guest)
echo 3. Watch logs: docker logs payment-service
echo.
echo See TESTING.md for detailed verification steps.

endlocal
