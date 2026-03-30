
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, threading, time, smtplib, random
from email.mime.text import MIMEText

app = Flask(__name__)
CORS(app)

PANELS = {
    1: {"url": "https://xmediasmm.in/api/v2", "key": "52bf994ea9b8fd9c173ace0f0080285e", "bot": "8291687285:AAFDWBGzzaKtQsoGa5ipaYt-dYCpUs7W2aU", "chat": "7044754988"},
    2: {"url": "https://secsers.com/api/v2", "key": "831913f4125f0576233bb032555d147c", "bot": "8611984647:AAEvQQy_Vcz9P3s2Zj0Zq7fn2sMxryk1nuA", "chat": "7044754988"}
}

# ⚠️ OTP BHEJNE KE LIYE EMAIL AUR PASSWORD SET KAR DIYA HAI
ADMIN_EMAIL = "aryanmalik888807@gmail.com" 
ADMIN_APP_PASS = "aryan_7611"

user_balances = {1: {}, 2: {}} 
transactions_db = []
orders_db = []
blocked_users = {1: [], 2: []} 
users_db = {1: {}, 2: {}} 
otp_db = {} # OTP Save karne ke liye

def poll_telegram(p_id):
    bot_token = PANELS[p_id]["bot"]
    offset = 0
    while True:
        try:
            res = requests.get(f"https://api.telegram.org/bot{bot_token}/getUpdates?offset={offset}&timeout=10").json()
            for update in res.get('result', []):
                offset = update['update_id'] + 1
                
                # 🛡️ BOT ADMIN COMMAND: /users
                if 'message' in update and 'text' in update['message']:
                    msg_text = update['message']['text']
                    chat_id = update['message']['chat']['id']
                    if msg_text == '/users':
                        if not users_db[p_id]:
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "No users found."})
                        else:
                            for u_name, u_details in users_db[p_id].items():
                                em = u_details['email']
                                bal = user_balances[p_id].get(em, 0.0)
                                stat = "🚫 BLOCKED" if em in blocked_users[p_id] else "✅ ACTIVE"
                                markup = {"inline_keyboard": [[{"text": f"🚫 BLOCK {u_name}", "callback_data": f"blkusr_{em}"}]]}
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"👤 User: {u_name}\n✉️ Email: {em}\n💰 Bal: ₹{bal}\n📊 Status: {stat}", "reply_markup": markup})

                if 'callback_query' in update:
                    data = update['callback_query']['data']
                    msg = update['callback_query']['message']
                    
                    if data.startswith("blkusr_"):
                        target_email = data.replace("blkusr_", "")
                        if target_email not in blocked_users[p_id]: blocked_users[p_id].append(target_email)
                        requests.post(f"https://api.telegram.org/bot{bot_token}/editMessageText", json={"chat_id": msg['chat']['id'], "message_id": msg['message_id'], "text": f"🚫 *USER COMPLETELY BLOCKED!*\n✉️ Email: {target_email}", "parse_mode": "Markdown"})
                        continue

                    action, utr = data.split('_', 1)
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
                        text_msg = f"❌ *REJECTED!*\n👤 User: {email}\n⚠️ Warning Sent."
                    
                    elif action == "blk":
                        if email not in blocked_users[p_id]: blocked_users[p_id].append(email)
                        text_msg = f"🚫 *USER BLOCKED!*\n👤 User: {email} blocked."
                    
                    requests.post(f"https://api.telegram.org/bot{bot_token}/editMessageText", json={"chat_id": msg['chat']['id'], "message_id": msg['message_id'], "text": text_msg, "parse_mode": "Markdown"})
        except: pass
        time.sleep(1.5)

threading.Thread(target=poll_telegram, args=(1,), daemon=True).start()
threading.Thread(target=poll_telegram, args=(2,), daemon=True).start()

