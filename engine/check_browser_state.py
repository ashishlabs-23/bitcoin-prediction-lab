import asyncio
import websockets
import json
import urllib.request

async def inspect():
    with urllib.request.urlopen("http://127.0.0.1:9222/json") as r:
        pages = json.loads(r.read().decode())
    page = next((p for p in pages if p.get("type") == "page"), None)
    ws = await websockets.connect(page["webSocketDebuggerUrl"])

    msg_id = 0
    async def eval_js(expr):
        nonlocal msg_id
        msg_id += 1
        msg = {"id": msg_id, "method": "Runtime.evaluate", "params": {"expression": expr, "returnByValue": True, "awaitPromise": True}}
        await ws.send(json.dumps(msg))
        while True:
            raw = await ws.recv()
            data = json.loads(raw)
            if data.get("id") == msg_id:
                res = data.get("result", {})
                if "exceptionDetails" in res:
                    print("JS EXCEPTION:", res["exceptionDetails"])
                return res.get("result", {}).get("value")

    print("Checking window.api methods:")
    has_api = await eval_js("Object.keys(window.api || {})")
    print("window.api methods:", has_api)
    print("Testing enterSimulatedTrade call in JS:")
    call_enter = await eval_js("""
    (async () => {
        const dec = await window.api.fetchSmartEntryLatest();
        console.log('Dec in browser:', dec);
        if (!dec || dec.status !== 'SMART_ENTRY_AVAILABLE') {
            return { error: 'Not eligible', dec };
        }
        try {
            const res = await window.api.enterSimulatedTrade({ decision_payload: dec, entry_price: 80600 });
            return { success: true, res };
        } catch (e) {
            return { error: e.message, stack: e.stack };
        }
    })()
    """)
    print("call_enter result:", call_enter)
    await ws.close()

asyncio.run(inspect())
