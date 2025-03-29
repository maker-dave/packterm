@echo on
setlocal enabledelayedexpansion
set PSCP="D:\Program Files\PuTTY\pscp.exe"
set PLINK="D:\Program Files\PuTTY\plink.exe"
set DEST=G:\My Drive\Game Dev\terminal\Logs
set CSV_DEST=G:\My Drive\Game Dev\terminal\CVS
set LOG_FILE=G:\My Drive\Game Dev\terminal\Logs\GrabLogs.log
set TEMP_LIST=%TEMP%\csv_list.txt

:: Ensure directories exist
if not exist "%DEST%" mkdir "%DEST%"
if not exist "%CSV_DEST%" mkdir "%CSV_DEST%"

:: Log startup
echo %DATE% %TIME%: Starting GrabLogs.bat >> "%LOG_FILE%"

:: Resolve IPs dynamically
echo %DATE% %TIME%: Resolving pi4.lan IP >> "%LOG_FILE%"
for /f "tokens=2 delims=[]" %%i in ('ping pi4.lan -n 1 ^| findstr /r /c:"\[.*\]"') do set "PI4_IP=%%i"
if defined PI4_IP (
    echo %DATE% %TIME%: pi4.lan resolved to %PI4_IP% >> "%LOG_FILE%"
    echo y | %PLINK% -batch -P 22 -pw xxxxxx aprs@%PI4_IP% "exit" >> "%LOG_FILE%" 2>&1
    ping %PI4_IP% -n 6 >> "%LOG_FILE%" 2>&1 && set "PI4_HOST=%PI4_IP%" || set "PI4_HOST=pi4.lan"
) else (
    echo %DATE% %TIME%: WARN: Failed to resolve pi4.lan IP, using hostname >> "%LOG_FILE%"
    set "PI4_HOST=pi4.lan"
)
echo %DATE% %TIME%: Resolving debian.lan IP >> "%LOG_FILE%"
for /f "tokens=2 delims=[]" %%i in ('ping debian.lan -n 1 ^| findstr /r /c:"\[.*\]"') do set "DEBIAN_IP=%%i"
if defined DEBIAN_IP (
    echo %DATE% %TIME%: debian.lan resolved to %DEBIAN_IP% >> "%LOG_FILE%"
    echo y | %PLINK% -batch -P 22 -pw xxxxxx dtaylor@%DEBIAN_IP% "exit" >> "%LOG_FILE%" 2>&1
    ping %DEBIAN_IP% -n 6 >> "%LOG_FILE%" 2>&1 && set "DEBIAN_HOST=%DEBIAN_IP%" || set "DEBIAN_HOST=debian.lan"
) else (
    echo %DATE% %TIME%: WARN: Failed to resolve debian.lan IP, using hostname >> "%LOG_FILE%"
    set "DEBIAN_HOST=debian.lan"
)

:: Switch to G: drive
G:
cd "\My Drive\Game Dev\terminal\Logs"

:: Fetch full logs
call :fetch_file "aprs@%PI4_HOST%:/home/aprs/terminal/server_data/server.log" "%DEST%\server.log.txt" "server.log"
call :fetch_file "dtaylor@%DEBIAN_HOST%:/opt/terminal_client/skippys_messups.log" "%DEST%\skippys_messups.log.txt" "skippys_messups.log"

:: Fetch all CSVs from server_data
echo %DATE% %TIME%: Fetching all .csv files from server_data >> "%LOG_FILE%"
%PLINK% -batch -P 22 -pw xxxxxx aprs@%PI4_HOST% "ls -1 /home/aprs/terminal/server_data/*.csv" > "%TEMP_LIST%" 2>> "%LOG_FILE%"
if exist "%TEMP_LIST%" (
    for /f "tokens=*" %%f in ('type "%TEMP_LIST%"') do (
        call :fetch_file "aprs@%PI4_HOST%:%%f" "%CSV_DEST%\%%~nxf" "%%~nxf"
    )
    echo %DATE% %TIME%: Fetched CSVs with sizes: >> "%LOG_FILE%"
    for %%f in ("%CSV_DEST%\*.csv") do (
        for %%A in ("%%f") do echo %%~nxf - %%~zA bytes >> "%LOG_FILE%"
    )
    del "%TEMP_LIST%"
) else (
    echo %DATE% %TIME%: WARN: Failed to list .csv files >> "%LOG_FILE%"
)

:: Log completion
echo %DATE% %TIME%: GrabLogs.bat completed >> "%LOG_FILE%"

:: Return to C:
C:
goto :eof

:: Subroutine to fetch files with 6 retries (2s delay)
:fetch_file
set "SOURCE=%~1"
set "TARGET=%~2"
set "NAME=%~3"
echo %DATE% %TIME%: Fetching %NAME% >> "%LOG_FILE%"
%PSCP% -P 22 -pw xxxxxx "%SOURCE%" "%TARGET%" >> "%LOG_FILE%" 2>&1 && goto :fetch_done
echo %DATE% %TIME%: WARN: Failed to fetch %NAME%, retrying (1/6) in 2s >> "%LOG_FILE%"
timeout /t 2 >nul
%PSCP% -P 22 -pw xxxxxx "%SOURCE%" "%TARGET%" >> "%LOG_FILE%" 2>&1 && goto :fetch_done
echo %DATE% %TIME%: WARN: Failed to fetch %NAME%, retrying (2/6) in 2s >> "%LOG_FILE%"
timeout /t 2 >nul
%PSCP% -P 22 -pw xxxxxx "%SOURCE%" "%TARGET%" >> "%LOG_FILE%" 2>&1 && goto :fetch_done
echo %DATE% %TIME%: WARN: Failed to fetch %NAME%, retrying (3/6) in 2s >> "%LOG_FILE%"
timeout /t 2 >nul
%PSCP% -P 22 -pw xxxxxx "%SOURCE%" "%TARGET%" >> "%LOG_FILE%" 2>&1 && goto :fetch_done
echo %DATE% %TIME%: WARN: Failed to fetch %NAME%, retrying (4/6) in 2s >> "%LOG_FILE%"
timeout /t 2 >nul
%PSCP% -P 22 -pw xxxxxx "%SOURCE%" "%TARGET%" >> "%LOG_FILE%" 2>&1 && goto :fetch_done
echo %DATE% %TIME%: WARN: Failed to fetch %NAME%, retrying (5/6) in 2s >> "%LOG_FILE%"
timeout /t 2 >nul
%PSCP% -P 22 -pw xxxxxx "%SOURCE%" "%TARGET%" >> "%LOG_FILE%" 2>&1 && goto :fetch_done
echo %DATE% %TIME%: WARN: Failed to fetch %NAME%, retrying (6/6) in 2s >> "%LOG_FILE%"
timeout /t 2 >nul
%PSCP% -P 22 -pw xxxxxx "%SOURCE%" "%TARGET%" >> "%LOG_FILE%" 2>&1 && goto :fetch_done
echo %DATE% %TIME%: ERROR: Failed to fetch %NAME% after 6 retries >> "%LOG_FILE%"
:fetch_done
for %%A in ("%TARGET%") do set "SIZE=%%~zA"
echo %DATE% %TIME%: Fetched %NAME% - !SIZE! bytes >> "%LOG_FILE%"
exit /b