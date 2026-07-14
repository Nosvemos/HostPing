@echo off
title HostPing Stock Tracker
echo =========================================
echo       Starting HostPing Spider...
echo =========================================
echo.

cd /d "%~dp0"
scrapy crawl dynamic_spider

echo.
echo =========================================
echo       Scan Completed!
echo =========================================
pause
