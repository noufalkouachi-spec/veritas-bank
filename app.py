import hashlib
import os
from flask import Flask, jsonify, request, render_template_string
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# ---------------------------------------------------------
# 1. إعداد الاتصال بقاعدة بيانات PostgreSQL السحابية
# ---------------------------------------------------------
DATABASE_URL = os.environ.get(
    'DATABASE_URL', 
    'postgresql://postgres:your_password@localhost:5432/veritas_db'
)

def get_db_connection():
    """فتح اتصال آمن مع قاعدة البيانات وبدء المعاملة."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    """توليد الجداول البنكية الأساسية تلقائياً في السيرفر السحابي عند التشغيل الأول."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            account_id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'User'
        );
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS ledger (
            tx_id SERIAL PRIMARY KEY,
            from_account VARCHAR(50) NOT NULL,
            to_account VARCHAR(50) NOT NULL,
            amount NUMERIC(15, 2) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'Approved',
            date_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS pending_deposits (
            req_id SERIAL PRIMARY KEY,
            account_id VARCHAR(50) NOT NULL,
            amount NUMERIC(15, 2) NOT NULL,
            date_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    cur.execute("SELECT COUNT(*) FROM accounts WHERE account_id = 'ACC-101';")
    if cur.fetchone()['count'] == 0:
        cur.execute("INSERT INTO accounts (account_id, name, role) VALUES ('ACC-101', 'Kamaro', 'User');")
        cur.execute("INSERT INTO ledger (from_account, to_account, amount, status) VALUES ('SYSTEM', 'ACC-101', 85420.00, 'Approved');")
        
    conn.commit()
    cur.close()
    conn.close()

try:
    init_db()
    print("✓ Connected to PostgreSQL and initialized database tables successfully.")
except Exception as e:
    print(f"❌ Database Connection Error: {e}")

# ---------------------------------------------------------
# 2. الخوارزميات المصرفية (الحسابات والتشفير)
# ---------------------------------------------------------
def calculate_balance(account_id):
    """حساب الرصيد الحي مباشرة من قاعدة البيانات بجمع الوارد وطرح الصادر."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT COALESCE(SUM(amount), 0) as total_in FROM ledger WHERE to_account = %s AND status = 'Approved';", (account_id,))
    total_in = cur.fetchone()['total_in']
    
    cur.execute("SELECT COALESCE(SUM(amount), 0) as total_out FROM ledger WHERE from_account = %s AND status = 'Approved';", (account_id,))
    total_out = cur.fetchone()['total_out']
    
    cur.close()
    conn.close()
    return float(total_in - total_out)

def get_transaction_count(account_id):
    """حساب عدد العمليات التي أجراها الحساب لاستخدامها كمكون لمنع التزوير."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM ledger WHERE from_account = %s OR to_account = %s;", (account_id, account_id))
    count = cur.fetchone()['count']
    cur.close()
    conn.close()
    return count

def generate_statement_hash(account_id, balance, tx_count):
    """توليد بصمة مشفرة فريدة لكل كشف حساب لمنع التلاعب بالأرقام خارجيًا."""
    secret_salt = "VERITAS_CREST_SECRET_2026"
    raw_string = f"{account_id}-{balance}-{tx_count}-{secret_salt}"
    return hashlib.sha256(raw_string.encode()).hexdigest()

# ---------------------------------------------------------
# 3. واجهة الـ HTML المصرفية المتطورة (Frontend المدمج)
# ---------------------------------------------------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Veritas Crest Bank - Secured Portal</title>
    <style>
        :root { --navy-dark: #0A192F; --gold-warm: #D4AF37; --bg-card: #172A45; --text-white: #F4F6F9; }
        body { font-family: 'Segoe UI', Arial, sans-serif; background-color: var(--navy-dark); color: var(--text-white); margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; }
        .container { width: 100%; max-width: 800px; }
        .header { text-align: center; margin-bottom: 30px; }
        .brand-title { color: var(--gold-warm); letter-spacing: 3px; margin: 0; text-transform: uppercase; font-size: 28px; }
        .sub-title { color: #8892B0; font-size: 11px; letter-spacing: 2px; margin-top: 5px; }
        .luxury-card { background: linear-gradient(135deg, #BF953F 0%, #FCF6BA 25%, #B38728 50%, #FBF5B7 75%, #AA771C 100%); color: #0A192F; padding: 30px; border-radius: 20px; font-weight: bold; margin-bottom: 25px; box-shadow: 0 15px 35px rgba(0,0,0,0.4); position: relative; overflow: hidden; }
        .card-balance { font-size: 38px; margin: 15px 0; letter-spacing: 1px; font-family: 'Courier New', monospace; }
        .hash-area { font-size: 11px; opacity: 0.85; background: rgba(0,0,0,0.08); padding: 8px; border-radius: 6px; word-break: break-all; font-family: monospace; }
        .layout-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        .panel { background: var(--bg-card); padding: 25px; border-radius: 14px; border: 1px solid rgba(212,175,55,0.15); box-shadow: 0 10px 20px rgba(0,0,0,0.2); }
        input, button { width: 100%; padding: 12px; margin: 10px 0; border-radius: 8px; box-sizing: border-box; font-size: 14px; }
        input { background: var(--navy-dark); border: 1px solid rgba(212,175,55,0.3); color: white; transition: 0.3s; }
        input:focus { border-color: var(--gold-warm); outline: none; }
        button { background: transparent; border: 2px solid var(--gold-warm); color: var(--gold-warm); font-weight: bold; cursor: pointer; text-transform: uppercase; transition: all 0.3s; }
        button:hover { background: var(--gold-warm); color: var(--navy-dark); box-shadow: 0 5px 15px rgba(212,175,55,0.4); }
        .admin-section { border-left: 4px solid #ff9f43; background: rgba(255,159,67,0.08); }
        .queue-item { background: rgba(0, 0, 0, 0.2); padding: 12px; margin: 10px 0; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; border: 1px solid rgba(255,159,67,0.2); }
        .queue-item button { width: auto; margin: 0; padding: 6px 15px; border-color: #10ac84; color: #10ac84; font-size: 12px; }
        .queue-item button:hover { background: #10ac84; color: white; }
        .status-msg { text-align: center; margin-top: 15px; font-weight: bold; font-size: 16px; letter-spacing: 1px; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1 class="brand-title">Veritas Crest Bank</h1>
        <p class="sub-title">SECURE CORE • LIVE POSTGRESQL LEDGER INTEGRATION</p>
    </div>

    <div class="luxury-card">
        <div style="display:flex; justify-content:between; text-transform:uppercase; font-size:13px; letter-spacing:1px;">
            <span>Private Vault Client</span>
            <span id="accNumber" style="margin-left: auto;">ACC-101</span>
        </div>
        <div class="card-balance" id="balance">$0.00</div>
        <div class="hash-area">Anti-Fraud Trace Hash: <span id="vCode">Generating token...</span></div>
    </div>

    <div class="layout-grid">
        <div class="panel">
            <h3 style="color:var(--gold-warm); margin-top:0; letter-spacing:1px;">Client Deposit Desk</h3>
            <p style="color: #8892B0; font-size:13px;">Submit an encrypted deposit entry into the database.</p>
            <input type="number" id="depositAmount" placeholder="Enter Amount ($)">
            <button onclick="sendDeposit()">Request Vault Injection</button>
        </div>

        <div class="panel admin-section">
            <h3 style="color: #ff9f43; margin-top:0; letter-spacing:1px;">Kamaro's Admin Gateway 📱</h3>
            <p style="color: #8892B0; font-size:13px;">Real-time database authorization queue.</p>
            <div id="adminQueue">Scanning server requests...</div>
        </div>
    </div>

    <div class="panel">
        <h3 style="color:var(--gold-warm); margin-top:0; letter-spacing:1px;">Audit Centre: Statement Authenticity Verifier 📜</h3>
        <p style="color: #8892B0; font-size:13px;">Verify whether any paper/PDF bank statement has been modified or forged.</p>
        <input type="text" id="vAcc" placeholder="Account ID (e.g., ACC-101)">
        <input type="number" id="vBal" placeholder="Claimed Balance Amount ($)">
        <input type="text" id="vHash" placeholder="Anti-Fraud Trace Hash Code">
        <button onclick="checkStatement()" style="background:var(--gold-warm); color:var(--navy-dark);">Scan & Audit Document</button>
        <div id="vResult" class="status-msg"></div>
    </div>
</div>

<script>
    const currentAccount = "ACC-101";

    async function updateUI() {
        const res = await fetch(`/api/account/${currentAccount}`);
        const data = await res.json();
        document.getElementById('balance').innerText = "$" + data.balance.toLocaleString('en-US', {minimumFractionDigits: 2});
        document.getElementById('vCode').innerText = data.verification_code;
        getAdminQueue();
    }

    async function sendDeposit() {
        const amt = document.getElementById('depositAmount').value;
        if(!amt || amt <= 0) { alert("Please enter a valid currency amount."); return; }
        
        await fetch('/api/deposit/request', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ account_id: currentAccount, amount: amt })
        });
        alert("Transaction staged to database queue! Awaiting Admin cryptographic approval.");
        document.getElementById('depositAmount').value = "";
        updateUI();
    }

    async function getAdminQueue() {
        const res = await fetch('/api/admin/pending');
        const data = await res.json();
        const queue = document.getElementById('adminQueue');
        queue.innerHTML = data.length === 0 ? "<span style='color:#8892B0; font-size:13px;'>No pending ledger writes found. Database clean.</span>" : "";
        data.forEach(req => {
            queue.innerHTML += `
                <div class="queue-item">
                    <span style="font-size:13px;">Amt: <b style="color:#10ac84">$${req.amount.toLocaleString()}</b></span>
                    <button onclick="actionAdmin('${req.req_id}', 'approve')">Approve & Write</button>
                </div>`;
        });
    }

    async function actionAdmin(reqId, action) {
        await fetch('/api/admin/approve', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ req_id: reqId, action: action })
        });
        updateUI();
    }

    async function checkStatement() {
        const res = await fetch('/api/verify-statement', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                account_id: document.getElementById('vAcc').value,
                balance: document.getElementById('vBal').value,
                verification_code: document.getElementById('vHash').value
            })
        });
        const data = await res.json();
        const rDiv = document.getElementById('vResult');
        if(data.status === "Genuine") {
            rDiv.innerText = "✓ OFFICIAL LOG: STATEMENT IS GENUINE AND MATCHES BLOCKCHAIN LABELS"; 
            rDiv.style.color = "#10ac84";
        } else {
            rDiv.innerText = "🛇 FRAUD DETECTED: INVALID SECURITY HASH OR CORRUPTED BALANCE DATA"; 
            rDiv.style.color = "#ff6b6b";
        }
    }

    window.onload = updateUI;
