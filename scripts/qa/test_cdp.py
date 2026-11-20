import asyncio
import json
import urllib.request
import websockets

async def check():
    with urllib.request.urlopen("http://127.0.0.1:9222/json") as resp:
        tabs = json.loads(resp.read().decode())
    target = next((t for t in tabs if "8000" in t.get("url", "")), None)
    if not target:
        print("No target tab on 8000")
        return
    ws_url = target["webSocketDebuggerUrl"]
    ws = await websockets.connect(ws_url)
    
    msg_id = 0
    async def cmd(m, p=None):
        nonlocal msg_id
        msg_id += 1
        cid = msg_id
        payload = {"id": cid, "method": m, "params": p or {}}
        await ws.send(json.dumps(payload))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == cid:
                return r

    await cmd("Runtime.enable")
    res = await cmd("Runtime.evaluate", {"expression": "document.querySelector('#tab-btn-smart-entry')?.innerText", "returnByValue": True})
    print("Tab btn text:", res.get("result", {}).get("result", {}).get("value"))

    res2 = await cmd("Runtime.evaluate", {"expression": "!!document.getElementById('historical-research-evidence-panel')", "returnByValue": True})
    print("Panel exists:", res2.get("result", {}).get("result", {}).get("value"))

    res3 = await cmd("Runtime.evaluate", {"expression": "Array.from(document.querySelectorAll('button')).map(b => b.id || b.innerText).slice(0, 20)", "returnByValue": True})
    print("Buttons:", res3.get("result", {}).get("result", {}).get("value"))
    
    await ws.close()

asyncio.run(check())

