@echo off
setlocal EnableDelayedExpansion

set SHARE=//192.168.86.74/terminal
set SMBUSER=cpusu
set SMBPASS=tiger123
set SSHPASS=tiger1
set PLINKPATH="D:\Program Files\PuTTY\plink.exe"
set BASEDIR=G:\My Drive\Game Dev\terminal
set TEMPDIR=%BASEDIR%\temp

echo Launching Terminal Apps in new windows...

:: Create temp folder if it doesn’t exist
if not exist %TEMPDIR% (
    mkdir %TEMPDIR%
    echo Created temp folder at %TEMPDIR%
)

:: Find and copy the newest files to temp with generic names
:: Server scripts
set FOUND=0
echo Checking for files in "%BASEDIR%\Server scripts\*.txt"...
for /f "delims=" %%f in ('dir "%BASEDIR%\Server scripts\*.txt" /b /o-d 2^>nul') do (
    copy "%BASEDIR%\Server scripts\%%f" "%TEMPDIR%\server.py" >nul
    if !errorlevel! equ 0 (
        echo Found "%BASEDIR%\Server scripts\%%f", copied to "%TEMPDIR%\server.py"
        set FOUND=1
        goto :next1
    )
)
:next1
if %FOUND% equ 0 (
    echo ERROR: No .txt files found in "%BASEDIR%\Server scripts"
    pause
    exit /b 1
)

:: Client Scripts
set FOUND=0
echo Checking for files in "%BASEDIR%\Client Scripts\*.txt"...
for /f "delims=" %%f in ('dir "%BASEDIR%\Client Scripts\*.txt" /b /o-d 2^>nul') do (
    copy "%BASEDIR%\Client Scripts\%%f" "%TEMPDIR%\terminal_client.py" >nul
    if !errorlevel! equ 0 (
        echo Found "%BASEDIR%\Client Scripts\%%f", copied to "%TEMPDIR%\terminal_client.py"
        set FOUND=1
        goto :next2
    )
)
:next2
if %FOUND% equ 0 (
    echo ERROR: No .txt files found in "%BASEDIR%\Client Scripts"
    pause
    exit /b 1
)

:: Fake Direwolf
set FOUND=0
echo Checking for files in "%BASEDIR%\Fake Direwolf\*.txt"...
for /f "delims=" %%f in ('dir "%BASEDIR%\Fake Direwolf\*.txt" /b /o-d 2^>nul') do (
    copy "%BASEDIR%\Fake Direwolf\%%f" "%TEMPDIR%\fake_direwolf.py" >nul
    if !errorlevel! equ 0 (
        echo Found "%BASEDIR%\Fake Direwolf\%%f", copied to "%TEMPDIR%\fake_direwolf.py"
        set FOUND=1
        goto :next3
    )
)
:next3
if %FOUND% equ 0 (
    echo ERROR: No .txt files found in "%BASEDIR%\Fake Direwolf"
    pause
    exit /b 1
)

:: Test connectivity with CMD ping
echo Pinging 192.168.86.69...
set SUCCESS=0
for /l %%i in (1,1,10) do (
    ping -n 1 -w 2000 192.168.86.69 | find "Reply from" >nul
    if !errorlevel! equ 0 (
        echo 192.168.86.69 is up on ping %%i.
        set SUCCESS=1
        goto :ping1_done
    ) else (
        echo Ping %%i to 192.168.86.69 failed.
    )
    timeout /t 3 /nobreak
)
:ping1_done
if %SUCCESS% equ 0 (
    echo ERROR: 192.168.86.69 is down after 10 pings! Check your mesh.
    pause
    exit /b 1
)

:: Test SSH authentication to pi4.lan
echo Testing SSH to 192.168.86.69...
%PLINKPATH% -batch -P 22 -pw %SSHPASS% aprs@192.168.86.69 "echo SSH test successful"
if !errorlevel! neq 0 (
    echo ERROR: SSH authentication to 192.168.86.69 failed. Check password or SSH configuration.
    pause
    exit /b 1
)

:: Unmount and mount the SMB share on pi4.lan
%PLINKPATH% -batch -P 22 -pw %SSHPASS% aprs@192.168.86.69 "sudo umount /mnt/terminal 2>/dev/null; sudo mkdir -p /mnt/terminal; sudo mount -t cifs -o username=cpusu,password=tiger123 //192.168.86.74/terminal /mnt/terminal"

:: Server on pi4.lan—top-left (0, 0)
start "Server" /I cmd /k "mode con: cols=80 lines=24 & echo Copying server.py... & %PLINKPATH% -batch -P 22 -pw %SSHPASS% aprs@192.168.86.69 \"cp /mnt/terminal/temp/server.py /home/aprs/terminal/server.py\" & echo Killing existing server process... & %PLINKPATH% -batch -P 22 -pw %SSHPASS% aprs@192.168.86.69 \"pkill -f 'python3 /home/aprs/terminal/server.py'\" & echo Running server.py... & %PLINKPATH% -batch -P 22 -pw %SSHPASS% aprs@192.168.86.69 \"python3 /home/aprs/terminal/server.py\" & %PLINKPATH% -batch -P 22 -pw %SSHPASS% aprs@192.168.86.69 \"bash\" & echo Press any key to close this window... & pause"

