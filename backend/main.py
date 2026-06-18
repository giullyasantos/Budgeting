from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import json
import os
import time

app = FastAPI(title="Balance Tracker API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data file path
DATA_FILE = "tracker_data.json"

# Pydantic models
class Transaction(BaseModel):
    type: str  # income, expense, savings
    description: str
    amount: float
    timestamp: int
    paymentMethod: Optional[str] = None
    goalId: Optional[str] = None
    recurringId: Optional[str] = None

class SavingsGoal(BaseModel):
    name: str
    target: float
    saved: float = 0
    contributions: List[Dict] = []  # Track individual contributions with dates

class RecurringTransaction(BaseModel):
    id: str
    type: str
    description: str
    amount: float
    frequency: str
    startDate: str
    endDate: Optional[str] = None
    dayOfMonth: Optional[int] = None
    paymentMethod: Optional[str] = None

class TrackerData(BaseModel):
    startingBalance: float
    months: Dict[str, Dict[str, List[Transaction]]]
    savingsGoals: Dict[str, SavingsGoal]
    recurringTransactions: List[RecurringTransaction]

# Load data from file
def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {
        "startingBalance": 0,
        "months": {},
        "savingsGoals": {},
        "recurringTransactions": []
    }

# Save data to file
def save_data(data: dict):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.get("/")
def root():
    return {"message": "Balance Tracker API is running!", "version": "1.0"}

@app.get("/api/data")
def get_all_data():
    """Get all tracker data"""
    return load_data()

@app.post("/api/data")
def update_all_data(data: TrackerData):
    """Update all tracker data"""
    save_data(data.dict())
    return {"message": "Data updated successfully"}

@app.get("/api/balance")
def get_current_balance():
    """Get current balance up to today"""
    data = load_data()
    balance = data["startingBalance"]
    
    # Calculate balance up to today
    today = datetime.now()
    months = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    
    for month in months:
        month_key = f"{month}-2026"
        if month_key in data["months"]:
            month_data = data["months"][month_key]
            for day_str in sorted(month_data.keys(), key=int):
                day = int(day_str)
                # Check if this date is in the past or today
                month_num = months.index(month) + 1
                if month_num > today.month or (month_num == today.month and day > today.day):
                    break
                    
                transactions = month_data[day_str]
                for t in transactions:
                    if t["type"] == "income":
                        balance += t["amount"]
                    elif t["type"] in ["expense", "savings"]:
                        balance -= t["amount"]
        
        if months.index(month) >= today.month:
            break
    
    return {"balance": balance, "date": today.isoformat()}

@app.post("/api/transactions/{month}/{day}")
def add_transaction(month: str, day: int, transaction: Transaction):
    """Add a transaction to a specific day"""
    data = load_data()
    month_key = f"{month}-2026"
    day_str = str(day)
    
    if month_key not in data["months"]:
        data["months"][month_key] = {}
    if day_str not in data["months"][month_key]:
        data["months"][month_key][day_str] = []
    
    data["months"][month_key][day_str].append(transaction.dict())
    save_data(data)
    
    return {"message": "Transaction added successfully", "transaction": transaction}

@app.post("/api/transactions/today")
def add_transaction_today(transaction: Transaction):
    """Add a transaction to today's date"""
    today = datetime.now()
    months = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    month = months[today.month - 1]
    day = today.day
    
    return add_transaction(month, day, transaction)

@app.get("/api/transactions/{month}/{day}")
def get_transactions(month: str, day: int):
    """Get all transactions for a specific day"""
    data = load_data()
    month_key = f"{month}-2026"
    day_str = str(day)
    
    if month_key in data["months"] and day_str in data["months"][month_key]:
        return {"transactions": data["months"][month_key][day_str]}
    return {"transactions": []}

@app.delete("/api/transactions/{month}/{day}/{index}")
def delete_transaction(month: str, day: int, index: int):
    """Delete a specific transaction"""
    data = load_data()
    month_key = f"{month}-2026"
    day_str = str(day)
    
    if month_key in data["months"] and day_str in data["months"][month_key]:
        transactions = data["months"][month_key][day_str]
        if 0 <= index < len(transactions):
            deleted = transactions.pop(index)
            if len(transactions) == 0:
                del data["months"][month_key][day_str]
            save_data(data)
            return {"message": "Transaction deleted successfully", "deleted": deleted}
    
    raise HTTPException(status_code=404, detail="Transaction not found")

@app.get("/api/savings-goals")
def get_savings_goals():
    """Get all savings goals"""
    data = load_data()
    return {"goals": data["savingsGoals"]}

@app.post("/api/savings-goals")
def add_savings_goal(goal: SavingsGoal):
    """Add a new savings goal"""
    data = load_data()
    goal_id = str(int(datetime.now().timestamp() * 1000))
    goal_dict = goal.dict()
    if "contributions" not in goal_dict:
        goal_dict["contributions"] = []
    data["savingsGoals"][goal_id] = goal_dict
    save_data(data)
    return {"message": "Savings goal created", "id": goal_id, "goal": goal}

@app.post("/api/savings-goals/{goal_id}/contribute")
def contribute_to_goal(goal_id: str, amount: float, date: Optional[str] = None):
    """Add a contribution to a savings goal"""
    data = load_data()
    if goal_id not in data["savingsGoals"]:
        raise HTTPException(status_code=404, detail="Savings goal not found")

    goal = data["savingsGoals"][goal_id]
    contribution = {
        "amount": amount,
        "date": date if date else datetime.now().isoformat(),
        "timestamp": int(datetime.now().timestamp() * 1000)
    }

    if "contributions" not in goal:
        goal["contributions"] = []
    goal["contributions"].append(contribution)
    goal["saved"] = goal.get("saved", 0) + amount

    save_data(data)
    return {
        "message": "Contribution added",
        "goal_id": goal_id,
        "contribution": contribution,
        "total_saved": goal["saved"],
        "remaining": goal["target"] - goal["saved"]
    }

@app.get("/api/savings-goals/{goal_id}")
def get_savings_goal(goal_id: str):
    """Get a specific savings goal with all contributions"""
    data = load_data()
    if goal_id not in data["savingsGoals"]:
        raise HTTPException(status_code=404, detail="Savings goal not found")

    goal = data["savingsGoals"][goal_id]
    return {
        "id": goal_id,
        "goal": goal,
        "progress_percentage": (goal["saved"] / goal["target"] * 100) if goal["target"] > 0 else 0,
        "remaining": goal["target"] - goal["saved"]
    }

@app.delete("/api/savings-goals/{goal_id}")
def delete_savings_goal(goal_id: str):
    """Delete a savings goal"""
    data = load_data()
    if goal_id in data["savingsGoals"]:
        deleted = data["savingsGoals"].pop(goal_id)
        save_data(data)
        return {"message": "Savings goal deleted", "deleted": deleted}
    raise HTTPException(status_code=404, detail="Savings goal not found")

@app.get("/api/savings-goals/{goal_id}/contributions")
def get_goal_contributions(goal_id: str, date: Optional[str] = Query(None)):
    """Get contributions for a goal, optionally filtered by date"""
    data = load_data()
    if goal_id not in data["savingsGoals"]:
        raise HTTPException(status_code=404, detail="Savings goal not found")

    goal = data["savingsGoals"][goal_id]
    contributions = goal.get("contributions", [])

    if date:
        # Filter contributions by specific date
        contributions = [c for c in contributions if c["date"].startswith(date)]

    return {
        "goal_id": goal_id,
        "goal_name": goal["name"],
        "contributions": contributions,
        "total_on_date": sum(c["amount"] for c in contributions) if date else goal.get("saved", 0)
    }

@app.get("/api/recurring-transactions")
def get_recurring_transactions():
    """Get all recurring transactions"""
    data = load_data()
    return {"recurring": data["recurringTransactions"]}

@app.post("/api/recurring-transactions")
def add_recurring_transaction(recurring: RecurringTransaction):
    """Add a new recurring transaction"""
    data = load_data()
    data["recurringTransactions"].append(recurring.dict())
    save_data(data)
    return {"message": "Recurring transaction created", "recurring": recurring}

@app.delete("/api/recurring-transactions/{recurring_id}")
def delete_recurring_transaction(recurring_id: str):
    """Delete a recurring transaction"""
    data = load_data()
    original_len = len(data["recurringTransactions"])
    data["recurringTransactions"] = [
        r for r in data["recurringTransactions"] if r["id"] != recurring_id
    ]
    
    if len(data["recurringTransactions"]) < original_len:
        save_data(data)
        return {"message": "Recurring transaction deleted"}
    raise HTTPException(status_code=404, detail="Recurring transaction not found")

@app.post("/api/starting-balance")
def set_starting_balance(balance: float):
    """Set the starting balance"""
    data = load_data()
    data["startingBalance"] = balance
    save_data(data)
    return {"message": "Starting balance updated", "balance": balance}

def get_last_business_day(year: int, month: int) -> int:
    """Get the last business day (Mon-Fri) of a given month"""
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    last_date = datetime(year, month, last_day)

    # If Saturday (5), go back to Friday
    if last_date.weekday() == 5:
        return last_day - 1
    # If Sunday (6), go back to Friday
    elif last_date.weekday() == 6:
        return last_day - 2
    else:
        return last_day

@app.get("/api/last-business-day/{year}/{month}")
def get_last_business_day_api(year: int, month: int):
    """Get the last business day of a month"""
    day = get_last_business_day(year, month)
    return {"year": year, "month": month, "lastBusinessDay": day}

# Natural language endpoint for AI agent
@app.post("/api/ai/add-expense")
def ai_add_expense(description: str, amount: float, payment_method: Optional[str] = None):
    """AI-friendly endpoint to add an expense"""
    transaction = Transaction(
        type="expense",
        description=description,
        amount=amount,
        timestamp=int(datetime.now().timestamp() * 1000),
        paymentMethod=payment_method
    )
    result = add_transaction_today(transaction)
    balance = get_current_balance()
    return {
        "message": f"Added ${amount} expense for {description}",
        "new_balance": balance["balance"],
        "transaction": transaction
    }

@app.post("/api/ai/add-income")
def ai_add_income(description: str, amount: float):
    """AI-friendly endpoint to add income"""
    transaction = Transaction(
        type="income",
        description=description,
        amount=amount,
        timestamp=int(datetime.now().timestamp() * 1000)
    )
    result = add_transaction_today(transaction)
    balance = get_current_balance()
    return {
        "message": f"Added ${amount} income for {description}",
        "new_balance": balance["balance"],
        "transaction": transaction
    }

@app.get("/api/ai/can-afford")
def ai_can_afford(amount: float):
    """Check if user can afford a purchase"""
    balance = get_current_balance()["balance"]
    can_afford = balance - amount >= 20  # Keep $20 buffer
    
    return {
        "can_afford": can_afford,
        "current_balance": balance,
        "amount": amount,
        "remaining_after": balance - amount,
        "message": f"{'Yes' if can_afford else 'No'}, you {'can' if can_afford else 'cannot'} afford ${amount}. Current balance: ${balance:.2f}"
    }

@app.get("/api/work/tasks")
async def get_tasks():
    """Get all tasks"""
    try:
        tasks = load_work_data()
        return {"tasks": tasks.get("tasks", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/work/tasks")
async def create_task(
    title: str = Query(...),
    description: str = Query(""),
    due_date: str = Query(...),
    priority: str = Query("medium")
):
    """Create a new task"""
    try:
        work_data = load_work_data()
        
        task = {
            "id": str(int(time.time() * 1000)),
            "title": title,
            "description": description,
            "dueDate": due_date,
            "priority": priority,
            "completed": False,
            "createdAt": datetime.now().isoformat()
        }
        
        if "tasks" not in work_data:
            work_data["tasks"] = []
        
        work_data["tasks"].append(task)
        save_work_data(work_data)
        
        return {"success": True, "task": task}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/work/tasks/{task_id}/complete")
async def complete_task(task_id: str):
    """Mark a task as complete"""
    try:
        work_data = load_work_data()
        
        tasks = work_data.get("tasks", [])
        task = next((t for t in tasks if t["id"] == task_id), None)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task["completed"] = True
        task["completedAt"] = datetime.now().isoformat()
        
        save_work_data(work_data)
        
        return {"success": True, "task": task}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/work/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a task"""
    try:
        work_data = load_work_data()
        
        tasks = work_data.get("tasks", [])
        work_data["tasks"] = [t for t in tasks if t["id"] != task_id]
        
        save_work_data(work_data)
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/work/eod/update")
async def add_eod_update(
    jira_card: str = Query(...),
    update: str = Query(...),
    status: str = Query("In Progress")
):
    """Add an EOD update for a Jira card"""
    try:
        work_data = load_work_data()
        
        if "eod_tracking" not in work_data:
            work_data["eod_tracking"] = {}
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        if today not in work_data["eod_tracking"]:
            work_data["eod_tracking"][today] = {
                "date": today,
                "cards": {},
                "created_at": datetime.now().isoformat()
            }
        
        if jira_card not in work_data["eod_tracking"][today]["cards"]:
            work_data["eod_tracking"][today]["cards"][jira_card] = {
                "title": jira_card,
                "status": status,
                "updates": []
            }
        
        update_entry = {
            "time": datetime.now().isoformat(),
            "text": update
        }
        work_data["eod_tracking"][today]["cards"][jira_card]["updates"].append(update_entry)
        work_data["eod_tracking"][today]["cards"][jira_card]["status"] = status
        
        save_work_data(work_data)
        
        return {"success": True, "date": today, "card": jira_card}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/work/eod/today")
async def get_today_eod():
    """Get today's EOD tracking data"""
    try:
        work_data = load_work_data()
        today = datetime.now().strftime("%Y-%m-%d")
        
        eod_data = work_data.get("eod_tracking", {}).get(today, {
            "date": today,
            "cards": {}
        })
        
        return {"success": True, "eod": eod_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/work/eod/generate")
async def generate_eod_report():
    """Generate formatted EOD report for today"""
    try:
        work_data = load_work_data()
        today = datetime.now().strftime("%Y-%m-%d")
        
        eod_data = work_data.get("eod_tracking", {}).get(today, {})
        
        if not eod_data or not eod_data.get("cards"):
            return {
                "success": False,
                "message": "No updates tracked for today"
            }
        
        report_lines = [f"EOD Update - {datetime.now().strftime('%B %d, %Y')}", ""]
        
        for card_name, card_data in eod_data["cards"].items():
            report_lines.append(f"{card_name}")
            report_lines.append(f"({card_data['status']})")
            
            for update in card_data["updates"]:
                report_lines.append(f"* {update['text']}")
            
            report_lines.append("")
        
        report = "\n".join(report_lines)
        
        return {
            "success": True,
            "report": report,
            "date": today,
            "card_count": len(eod_data["cards"])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/work/notes")
async def get_notes():
    """Get all meeting notes"""
    try:
        work_data = load_work_data()
        return {"notes": work_data.get("notes", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/work/notes")
async def create_note(
    meeting_type: str = Query(...),
    transcript: str = Query(...),
    summary: str = Query(""),
    action_items: list = Query([])
):
    """Create a new meeting note"""
    try:
        work_data = load_work_data()
        
        note = {
            "id": str(int(time.time() * 1000)),
            "type": meeting_type,
            "transcript": transcript,
            "summary": summary,
            "actionItems": action_items,
            "date": datetime.now().isoformat()
        }
        
        if "notes" not in work_data:
            work_data["notes"] = []
        
        work_data["notes"].append(note)
        save_work_data(work_data)
        
        return {"success": True, "note": note}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/spiritual/status")
async def get_spiritual_status():
    """Get spiritual accountability status"""
    try:
        spiritual_data = load_spiritual_data()
        return {"status": spiritual_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/spiritual/reading")
async def log_reading(
    book_title: str = Query(...),
    pages_read: int = Query(0),
    notes: str = Query("")
):
    """Log reading progress"""
    try:
        spiritual_data = load_spiritual_data()
        
        if "reading" not in spiritual_data:
            spiritual_data["reading"] = {"current_books": [], "completed_books": [], "history": []}
        
        entry = {
            "date": datetime.now().isoformat(),
            "book": book_title,
            "pages": pages_read,
            "notes": notes
        }
        
        spiritual_data["reading"]["history"].append(entry)
        save_spiritual_data(spiritual_data)
        
        return {"success": True, "entry": entry}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/spiritual/fasting")
async def log_fasting(
    fast_type: str = Query(...),
    duration_days: int = Query(1),
    notes: str = Query("")
):
    """Log fasting activity"""
    try:
        spiritual_data = load_spiritual_data()
        
        if "fasting" not in spiritual_data:
            spiritual_data["fasting"] = {"history": [], "last_fast": None}
        
        entry = {
            "date": datetime.now().isoformat(),
            "type": fast_type,
            "duration": duration_days,
            "notes": notes
        }
        
        spiritual_data["fasting"]["history"].append(entry)
        spiritual_data["fasting"]["last_fast"] = entry
        save_spiritual_data(spiritual_data)
        
        return {"success": True, "entry": entry}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/spiritual/giving")
async def log_giving(
    amount: float = Query(...),
    giving_type: str = Query("tithe"),
    notes: str = Query("")
):
    """Log tithing/offering"""
    try:
        spiritual_data = load_spiritual_data()
        
        if "giving" not in spiritual_data:
            spiritual_data["giving"] = {"history": [], "total": 0}
        
        entry = {
            "date": datetime.now().isoformat(),
            "amount": amount,
            "type": giving_type,
            "notes": notes
        }
        
        spiritual_data["giving"]["history"].append(entry)
        spiritual_data["giving"]["total"] += amount
        save_spiritual_data(spiritual_data)
        
        return {"success": True, "entry": entry}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/spiritual/community")
async def log_community(
    activity: str = Query(...),
    people: str = Query(""),
    notes: str = Query("")
):
    """Log community engagement"""
    try:
        spiritual_data = load_spiritual_data()
        
        if "community" not in spiritual_data:
            spiritual_data["community"] = {"history": []}
        
        entry = {
            "date": datetime.now().isoformat(),
            "activity": activity,
            "people": people,
            "notes": notes
        }
        
        spiritual_data["community"]["history"].append(entry)
        save_spiritual_data(spiritual_data)
        
        return {"success": True, "entry": entry}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/spiritual/goals")
async def get_spiritual_goals():
    """Get spiritual goals/recurring reminders"""
    try:
        spiritual_data = load_spiritual_data()
        return {"goals": spiritual_data.get("goals", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/personal/wishlist")
async def get_wishlist():
    """Get home/personal wishlist"""
    try:
        personal_data = load_personal_data()
        return {"wishlist": personal_data.get("wishlist", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/personal/wishlist")
async def add_to_wishlist(
    item: str = Query(...),
    category: str = Query("home"),
    estimated_price: float = Query(0),
    priority: str = Query("medium"),
    notes: str = Query("")
):
    """Add item to wishlist"""
    try:
        personal_data = load_personal_data()
        
        if "wishlist" not in personal_data:
            personal_data["wishlist"] = []
        
        item_entry = {
            "id": str(int(time.time() * 1000)),
            "item": item,
            "category": category,
            "estimated_price": estimated_price,
            "priority": priority,
            "notes": notes,
            "purchased": False,
            "added_date": datetime.now().isoformat()
        }
        
        personal_data["wishlist"].append(item_entry)
        save_personal_data(personal_data)
        
        return {"success": True, "item": item_entry}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/personal/wishlist/{item_id}/purchase")
async def mark_purchased(item_id: str, actual_price: float = Query(0)):
    """Mark wishlist item as purchased"""
    try:
        personal_data = load_personal_data()
        
        items = personal_data.get("wishlist", [])
        item = next((i for i in items if i["id"] == item_id), None)
        
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        
        item["purchased"] = True
        item["actual_price"] = actual_price
        item["purchase_date"] = datetime.now().isoformat()
        
        save_personal_data(personal_data)
        
        return {"success": True, "item": item}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/personal/recurring-needs")
async def get_recurring_needs():
    """Get monthly recurring personal needs"""
    try:
        personal_data = load_personal_data()
        return {"recurring_needs": personal_data.get("recurring_needs", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/personal/recurring-needs")
async def add_recurring_need(
    item: str = Query(...),
    frequency: str = Query("monthly"),
    estimated_cost: float = Query(0),
    last_purchased: str = Query(None)
):
    """Add recurring personal need"""
    try:
        personal_data = load_personal_data()
        
        if "recurring_needs" not in personal_data:
            personal_data["recurring_needs"] = []
        
        need = {
            "id": str(int(time.time() * 1000)),
            "item": item,
            "frequency": frequency,
            "estimated_cost": estimated_cost,
            "last_purchased": last_purchased  # Don't default to today
        }
        
        personal_data["recurring_needs"].append(need)
        save_personal_data(personal_data)
        
        return {"success": True, "need": need}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/spiritual/goals")
async def get_spiritual_goals():
    """Get all spiritual goals"""
    try:
        spiritual_data = load_spiritual_data()
        return {"goals": spiritual_data.get("goals", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/spiritual/goals")
async def add_spiritual_goal(
    goal: str = Query(...),
    category: str = Query(...),
    frequency: str = Query("daily"),
    target: str = Query(""),
    reminder_enabled: bool = Query(True)
):
    """Add a spiritual goal"""
    try:
        spiritual_data = load_spiritual_data()
        
        if "goals" not in spiritual_data:
            spiritual_data["goals"] = []
        
        new_goal = {
            "id": str(int(time.time() * 1000)),
            "goal": goal,
            "category": category,
            "frequency": frequency,
            "target": target,
            "reminder_enabled": reminder_enabled,
            "created_at": datetime.now().isoformat(),
            "last_completed": None,
            "completion_count": 0,
            "progress": 0,
            "target_count": int(target) if target.isdigit() else 0,
            "period_start": datetime.now().isoformat(),
            "updates": [],  # Track each progress update
            "details": ""  # Additional details about the goal
        }
        
        spiritual_data["goals"].append(new_goal)
        save_spiritual_data(spiritual_data)
        
        return {"success": True, "goal": new_goal}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/spiritual/goals/{goal_id}/complete")
async def complete_spiritual_goal(goal_id: str):
    """Mark spiritual goal as completed for this period"""
    try:
        spiritual_data = load_spiritual_data()
        
        goals = spiritual_data.get("goals", [])
        goal = next((g for g in goals if g["id"] == goal_id), None)
        
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        goal["last_completed"] = datetime.now().isoformat()
        goal["completion_count"] = goal.get("completion_count", 0) + 1
        
        save_spiritual_data(spiritual_data)
        
        return {"success": True, "goal": goal}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/spiritual/goals/{goal_id}/progress")
async def update_goal_progress(
    goal_id: str,
    increment: int = Query(1),
    note: str = Query("")
):
    """Update progress on a spiritual goal"""
    try:
        spiritual_data = load_spiritual_data()
        goals = spiritual_data.get("goals", [])
        
        goal = next((g for g in goals if g["id"] == goal_id), None)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        # Increment progress
        goal["progress"] = goal.get("progress", 0) + increment
        goal["last_completed"] = datetime.now().isoformat()
        
        # Add update entry
        if "updates" not in goal:
            goal["updates"] = []
        
        update_entry = {
            "date": datetime.now().isoformat(),
            "increment": increment,
            "note": note,
            "progress_after": goal["progress"]
        }
        goal["updates"].append(update_entry)
        
        # Check if goal is complete for this period
        target = goal.get("target_count", 0)
        if target > 0 and goal["progress"] >= target:
            goal["completed_this_period"] = True
        
        save_spiritual_data(spiritual_data)
        
        return {
            "success": True,
            "goal": goal,
            "progress": goal["progress"],
            "target": target,
            "remaining": max(0, target - goal["progress"]),
            "updates": goal["updates"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/spiritual/goals/{goal_id}")
async def delete_spiritual_goal(goal_id: str):
    """Delete a spiritual goal"""
    try:
        spiritual_data = load_spiritual_data()
        
        goals = spiritual_data.get("goals", [])
        spiritual_data["goals"] = [g for g in goals if g["id"] != goal_id]
        
        save_spiritual_data(spiritual_data)
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/spiritual/reminders")
async def get_spiritual_reminders():
    """Get pending spiritual reminders based on goals and last activities"""
    try:
        spiritual_data = load_spiritual_data()
        reminders = []
        today = datetime.now()
        
        # Check reading goal
        reading_history = spiritual_data.get("reading", {}).get("history", [])
        if reading_history:
            last_reading = datetime.fromisoformat(reading_history[-1]["date"])
            days_since = (today - last_reading).days
            if days_since >= 1:
                reminders.append({
                    "type": "reading",
                    "message": f"It's been {days_since} day(s) since you last read. Keep your reading habit going! 📖",
                    "priority": "medium" if days_since < 3 else "high"
                })
        else:
            reminders.append({
                "type": "reading",
                "message": "Start your reading journey! Have you read anything spiritual today? 📖",
                "priority": "low"
            })
        
        # Check fasting (every 90 days)
        last_fast = spiritual_data.get("fasting", {}).get("last_fast")
        if last_fast:
            last_fast_date = datetime.fromisoformat(last_fast["date"])
            days_since = (today - last_fast_date).days
            if days_since >= 90:
                reminders.append({
                    "type": "fasting",
                    "message": f"It's been {days_since} days since your last fast. Consider fasting this week! 🙏",
                    "priority": "high"
                })
        else:
            reminders.append({
                "type": "fasting",
                "message": "Have you considered fasting? It's a powerful spiritual practice. 🙏",
                "priority": "low"
            })
        
        # Check giving (monthly reminder)
        giving_history = spiritual_data.get("giving", {}).get("history", [])
        if giving_history:
            last_giving = datetime.fromisoformat(giving_history[-1]["date"])
            days_since = (today - last_giving).days
            if days_since >= 30:
                reminders.append({
                    "type": "giving",
                    "message": f"It's been {days_since} days since your last offering. Time to give? 💰",
                    "priority": "medium"
                })
        
        # Check community engagement (weekly)
        community_history = spiritual_data.get("community", {}).get("history", [])
        this_week_activities = [
            c for c in community_history
            if (today - datetime.fromisoformat(c["date"])).days <= 7
        ]
        if len(this_week_activities) < 2:
            reminders.append({
                "type": "community",
                "message": f"You've had {len(this_week_activities)} community activity this week. Reach out to friends! 🤝",
                "priority": "medium"
            })
        
        return {"reminders": reminders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def load_spiritual_data():
    """Load spiritual data from JSON file"""
    spiritual_file = "spiritual_data.json"
    if os.path.exists(spiritual_file):
        with open(spiritual_file, 'r') as f:
            return json.load(f)
    return {
        "reading": {"current_books": [], "completed_books": [], "history": []},
        "fasting": {"history": [], "last_fast": None},
        "giving": {"history": [], "total": 0},
        "community": {"history": []},
        "goals": []
    }

def save_spiritual_data(data):
    """Save spiritual data to JSON file"""
    with open("spiritual_data.json", 'w') as f:
        json.dump(data, f, indent=2)

def load_personal_data():
    """Load personal data from JSON file"""
    personal_file = "personal_data.json"
    if os.path.exists(personal_file):
        with open(personal_file, 'r') as f:
            return json.load(f)
    return {
        "wishlist": [],
        "recurring_needs": []
    }

def save_personal_data(data):
    """Save personal data to JSON file"""
    with open("personal_data.json", 'w') as f:
        json.dump(data, f, indent=2)

def load_work_data():
    """Load work data from JSON file"""
    work_file = "work_data.json"
    if os.path.exists(work_file):
        with open(work_file, 'r') as f:
            return json.load(f)
    return {
        "tasks": [],
        "notes": [],
        "eod_tracking": {}  # Track daily work updates
    }

def save_work_data(data):
    """Save work data to JSON file"""
    with open("work_data.json", 'w') as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)