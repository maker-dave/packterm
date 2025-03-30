@echo off

REM Update terminal repository
cd /d "G:\My Drive\GameDev\terminal"
echo Updating terminal repository...
git fetch --prune origin
git pull origin main || goto :pull_error_terminal
git add .
git commit -m "Auto-sync terminal from Windows %date% %time%" || goto :no_changes_terminal
git push origin main
goto :terminal_done

:pull_error_terminal
echo Error pulling terminal from GitHub. Check conflicts or connectivity.
goto :terminal_done

:no_changes_terminal
echo No changes to commit in terminal locally.
git push origin main

:terminal_done

REM Update starship repository
cd /d "G:\My Drive\GameDev\starship"
echo Updating starship repository...
git fetch --prune origin
git pull origin main || goto :pull_error_starship
git add .
git commit -m "Auto-sync starship from Windows %date% %time%" || goto :no_changes_starship
git push origin main
goto :end

:pull_error_starship
echo Error pulling starship from GitHub. Check conflicts or connectivity.
goto :end

:no_changes_starship
echo No changes to commit in starship locally.
git push origin main

:end
