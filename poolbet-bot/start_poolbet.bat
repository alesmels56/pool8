@echo off
echo =========================================
echo Avviando PoolBet Bot - Deployment Globale
echo =========================================

echo [1/3] Avvio Main Bot (main.py)...
start "PoolBet Bot (Main)" cmd /c "python main.py"
timeout /t 2 >nul

echo [2/3] Avvio Worker Scheduler...
start "PoolBet Scheduler" cmd /c "python workers/worker_scheduler.py"
timeout /t 2 >nul

echo [3/3] Avvio Worker Blockchain...
start "PoolBet Blockchain" cmd /c "python workers/worker_blockchain.py"

echo.
echo Tutti i moduli sono stati avviati!
echo Troverai 3 finestre terminale separate per il monitoraggio dei log.
echo Chiudi le singole finestre per terminare i processi.
pause
