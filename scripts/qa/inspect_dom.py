import asyncio
import json
import subprocess
import time
import urllib.request
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
proc = subprocess.Popen([CHROME_PATH, "--headless=new", "--remote-debugging-port=9333", "--user-data-dir=C:/temp/c1", "http://127.0.0.1:8000/"])
time.sleep(3)

async def inspect():
    with urllib.request.urlopen("http://127.0.0.1:9333/json") as resp:
        tabs = json.loads(resp.read().decode())
    target = next(t for t in tabs if "8000" in t.get("url", ""))

    ws = await websockets.connect(target["webSocketDebuggerUrl"])
    
    msg_id = 0
    async def cmd(m, p=None):
        nonlocal msg_id
        msg_id += 1
        cid = msg_id
        await ws.send(json.dumps({"id": cid, "method": m, "params": p or {}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == cid:
                return r

    await cmd("Runtime.enable")
    await asyncio.sleep(2)

    res1 = await cmd("Runtime.evaluate", {"expression": "Array.from(document.querySelectorAll('[id*=\"tab\"]')).map(e => e.id)", "returnByValue": True})
    print("Tab IDs in page:", res1.get("result", {}).get("result", {}).get("value"))

    res2 = await cmd("Runtime.evaluate", {"expression": "!!document.getElementById('historical-research-evidence-panel')", "returnByValue": True})
    print("Evidence panel in DOM:", res2.get("result", {}).get("result", {}).get("value"))

    res3 = await cmd("Runtime.evaluate", {"expression": "document.body.innerText.substring(0, 500)", "returnByValue": True})
    print("Body snippet:\n", res3.get("result", {}).get("result", {}).get("value"))

    await ws.close()

try:
    asyncio.run(inspect())
finally:
    proc.terminate()

