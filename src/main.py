import json
import os
import sys
from asyncio import sleep
from fastapi import FastAPI, Request, Response
import requests
import signal
app = FastAPI(title="resilience-test")
dapr_port = os.getenv("DAPR_HTTP_PORT", 5002)

pid = os. getpid()
print(f"running on pid {pid}")


@app.post("/orders")
async def post_invoke_order(request: Request):
    payload = await request.json()
    data = payload['data']
    print(f"got dapr message: {data}")
    wait_secs = data.get("wait_secs") or 0
    await sleep(wait_secs)
    status_string = data.get("status_string")
    print(status_string)
    return_obj = {}
    if status_string:
        return_obj["status"] = status_string

    status_http_code = data.get("status_http_code") or 200
    if data.get("force_fail"):
        os.kill(pid, signal.SIGKILL)
    print(f'returning status {status_http_code} and data {return_obj}')
    return Response(
        status_code=status_http_code,
        content=json.dumps(return_obj),
        headers={'content-type': 'application/json'}
    )


@app.get("/invoke-order")
def get_invoke_order(force_fail: bool = False, wait_secs: int = 0, status_string: str = None, status_http_code: int = 0, msg_count: int = 1):
    for i in range(msg_count):
        print("publishing message")
        requests.post(
            f"http://localhost:{dapr_port}/v1.0/publish/test/orders",
            json={
                "force_fail": force_fail,
                "wait_secs": wait_secs,
                "status_string": status_string,
                "status_http_code": status_http_code
            }
        )
