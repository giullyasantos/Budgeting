from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pywebpush import webpush, WebPushException
import json
import os
from datetime import datetime, timedelta, timezone

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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


def get_subscriptions():
    if not (_USE_KV and _redis):
        return []
    try:
        raw = _redis.get("push_subscriptions")
        return json.loads(raw) if raw else []
    except Exception:
        return []


def get_tracker_data():
    if not (_USE_KV and _redis):
        return {}
    try:
        raw = _redis.get("tracker_data")
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


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
async def notify(test: bool = False):
    if test:
        subs = get_subscriptions()
        if not subs:
            return {"message": "No subscribers — open the app on your phone first and allow notifications"}
        for sub in subs:
            send_push(sub, "Test Notification ✅", "Push notifications are working!")
        return {"message": f"Test sent to {len(subs)} subscriber(s)"}

    subs = get_subscriptions()
    if not subs:
        return {"message": "No subscribers"}

    tracker = get_tracker_data()
    recurring = tracker.get("recurringTransactions", [])

    # Use UTC today and tomorrow
    now       = datetime.now(timezone.utc)
    tomorrow  = now + timedelta(days=1)
    tom_day   = tomorrow.day
    tom_month = MONTH_NAMES[tomorrow.month - 1]
    tom_year  = tomorrow.year
    is_sunday = now.weekday() == 6

    sent = 0

    # Bill reminders: expenses due tomorrow
    for rt in recurring:
        if rt.get("type") != "expense":
            continue
        if rt.get("frequency") == "monthly" and rt.get("dayOfMonth") == tom_day:
            # Check end date
            if rt.get("endDate"):
                end = datetime.fromisoformat(rt["endDate"].replace("Z", "+00:00"))
                if tomorrow > end:
                    continue
            amount = rt.get("amount", 0)
            desc   = rt.get("description", "Bill")
            for sub in subs:
                send_push(sub, "Bill Due Tomorrow 💸",
                          f"{desc} — ${amount:,.2f} due {tom_month} {tom_day}")
            sent += 1

    # Weekly budget review reminder on Sunday
    if is_sunday:
        for sub in subs:
            send_push(sub, "Weekly Budget Review 📊",
                      "Take a moment to review your budget and make sure your numbers look right!")
        sent += 1

    return {"message": f"Sent {sent} notification(s)"}
