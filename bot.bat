:: version 1.1
@echo off
title Discord - Minecraft Manager Bot
set debug=off
echo %* | find /I "-debug"
if /I "%errorlevel%" EQU "0" set debug=on
cd %~dp0
py bot.py
if /I "%debug%" EQU "on" pause
exit