import subprocess
import os
import time
import sys

def kill_python():
    print("--- [CLEANUP] Cleaning processes... ---")
    if sys.platform == "win32":
        # Using taskkill but ignoring errors if not found
        try:
            subprocess.run(["taskkill", "/F", "/IM", "python.exe", "/T"], capture_output=True)
        except:
            pass
    else:
        try:
            subprocess.run(["pkill", "-9", "python"], capture_output=True)
        except:
            pass
    time.sleep(2)

def start_process(file, log_file):
    print(f"--- [START] {file} (Logging to {log_file})... ---")
    f = open(log_file, "a") # Open in append mode
    # For Windows, we might want to use DETACHED_PROCESS to keep it alive even if this script dies
    return subprocess.Popen([sys.executable, file], stdout=f, stderr=f)

if __name__ == "__main__":
    # We don't kill python in the loop, only once at start
    # kill_python() # Removed for safety
    
    # Files to run
    to_run = [
        ("main.py", "bot_main.log"),
        ("worker_blockchain.py", "worker_blockchain.log"),
        ("worker_scheduler.py", "worker_scheduler.log")
    ]
    
    processes = []
    try:
        for file, log in to_run:
            processes.append(start_process(file, log))
            time.sleep(3) # Wait a bit more for stability
        
        print("\n✅ --- INFRASTRUTTURA AVVIATA (PRODUCTION MODE) --- ✅")
        print("Il bot e i worker sono attivi in background.")
        
        # Monitor processes
        while True:
            for i, p in enumerate(processes):
                if p.poll() is not None:
                    print(f"⚠️ [WARNING] Processo {to_run[i][0]} arrestato inaspettatamente! Riavvio in corso...")
                    processes[i] = start_process(to_run[i][0], to_run[i][1])
            time.sleep(15)
            
    except KeyboardInterrupt:
        print("\n--- [STOP] Shutdown... ---")
        for p in processes:
            p.terminate()
        sys.exit(0)
