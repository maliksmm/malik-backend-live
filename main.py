import json, os, threading, time, requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

PANELS = {
    "1": {"url": "https://xmediasmm.in/api/v2", "key": "52bf994ea9b8fd9c173ace0f0080285e", "bot": "8291687285:AAFDWBGzzaKtQsoGa5ipaYt-dYCpUs7W2aU", "chat": "7044754988"},
    "2": {"url": "https://secsers.com/api/v2", "key": "831913f4125f0576233bb032555d147c", "bot": "8611984647:AAEvQQy_Vcz9P3s2Zj0Zq7fn2sMxryk1nuA", "chat": "7044754988"}
}

DB_FILE = "malik_db.json"
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: pass
    return {"users": {"1": {}, "2": {}}, "balances": {"1": {}, "2": {}}, "txns": [], "orders": [], "blocked": {"1": [], "2": []}}

db = load_db()

def save_db():
    with open(DB_FILE, "w") as f: json.dump(db, f)

# 🛑 ULTRA STRONG ANTI-SLEEP METHOD (DATA LOSS FIX)
def keep_awake():
    while True:
        time.sleep(300) # Pings itself every 5 mins so Render NEVER sleeps
        try: requests.get("https://malik-proxy-smm.onrender.com/api/ping")
        except: pass
threading.Thread(target=keep_awake, daemon=True).start()

@app.route("/api/ping", methods=["GET"])
def ping(): return "Alive"

def background_order_sync():
    while True:
        time.sleep(30)
        for p_id in ["1", "2"]:
            pending_orders = [o for o in db['orders'] if o['panel'] == p_id and o['status'].lower() not in ['completed', 'canceled', 'cancelled', 'partial']]
            if pending_orders:
                order_ids = ",".join([str(o['id']) for o in pending_orders])
                try:
                    res = requests.post(PANELS[p_id]["url"], data={"key": PANELS[p_id]["key"], "action": "status", "orders": order_ids}).json()
                    for o in pending_orders:
                        oid = str(o['id'])
                        if oid in res and type(res[oid]) == dict:
                            real_status = res[oid].get("status", o['status'])
                            if real_status.lower() != o['status'].lower():
                                if real_status.lower() in ['completed', 'canceled', 'cancelled', 'partial']:
                                    msg = f"🔔 *ORDER {real_status.upper()} (P{p_id})*\n👤 User: {o['username']}\n🛒 Service: {o['name']}\n🆔 Order ID: {oid}\n📊 Qty: {o['qty']}"
                                    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": msg, "parse_mode": "Markdown"})
                                    o['status'] = real_status
                                    if real_status.lower() in ['canceled', 'cancelled'] and not o['refunded']:
                                        db['balances'][p_id][o['email']] = db['balances'][p_id].get(o['email'], 0.0) + o['charge']
                                        o['refunded'] = True
                                    elif real_status.lower() == 'partial' and not o['refunded']:
                                        remains = float(res[oid].get("remains", 0))
                                        if remains > 0:
                                            refund_amt = (remains / float(o['qty'])) * o['charge']
                                            db['balances'][p_id][o['email']] = db['balances'][p_id].get(o['email'], 0.0) + refund_amt
                                        o['refunded'] = True
                                    save_db()
                except: pass

threading.Thread(target=background_order_sync, daemon=True).start()

