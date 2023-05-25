:: version 1.0.0
@echo off
title Minecraft-Manager Updater
set pat=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
set gver=SOME
set lver=NONE
cd %~dp0
echo %* | findstr /I "install"
if %errorlevel% == 0 goto :install
echo %* | findstr /I "update"
if %errorlevel% == 0 goto :update

:: ==================================================Obtain==================================================
curl --output releases.tmp -L -H "Authorization: token %pat%" https://api.github.com/repos/yuri010/minecraft-manager/releases
pause
call :gver
echo gver = %gver%
call :gvercleanup
echo clean gver = %gver%
call :lver
echo lver = %lver%
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
curl -H "Authorization: token %pat%" -0 -L https://raw.githubusercontent.com/Yuri010/minecraft-manager/main/start.bat -o start-new.bat
curl -H "Authorization: token %pat%" -0 -L https://raw.githubusercontent.com/Yuri010/minecraft-manager/main/bot.bat -o bot-new.bat
curl -H "Authorization: token %pat%" -0 -L https://raw.githubusercontent.com/Yuri010/minecraft-manager/main/bot.py -o bot-new.py
curl -H "Authorization: token %pat%" -0 -L https://raw.githubusercontent.com/Yuri010/minecraft-manager/main/updater.bat -o updater-new.bat
curl -H "Authorization: token %pat%" -0 -L https://raw.githubusercontent.com/Yuri010/minecraft-manager/main/config.cfg -o config-new.cfg
echo.
echo =========================================================================================================
echo Updating to version %gver% over %lver%...
move start-new.bat start.bat
move bot-new.bat bot.bat
move bot-new.py bot.py
move config-new.cfg config.cfg
timeout 1 > nul
start "" "cmd /c move updater-new.bat updater.bat"
exit