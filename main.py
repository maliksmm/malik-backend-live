import json, os, threading, time, requests, re, hashlib
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

PANELS = {
    "1": {"url": "https://xmediasmm.in/api/v2", "key": "52bf994ea9b8fd9c173ace0f0080285e", "bot": "8291687285:AAFDWBGzzaKtQsoGa5ipaYt-dYCpUs7W2aU", "chat": "7044754988"},
    "2": {"url": "https://wowsmmpanel.com/api/v2", "key": "9ddd128b2174a854bb4c3c97a7769ebe", "bot": "8611984647:AAEvQQy_Vcz9P3s2Zj0Zq7fn2sMxryk1nuA", "chat": "7044754988"}
}

DB_FILE = "malik_db.json"
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                if "mails" not in data: data["mails"] = {"1": {}, "2": {}}
                if "config" not in data: data["config"] = {"upi": "followersincrease870@oksbi", "qr": "./AccountQRCodeJ&K Bank - 6648_DARK_THEME (13).png", "wa": "", "yt": "https://youtube.com/@z3rv_x?si=ayQnR40t-521AFTb", "tg": "@zr3v_x", "ch": "https://t.me/all_services_provider"}
                if "notifications" not in data: data["notifications"] = {"1": {}, "2": {}}
                return data
        except: pass
    return {"users": {"1": {}, "2": {}}, "balances": {"1": {}, "2": {}}, "txns": [], "orders": [], "blocked": {"1": [], "2": []}, "mails": {"1": {}, "2": {}}, "config": {"upi": "followersincrease870@oksbi", "qr": "./AccountQRCodeJ&K Bank - 6648_DARK_THEME (13).png", "wa": "", "yt": "https://youtube.com/@z3rv_x?si=ayQnR40t-521AFTb", "tg": "@zr3v_x", "ch": "https://t.me/all_services_provider"}, "notifications": {"1": {}, "2": {}}}

db = load_db()
def save_db():
    with open(DB_FILE, "w") as f: json.dump(db, f)

def keep_awake():
    while True:
        time.sleep(120)
        try: requests.get("https://malik-proxy-smm.onrender.com/api/ping")
        except: pass
threading.Thread(target=keep_awake, daemon=True).start()

@app.route("/api/ping", methods=["GET"])
def ping(): return "Alive"

def send_notification(p_id, email, msg):
    if email not in db['notifications'][p_id]: db['notifications'][p_id][email] = []
    db['notifications'][p_id][email].append(msg)
    save_db()