def poll_telegram(p_id):
    bot_token = PANELS[p_id]["bot"]
    offset = 0
    while True:
        try:
            res = requests.get(f"https://api.telegram.org/bot{bot_token}/getUpdates?offset={offset}&timeout=10").json()
            for update in res.get('result', []):
                offset = update['update_id'] + 1
                
                # 🛡️ ULTRA STRONG BOT ADMIN PANEL
                if 'message' in update and 'text' in update['message']:
                    msg_text = update['message']['text']
                    chat_id = update['message']['chat']['id']
                    if msg_text == '/users':
                        total_users = len(db['users'][p_id])
                        if total_users == 0:
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "No users found."})
                        else:
                            keys = []
                            for u_name, u_details in db['users'][p_id].items():
                                em = u_details['email']
                                keys.append([{"text": f"👤 {u_name} ({em})", "callback_data": f"uinfo_{em}"}])
                            markup = {"inline_keyboard": keys}
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"👥 *TOTAL USERS (P{p_id}): {total_users}*\nClick a user for details:", "parse_mode": "Markdown", "reply_markup": markup})

                if 'callback_query' in update:
                    data = update['callback_query']['data']
                    msg = update['callback_query']['message']
                    chat_id = msg['chat']['id']
                    msg_id = msg['message_id']
                    
                    if data.startswith("uinfo_"):
                        target_email = data.replace("uinfo_", "")
                        uname = next((u for u, d in db['users'][p_id].items() if d['email'] == target_email), "Unknown")
                        bal = db['balances'][p_id].get(target_email, 0.0)
                        stat = "🚫 BLOCKED" if target_email in db['blocked'][p_id] else "✅ ACTIVE"
                        b_text = "✅ UNBLOCK USER" if target_email in db['blocked'][p_id] else "🚫 BLOCK USER"
                        markup = {"inline_keyboard": [
                            [{"text": b_text, "callback_data": f"blkusr_{target_email}"}],
                            [{"text": "📦 VIEW ORDERS", "callback_data": f"uord_{target_email}"}],
                        ]}
                        text = f"👤 *USER INFO*\nName: {uname}\nEmail: {target_email}\n💰 Balance: ₹{bal}\n📊 Status: {stat}"
                        requests.post(f"https://api.telegram.org/bot{bot_token}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": "Markdown", "reply_markup": markup})
                        continue
                        
                    if data.startswith("uord_"):
                        target_email = data.replace("uord_", "")
                        u_orders = [o for o in db['orders'] if o['email'] == target_email and o['panel'] == p_id][-5:] # Last 5 orders
                        if not u_orders:
                            o_text = f"User {target_email} has no orders."
                        else:
                            o_text = f"📦 *LAST 5 ORDERS for {target_email}*\n\n"
                            for o in u_orders: o_text += f"ID: {o['id']} | {o['name'][:15]}... | Qty: {o['qty']} | Stat: {o['status']}\n"
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": o_text, "parse_mode": "Markdown"})
                        continue

                    if data.startswith("blkusr_"):
                        target_email = data.replace("blkusr_", "")
                        if target_email in db['blocked'][p_id]:
                            db['blocked'][p_id].remove(target_email)
                            stat = "✅ UNBLOCKED"
                        else:
                            db['blocked'][p_id].append(target_email)
                            stat = "🚫 BLOCKED"
                        save_db()
                        requests.post(f"https://api.telegram.org/bot{bot_token}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": f"*USER STATUS UPDATED: {stat}!*\n✉️ Email: {target_email}", "parse_mode": "Markdown"})
                        continue

                    if "_" in data and data.split('_')[0] in ["app", "rej", "blk"]:
                        action, utr = data.split('_', 1)
                        email = msg['text'].split('\n')[1].replace('👤 ', '').strip()
                        amount = float(msg['text'].split('\n')[2].replace('💰 ₹', '').strip())
                        
                        if action == "app":
                            db['balances'][p_id][email] = db['balances'][p_id].get(email, 0.0) + amount
                            for t in db['txns']:
                                if t['utr'] == utr: t['status'] = "Approved"
                            if not any(t['utr'] == utr for t in db['txns']):
                                db['txns'].append({"status": "Approved", "email": email, "panel": p_id, "amount": amount, "utr": utr})
                            save_db()
                            text_msg = f"✅ *APPROVED SUCCESSFULLY!*\n👤 User: {email}\n💰 New Balance: ₹{db['balances'][p_id][email]}"
                        
                        elif action == "rej":
                            for t in db['txns']:
                                if t['utr'] == utr: t['status'] = "Rejected"
                            if not any(t['utr'] == utr for t in db['txns']):
                                db['txns'].append({"status": "Rejected", "email": email, "panel": p_id, "amount": amount, "utr": utr})
                            save_db()
                            text_msg = f"❌ *REJECTED!*\n👤 User: {email}\n⚠️ Warning Sent."
                        
                        requests.post(f"https://api.telegram.org/bot{bot_token}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": text_msg, "parse_mode": "Markdown"})
        except: pass
        time.sleep(1.5)

threading.Thread(target=poll_telegram, args=("1",), daemon=True).start()
threading.Thread(target=poll_telegram, args=("2",), daemon=True).start()

@app.route("/api/signup", methods=["POST"])
def signup():
    d = request.json
    p_id, user, email, pwd = str(d['panel']), d['username'].lower().strip(), d['email'].lower().strip(), d['pass']
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    if user in db['users'][p_id] or any(u['email'] == email for u in db['users'][p_id].values()): return jsonify({"error": "Username or Email already exists!"}), 400
    db['users'][p_id][user] = {"email": email, "password": pwd}
    save_db()
    msg = f"👤 *NEW SIGNUP (P{p_id})*\nName: {user}\nEmail: {email}\nPass: {pwd}"
    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": msg, "parse_mode": "Markdown"})
    return jsonify({"status": "success"})

