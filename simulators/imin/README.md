# Mock iMin Printer

`imin.py` runs a small FastAPI server that emulates the parts of an iMin printer
integration used by a client application. It displays received print text and
uploaded receipt images in a browser, and records recent WebSocket events.

## Requirements

- Python 3.8 or newer
- FastAPI, Uvicorn, and `python-multipart`

Install the dependencies with:

```bash
python -m pip install fastapi uvicorn python-multipart
```

## Run

From this directory, start the server with:

```bash
python imin.py
```

Open <http://localhost:8000/> to view the dashboard. The server listens on port
`8000` on all network interfaces. To use a different port or host, change the
`uvicorn.run` arguments at the bottom of `imin.py`.

## Endpoints

| Path | Method | Purpose |
| --- | --- | --- |
| `/` | GET | Dashboard showing print text, uploaded images, and other events |
| `/events` | GET | Recent event data as JSON (up to 200 events) |
| `/websocket` | WebSocket | Printer message endpoint; responds to heartbeat and status messages |
| `/upload` | POST | Accepts a multipart file field named `file` and displays it as a receipt image |

The WebSocket handler expects JSON messages with a `type` field. It responds to
type `0` heartbeat messages with `pong`, and type `2` status messages with
`SPI`. Other message types receive a generic response.

## no module needed in odoo to use it