def background_order_sync():
    while True:
        time.sleep(15)
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
                                o['status'] = real_status
                                
                                # App Notification for Order Complete!
                                if real_status.lower() in ['completed', 'partial']:
                                    send_notification(p_id, o['email'], f"Order Completed! ID: {oid}")
                                
                                if real_status.lower() in ['canceled', 'cancelled'] and not o['refunded']:
                                    db['balances'][p_id][o['email']] = db['balances'][p_id].get(o['email'], 0.0) + o['charge']
                                    o['refunded'] = True
                                    send_notification(p_id, o['email'], f"Order Canceled & Refunded! ID: {oid}")
                                elif real_status.lower() == 'partial' and not o['refunded']:
                                    remains = float(res[oid].get("remains", 0))
                                    if remains > 0:
                                        db['balances'][p_id][o['email']] = db['balances'][p_id].get(o['email'], 0.0) + ((remains / float(o['qty'])) * o['charge'])
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
                
                if 'message' in update and 'text' in update['message']:
                    msg_text = update['message']['text']
                    chat_id = update['message']['chat']['id']
                    
                    # 🛠️ DYNAMIC CONTROL COMMANDS
                    if msg_text == '/users':
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"👑 Total Users (P{p_id}): {len(db['users'][p_id])}"})
                    
                    elif msg_text.startswith('/reply '):
                        parts = msg_text.split(' ', 2)
                        if len(parts) >= 3:
                            t_email, r_msg = parts[1].strip(), parts[2].strip()
                            if t_email not in db['mails'][p_id]: db['mails'][p_id][t_email] = []
                            db['mails'][p_id][t_email].append({"from": "admin", "msg": r_msg, "read": False})
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Reply sent to {t_email}!"})

                    elif msg_text.startswith('/broadcast '):
                        b_msg = msg_text.split(' ', 1)[1]
                        for email in db['users'][p_id].keys():
                            if email not in db['mails'][p_id]: db['mails'][p_id][email] = []
                            db['mails'][p_id][email].append({"from": "admin", "msg": b_msg, "read": False})
                        save_db()
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "✅ Broadcast sent to all users!"})

                    elif msg_text.startswith('/discount '):
                        parts = msg_text.split(' ')
                        if len(parts) == 3:
                            t_email, disc = parts[1], int(parts[2])
                            for u, d in db['users'][p_id].items():
                                if d['email'] == t_email:
                                    d['discount'] = disc; save_db()
                                    requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ {disc}% Discount given to {t_email}!"})

                    elif msg_text.startswith('/gift '):
                        parts = msg_text.split(' ')
                        if len(parts) == 3:
                            t_email, amt = parts[1], float(parts[2])
                            db['balances'][p_id][t_email] = db['balances'][p_id].get(t_email, 0.0) + amt
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"🎁 Gifted ₹{amt} to {t_email}!"})

                    elif msg_text.startswith('/set_upi '): db['config']['upi'] = msg_text.split(' ')[1]; save_db(); requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "✅ UPI Updated!"})
                    elif msg_text.startswith('/set_qr '): db['config']['qr'] = msg_text.split(' ')[1]; save_db(); requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "✅ QR Updated!"})
                    elif msg_text.startswith('/set_wa '): db['config']['wa'] = msg_text.split(' ')[1]; save_db(); requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "✅ WhatsApp Updated!"})
                    elif msg_text.startswith('/set_yt '): db['config']['yt'] = msg_text.split(' ')[1]; save_db(); requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "✅ YouTube Updated!"})
                    
                    elif msg_text.startswith('/getdata '):
                        t_email = msg_text.split(' ')[1]
                        for u, d in db['users'][p_id].items():
                            if d['email'] == t_email:
                                bal = db['balances'][p_id].get(t_email, 0.0)
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"🕵️ DATA EXTRACTED:\nUsername: {u}\nPassword: {d['password']}\nBalance: ₹{bal}"})

                if 'callback_query' in update:
                    data = update['callback_query']['data']
                    msg = update['callback_query']['message']
                    chat_id = msg['chat']['id']
                    msg_id = msg['message_id']
                    text_content = msg.get('text', '')

                    if data.startswith("replymail_"):
                        target_email = data.replace("replymail_", "")
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"💬 Copy this to reply:\n`/reply {target_email} Your msg`", "parse_mode": "Markdown"})
                        continue

                    if "_" in data and data.split('_')[0] in ["app", "rej", "blk"]:
                        action, utr = data.split('_', 1)
                        email_match = re.search(r'User:\s*([^\n]+)', text_content)
                        email = email_match.group(1).strip() if email_match else "Unknown"
                        
                        if action == "blk":
                            if email not in db['blocked'][p_id]: db['blocked'][p_id].append(email)
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": f"🚫 USER BLOCKED!\nUser: {email}"})
                            continue
                            
                        amt_match = re.search(r'Amount: ₹([\d\.]+)', text_content)
                        amount = float(amt_match.group(1)) if amt_match else 0.0
                        
                        if action == "app":
                            db['balances'][p_id][email] = db['balances'][p_id].get(email, 0.0) + amount
                            for t in db['txns']:
                                if t['utr'] == utr: t['status'] = "Approved"
                            if not any(t['utr'] == utr for t in db['txns']):
                                db['txns'].append({"status": "Approved", "email": email, "panel": p_id, "amount": amount, "utr": utr})
                            send_notification(p_id, email, f"Payment of ₹{amount} Approved!")
                            save_db()
                            text_msg = f"✅ APPROVED!\nUser: {email}\nBal: ₹{db['balances'][p_id][email]}"
                        elif action == "rej":
                            for t in db['txns']:
                                if t['utr'] == utr: t['status'] = "Rejected"
                            if not any(t['utr'] == utr for t in db['txns']):
                                db['txns'].append({"status": "Rejected", "email": email, "panel": p_id, "amount": amount, "utr": utr})
                            send_notification(p_id, email, f"Payment of ₹{amount} Rejected! UTR: {utr}")
                            save_db()
                            text_msg = f"❌ REJECTED!\nUser: {email}"
                        requests.post(f"https://api.telegram.org/bot{bot_token}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": text_msg})
        except: pass
        time.sleep(1.5)