@app.route("/api/login", methods=["POST"])
def login():
    d = request.json
    p_id, user, pwd = str(d['panel']), d['username'].lower().strip(), d['pass']
    if user not in db['users'][p_id] or db['users'][p_id][user]["password"] != pwd:
        return jsonify({"error": "Invalid Username or Password!"}), 400
    email = db['users'][p_id][user]["email"]
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    return jsonify({"status": "success", "email": email})

@app.route("/api/google-auth", methods=["POST"])
def google_auth():
    d = request.json
    p_id, email = str(d['panel']), d['email'].lower().strip()
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    
    for u, details in db['users'][p_id].items():
        if details['email'] == email:
            return jsonify({"status": "success", "email": email, "username": u})
            
    username = email.split('@')[0]
    if username in db['users'][p_id]: username += str(int(time.time()))[-4:]
    db['users'][p_id][username] = {"email": email, "password": "GoogleLogin"}
    save_db()
    msg = f"👤 *NEW GOOGLE LOGIN (P{p_id})*\nName: {username}\nEmail: {email}"
    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": msg, "parse_mode": "Markdown"})
    return jsonify({"status": "success", "email": email, "username": username})

@app.route("/api/get-services", methods=["POST"])
def get_services():
    p_id = str(request.json.get("panel"))
    res = requests.post(PANELS[p_id]["url"], data={"key": PANELS[p_id]["key"], "action": "services"}, headers={'User-Agent': 'Mozilla/5.0'})
    return jsonify(res.json() if res.status_code == 200 else [])

@app.route("/api/add-funds", methods=["POST"])
def add_funds():
    data = request.json
    p_id, email, amt, utr = str(data['panel']), data['email'], float(data['amount']), data['utr']
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    db['txns'].append({"status": "Pending", "email": email, "panel": p_id, "amount": amt, "utr": utr})
    save_db()
    text = f"🚨 *FUND REQUEST*\n👤 {email}\n💰 ₹{amt}\n🧾 UTR: {utr}\nPanel: {p_id}"
    markup = {"inline_keyboard": [[{"text": "✅ APPROVE", "callback_data": f"app_{utr}"}, {"text": "❌ REJECT", "callback_data": f"rej_{utr}"}], [{"text": "🚫 BLOCK & DELETE USER", "callback_data": f"blk_{utr}"}]]}
    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": text, "parse_mode": "Markdown", "reply_markup": markup})
    return jsonify({"status": "success"})

@app.route("/api/place-order", methods=["POST"])
def place_order():
    d = request.json
    p_id, email, user, s_id, s_name, link, qty, charge = str(d['panel']), d['email'], d['username'], d['service'], d['service_name'], d['link'], int(d['qty']), float(d['charge'])
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    if db['balances'][p_id].get(email, 0.0) < charge: return jsonify({"error": "Insufficient Wallet Balance!"}), 400
    
    res = requests.post(PANELS[p_id]["url"], data={"key": PANELS[p_id]["key"], "action": "add", "service": s_id, "link": link, "quantity": qty}).json()
    if "error" in res: return jsonify({"error": res['error']}), 400
    
    db['balances'][p_id][email] -= charge
    order_id = res.get("order")
    db['orders'].append({"email": email, "panel": p_id, "id": order_id, "name": s_name, "qty": qty, "charge": charge, "status": "Pending", "refunded": False, "username": user})
    save_db()
    msg = f"📦 *ORDER RECEIVED (P{p_id})*\n👤 Username: {user}\n🛒 Service: {s_name}\n🆔 ID: {s_id}\n🔢 Qty: {qty}\n💸 Amt: ₹{charge}"
    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": msg, "parse_mode": "Markdown"})
    return jsonify({"status": "success", "order": order_id})

@app.route("/api/sync", methods=["POST"])
def sync():
    email, p_id = request.json['email'], str(request.json['panel'])
    if email in db['blocked'][p_id]: return jsonify({"status": "blocked"}), 403
    user_orders = [o for o in db['orders'] if o['email'] == email and o['panel'] == p_id]
    user_txns = [t for t in db['txns'] if t['email'] == email and t['panel'] == p_id]
    return jsonify({"balance": db['balances'][p_id].get(email, 0.0), "txns": user_txns, "orders": user_orders})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
