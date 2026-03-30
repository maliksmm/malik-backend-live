from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, threading, time

app = Flask(__name__)
CORS(app)

PANELS = {
    1: {"url": "https://xmediasmm.in/api/v2", "key": "52bf994ea9b8fd9c173ace0f0080285e", "bot": "8291687285:AAFDWBGzzaKtQsoGa5ipaYt-dYCpUs7W2aU", "chat": "7044754988"},
    2: {"url": "https://secsers.com/api/v2", "key": "831913f4125f0576233bb032555d147c", "bot": "8611984647:AAEvQQy_Vcz9P3s2Zj0Zq7fn2sMxryk1nuA", "chat": "7044754988"}
}

user_balances = {1: {}, 2: {}} 
transactions_db = []
orders_db = []
blocked_users = {1: [], 2: []} 
users_db = {1: {}, 2: {}} # Real Strict Auth DB

def poll_telegram(p_id):
    bot_token = PANELS[p_id]["bot"]
    offset = 0
    while True:
        try:
            res = requests.get(f"https://api.telegram.org/bot{bot_token}/getUpdates?offset={offset}&timeout=10").json()
            for update in res.get('result', []):
                offset = update['update_id'] + 1
                if 'callback_query' in update:
                    data = update['callback_query']['data']
                    msg = update['callback_query']['message']
                    action, utr = data.split('_')
                    email = msg['text'].split('\n')[1].replace('👤 ', '').strip()
                    amount = float(msg['text'].split('\n')[2].replace('💰 ₹', '').strip())
                    
                    if action == "app":
                        user_balances[p_id][email] = user_balances[p_id].get(email, 0.0) + amount
                        for t in transactions_db:
                            if t['utr'] == utr: t['status'] = "Approved"
                        if not any(t['utr'] == utr for t in transactions_db):
                            transactions_db.append({"status": "Approved", "email": email, "panel": p_id, "amount": amount, "utr": utr})
                        new_bal = user_balances[p_id][email]
                        text_msg = f"✅ *APPROVED SUCCESSFULLY!*\n👤 User: {email}\n💰 New Balance: ₹{new_bal}"
                    
                    elif action == "rej":
                        for t in transactions_db:
                            if t['utr'] == utr: t['status'] = "Rejected"
                        if not any(t['utr'] == utr for t in transactions_db):
                            transactions_db.append({"status": "Rejected", "email": email, "panel": p_id, "amount": amount, "utr": utr})
                        text_msg = f"❌ *REJECTED!*\n👤 User: {email}\n⚠️ Big Warning Sent to User."
                    
                    elif action == "blk":
                        if email not in blocked_users[p_id]:
                            blocked_users[p_id].append(email)
                        text_msg = f"🚫 *USER BLOCKED!*\n👤 User: {email} has been completely deleted and blocked from the app."
                    
                    requests.post(f"https://api.telegram.org/bot{bot_token}/editMessageText", json={"chat_id": msg['chat']['id'], "message_id": msg['message_id'], "text": text_msg, "parse_mode": "Markdown"})
        except: pass
        time.sleep(1)

threading.Thread(target=poll_telegram, args=(1,), daemon=True).start()
threading.Thread(target=poll_telegram, args=(2,), daemon=True).start()

@app.route("/api/signup", methods=["POST"])
def signup():
    d = request.json
    p_id, user, email, pwd = d['panel'], d['username'], d['email'], d['pass']
    
    if email in blocked_users[p_id]: return jsonify({"error": "Blocked"}), 403
    if user in users_db[p_id]: return jsonify({"error": "Please give valid details!"}), 400
    
    users_db[p_id][user] = {"email": email, "password": pwd}
    
    msg = f"👤 *NEW SIGNUP (P{p_id})*\nName: {user}\nEmail: {email}\nPass: {pwd}"
    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": msg, "parse_mode": "Markdown"})
    return jsonify({"status": "success"})

@app.route("/api/login", methods=["POST"])
def login():
    d = request.json
    p_id, user, pwd = d['panel'], d['username'], d['pass']
    
    if user not in users_db[p_id] or users_db[p_id][user]["password"] != pwd:
        return jsonify({"error": "Please give valid details!"}), 400
        
    email = users_db[p_id][user]["email"]
    if email in blocked_users[p_id]: return jsonify({"error": "Blocked"}), 403
    
    return jsonify({"status": "success", "email": email})