@app.route("/api/signup", methods=["POST"])
def signup():
    d = request.json
    p_id, user, email, pwd = d['panel'], d['username'], d['email'], d['pass']
    if email in blocked_users[p_id]: return jsonify({"error": "Blocked"}), 403
    if user in users_db[p_id] or any(u['email'] == email for u in users_db[p_id].values()): return jsonify({"error": "Username or Email already exists!"}), 400
    users_db[p_id][user] = {"email": email, "password": pwd}
    msg = f"👤 *NEW SIGNUP (P{p_id})*\nName: {user}\nEmail: {email}\nPass: {pwd}"
    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": msg, "parse_mode": "Markdown"})
    return jsonify({"status": "success"})

@app.route("/api/login", methods=["POST"])
def login():
    d = request.json
    p_id, user, pwd = d['panel'], d['username'], d['pass']
    if user not in users_db[p_id] or users_db[p_id][user]["password"] != pwd:
        return jsonify({"error": "Invalid Username or Password!"}), 400
    email = users_db[p_id][user]["email"]
    if email in blocked_users[p_id]: return jsonify({"error": "Blocked"}), 403
    return jsonify({"status": "success", "email": email})

@app.route("/api/forgot-password", methods=["POST"])
def forgot_password():
    email = request.json['email']
    user_found = None
    p_id_found = None
    for pid in [1, 2]:
        for u, d in users_db[pid].items():
            if d['email'] == email:
                user_found, p_id_found = u, pid
                break
    if not user_found: return jsonify({"error": "Email not found!"}), 400
    
    otp = str(random.randint(1000, 9999))
    otp_db[email] = otp
    try:
        msg = MIMEText(f"Your MALIK VIP HUB Password Reset OTP is: {otp}")
        msg['Subject'] = 'Password Reset OTP'
        msg['From'] = ADMIN_EMAIL
        msg['To'] = email
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(ADMIN_EMAIL, ADMIN_APP_PASS)
        server.sendmail(ADMIN_EMAIL, email, msg.as_string())
        server.quit()
        return jsonify({"status": "success"})
    except:
        return jsonify({"error": "Failed to send email. Check Admin SMTP."}), 500

@app.route("/api/reset-password", methods=["POST"])
def reset_password():
    d = request.json
    email, otp, new_pass = d['email'], d['otp'], d['new_pass']
    if otp_db.get(email) != otp: return jsonify({"error": "Invalid OTP!"}), 400
    for pid in [1, 2]:
        for u, details in users_db[pid].items():
            if details['email'] == email:
                users_db[pid][u]['password'] = new_pass
                return jsonify({"status": "success"})
    return jsonify({"error": "Error resetting password."}), 400

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
    markup = {"inline_keyboard": [[{"text": "✅ APPROVE", "callback_data": f"app_{utr}"}, {"text": "❌ REJECT", "callback_data": f"rej_{utr}"}], [{"text": "🚫 BLOCK & DELETE USER", "callback_data": f"blk_{utr}"}]]}
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
    order_id = res.get("order")
    orders_db.append({"email": email, "panel": p_id, "id": order_id, "name": s_name, "qty": qty, "charge": charge, "status": "Pending", "refunded": False, "username": user})
    msg = f"📦 *ORDER RECEIVED (P{p_id})*\n👤 Username: {user}\n🛒 Service: {s_name}\n🆔 ID: {s_id}\n🔢 Qty: {qty}\n💸 Amt: ₹{charge}"
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
                    
                    # 🔔 STRONG NOTIFICATION FOR COMPLETE / CANCEL
                    if real_status.lower() != o['status'].lower():
                        if real_status.lower() in ['completed', 'canceled', 'cancelled', 'partial']:
                            msg = f"🔔 *ORDER {real_status.upper()} (P{p_id})*\n👤 User: {o['username']}\n🛒 Service: {o['name']}\n🆔 Order ID: {oid}\n📊 Qty: {o['qty']}"
                            requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": msg, "parse_mode": "Markdown"})
                    
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
