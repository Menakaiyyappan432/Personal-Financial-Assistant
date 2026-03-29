from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import json
import os

app = FastAPI()
FILE_NAME = "expenses.json"

# --- DATA MODEL ---
class Expense(BaseModel):
    id: int
    title: str
    amount: float
    category: str

# --- DATA HELPERS ---
def load_data():
    if not os.path.exists(FILE_NAME): return []
    with open(FILE_NAME, "r") as f:
        try: return json.load(f)
        except: return []

def save_data(data):
    with open(FILE_NAME, "w") as f:
        json.dump(data, f, indent=4)

# --- REST API ENDPOINTS ---

@app.get("/api/expenses")
def get_expenses():
    return load_data()

@app.post("/api/expenses", status_code=status.HTTP_201_CREATED)
def add_expense(expense: Expense):
    expenses = load_data()
    expenses.append(expense.model_dump())
    save_data(expenses)
    return {"message": "Success"}

@app.delete("/api/expenses/{expense_id}")
def delete_expense(expense_id: int):
    expenses = load_data()
    updated_list = [e for e in expenses if e["id"] != expense_id]
    if len(updated_list) == len(expenses):
        raise HTTPException(status_code=404, detail="Item not found")
    save_data(updated_list)
    return {"message": "Deleted"}

# --- FRONTEND (DARK UI WITH ICONS) ---
@app.get("/", response_class=HTMLResponse)
def home():
    expenses = load_data()
    total = sum(e["amount"] for e in expenses)
    
    # Logic to pick icons based on category
    def get_icon(cat):
        cat = cat.lower()
        if any(x in cat for x in ["food", "eat", "hotel", "snack"]): return "🍕"
        if any(x in cat for x in ["travel", "bus", "bike", "petrol", "auto"]): return "🚗"
        if any(x in cat for x in ["recharge", "phone", "eb", "bill", "wifi"]): return "📱"
        if any(x in cat for x in ["dress", "shop", "cloth"]): return "🛍️"
        if any(x in cat for x in ["movie", "game", "fun"]): return "🎬"
        return "💰"

    # Creating Modern Expense Cards instead of a Table
    cards_html = ""
    for e in expenses:
        cards_html += f"""
        <div class="expense-card">
            <div class="icon-circle">{get_icon(e['category'])}</div>
            <div class="details">
                <span class="title">{e['title']}</span>
                <span class="category-tag">{e['category']}</span>
            </div>
            <div class="price-action">
                <span class="amount">₹{e['amount']}</span>
                <button class="del-btn" onclick="apiDelete({e['id']})">✕</button>
            </div>
        </div>
        """

    return f"""
    <html>
        <head>
            <title>Personal Financial Assistant</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                :root {{ 
                    --bg: #0f172a; 
                    --card: #1e293b; 
                    --text: #f8fafc; 
                    --accent: #38bdf8; 
                    --danger: #ef4444; 
                }}
                body {{ 
                    font-family: 'Segoe UI', sans-serif; 
                    background: var(--bg); 
                    color: var(--text); 
                    margin: 0; 
                    padding: 20px; 
                    display: flex; 
                    justify-content: center; 
                }}
                .app-container {{ width: 100%; max-width: 450px; }}
                h1 {{ text-align: center; color: var(--accent); font-weight: 600; margin-bottom: 30px; }}
                
                /* Input Box Design */
                .input-card {{ 
                    background: var(--card); 
                    padding: 20px; 
                    border-radius: 16px; 
                    margin-bottom: 25px; 
                    box-shadow: 0 10px 25px rgba(0,0,0,0.3);
                }}
                input {{ 
                    width: 100%; 
                    padding: 12px; 
                    margin-bottom: 12px; 
                    border-radius: 8px; 
                    border: 1px solid #334155; 
                    background: #0f172a; 
                    color: white; 
                    box-sizing: border-box;
                    font-size: 14px;