threading.Thread(target=poll_telegram, args=("1",), daemon=True).start()
threading.Thread(target=poll_telegram, args=("2",), daemon=True).start()

@app.route("/api/signup", methods=["POST"])
def signup():
    d = request.json
    p_id, user, email, pwd = str(d['panel']), d['username'].lower().strip(), d['email'].lower().strip(), d['pass']
    ref_by = d.get('ref', '')
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    if user in db['users'][p_id] or any(u['email'] == email for u in db['users'][p_id].values()): return jsonify({"error": "User Exists!"}), 400
    
    api_key = hashlib.md5(f"{email}{time.time()}".encode()).hexdigest() # Reseller API logic
    db['users'][p_id][user] = {"email": email, "password": pwd, "ref_by": ref_by, "ordered": False, "ref_signups": 0, "ref_active": 0, "first_claim": False, "discount": 0, "api_key": api_key}
    
    if ref_by and ref_by in db['users'][p_id]: db['users'][p_id][ref_by]['ref_signups'] += 1
    save_db()
    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": f"💎 NEW SIGNUP\nName: {user}\nEmail: {email}"})
    return jsonify({"status": "success"})

@app.route("/api/login", methods=["POST"])
def login():
    d = request.json
    p_id, user, pwd = str(d['panel']), d['username'].lower().strip(), d['pass']
    if user not in db['users'][p_id] or db['users'][p_id][user]["password"] != pwd: return jsonify({"error": "Invalid Details!"}), 400
    email = db['users'][p_id][user]["email"]
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    return jsonify({"status": "success", "email": email})

@app.route("/api/google-auth", methods=["POST"])
def google_auth(): # Unchanged from before
    d = request.json
    p_id, email, req_username = str(d['panel']), d['email'].lower().strip(), d['username'].lower().strip()
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    for u, details in db['users'][p_id].items():
        if details['email'] == email:
            if u != req_username: return jsonify({"error": "Mismatch!"}), 400
            return jsonify({"status": "success", "email": email, "username": u})
    if req_username in db['users'][p_id]: return jsonify({"error": "Taken!"}), 400
    db['users'][p_id][req_username] = {"email": email, "password": "GoogleLogin", "ref_by": "", "ordered": False, "ref_signups": 0, "ref_active": 0, "first_claim": False, "discount": 0, "api_key": hashlib.md5(f"{email}{time.time()}".encode()).hexdigest()}
    save_db()
    return jsonify({"status": "success", "email": email, "username": req_username})

@app.route("/api/get-services", methods=["POST"])
def get_services():
    p_id = str(request.json.get("panel"))
    res = requests.post(PANELS[p_id]["url"], data={"key": PANELS[p_id]["key"], "action": "services"}, headers={'User-Agent': 'Mozilla/5.0'})
    return jsonify(res.json() if res.status_code == 200 else [])

@app.route("/api/add-funds", methods=["POST"])
def add_funds():
    d = request.json
    p_id, email, amt, utr = str(d['panel']), d['email'], float(d['amount']), d['utr']
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    db['txns'].append({"status": "Pending", "email": email, "panel": p_id, "amount": amt, "utr": utr})
    save_db()
    text = f"🚨 FUND REQUEST\nUser: {email}\nAmt: ₹{amt}\nUTR: {utr}"
    markup = {"inline_keyboard": [[{"text": "✅ APPROVE", "callback_data": f"app_{utr}"}, {"text": "❌ REJECT", "callback_data": f"rej_{utr}"}]]}
    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": text, "reply_markup": markup})
    return jsonify({"status": "success"})

