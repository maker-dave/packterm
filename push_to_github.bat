@echo off
cd /d "G:\My Drive\GameDev\terminal"

REM Clean up any bad refs
git fetch --prune origin

REM Pull changes from GitHub
git pull origin main || goto :pull_error

REM Add and commit local changes
git add .
git commit -m "Auto-sync from Windows %date% %time%" || goto :no_changes

REM Push to GitHub
git push origin main
goto :end

:pull_error
echo Error pulling from GitHub. Check conflicts or connectivity.
goto :end

:no_changes
echo No changes to commit locally.
git push origin main
goto :end

:end