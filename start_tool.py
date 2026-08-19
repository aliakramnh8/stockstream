import webbrowser
import threading
import time
import sys
import os
import uvicorn

def open_browser():
    time.sleep(1.2)
    url = "http://127.0.0.1:8000"
    print(f"\n=======================================================")
    print(f"🚀 StockStream is running at: {url}")
    print(f"=======================================================\n")
    webbrowser.open(url)

if __name__ == "__main__":
    # Ensure current directory is in sys.path
    root_dir = os.path.abspath(os.path.dirname(__file__))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, log_level="info")
