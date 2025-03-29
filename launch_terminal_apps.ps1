$share = "//192.168.86.74/terminal"  # Your Windows IP—COMPUTEROFGOD
$smbUser = "cpusu"
$smbPass = "tiger123"
$sshPass = "tiger1"
$plinkPath = "D:\Program Files\PuTTY\plink.exe"  # Your PuTTY path
$baseDir = "G:\My Drive\Game Dev\terminal"  # Your local sync
$tempDir = "$baseDir\temp"  # Temp folder for generic names

Write-Host "Launching Terminal Apps in new windows..."

# Define SetWindowPos using P/Invoke
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);
}
"@

# Function to set window position
function Set-WindowPosition {
    param ($process, $x, $y, $width, $height)
    $attempts = 5
    $success = $false
    for ($i = 1; $i -le $attempts; $i++) {
        Start-Sleep -Milliseconds 5000  # 5000ms for window to spawn
        $hwnd = $process.MainWindowHandle
        if ($hwnd -ne 0) {
            $result = [Win32]::SetWindowPos($hwnd, [IntPtr]::Zero, $x, $y, $width, $height, 0x0040)
            if ($result) {
                Write-Host "Positioned window at ($x, $y) with size ($width, $height) on attempt $i."
                $success = $true
                break
            } else {
                Write-Host "Attempt ${i}: Failed to position window—SetWindowPos returned false."
            }
        } else {
            Write-Host "Attempt ${i}: Couldn’t position window—handle missing, retrying..."
        }
    }
    if (-not $success) {
        Write-Host "ERROR: Couldn’t position window after $attempts attempts."
    }
}

# Create temp folder if it doesn’t exist
if (-not (Test-Path $tempDir)) {
    New-Item -Path $tempDir -ItemType Directory | Out-Null
    Write-Host "Created temp folder at $tempDir."
}

# Subroutine to find newest file and copy to temp with generic name
function Copy-LatestFile {
    param ($subDir, $genericName)
    $sourceDir = "$baseDir\$subDir"
    Write-Host "Searching $sourceDir for the newest file..."
    $latestFile = Get-ChildItem -Path $sourceDir -Filter "*.txt" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latestFile) {
        $sourcePath = $latestFile.FullName
        $destPath = "$tempDir\$genericName"
        Copy-Item -Path $sourcePath -Destination $destPath -Force
        Write-Host "Found $sourcePath, copied to $destPath."
    } else {
        Write-Host "ERROR: No files found in $sourceDir."
        pause
        exit
    }
}

# Find and copy the newest files to temp with generic names
Copy-LatestFile "Server scripts" "server.py"
Copy-LatestFile "Client Scripts" "terminal_client.py"
Copy-LatestFile "Fake Direwolf" "fake_direwolf.py"

# Add a delay to ensure Google Drive syncs the temp folder
Write-Host "Waiting for Google Drive to sync the temp folder..."
Start-Sleep -Seconds 60  # Increased to 60 seconds to allow sync

# Test connectivity with CMD ping
function Test-Host {
    param ($ip)
    Write-Host "Pinging $ip to wake up Google mesh..."
    $attempts = 5
    $success = $false
    for ($i = 1; $i -le $attempts; $i++) {
        $pingResult = ping -n 1 $ip | Select-String "Reply from"
        if ($pingResult) {
            Write-Host "$ip is up on ping $i."
            $success = $true
            break
        } else {
            Write-Host "Ping $i to $ip failed."
        }
        Start-Sleep -Seconds 2
    }
    if (-not $success) {
        Write-Host "ERROR: $ip is still down after $attempts pings! Check your mesh."
        pause
        exit
    }
}

# Test for pi4.lan
Test-Host "192.168.86.69"

# Set console size for PowerShell windows
[Console]::SetWindowSize(80, 24)
[Console]::SetBufferSize(80, 24)

# Server on pi4.lan—top-left (0, 0)
$serverScript = @"
echo "Starting server script..."
smbclient -U $smbUser%$smbPass $share -c "ls" -D "Checking share access"
# Retry loop for smbclient fetch
for i in {1..3}
do
    echo "Attempt \$i to fetch temp/server.py..."
    sshpass -p "$sshPass" smbclient -U $smbUser%$smbPass $share -c "get temp/server.py /tmp/server.py" -D "Fetched server.py" && break
    echo "Fetch attempt \$i failed, retrying..."
    sleep 5
done
ls -l /tmp/server.py
sudo mv /tmp/server.py /home/aprs/terminal/server.py
sudo chmod 775 /home/aprs/terminal/server.py
sudo chgrp users /home/aprs/terminal/server.py
ls -ld /home/aprs/terminal/
pkill -f "python3 /home/aprs/terminal/server.py"
python3 /home/aprs/terminal/server.py
bash
"@
$serverScript | Out-File -FilePath "server.sh" -Encoding ASCII
$serverProcess = Start-Process -FilePath "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -ArgumentList "-NoExit -Command & '$plinkPath' -batch -P 22 -pw $sshPass aprs@192.168.86.69 -m server.sh" -PassThru
Set-WindowPosition -process $serverProcess -x 0 -y 0 -width 800 -height 600