@app.route("/api/place-order", methods=["POST"])
def place_order():
    d = request.json
    p_id, email, user, s_id, s_name, link, qty, charge = str(d['panel']), d['email'], d['username'], d['service'], d['service_name'], d['link'], int(d['qty']), float(d['charge'])
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    if db['balances'][p_id].get(email, 0.0) < charge: return jsonify({"error": "Insufficient Balance!"}), 400
    res = requests.post(PANELS[p_id]["url"], data={"key": PANELS[p_id]["key"], "action": "add", "service": s_id, "link": link, "quantity": qty}).json()
    if "error" in res: return jsonify({"error": res['error']}), 400
    
    db['balances'][p_id][email] -= charge
    db['orders'].append({"email": email, "panel": p_id, "id": res.get("order"), "name": s_name, "qty": qty, "charge": charge, "status": "Pending", "refunded": False, "username": user})
    if user in db['users'][p_id] and not db['users'][p_id][user].get('ordered', False):
        db['users'][p_id][user]['ordered'] = True
        ref_by = db['users'][p_id][user].get('ref_by')
        if ref_by and ref_by in db['users'][p_id]: db['users'][p_id][ref_by]['ref_active'] = db['users'][p_id][ref_by].get('ref_active', 0) + 1
    save_db()
    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": f"🚀 ORDER\nUser: {user}\nID: {s_id}\nQty: {qty}\nAmt: ₹{charge}"})
    return jsonify({"status": "success"})

@app.route("/api/cancel-order", methods=["POST"])
def cancel_order():
    d = request.json
    p_id, email, order_id = str(d['panel']), d['email'], d['order_id']
    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": f"⚠️ CANCEL/REFUND REQUEST\nUser: {email}\nOrder ID: {order_id}"})
    return jsonify({"status": "success"})

@app.route("/api/send-mail", methods=["POST"])
def send_mail():
    d = request.json
    p_id, email, message = str(d['panel']), d['email'], d['message']
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    
    if email not in db['mails'][p_id]: db['mails'][p_id][email] = []
    db['mails'][p_id][email].append({"from": "user", "msg": message, "read": True})
    
    # 🤖 SMART AI AUTO-REPLY FILTER (Only App Related)
    ai_reply = None
    msg_low = message.lower()
    if any(w in msg_low for w in ['how', 'use', 'start']): ai_reply = "Hi! To use the app: 1. Add Funds via QR/UPI. 2. Copy 12-digit UTR. 3. Submit UTR in app. 4. Go to Services and place order!"
    elif any(w in msg_low for w in ['admin', 'talk', 'contact']): ai_reply = "I have notified the Admin. Please wait, they will reply to you shortly right here."
    elif 'international' in msg_low or 'usd' in msg_low: ai_reply = "For International payments (Crypto/PayPal), admin will contact you here soon with details."
    
    if ai_reply:
        db['mails'][p_id][email].append({"from": "admin", "msg": ai_reply, "read": False})
    save_db()
    
    markup = {"inline_keyboard": [[{"text": "✉️ REPLY TO USER", "callback_data": f"replymail_{email}"}]]}
    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": f"📬 MAIL\nUser: {email}\nMsg: {message}", "reply_markup": markup})
    return jsonify({"status": "success", "ai_reply": ai_reply})

@app.route("/api/sync", methods=["POST"])
def sync():
    email, p_id = request.json['email'], str(request.json['panel'])
    if email in db['blocked'][p_id]: return jsonify({"status": "blocked"}), 403
    
    user_orders = [o for o in db['orders'] if o['email'] == email and o['panel'] == p_id]
    user_txns = [t for t in db['txns'] if t['email'] == email and t['panel'] == p_id]
    
    user_info = {}
    for u, details in db['users'][p_id].items():
        if details['email'] == email:
            user_info = details; break
            
    user_mails = db['mails'][p_id].get(email, [])
    unread_mails = [m['msg'] for m in user_mails if m['from'] == 'admin' and not m.get('read', False)]
    for m in user_mails:
        if m['from'] == 'admin': m['read'] = True
        
    user_notifs = db['notifications'][p_id].get(email, [])
    if user_notifs:
        db['notifications'][p_id][email] = [] # clear after reading
        
    save_db()
    return jsonify({
        "balance": db['balances'][p_id].get(email, 0.0), 
        "txns": user_txns, 
        "orders": user_orders, 
        "user_info": user_info,
        "unread_mails": unread_mails,
        "all_mails": user_mails,
        "config": db['config'],
        "notifications": user_notifs
    })

@app.route("/api/claim-reward", methods=["POST"])
def claim_reward():
    pass # Kept unchanged on server end

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
