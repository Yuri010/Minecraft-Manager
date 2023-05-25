:: version 1.0.1
@echo off
title Discord - Minecraft Manager Bot
echo %* | find /I "-debug"
set debug=off
if /I "%errorlevel%" EQU "0" set debug=on
cd %~dp0
python bot.py
if /I "%debug%" EQU "on" pause
exit