# Fake Direwolf on pi4.lan—top-right (800, 0)
$direwolfPi4Script = @"
echo "Starting direwolf_pi4 script..."
smbclient -U $smbUser%$smbPass $share -c "ls" -D "Checking share access"
# Retry loop for smbclient fetch
for i in {1..3}
do
    echo "Attempt \$i to fetch temp/fake_direwolf.py..."
    sshpass -p "$sshPass" smbclient -U $smbUser%$smbPass $share -c "get temp/fake_direwolf.py /tmp/fake_direwolf.py" -D "Fetched fake_direwolf.py" && break
    echo "Fetch attempt \$i failed, retrying..."
    sleep 5
done
ls -l /tmp/fake_direwolf.py
sudo mv /tmp/fake_direwolf.py /home/aprs/terminal/fake_direwolf.py
sudo chmod 775 /home/aprs/terminal/fake_direwolf.py
sudo chgrp users /home/aprs/terminal/fake_direwolf.py
ls -ld /home/aprs/terminal/
pkill -f "python3 /home/aprs/terminal/fake_direwolf.py"
python3 /home/aprs/terminal/fake_direwolf.py
bash
"@
$direwolfPi4Script | Out-File -FilePath "direwolf_pi4.sh" -Encoding ASCII
$direwolfPi4Process = Start-Process -FilePath "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -ArgumentList "-NoExit -Command & '$plinkPath' -batch -P 22 -pw $sshPass aprs@192.168.86.69 -m direwolf_pi4.sh" -PassThru
Set-WindowPosition -process $direwolfPi4Process -x 800 -y 0 -width 800 -height 600

# Test for debian.lan
Test-Host "192.168.86.49"

# Client on debian.lan—bottom-left (0, 600)
$clientScript = @"
echo "Starting client script..."
smbclient -U $smbUser%$smbPass $share -c "ls" -D "Checking share access"
# Retry loop for smbclient fetch
for i in {1..3}
do
    echo "Attempt \$i to fetch temp/terminal_client.py..."
    sshpass -p "$sshPass" smbclient -U $smbUser%$smbPass $share -c "get temp/terminal_client.py /tmp/terminal_client.py" -D "Fetched terminal_client.py" && break
    echo "Fetch attempt \$i failed, retrying..."
    sleep 5
done
ls -l /tmp/terminal_client.py
echo $sshPass | sudo -S mv /tmp/terminal_client.py /opt/terminal_client/terminal_client.py
sudo chmod 775 /opt/terminal_client/terminal_client.py
sudo chgrp users /opt/terminal_client/terminal_client.py
ls -ld /opt/terminal_client/
pkill -f "python3 /opt/terminal_client/terminal_client.py"
python3 /opt/terminal_client/terminal_client.py
bash
"@
$clientScript | Out-File -FilePath "client.sh" -Encoding ASCII
$clientProcess = Start-Process -FilePath "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -ArgumentList "-NoExit -Command & '$plinkPath' -batch -P 22 -pw $sshPass dtaylor@192.168.86.49 -m client.sh" -PassThru
Set-WindowPosition -process $clientProcess -x 0 -y 600 -width 800 -height 600

# Fake Direwolf on debian.lan—bottom-right (800, 600)
$direwolfDebianScript = @"
echo "Starting direwolf_debian script..."
smbclient -U $smbUser%$smbPass $share -c "ls" -D "Checking share access"
# Retry loop for smbclient fetch
for i in {1..3}
do
    echo "Attempt \$i to fetch temp/fake_direwolf.py..."
    sshpass -p "$sshPass" smbclient -U $smbUser%$smbPass $share -c "get temp/fake_direwolf.py /tmp/fake_direwolf.py" -D "Fetched fake_direwolf.py" && break
    echo "Fetch attempt \$i failed, retrying..."
    sleep 5
done
ls -l /tmp/fake_direwolf.py
sudo mv /tmp/fake_direwolf.py /opt/terminal_client/fake_direwolf.py
sudo chmod 775 /opt/terminal_client/fake_direwolf.py
sudo chgrp users /opt/terminal_client/fake_direwolf.py
ls -ld /opt/terminal_client/
pkill -f "python3 /opt/terminal_client/fake_direwolf.py"
python3 /opt/terminal_client/fake_direwolf.py
bash
"@
$direwolfDebianScript | Out-File -FilePath "direwolf_debian.sh" -Encoding ASCII
$direwolfDebianProcess = Start-Process -FilePath "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -ArgumentList "-NoExit -Command & '$plinkPath' -batch -P 22 -pw $sshPass dtaylor@192.168.86.49 -m direwolf_debian.sh" -PassThru
Set-WindowPosition -process $direwolfDebianProcess -x 800 -y 600 -width 800 -height 600

Write-Host "Done! Check the new PowerShell windows for your apps."
pause