from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import os

app = FastAPI(title="Balance Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Storage: Vercel KV (upstash-redis) when env vars are set ──
try:
    from upstash_redis import Redis as _URedis
    _kv_url   = os.environ.get("KV_REST_API_URL", "")
    _kv_token = os.environ.get("KV_REST_API_TOKEN", "")
    if _kv_url and _kv_token:
        _redis  = _URedis(url=_kv_url, token=_kv_token)
        _USE_KV = True
    else:
        _redis  = None
        _USE_KV = False
except Exception:
    _redis  = None
    _USE_KV = False

_EMPTY: Dict[str, Any] = {
    "startingBalance": 0,
    "months": {},
    "savingsGoals": {},
    "recurringTransactions": [],
}


def load_data() -> dict:
    if _USE_KV and _redis:
        try:
            raw = _redis.get("tracker_data")
            return json.loads(raw) if raw else dict(_EMPTY)
        except Exception:
            pass
    return dict(_EMPTY)


def save_data(data: dict) -> None:
    if _USE_KV and _redis:
        try:
            _redis.set("tracker_data", json.dumps(data))
        except Exception:
            pass


class TrackerData(BaseModel):
    startingBalance: float
    months: Dict[str, Any]
    savingsGoals: Dict[str, Any]
    recurringTransactions: List[Any]


@app.get("/")
def root():
    return {"message": "Balance Tracker API", "kv_enabled": _USE_KV}


@app.get("/api/data")
def get_all_data():
    return load_data()


@app.post("/api/data")
def update_all_data(data: TrackerData):
    save_data(data.model_dump())
    return {"message": "Data updated successfully"}
