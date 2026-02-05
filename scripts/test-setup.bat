@echo off
REM Comprehensive test script for Phase 0 MVP (Windows)

setlocal enabledelayedexpansion
set TESTS_PASSED=0
set TESTS_FAILED=0

echo ==========================================
echo Compliance Platform MVP - Test Suite
echo ==========================================
echo.

REM Test 1: Docker containers running
echo TEST: Checking if Docker containers are running...
docker ps | findstr "compliance-postgres" >nul 2>&1
if %errorlevel% equ 0 (
    echo [PASS] PostgreSQL container running
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] PostgreSQL container not running
    set /a TESTS_FAILED+=1
)

docker ps | findstr "compliance-backend" >nul 2>&1
if %errorlevel% equ 0 (
    echo [PASS] Backend container running
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] Backend container not running
    set /a TESTS_FAILED+=1
)

echo.

REM Test 2: Database connectivity
echo TEST: Testing database connectivity...
docker-compose exec -T postgres pg_isready -U admin -d multitenantpostgresdb >nul 2>&1
if %errorlevel% equ 0 (
    echo [PASS] Database connectivity
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] Cannot connect to database
    set /a TESTS_FAILED+=1
)

echo.

REM Test 3: Health endpoint
echo TEST: Testing health endpoint...
curl -s http://localhost:8000/health | findstr "healthy" >nul 2>&1
if %errorlevel% equ 0 (
    echo [PASS] Health endpoint responding
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] Health endpoint not responding
    set /a TESTS_FAILED+=1
)

echo.

REM Test 4: Database tables
echo TEST: Checking database tables...
docker-compose exec -T postgres psql -U admin -d multitenantpostgresdb -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'" | findstr /r "^[0-9]" >nul 2>&1
if %errorlevel% equ 0 (
    echo [PASS] Database tables exist
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] No database tables found
    set /a TESTS_FAILED+=1
)

echo.
echo ==========================================
echo Test Results: Passed=%TESTS_PASSED% Failed=%TESTS_FAILED%
echo ==========================================

if %TESTS_FAILED% equ 0 (
    echo All tests passed!
    exit /b 0
) else (
    echo Some tests failed!
    exit /b 1
)
