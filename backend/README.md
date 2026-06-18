# Balance Tracker Backend API

Your personal finance tracker with AI integration support!

## 🚀 Quick Start

### For Mac/Linux:
```bash
chmod +x setup.sh run.sh
./setup.sh
./run.sh
```

### For Windows:
```bash
setup.bat
run.bat
```

## 📋 What This Does

This backend API powers your Balance Tracker with:
- ✅ Full data persistence (all your transactions saved)
- ✅ RESTful API for all operations
- ✅ AI-friendly endpoints for voice/chat commands
- ✅ Automatic balance calculations
- ✅ Support for all tracker features (savings, recurring, etc.)

## 🎯 API Endpoints

### Main Endpoints
- `GET /api/data` - Get all your data
- `POST /api/data` - Update all data
- `GET /api/balance` - Get current balance

### Transactions
- `POST /api/transactions/today` - Add transaction to today
- `POST /api/transactions/{month}/{day}` - Add to specific day
- `GET /api/transactions/{month}/{day}` - Get day's transactions
- `DELETE /api/transactions/{month}/{day}/{index}` - Delete transaction

### AI Integration Endpoints
- `POST /api/ai/add-expense` - Add expense via AI
  - Params: `description`, `amount`, `payment_method`
- `POST /api/ai/add-income` - Add income via AI
  - Params: `description`, `amount`
- `GET /api/ai/can-afford` - Check if you can afford something
  - Params: `amount`

### Savings Goals
- `GET /api/savings-goals` - Get all goals
- `POST /api/savings-goals` - Create goal
- `DELETE /api/savings-goals/{goal_id}` - Delete goal

### Recurring Transactions
- `GET /api/recurring-transactions` - Get all recurring
- `POST /api/recurring-transactions` - Create recurring
- `DELETE /api/recurring-transactions/{recurring_id}` - Delete recurring

## 🤖 Using with AI Agent

### Example Commands:

**Add Expense:**
```bash
curl -X POST "http://localhost:8000/api/ai/add-expense?description=Target&amount=50&payment_method=card"
```

**Add Income:**
```bash
curl -X POST "http://localhost:8000/api/ai/add-income?description=Paycheck&amount=3000"
```

**Check Affordability:**
```bash
curl "http://localhost:8000/api/ai/can-afford?amount=200"
```

## 📱 Connecting Your Frontend

Update your HTML tracker to use this API:

1. Change the API URL to: `http://localhost:8000`
2. All data will now persist to `tracker_data.json`
3. Access from any device on your network

## 🌐 API Documentation

Once running, visit: **http://localhost:8000/docs**

This gives you an interactive API explorer where you can:
- Test all endpoints
- See request/response formats
- Try out the AI endpoints

## 📂 Data Storage

All your data is stored in `tracker_data.json` in the same folder. This file contains:
- All transactions
- Savings goals
- Recurring transactions
- Starting balance

**Backup:** Just copy this file to backup all your data!

## 🔧 Troubleshooting

**Port already in use?**
Edit `main.py` line 248 to use a different port:
```python
uvicorn.run(app, host="0.0.0.0", port=8001)  # Change to 8001 or any free port
```

**Can't connect from phone?**
Make sure your phone and laptop are on the same WiFi, then use your laptop's IP address instead of `localhost`.

## 🚀 Next Steps

1. ✅ Run this backend locally
2. ✅ Update your frontend HTML to connect to it
3. ✅ Test adding transactions via API
4. ✅ Set up AI agent integration
5. ✅ Deploy to cloud for access anywhere

## 💡 Pro Tips

- The API auto-saves everything - no manual saving needed!
- Use `/api/balance` to get your current balance instantly
- The AI endpoints are designed for natural language - perfect for voice commands
- Export `tracker_data.json` regularly as backup
