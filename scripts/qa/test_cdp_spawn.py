import subprocess
import time
import urllib.request
import json
import os
import shutil

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
user_data = os.path.join(os.environ["TEMP"], "chrome_cdp_test")
if os.path.exists(user_data):
    try:
        shutil.rmtree(user_data)
    except Exception:
        pass

cmd = [
    chrome_path,
    "--headless=new",
    "--remote-debugging-port=9222",
    "--remote-allow-origins=*",
    f"--user-data-dir={user_data}",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-gpu",
    "http://127.0.0.1:8000/"
]

print("Launching Chrome...")
proc = subprocess.Popen(cmd)
try:
    for i in range(20):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen("http://127.0.0.1:9222/json") as resp:
                data = json.loads(resp.read().decode())
                print("CDP Connected successfully! Tabs:", len(data))
                for t in data:
                    print("  Tab:", t.get("title"), t.get("url"))
                break
        except Exception as e:
            pass
    else:
        print("Failed to connect to CDP within 10s")
finally:
    print("Terminating Chrome...")
    proc.terminate()
    proc.wait()
    print("Done.")

