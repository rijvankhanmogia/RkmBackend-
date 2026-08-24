
"""
Simple FastAPI service.

Endpoints
---------
GET  /      -> health check
POST /ask   -> takes auth headers + {"Prompt": "..."} body, returns an answer

Run:
    pip install fastapi uvicorn
    python main.py
    # or: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import time
import uuid
import logging

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("ask-service")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Keep the real key in an env var in production; the literal is only a fallback.
API_KEY = os.getenv("API_KEY", "wisuedjjd134")

app = FastAPI(
    title="Ask Service",
    version="1.0.0",
    description="Health check + prompt endpoint",
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    Prompt: str = Field(..., min_length=1, description="User prompt text")

    model_config = {
        "json_schema_extra": {
            "example": {"Prompt": "hi google how are you?"}
        }
    }


class AskResponse(BaseModel):
    status: str
    requestId: str
    userId: str
    username: str
    flowId: str
    prompt: str
    response: str
    latencyMs: int


# ---------------------------------------------------------------------------
# Core logic  (replace this with your real model / downstream call)
# ---------------------------------------------------------------------------

def generate_answer(prompt: str, user_id: str, username: str, flow_id: str) -> str:
    """
    Hook your LLM / backend call in here.
    Right now it just echoes a canned reply so you can verify the plumbing.
    """
    return f"Hello {username}, you asked: '{prompt}'. I'm working fine!"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
async def health():
    """Quick check that the server is alive."""
    return {
        "status": "ok",
        "message": "Server is up and running",
        "service": "ask-service",
        "timestamp": int(time.time()),
    }


@app.post("/ask", response_model=AskResponse)
async def ask(
    payload: AskRequest,
    apikey: str = Header(..., alias="apikey"),
    user_id: str = Header(..., alias="UserId"),
    username: str = Header(..., alias="Username"),
    flow_id: str = Header(..., alias="Flow-id"),
):
    started = time.perf_counter()
    request_id = str(uuid.uuid4())

    # --- auth ---
    if apikey != API_KEY:
        logger.warning("Invalid apikey for user=%s reqId=%s", user_id, request_id)
        raise HTTPException(status_code=401, detail="Invalid API key")

    logger.info(
        "reqId=%s user=%s (%s) flow=%s prompt=%r",
        request_id, user_id, username, flow_id, payload.Prompt,
    )

    # --- work ---
    try:
        answer = generate_answer(payload.Prompt, user_id, username, flow_id)
    except Exception as exc:                      # noqa: BLE001
        logger.exception("reqId=%s failed: %s", request_id, exc)
        raise HTTPException(status_code=500, detail="Failed to process prompt")

    return AskResponse(
        status="success",
        requestId=request_id,
        userId=user_id,
        username=username,
        flowId=flow_id,
        prompt=payload.Prompt,
        response=answer,
        latencyMs=int((time.perf_counter() - started) * 1000),
    )


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "code": exc.status_code, "message": exc.detail},
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
