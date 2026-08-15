from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
import json
import os
import csv
import io
from datetime import datetime

app = FastAPI()

DATA_FILE = "expenses.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

class Expense(BaseModel):
    title: str
    amount: float
    category: str

@app.post("/api/expenses")
def add_expense(expense: Expense):
    expenses = load_data()
    new_id = max([e.get("id", 0) for e in expenses], default=0) + 1
    new_item = {
        "id": new_id,
        "title": expense.title,
        "amount": expense.amount,
        "category": expense.category,
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    expenses.append(new_item)
    save_data(expenses)
    return new_item

@app.delete("/api/expenses/{expense_id}")
def delete_expense(expense_id: int):
    expenses = load_data()
    updated_list = [e for e in expenses if e["id"] != expense_id]
    if len(updated_list) == len(expenses):
        raise HTTPException(status_code=404, detail="Item not found")
    save_data(updated_list)
    return {"message": "Deleted"}

@app.get("/api/export")
def export_csv():
    expenses = load_data()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Title", "Amount", "Category", "Date"])
    for e in expenses:
        writer.writerow([e.get("id"), e.get("title"), e.get("amount"), e.get("category"), e.get("date")])
    
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=expenses_report.csv"}
    )

@app.get("/", response_class=HTMLResponse)
def home():
    expenses = load_data()
    
    MONTHLY_SALARY = 25000.0
    FIXED_RENT = 7000.0
    
    today = datetime.now().date()
    current_month_str = today.strftime("%Y-%m")

    food_total = 0.0
    other_total = 0.0
    cat_totals = {"Rent / PG": FIXED_RENT}

    for e in expenses:
        exp_date_str = e.get("date", today.strftime("%Y-%m-%d"))
        
        # Calculate monthly dynamic expenses
        if exp_date_str.startswith(current_month_str):
            amt = e["amount"]
            cat = e.get("category", "Others")
            
            if cat == "Food":
                food_total += amt
            else:
                other_total += amt
                
            cat_totals[cat] = cat_totals.get(cat, 0.0) + amt

    total_spent = FIXED_RENT + food_total + other_total
    remaining_balance = MONTHLY_SALARY - total_spent

    def get_icon(cat):
        icons = {
            "Petrol": "⛽", 
            "Fruits": "🍎", 
            "Shopping": "👗",
            "Food": "🍕", 
            "Travel": "🚗", 
            "Auto": "🛺", 
            "Bills": "⚡",
            "Entertainment": "🎬", 
            "Others": "💰"
        }
        return icons.get(cat, "💰")

    cards_html = ""
    for e in reversed(expenses):
        cards_html += f"""
        <div class="expense-card">
            <div class="icon-circle">{get_icon(e['category'])}</div>
            <div class="details">
                <span class="title">{e['title']}</span>
                <span class="category-tag">{e['category']} • {e.get('date', '')}</span>
            </div>
            <div class="price-action">
                <span class="amount">₹{e['amount']:.2f}</span>
                <button class="del-btn" onclick="apiDelete({e['id']})">✕</button>
            </div>
        </div>
        """

    chart_labels = json.dumps(list(cat_totals.keys()))
    chart_data = json.dumps(list(cat_totals.values()))

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Expense & Salary Tracker</title>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * {{ box-sizing: border-box; font-family: 'Plus Jakarta Sans', sans-serif; transition: all 0.25s ease; }}
            body {{ 
                background: radial-gradient(circle at top left, #1e1b4b, #0f172a, #020617);
                color: #f8fafc; margin: 0; min-height: 100vh;
                display: flex; justify-content: center; align-items: center; padding: 25px 15px;
            }}
            .container {{ 
                width: 100%; max-width: 500px; 
                background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(16px);
                padding: 24px; border-radius: 28px; 
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7), 0 0 0 1px rgba(255, 255, 255, 0.1); 
            }}
            .header-title {{ text-align: center; margin-bottom: 18px; }}
            .header-title h2 {{ 
                margin: 0; font-size: 1.5rem; font-weight: 800;
                background: linear-gradient(135deg, #38bdf8, #818cf8, #c084fc);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            }}
            
            /* Salary Overview Grid */
            .stats-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 12px; }}
            .stat-card {{ 
                background: rgba(15, 23, 42, 0.6); padding: 12px 10px; border-radius: 16px; 
                text-align: center; border: 1px solid rgba(255, 255, 255, 0.05); position: relative; overflow: hidden;
            }}
            .stat-card::after {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; }}
            .stat-card.salary::after {{ background: #38bdf8; }}
            .stat-card.balance::after {{ background: #34d399; }}
            .stat-card h4 {{ margin: 0; font-size: 0.65rem; color: #94a3b8; text-transform: uppercase; font-weight: 700; }}
            .stat-card p {{ margin: 4px 0 0 0; font-size: 1.1rem; font-weight: 800; }}

            .sub-stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 18px; }}
            .sub-card {{ background: rgba(15, 23, 42, 0.4); padding: 8px; border-radius: 12px; text-align: center; border: 1px solid rgba(255, 255, 255, 0.05); }}
            .sub-card span {{ font-size: 0.6rem; color: #94a3b8; display: block; font-weight: 600; text-transform: uppercase; }}
            .sub-card strong {{ font-size: 0.85rem; color: #fb7185; margin-top: 2px; display: block; }}

            .chart-box {{
                background: rgba(15, 23, 42, 0.5); padding: 12px; border-radius: 18px; 
                border: 1px solid rgba(255, 255, 255, 0.05); margin-bottom: 18px; height: 160px;
                display: flex; justify-content: center; align-items: center;
            }}

            .quick-presets {{ display: flex; gap: 8px; margin-bottom: 14px; overflow-x: auto; padding-bottom: 4px; }}
            .chip {{ 
                background: rgba(56, 189, 248, 0.1); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3);
                padding: 6px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; cursor: pointer; white-space: nowrap;
            }}
            .chip:hover {{ background: #38bdf8; color: #0f172a; }}

            .form-group {{ display: flex; flex-direction: column; gap: 10px; margin-bottom: 18px; background: rgba(15, 23, 42, 0.4); padding: 14px; border-radius: 18px; border: 1px solid rgba(255, 255, 255, 0.05); }}
            input, select {{ padding: 10px 14px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.1); background: rgba(15, 23, 42, 0.8); color: #f8fafc; font-size: 0.88rem; outline: none; }}
            button.add-btn {{ background: linear-gradient(135deg, #0284c7, #6366f1); color: white; font-weight: 700; border: none; padding: 12px; border-radius: 10px; cursor: pointer; box-shadow: 0 6px 16px -4px rgba(99, 102, 241, 0.5); }}
            
            .export-btn {{ background: rgba(52, 211, 153, 0.15); color: #34d399; border: 1px solid rgba(52, 211, 153, 0.3); font-weight: 700; padding: 8px; border-radius: 10px; cursor: pointer; width: 100%; margin-bottom: 14px; font-size: 0.8rem; display: flex; align-items: center; justify-content: center; gap: 6px; }}
            .export-btn:hover {{ background: #34d399; color: #0f172a; }}

            .expense-list {{ display: flex; flex-direction: column; gap: 8px; max-height: 250px; overflow-y: auto; padding-right: 4px; }}
            .expense-card {{ display: flex; align-items: center; background: rgba(15, 23, 42, 0.6); padding: 10px 12px; border-radius: 14px; gap: 10px; border: 1px solid rgba(255, 255, 255, 0.05); }}
            .icon-circle {{ font-size: 1.2rem; background: rgba(255, 255, 255, 0.05); border-radius: 12px; display: flex; align-items: center; justify-content: center; min-width: 38px; height: 38px; }}
            .details {{ flex-grow: 1; display: flex; flex-direction: column; }}
            .title {{ font-weight: 600; color: #f8fafc; font-size: 0.88rem; }}
            .category-tag {{ font-size: 0.68rem; color: #94a3b8; }}
            .price-action {{ display: flex; align-items: center; gap: 8px; }}
            .amount {{ font-weight: 800; color: #fb7185; font-size: 0.92rem; }}
            .del-btn {{ background: rgba(244, 63, 94, 0.1); color: #fb7185; border: none; border-radius: 6px; width: 24px; height: 24px; font-size: 0.75rem; cursor: pointer; }}
            .del-btn:hover {{ background: #f43f5e; color: white; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header-title">
                <h2>Monthly Finance Tracker</h2>
                <p style="margin:2px; font-size:0.75rem; color:#94a3b8;">Salary & Expenditure Summary</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card salary">
                    <h4>Monthly Salary</h4>
                    <p style="color:#38bdf8;">₹{MONTHLY_SALARY:,.2f}</p>
                </div>
                <div class="stat-card balance">
                    <h4>Remaining Balance</h4>
                    <p style="color:#34d399;">₹{remaining_balance:,.2f}</p>
                </div>
            </div>

            <div class="sub-stats">
                <div class="sub-card">
                    <span>PG / Rent</span>
                    <strong>₹{FIXED_RENT:,.0f}</strong>
                </div>
                <div class="sub-card">
                    <span>Food & Juice</span>
                    <strong>₹{food_total:,.2f}</strong>
                </div>
                <div class="sub-card">
                    <span>Other Expenses</span>
                    <strong>₹{other_total:,.2f}</strong>
                </div>
            </div>

            <div class="chart-box">
                <canvas id="expenseChart"></canvas>
            </div>

            <div class="quick-presets">
                <div class="chip" onclick="setPreset('Petrol', 100, 'Petrol')">⛽ Petrol ₹100</div>
                <div class="chip" onclick="setPreset('Lunch / Juice', 60, 'Food')">🍕 Food/Juice ₹60</div>
                <div class="chip" onclick="setPreset('Auto Fare', 50, 'Auto')">🛺 Auto ₹50</div>
                <div class="chip" onclick="setPreset('Shopping', 500, 'Shopping')">👗 Shopping ₹500</div>
            </div>

            <div class="form-group">
                <input type="text" id="title" placeholder="What did you spend on?" />
                <input type="number" id="amount" placeholder="Amount (₹)" />
                <select id="category">
                    <option value="Food">🍕 Food / Juice / Snacks</option>
                    <option value="Petrol">⛽ Petrol / Fuel</option>
                    <option value="Fruits">🍎 Fruits</option>
                    <option value="Shopping">👗 Shopping</option>
                    <option value="Travel">🚗 Travel</option>
                    <option value="Auto">🛺 Auto / Cab</option>
                    <option value="Bills">⚡ Bills / Recharge</option>
                    <option value="Entertainment">🎬 Movies & Fun</option>
                    <option value="Others">💰 Others</option>
                </select>
                <button class="add-btn" onclick="apiAdd()">+ Add Transaction</button>
            </div>

            <button class="export-btn" onclick="window.location.href='/api/export'">📥 Download Excel/CSV Report</button>

            <div class="expense-list">
                {cards_html if cards_html else '<div style="text-align:center; color:#64748b; padding: 20px; font-size: 0.8rem;">No expenses added this month!</div>'}
            </div>
        </div>

        <script>
            function setPreset(t, a, c) {{
                document.getElementById('title').value = t;
                document.getElementById('amount').value = a;
                document.getElementById('category').value = c;
            }}

            async function apiAdd() {{
                const title = document.getElementById('title').value;
                const amount = parseFloat(document.getElementById('amount').value);
                const category = document.getElementById('category').value;
                if(!title || !amount) return alert('Please enter title and amount');

                await fetch('/api/expenses', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ title, amount, category }})
                }});
                window.location.reload();
            }}

            async function apiDelete(id) {{
                await fetch('/api/expenses/' + id, {{ method: 'DELETE' }});
                window.location.reload();
            }}

            // Chart Rendering
            const ctx = document.getElementById('expenseChart').getContext('2d');
            new Chart(ctx, {{
                type: 'doughnut',
                data: {{
                    labels: {chart_labels},
                    datasets: [{{
                        data: {chart_data},
                        backgroundColor: ['#6366f1', '#fb7185', '#38bdf8', '#34d399', '#facc15', '#a78bfa', '#f472b6'],
                        borderWidth: 0
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ position: 'right', labels: {{ color: '#94a3b8', font: {{ size: 9 }} }} }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