:: Fake Direwolf on pi4.lan—top-right (800, 0)
start "Direwolf_pi4" /I cmd /k "mode con: cols=80 lines=24 & echo Copying fake_direwolf.py... & %PLINKPATH% -batch -P 22 -pw %SSHPASS% aprs@192.168.86.69 \"cp /mnt/terminal/temp/fake_direwolf.py /home/aprs/terminal/fake_direwolf.py\" & echo Killing existing fake_direwolf process... & %PLINKPATH% -batch -P 22 -pw %SSHPASS% aprs@192.168.86.69 \"pkill -f 'python3 /home/aprs/terminal/fake_direwolf.py'\" & echo Running fake_direwolf.py... & %PLINKPATH% -batch -P 22 -pw %SSHPASS% aprs@192.168.86.69 \"python3 /home/aprs/terminal/fake_direwolf.py\" & %PLINKPATH% -batch -P 22 -pw %SSHPASS% aprs@192.168.86.69 \"bash\" & echo Press any key to close this window... & pause"

:: Test connectivity for debian.lan
echo Pinging 192.168.86.49...
set SUCCESS=0
for /l %%i in (1,1,10) do (
    ping -n 1 -w 2000 192.168.86.49 | find "Reply from" >nul
    if !errorlevel! equ 0 (
        echo 192.168.86.49 is up on ping %%i.
        set SUCCESS=1
        goto :ping2_done
    ) else (
        echo Ping %%i to 192.168.86.49 failed.
    )
    timeout /t 3 /nobreak
)
:ping2_done
if %SUCCESS% equ 0 (
    echo ERROR: 192.168.86.49 is down after 10 pings! Check your mesh.
    pause
    exit /b 1
)

:: Test SSH authentication to debian.lan
echo Testing SSH to 192.168.86.49...
%PLINKPATH% -batch -P 22 -pw %SSHPASS% dtaylor@192.168.86.49 "echo SSH test successful"
if !errorlevel! neq 0 (
    echo ERROR: SSH authentication to 192.168.86.49 failed. Check password or SSH configuration.
    pause
    exit /b 1
)

:: Unmount and mount the SMB share on debian.lan
%PLINKPATH% -batch -P 22 -pw %SSHPASS% dtaylor@192.168.86.49 "sudo umount /mnt/terminal 2>/dev/null; sudo mkdir -p /mnt/terminal; sudo mount -t cifs -o username=cpusu,password=tiger123 //192.168.86.74/terminal /mnt/terminal"

:: Client on debian.lan—bottom-left (0, 600)
start "Client" /I cmd /k "mode con: cols=80 lines=24 & echo Copying terminal_client.py... & %PLINKPATH% -batch -P 22 -pw %SSHPASS% dtaylor@192.168.86.49 \"sudo cp /mnt/terminal/temp/terminal_client.py /opt/terminal_client/terminal_client.py\" & echo Killing existing terminal_client process... & %PLINKPATH% -batch -P 22 -pw %SSHPASS% dtaylor@192.168.86.49 \"sudo pkill -f 'python3 /opt/terminal_client/terminal_client.py'\" & echo Running terminal_client.py... & %PLINKPATH% -batch -P 22 -pw %SSHPASS% dtaylor@192.168.86.49 \"sudo python3 /opt/terminal_client/terminal_client.py\" & %PLINKPATH% -batch -P 22 -pw %SSHPASS% dtaylor@192.168.86.49 \"bash\" & echo Press any key to close this window... & pause"

:: Fake Direwolf on debian.lan—bottom-right (800, 600)
start "Direwolf_debian" /I cmd /k "mode con: cols=80 lines=24 & echo Copying fake_direwolf.py... & %PLINKPATH% -batch -P 22 -pw %SSHPASS% dtaylor@192.168.86.49 \"sudo cp /mnt/terminal/temp/fake_direwolf.py /opt/terminal_client/fake_direwolf.py\" & echo Killing existing fake_direwolf process... & %PLINKPATH% -batch -P 22 -pw %SSHPASS% dtaylor@192.168.86.49 \"sudo pkill -f 'python3 /opt/terminal_client/fake_direwolf.py'\" & echo Running fake_direwolf.py... & %PLINKPATH% -batch -P 22 -pw %SSHPASS% dtaylor@192.168.86.49 \"sudo python3 /opt/terminal_client/fake_direwolf.py\" & %PLINKPATH% -batch -P 22 -pw %SSHPASS% dtaylor@192.168.86.49 \"bash\" & echo Press any key to close this window... & pause"

echo Done! Check the new windows for your apps.
pause