</script>
</body>
</html>
"""

# ---------------------------------------------------------
# 4. متحكمات الـ API والمسارات التوجيهية (Routes)
# ---------------------------------------------------------
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/account/<account_id>', methods=['GET'])
def get_account(account_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM accounts WHERE account_id = %s;", (account_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    if not user:
        return jsonify({"error": "Account database record not found"}), 404
        
    balance = calculate_balance(account_id)
    tx_count = get_transaction_count(account_id)
    statement_code = generate_statement_hash(account_id, balance, tx_count)
    
    return jsonify({
        "account_id": account_id,
        "name": user["name"],
        "balance": balance,
        "verification_code": statement_code
    })

@app.route('/api/deposit/request', methods=['POST'])
def request_deposit():
    data = request.json
    account_id = data.get("account_id")
    amount = float(data.get("amount"))
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO pending_deposits (account_id, amount) VALUES (%s, %s);", (account_id, amount))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "Staged"})

@app.route('/api/admin/pending', methods=['GET'])
def get_pending():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT req_id, account_id, amount FROM pending_deposits ORDER BY req_id ASC;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{"req_id": r["req_id"], "account_id": r["account_id"], "amount": float(r["amount"])} for r in rows])

@app.route('/api/admin/approve', methods=['POST'])
def approve_deposit():
    data = request.json
    req_id = int(data.get("req_id"))
    action = data.get("action")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM pending_deposits WHERE req_id = %s;", (req_id,))
    req = cur.fetchone()
    
    if req and action == "approve":
        cur.execute("INSERT INTO ledger (from_account, to_account, amount, status) VALUES ('SYSTEM', %s, %s, 'Approved');", 
                    (req["account_id"], req["amount"]))
    
    if req:
        cur.execute("DELETE FROM pending_deposits WHERE req_id = %s;", (req_id,))
        
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/verify-statement', methods=['POST'])
def verify_statement():
    data = request.json
    account_id = data.get("account_id")
    claimed_balance = float(data.get("balance"))
    provided_code = data.get("verification_code")
    
    balance = calculate_balance(account_id)
    tx_count = get_transaction_count(account_id)
    expected_code = generate_statement_hash(account_id, balance, tx_count)
    
    if provided_code == expected_code and claimed_balance == balance:
        return jsonify({"status": "Genuine"})
    else:
        return jsonify({"status": "Fake"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
