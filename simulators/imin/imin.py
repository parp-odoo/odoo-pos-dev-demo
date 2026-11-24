from fastapi import FastAPI, WebSocket, UploadFile, File, Request
from fastapi.responses import HTMLResponse
import base64
import json
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

events = []

HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Mock iMin Printer</title>

<style>
body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f4f4f4;
}

.header {
    background: #1f2937;
    color: white;
    padding: 16px 24px;
}

.layout {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    padding: 16px;
    height: calc(100vh - 80px);
}

.panel {
    background: white;
    border-radius: 8px;
    overflow-y: auto;
    box-shadow: 0 1px 4px rgba(0,0,0,.1);
    padding: 16px;
}

.panel h2 {
    margin-top: 0;
}

.print-card {
    border-left: 4px solid #10b981;
    background: #f0fdf4;
    padding: 12px;
    margin-bottom: 12px;
    border-radius: 6px;
}

.print-time {
    color: #666;
    font-size: 12px;
    margin-bottom: 8px;
}

.print-text {
    white-space: pre-wrap;
    font-family: monospace;
}

.receipt {
    margin-bottom: 16px;
}

.receipt img {
    width: 100%;
    border: 1px solid #ddd;
}

details {
    margin-bottom: 10px;
    border: 1px solid #ddd;
    border-radius: 6px;
    padding: 8px;
}

summary {
    cursor: pointer;
    font-weight: bold;
}

pre {
    overflow-x: auto;
    white-space: pre-wrap;
    margin: 8px 0 0;
}

.empty {
    color: #888;
    text-align: center;
    padding: 24px;
}
</style>
</head>

<body>

<div class="header">
    <h1>🖨 Mock iMin Printer</h1>
</div>

<div class="layout">

    <div class="panel">
        <h2>Print Text</h2>
        <div id="prints"></div>
    </div>

    <div class="panel">
        <h2>Receipt Images</h2>
        <div id="receipts"></div>
    </div>

</div>

<script>

async function refresh() {
    const r = await fetch('/events');
    const data = await r.json();

    const printEvents = data
        .filter(
            e =>
                e.kind === "WEBSOCKET" &&
                e.payload?.type === 12
        )
        .reverse();

    const imageEvents = data
        .filter(e => e.type === "image")
        .reverse();

    const otherEvents = data
        .filter(e => {
            if (e.type === "image") return false;
            if (e.payload?.type === 12) return false;
            return true;
        })
        .reverse();

    document.getElementById("prints").innerHTML =
        printEvents.length
            ? printEvents.map(e => `
                <div class="print-card">
                    <div class="print-time">
                        ${e.timestamp}
                    </div>

                    <div class="print-text">
${e.payload?.data?.text || "(empty text)"}
                    </div>
                </div>
            `).join("")
            : '<div class="empty">No print text received</div>';

    document.getElementById("receipts").innerHTML =
        imageEvents.length
            ? imageEvents.map(e => `
                <div class="receipt">
                    <div><b>${e.timestamp}</b></div>
                    <div>${e.filename}</div>
                    <img src="${e.data}">
                </div>
            `).join("")
            : '<div class="empty">No receipts</div>';

    document.getElementById("events").innerHTML =
        otherEvents.length
            ? otherEvents.map(e => `
                <details>
                    <summary>
                        ${e.timestamp}
                        ${e.kind}
                        ${e.payload?.type !== undefined
                            ? `(type ${e.payload.type})`
                            : ""}
                    </summary>

                    <pre>${JSON.stringify(e.payload || {}, null, 2)}</pre>
                </details>
            `).join("")
            : '<div class="empty">No events</div>';
}

refresh();
setInterval(refresh, 1000);

</script>

</body>
</html>
"""



@app.get("/")
async def home():
    return HTMLResponse(HTML)


@app.get("/events")
async def get_events():
    if len(events) > 200:
        del events[:-200]
    return events


@app.websocket("/websocket")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    events.append({
        "kind": "CONNECT",
        "payload": {},
        "timestamp": time.strftime("%H:%M:%S")
    })

    try:
        while True:
            msg = await ws.receive_text()

            try:
                data = json.loads(msg)
            except Exception:
                data = {"raw": msg}

            print("WS:", data)

            events.append({
                "kind": "WEBSOCKET",
                "payload": data,
                "timestamp": time.strftime("%H:%M:%S")
            })

            msg_type = data.get("type")

            # heartbeat
            if msg_type == 0:
                await ws.send_json({
                    "data": {
                        "text": "pong",
                        "value": 0,
                        "labelData": {}
                    },
                    "type": 0
                })

            # printer status
            elif msg_type == 2:
                await ws.send_json({
                    "data": {
                        "text": "SPI",
                        "value": 0,
                        "labelData": {}
                    },
                    "type": 2
                })

            else:
                await ws.send_json({
                    "data": {
                        "value": 0
                    },
                    "type": msg_type
                })

    except Exception as e:
        print("WebSocket disconnected:", e)

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    data = await file.read()

    print("UPLOAD")
    print("filename:", file.filename)
    print("content_type:", file.content_type)
    print("size:", len(data))

    image_data = (
        f"data:{file.content_type};base64,"
        + base64.b64encode(data).decode()
    )

    events.append({
        "type": "image",
        "filename": file.filename,
        "data": image_data,
        "timestamp": time.strftime("%H:%M:%S")
    })

    return {
        "code": 0,
        "msg": "success"
    }

def main():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
