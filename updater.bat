:: version 1.0.2
@echo off
title Minecraft-Manager Updater
set gver=SOME
set lver=NONE
cd %~dp0
echo %* | findstr /I "install"
if %errorlevel% == 0 goto :install
set debug=off
echo %* | find /I "-debug"
if %errorlevel% == 0 set debug=on
echo %* | find /I "-install"
if %errorlevel% == 0 goto :reqadmin
echo %* | find /I "-modules"
if %errorlevel% == 0 goto :modules
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
    goto :reqadmin
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
curl -0 -L --progress-bar https://raw.githubusercontent.com/Yuri010/minecraft-manager/main/config.cfg -o config-new.cfg
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
if "%newinstall%" == "true" (
    cd ..
    start "" cmd /c del /f updater.bat"
)
exit

:reqadmin
"%SYSTEMROOT%\SysWOW64\cacls.exe" "%SYSTEMROOT%\SysWOW64\config\system"
if '%errorlevel%' NEQ '0' (
echo.
echo For installing the server, Administrative rights will be needed
echo Please accept the UAC Prompt
timeout /t 3 /nobreak > nul
goto UACPrompt
) else ( goto install )

:UACPrompt
echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
set params = %*:"=""
echo UAC.ShellExecute "cmd.exe", "/c ""%~s0"" %params% -install", "", "runas", 1 >> "%temp%\getadmin.vbs"
"%temp%\getadmin.vbs"
del "%temp%\getadmin.vbs"
exit

:install
java --version > nul
if %errorlevel% NEQ 0 (
set javaver=0
) else (
for /F "tokens=3" %%F IN ('java -version 2^>^&1 ^| findstr /i "version"') DO set javaver=%%F
)
py --version > nul
if %errorlevel% NEQ 0 (
set pyver=0
) else (
for /F "tokens=2" %%F IN ('py --version') DO set pyver=%%F
)
cls
echo Installing Minecraft-Manager Step 1/2
if %javaver% LSS "17.0.7" (
echo Downloading Java
curl --progress-bar https://download.oracle.com/java/20/latest/jdk-20_windows-x64_bin.msi -o jdk-20.msi
echo Installing Java
msiexec /i jdk-20.msi /qn /passive
)
if %pyver% LSS 3.0.0 (
echo Downloading Python
curl --progress-bar https://www.python.org/ftp/python/3.11.3/python-3.11.3-amd64.exe -o python-install.exe
echo Installing Python
python-install.exe /passive
)
cls
echo Restarting...
timeout /t 2 /nobreak > nul
start cmd /c "updater.bat -modules"
:modules
cls
echo Downloading Python Modules
py -m pip -q install requests mcrcon discord.py
cls
echo What server would you like to install?
echo. (V)anilla Minecraft
echo. (S)pigot Server (Supports Plugins)
echo. (A)dd later (manually)
choice /C VSA /M "Choice: "
if %errorlevel% == 3 (
    echo By doing this manually, you will have to download and set-up a server.jar
    echo before being able to use the script.
    timeout /t 2 /nobreak > nul
    goto :continue
)
if %errorlevel% == 2 set dwdlk=https://download.getbukkit.org/spigot/spigot-1.19.4.jar & set server=Spigot
if %errorlevel% == 1 set dwdlk=https://piston-data.mojang.com/v1/objects/8f3112a1049751cc472ec13e397eade5336ca7ae/server.jar & set server=Vanilla
echo.
echo.
echo Downloading the %server% Server JAR (1.19.4)
curl --progress-bar %dwdlk% -o server.jar
java -jar server.jar nogui
del eula.txt
echo eula=true > eula.txt
:continue
echo Downloading Ngrok
curl --progress-bar https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip -o ngrok.zip
tar -xf ngrok.zip
del ngrok.zip
cls
:: Could use this to set part of the config and server properties already: https://www.dostips.com/forum/viewtopic.php?t=7167#p46694
echo Please refer to https://github.com/Yuri010/Minecraft-Manager/blob/main/README.md
echo This will guide you through configuring the Discord Application and script configuration
echo.
pause
set newinstall=true
mkdir scripts
cd scripts
goto :update