@app.route("/api/get-services", methods=["POST"])
def get_services():
    p_id = request.json.get("panel")
    res = requests.post(PANELS[p_id]["url"], data={"key": PANELS[p_id]["key"], "action": "services"}, headers={'User-Agent': 'Mozilla/5.0'})
    return jsonify(res.json() if res.status_code == 200 else [])

@app.route("/api/add-funds", methods=["POST"])
def add_funds():
    data = request.json
    p_id, email, amt, utr = data['panel'], data['email'], float(data['amount']), data['utr']
    if email in blocked_users[p_id]: return jsonify({"error": "Blocked"}), 403
    
    transactions_db.append({"status": "Pending", "email": email, "panel": p_id, "amount": amt, "utr": utr})
    
    text = f"🚨 *FUND REQUEST*\n👤 {email}\n💰 ₹{amt}\n🧾 UTR: {utr}\nPanel: {p_id}"
    markup = {"inline_keyboard": [
        [{"text": "✅ APPROVE", "callback_data": f"app_{utr}"}, {"text": "❌ REJECT", "callback_data": f"rej_{utr}"}],
        [{"text": "🚫 BLOCK & DELETE USER", "callback_data": f"blk_{utr}"}]
    ]}
    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": text, "parse_mode": "Markdown", "reply_markup": markup})
    return jsonify({"status": "success"})

@app.route("/api/place-order", methods=["POST"])
def place_order():
    d = request.json
    p_id, email, user, s_id, s_name, link, qty, charge = d['panel'], d['email'], d['username'], d['service'], d['service_name'], d['link'], int(d['qty']), float(d['charge'])
    
    if email in blocked_users[p_id]: return jsonify({"error": "Blocked"}), 403
    if user_balances[p_id].get(email, 0.0) < charge: return jsonify({"error": "Insufficient Wallet Balance!"}), 400
    
    res = requests.post(PANELS[p_id]["url"], data={"key": PANELS[p_id]["key"], "action": "add", "service": s_id, "link": link, "quantity": qty}).json()
    if "error" in res: return jsonify({"error": res['error']}), 400
    
    user_balances[p_id][email] -= charge
    rem_bal = user_balances[p_id][email]
    order_id = res.get("order")
    
    orders_db.append({
        "email": email, "panel": p_id, "id": order_id, "name": s_name, 
        "qty": qty, "charge": charge, "status": "Pending", "refunded": False
    })
    
    msg = f"📦 *ORDER RECEIVED (P{p_id})*\n👤 Username: {user}\n🛒 Service Name: {s_name}\n🆔 Service ID: {s_id}\n🔢 Quantity: {qty}\n💸 Amount: ₹{charge}\n💰 User Balance: ₹{rem_bal}"
    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": msg, "parse_mode": "Markdown"})
    
    return jsonify({"status": "success", "order": order_id})

@app.route("/api/sync", methods=["POST"])
def sync():
    email, p_id = request.json['email'], request.json['panel']
    if email in blocked_users[p_id]: return jsonify({"status": "blocked"}), 403
        
    user_orders = [o for o in orders_db if o['email'] == email and o['panel'] == p_id]
    if len(user_orders) > 0:
        order_ids = ",".join([str(o['id']) for o in user_orders])
        try:
            res = requests.post(PANELS[p_id]["url"], data={"key": PANELS[p_id]["key"], "action": "status", "orders": order_ids}).json()
            for o in user_orders:
                oid = str(o['id'])
                if oid in res and type(res[oid]) == dict:
                    real_status = res[oid].get("status", o['status'])
                    o['status'] = real_status
                    if real_status.lower() in ['canceled', 'cancelled'] and not o['refunded']:
                        user_balances[p_id][email] = user_balances[p_id].get(email, 0.0) + o['charge']
                        o['refunded'] = True
                    elif real_status.lower() == 'partial' and not o['refunded']:
                        remains = float(res[oid].get("remains", 0))
                        if remains > 0:
                            refund_amt = (remains / float(o['qty'])) * o['charge']
                            user_balances[p_id][email] = user_balances[p_id].get(email, 0.0) + refund_amt
                        o['refunded'] = True
        except: pass

    user_txns = [t for t in transactions_db if t['email'] == email and t['panel'] == p_id]
    return jsonify({"balance": user_balances[p_id].get(email, 0.0), "txns": user_txns, "orders": user_orders})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
Enter
