:: version 1.0.1
@echo off
title Minecraft-Manager Updater
set gver=SOME
set lver=NONE
cd %~dp0
::echo %* | findstr /I "install"
::if %errorlevel% == 0 goto :install
set debug=off
echo %* | find /I "-debug"
if %errorlevel% == 0 set debug=on
echo %* | find /I "update"
if %errorlevel% == 0 goto :update

:: ==================================================Obtain==================================================
if /I "%debug%" == "on" (
echo Any errors with checking for updates should appear here:
)
curl --output releases.tmp -L https://api.github.com/repos/yuri010/minecraft-manager/releases
if /I "%debug%" == "on" (
echo.
pause
)
call :gver
call :gvercleanup
call :lver
goto :main
:: ==================================================Checks==================================================

:gver
for /F "tokens=2 delims= " %%a IN ('findstr /I "tag_name" releases.tmp') DO (
    set gver=%%a
    exit /b
)
:gvercleanup
for /F "tokens=1 delims=," %%b IN ("%gver%") DO (
    set gver=%%b
    exit /b
)

:lver
for /F "tokens=3 delims= " %%c IN ('findstr /I "version" bot.py') DO (
    set lver=%%c
    exit /b
)


:main
del releases.tmp
if exist "start.bat" (
    if "%lver%" LSS %gver% (
        cls
        echo An update is available, would you like to install it? [Y/N]
        choice /c YN /N
        if /I "%errorlevel%" EQU "2" exit
        if /I "%errorlevel%" EQU "1" goto :update
    )
    if /I "%lver%" GTR %gver% (
        cls
        echo Hey! Github isn't Up-to-Date!
        echo.
        echo Press any key to exit...
        pause > nul
        exit
    )
    if /I "%lver%" == %gver% (
        cls
        echo Minecraft-Manager is Up-to-Date.
        echo.
        echo Press any key to exit...
        pause > nul
        exit
    )
) else (
    cls
    echo Minecraft-Manager is not installed! It will be installed automatically.
    timeout /t 3 /nobreak > nul
    goto :update
)

:: ==================================================Update==================================================

:update
cls
echo Attempting to obtain the latest Minecraft-Manager...
echo.
echo Log: ====================================================================================================
echo.
curl -0 -L https://raw.githubusercontent.com/Yuri010/minecraft-manager/main/start.bat -o start-new.bat
curl -0 -L https://raw.githubusercontent.com/Yuri010/minecraft-manager/main/bot.bat -o bot-new.bat
curl -0 -L https://raw.githubusercontent.com/Yuri010/minecraft-manager/main/bot.py -o bot-new.py
curl -0 -L https://raw.githubusercontent.com/Yuri010/minecraft-manager/main/updater.bat -o updater-new.bat
if NOT exist config.cfg (
    cls
    echo NOTE: EXISTING CONFIG COULD NOT BE FOUND, DOWNLOADING TEMPLATE...
curl -0 -L https://raw.githubusercontent.com/Yuri010/minecraft-manager/main/config.cfg -o config-new.cfg > nul
)
echo.
echo =========================================================================================================
echo Updating to version %gver% over %lver%...
move start-new.bat start.bat
move bot-new.bat bot.bat
move bot-new.py bot.py
if NOT exist config.cfg (
move config-new.cfg config.cfg
echo.
echo Please note that the configuration file is not set up
echo Any attempts to start the bot or server will most likely fail.
echo.
echo Please refer to the README.md file at https://github.com/Yuri010/Minecraft-Manager/blob/main/README.md
pause
)
timeout 1 > nul
start "" "cmd /c move updater-new.bat updater.bat"
exit