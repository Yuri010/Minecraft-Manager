@echo off
echo %* | find /I "-y"
set force=off
if /I "%errorlevel%" EQU "0" set force=on
:: ==============================
set workdir=%~dp0
set jar=spigot-1.19.4.jar
set port=25565
set maxram=6144M
set minram=2048M
set command=java -Xmx%maxram% -Xms%minram% -jar "%workdir%%jar%" nogui
cd %workdir%
:: ==============================
title Minecraft Server
:: Getting Server JAR Version
FOR /F "tokens=* delims=3 USEBACKQ" %%F IN (`java -jar %jar% -version`) DO (
SET ver=%%F
)
:: Info Brick
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
if /I "%force%" NEQ "on" pause
echo Proceeding with Server Startup...
timeout /t 2 /nobreak > nul
cls
:: "Boot Screen"
echo Starting Server (Step 1/2)
echo [RUNNING] Starting Minecraft Server.
timeout /t 1 /nobreak > nul
cls
echo Starting Server (Step 1/2)
echo [RUNNING] Starting Minecraft Server..
:: Actual point where it starts the server
start cmd /c "%command%"
timeout /t 1 /nobreak > nul
cls
echo Starting Server (Step 1/2)
echo [RUNNING] Starting Minecraft Server...
timeout /t 1 /nobreak > nul
:: Awaiting Server to come online
set ctries=0
:waitinggame
cls
echo Starting Server (Step 2/2)
echo [BACKGROUND] Starting Minecraft Server...
echo [RUNNING] Waiting for Minecraft Server link state to become UP (Attempt %ctries%/5)
:: Check if the host is up (after a small wait)
if /I "%ctries%" EQU "0" timeout /t 10
powershell -Command "Test-NetConnection -ComputerName 'localhost' -Port %port% | Select-Object -ExpandProperty TcpTestSucceeded" | findstr /I "true"
if /I "%errorlevel%" NEQ "0" (
    set /A ctries=ctries+1
    if /I "%ctries%" GEQ "5" goto :hell
    goto :waitinggame
)
cls
echo Starting Server (Step 2/2)
echo [BACKGROUND] Starting Minecraft Server...
echo [SUCCESS] Waiting for Minecraft Server link state to become UP (Attempt %ctries%/5)
echo [RUNNING] A start job is running for Ngrok...
ngrok tcp %port%
cls
if "%errorlevel%" EQU "0" (
    echo [  OK  ] Ngrok exited with code 0, indicating a regular shutdown.
) else (
    echo [WARNING] Ngrok exited with code %errorlevel%, indicating an irregular shutdown!
)
echo [RUNNING] Poking around to see if the server is still UP...
powershell -Command "Test-NetConnection -ComputerName 'localhost' -Port %port% | Select-Object -ExpandProperty TcpTestSucceeded" | findstr /I "true"
if /I "%errorlevel%" EQU "0" (
    echo [WARNING] Seems like the server is still running... Perhaps shut that down first?
) else (
    echo [  OK  ] Looks like you shut it down correctly this time, Good Job!
)
if /I "%force%" EQU "on" (
echo [RUNNING] Restarting bot to update server status :P
taskkill -im python.exe /f > nul
start /min cmd /c "bot.bat"
)
echo [ Note ] Anyways.. I'll be going now, Bye!
timeout /t 3 /nobreak > nul
exit

:hell
cls
echo Starting Server (Step 2/2)
echo [BACKGROUND] Starting Minecraft Server...
echo [FAILED] Waiting for Minecraft Server link state to become UP (Attempt 5/5)
echo.
echo [FATAL] Minecraft Server couldn't be reached for 5 consecutive tries, giving up...
echo [ Note ] Would you like to (R)etry or (Q)uit?
if /I "%force%" EQU "on" set ctries=1 & goto :waitinggame
choice /c RQ /n
if /I "%errorlevel%" EQU "2" exit
if /I "%errorlevel%" EQU "1" set ctries=1 & goto :waitinggame