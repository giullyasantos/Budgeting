from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from pywebpush import webpush, WebPushException
import json
import os
from datetime import datetime, timedelta, timezone

app = FastAPI(title="Balance Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Storage: Upstash Redis ──
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

VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY  = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_CLAIMS      = {"sub": "mailto:notifications@balancetracker.app"}

MONTH_NAMES = ["January","February","March","April","May","June",
               "July","August","September","October","November","December"]

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


def get_subscriptions():
    if not (_USE_KV and _redis):
        return []
    try:
        raw = _redis.get("push_subscriptions")
        return json.loads(raw) if raw else []
    except Exception:
        return []


def send_push(subscription, title, body):
    try:
        webpush(
            subscription_info=subscription,
            data=json.dumps({"title": title, "body": body}),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS,
        )
    except WebPushException:
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


@app.post("/api/subscribe")
async def subscribe(request: Request):
    sub = await request.json()
    if not (_USE_KV and _redis):
        return {"error": "KV not configured"}
    try:
        raw = _redis.get("push_subscriptions")
        subs = json.loads(raw) if raw else []
        endpoint = sub.get("endpoint")
        if not any(s.get("endpoint") == endpoint for s in subs):
            subs.append(sub)
            _redis.set("push_subscriptions", json.dumps(subs))
        return {"message": "Subscribed"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/notify")
async def notify(test: bool = False, test_bill: bool = False, test_sunday: bool = False):
    subs = get_subscriptions()
    if not subs:
        return {"message": "No subscribers — open the app and tap Enable Notifications first"}

    if test:
        for sub in subs:
            send_push(sub, "Test Notification ✅", "Push notifications are working!")
        return {"message": f"Test sent to {len(subs)} subscriber(s)"}

    if test_bill:
        for sub in subs:
            send_push(sub, "Bill Due Tomorrow 💸", "Light bill — $180.00 due June 22")
        return {"message": f"Test bill reminder sent to {len(subs)} subscriber(s)"}

    if test_sunday:
        for sub in subs:
            send_push(sub, "Weekly Budget Review 📊", "Take a moment to review your budget and make sure your numbers look right!")
        return {"message": f"Test Sunday reminder sent to {len(subs)} subscriber(s)"}

    tracker = load_data()
    recurring = tracker.get("recurringTransactions", [])

    now      = datetime.now(timezone.utc)
    tomorrow = now + timedelta(days=1)
    tom_day  = tomorrow.day
    is_sunday = now.weekday() == 6

    sent = 0

    for rt in recurring:
        if rt.get("type") != "expense":
            continue
        if rt.get("frequency") == "monthly" and rt.get("dayOfMonth") == tom_day:
            if rt.get("endDate"):
                end = datetime.fromisoformat(rt["endDate"].replace("Z", "+00:00"))
                if tomorrow > end:
                    continue
            amount = rt.get("amount", 0)
            desc   = rt.get("description", "Bill")
            for sub in subs:
                send_push(sub, "Bill Due Tomorrow 💸",
                          f"{desc} — ${amount:,.2f} due {MONTH_NAMES[tomorrow.month-1]} {tom_day}")
            sent += 1

    if is_sunday:
        for sub in subs:
            send_push(sub, "Weekly Budget Review 📊",
                      "Take a moment to review your budget and make sure your numbers look right!")
        sent += 1

    return {"message": f"Sent {sent} notification(s)"}
