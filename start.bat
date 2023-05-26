:: version 1.0.2
@echo off
title Minecraft Manager Script
:: ===================================VAR+CHECKS===================================
cd %~dp0
echo %* | find /I "-y"
set force=off
if /I "%errorlevel%" EQU "0" set force=on

if NOT exist config.cfg (
    cls
    echo [FATAL] CONFIG COULD NOT BE FOUND
    echo FAILED TO START SERVER
    echo.
    echo Press any key to exit...
    pause > nul
    exit
)
for /f "usebackq tokens=1,2 delims==" %%G in ("config.cfg") do (
    if "%%G"=="jar " set "jar=%%H"
    if "%%G"=="port " set "port=%%H"
    if "%%G"=="maxram " set "maxram=%%H"
    if "%%G"=="minram " set "minram=%%H"
)

set "jar=%jar: =%"
set "port=%port: =%"
set "maxram=%maxram: =%"
set "minram=%minram: =%"
cd ..
set workdir=%cd%
set command=java -Xmx%maxram% -Xms%minram% -jar "%workdir%\%jar%" nogui
java -version
if /I "%errorlevel%" NEQ "0" (
    cls
    echo [FATAL] JAVA COULD NOT BE FOUND
    echo FAILED TO START SERVER
    echo.
    echo Press any key to exit...
    pause > nul
    exit
)
if NOT exist %jar% (
    cls
    echo [FATAL] SERVER JAR COULD NOT BE FOUND
    echo FAILED TO START SERVER
    echo.
    echo Press any key to exit...
    pause > nul
    exit
)
if NOT exist ngrok.exe (
    cls
    echo [FATAL] NGROK COULD NOT BE FOUND
    echo FAILED TO START SERVER
    echo.
    echo Press any key to exit...
    pause > nul
    exit
)
FOR /F "tokens=* delims=3 USEBACKQ" %%F IN (`java -jar %jar% -version`) DO (
SET ver=%%F
)
:: ===================================MAIN===================================
echo ==================================================
echo.
echo Configuration:
echo.
java -version
echo.
echo.   Server JAR:         %jar%
echo.   Server JAR Version: %ver%
echo.
echo.   Minimum RAM Usage:  %minram%
echo.   Maximum RAM Usage:  %maxram%
echo.
echo Network Info:
echo.   IP:                 To be determined...
echo.   Port:               %port%
echo.
echo ==================================================
if /I "%force%" NEQ "on" (
	pause
	echo Proceeding with Server Startup...
	timeout /t 2 /nobreak > nul
)
cls
echo Starting Server (Step 1/2)
echo [RUNNING] Starting Minecraft Server.
timeout /t 1 /nobreak > nul
cls
echo Starting Server (Step 1/2)
echo [RUNNING] Starting Minecraft Server..
timeout /t 1 /nobreak > nul
cls
echo Starting Server (Step 1/2)
echo [RUNNING] Starting Minecraft Server...
start cmd /c "%command%"
timeout /t 1 /nobreak > nul
set ctries=0
:waitinggame
cls
echo Starting Server (Step 2/2)
echo [BACKGROUND] Starting Minecraft Server...
echo [RUNNING] Waiting for Minecraft Server link state to become UP (Attempt %ctries%/5)
if /I "%ctries%" EQU "0" timeout /t 10
powershell -Command "Test-NetConnection -ComputerName 'localhost' -Port %port% | Select-Object -ExpandProperty TcpTestSucceeded" | findstr /I "true"
if /I "%errorlevel%" NEQ "0" (
    set /A ctries=ctries+1
    if /I "%ctries%" GEQ "5" (
        cls
        echo Starting Server ^(Step 2/2^)
        echo [BACKGROUND] Starting Minecraft Server...
        echo [FAILED] Waiting for Minecraft Server link state to become UP ^(Attempt 5/5^)
        echo.
        echo [FATAL] Minecraft Server couldn't be reached for 5 consecutive tries, giving up...
        echo [ Note ] Would you like to ^(R^)etry or ^(Q^)uit?
        if /I "%force%" EQU "on" set ctries=1 & goto :waitinggame
        choice /c RQ /n
        if /I "%errorlevel%" EQU "2" exit
        if /I "%errorlevel%" EQU "1" set ctries=1 & goto :waitinggame
    )
    goto :waitinggame
)
cls
echo Starting Server (Step 2/2)
echo [BACKGROUND] Starting Minecraft Server...
echo [SUCCESS] Waiting for Minecraft Server link state to become UP (Attempt %ctries%/5)
echo [RUNNING] A start job is running for Ngrok...
start /min ngrok tcp %port%
cls
echo Starting Server (Step 2/2)
echo [SUCCESS] Starting Minecraft Server... Done.
echo [SUCCESS] Waiting for Minecraft Server link state to become UP (Attempt %ctries%/5)
echo [SUCCESS] A start job is running for Ngrok... Done.
echo [BACKGROUND] This script will now wait until the Minecraft server goes offline...
:check_process
tasklist | find /i "java.exe" > nul 2> nul
if /I "%errorlevel%" EQU "0" timeout /t 10 /nobreak > nul & goto check_process
cls
echo [ Note ] The Minecraft server is no longer running...
echo [RUNNING] A stop job is running for Ngrok...
taskkill -im ngrok.exe /f
timeout /t 1 /nobreak > nul
echo [RUNNING] Restarting bot to update server status :P
taskkill -im python3.11.exe /f > nul
start /min cmd /c "%~dp0bot.bat"
echo [ Note ] Anyways.. I'll be going now, Bye!
timeout /t 3 /nobreak > nul
exit