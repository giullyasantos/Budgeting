#!/usr/bin/env python3
"""
Add article research task with milestones
"""

import requests

API_URL = "http://localhost:8000"

# Main task with sub-tasks/milestones
tasks = [
    {
        "title": "Find interesting article for team presentation",
        "description": "Research daily - read articles or watch YouTube videos until finding something compelling to share. Look for: tech trends, AI developments, industry insights, best practices.",
        "due_date": "2026-01-21",
        "priority": "high"
    },
    {
        "title": "Deep study and prepare article presentation",
        "description": "Once article is found, study it thoroughly. Understand key points, create talking points, prepare to explain to team. Master the content.",
        "due_date": "2026-01-23",
        "priority": "high"
    },
    {
        "title": "Daily review of article until presentation",
        "description": "Review article daily to stay sharp. Refine talking points, anticipate questions, practice explaining key concepts.",
        "due_date": "2026-01-30",
        "priority": "urgent"
    },
    {
        "title": "Present article to team",
        "description": "Final presentation day! Share the article, key insights, and lead discussion with team.",
        "due_date": "2026-01-30",
        "priority": "urgent"
    }
]

def add_tasks():
    print("\n📚 Adding Article Research & Presentation Tasks...")
    print("="*60)
    
    try:
        response = requests.get(f"{API_URL}/api/balance")
        print("✅ Backend is running!\n")
    except:
        print("❌ Backend is NOT running! Please start it first:")
        print("   cd ~/Desktop/AI\\ Assistant/backend")
        print("   python3 main.py")
        return
    
    for task in tasks:
        try:
            response = requests.post(
                f"{API_URL}/api/work/tasks",
                params={
                    "title": task["title"],
                    "description": task["description"],
                    "due_date": task["due_date"],
                    "priority": task["priority"]
                }
            )
            if response.status_code == 200:
                print(f"✅ {task['due_date']}: {task['title']}")
            else:
                print(f"❌ Failed: {task['title']}")
        except Exception as e:
            print(f"❌ Error: {task['title']} - {str(e)}")
    
    print("\n" + "="*60)
    print("✅ All tasks added!")
    print("\n💡 Daily workflow:")
    print("  1. Tell AI: 'I spent 30 min researching articles today'")
    print("  2. When you find one: 'I found the perfect article about [topic]'")
    print("  3. Mark complete: 'I finished finding the article'")
    print("  4. Daily: 'I reviewed the article today'")
    print("  5. Jan 30: 'I presented the article to the team'")
    print("\n🎯 Your standup helper will remind you about these!")

if __name__ == "__main__":
    add_tasks()