@echo off
cd /d "G:\My Drive\GameDev\terminal"
git add .
git commit -m "Auto-push from Windows %date% %time%" || goto :no_changes
git push origin main
goto :end

:no_changes
echo No changes to commit.
:end