@echo off
title Saude 360 - Backup rapido
cd /d "%~dp0"
python -c "from services.app_local_service import criar_backup_local; print(criar_backup_local('Manual'))"
pause
