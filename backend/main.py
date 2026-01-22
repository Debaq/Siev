"""
Entry point for PyInstaller or standalone execution.
This script simply starts the SievWorker.
"""
import asyncio
import sys
import os
import multiprocessing

# Ensure output is flushed immediately for Tauri to capture
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

# Add the current directory to sys.path to ensure imports work when packaged
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from worker import SievWorker

async def main_async():
    # In a sidecar environment, we could pass arguments like port
    port = 9999
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
            
    worker = SievWorker(port=port)
    try:
        await worker.start()
    except KeyboardInterrupt:
        await worker.stop()
    except Exception as e:
        print(f"Fatal error in worker: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Required for multiprocessing in packaged executables
    multiprocessing.freeze_support()
    
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        pass