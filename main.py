import json, os, threading, time, requests, re, uuid
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
                if "config" not in data: data["config"] = {"1": {}, "2": {}}
                return data
        except: pass
    return {"users": {"1": {}, "2": {}}, "balances": {"1": {}, "2": {}}, "txns": [], "orders": [], "blocked": {"1": [], "2": []}, "mails": {"1": {}, "2": {}}, "config": {"1": {}, "2": {}}}

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
                                
                                if real_status.lower() == 'completed':
                                    o['notified'] = False
                                    
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
                
                if 'message' in update and 'text' in update['message']:
                    msg_text = update['message']['text']
                    chat_id = update['message']['chat']['id']
                    
                    if msg_text in ['/start', '/menu']:
                        menu_text = (
                            "👑 *ADMIN MASTER CONTROL PANEL* 👑\n\n"
                            "Copy & paste the commands below to control your app:\n\n"
                            "👥 `/users` - View all users\n"
                            "💰 `/gift user@email.com 50` - Add ₹50 to user\n"
                            "💸 `/discount user@email.com 10` - Give 10% discount to user\n"
                            "🔥 `/discountall 15` - Give 15% discount to EVERYONE\n"
                            "📬 `/mailall Welcome guys!` - Send mail to all app users\n"
                            "⚙️ `/setupi your_upi_id` - Change App UPI QR ID\n"
                            "🖼️ `/setqr direct_image_link` - Change QR Code Image\n"
                            "💬 `/setwa 919876543210` - Add WhatsApp Support Button\n"
                            "▶️ `/setyt youtube_embed_link` - Add YT Video in app\n"
                            "📢 `/setupdate System is fast now!` - Show banner in app\n"
                            "🛡️ `/appdata` - Download all user data (Security)\n"
                            "✉️ `/reply user@email.com Message` - Reply to user mailbox"
                        )
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": menu_text, "parse_mode": "Markdown"})
                    
                    elif msg_text == '/users':
                        total_users = len(db['users'][p_id])
                        if total_users == 0:
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "⚠️ No users found."})
                        else:
                            keys = []
                            for u_name, u_details in db['users'][p_id].items():
                                em = u_details['email']
                                keys.append([{"text": f"👤 {u_name}", "callback_data": f"uinfo_{em}"}])
                            markup = {"inline_keyboard": keys[:50]} 
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"👑 TOTAL USERS (P{p_id}): {total_users} 👑", "reply_markup": markup})
                    
                    elif msg_text.startswith('/gift '):
                        parts = msg_text.split(' ')
                        if len(parts) == 3:
                            em, amt = parts[1].strip(), float(parts[2].strip())
                            db['balances'][p_id][em] = db['balances'][p_id].get(em, 0.0) + amt
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Gifted ₹{amt} to {em}"})

                    elif msg_text.startswith('/discount '):
                        parts = msg_text.split(' ')
                        if len(parts) == 3:
                            em, perc = parts[1].strip(), float(parts[2].strip())
                            for u, d in db['users'][p_id].items():
                                if d['email'] == em: d['discount'] = perc
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ {perc}% Discount given to {em}"})

                    elif msg_text.startswith('/discountall '):
                        perc = float(msg_text.split(' ')[1].strip())
                        db['config'][p_id]['global_discount'] = perc
                        save_db()
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Global {perc}% Discount applied to ALL users!"})

                    elif msg_text.startswith('/setupi '):
                        db['config'][p_id]['upi'] = msg_text.replace('/setupi ', '').strip()
                        save_db()
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "✅ UPI updated!"})

                    elif msg_text.startswith('/setqr '):
                        db['config'][p_id]['qr'] = msg_text.replace('/setqr ', '').strip()
                        save_db()
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "✅ QR Image updated!"})

                    elif msg_text.startswith('/setwa '):
                        db['config'][p_id]['wa'] = msg_text.replace('/setwa ', '').strip()
                        save_db()
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "✅ WhatsApp updated!"})

                    elif msg_text.startswith('/setyt '):
                        db['config'][p_id]['yt'] = msg_text.replace('/setyt ', '').strip()
                        save_db()
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "✅ YouTube Video updated!"})

                    elif msg_text.startswith('/setupdate '):
                        db['config'][p_id]['updates'] = msg_text.replace('/setupdate ', '').strip()
                        save_db()
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "✅ Announcement Banner updated!"})

                    elif msg_text == '/appdata':
                        raw_data = json.dumps(db['users'][p_id], indent=2)
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"🛡️ SECURE DATA DUMP:\n\n{raw_data[:4000]}"})

                    elif msg_text.startswith('/mailall '):
                        mail_msg = msg_text.replace('/mailall ', '').strip()
                        for u_name, details in db['users'][p_id].items():
                            em = details['email']
                            if em not in db['mails'][p_id]: db['mails'][p_id][em] = []
                            db['mails'][p_id][em].append({"from": "admin", "msg": mail_msg, "read": False})
                        save_db()
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "✅ Mail sent to ALL users!"})

                    elif msg_text.startswith('/reply '):
                        parts = msg_text.split(' ', 2)
                        if len(parts) >= 3:
                            target_email, reply_msg = parts[1].strip(), parts[2].strip()
                            if target_email not in db['mails'][p_id]: db['mails'][p_id][target_email] = []
                            db['mails'][p_id][target_email].append({"from": "admin", "msg": reply_msg, "read": False})
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Reply sent to {target_email}!"})

                if 'callback_query' in update:
                    data = update['callback_query']['data']
                    msg = update['callback_query']['message']
                    chat_id = msg['chat']['id']
                    msg_id = msg['message_id']
                    text_content = msg.get('text', '')
                    
                    if data.startswith("replymail_"):
                        target_email = data.replace("replymail_", "")
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"`/reply {target_email} Message`", "parse_mode": "Markdown"})
                        continue

                    if data.startswith("uinfo_"):
                        target_email = data.replace("uinfo_", "")
                        uname = next((u for u, d in db['users'][p_id].items() if d['email'] == target_email), "Unknown")
                        bal = db['balances'][p_id].get(target_email, 0.0)
                        stat = "🚫 BLOCKED" if target_email in db['blocked'][p_id] else "✅ ACTIVE"
                        b_text = "✅ UNBLOCK" if target_email in db['blocked'][p_id] else "🚫 BLOCK"
                        markup = {"inline_keyboard": [[{"text": b_text, "callback_data": f"blkusr_{target_email}"}], [{"text": "📦 LAST ORDERS", "callback_data": f"uord_{target_email}"}]]}
                        requests.post(f"https://api.telegram.org/bot{bot_token}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": f"🪬 USER PROFILE\n\n👤 Name: {uname}\n✉️ Email: {target_email}\n💰 Bal: ₹{bal}\n📊 Stat: {stat}", "reply_markup": markup})
                        continue
                        
                    if data.startswith("uord_"):
                        target_email = data.replace("uord_", "")
                        u_orders = [o for o in db['orders'] if o['email'] == target_email and o['panel'] == p_id][-5:]
                        o_text = "⚠️ No orders yet." if not u_orders else "📦 LAST 5 ORDERS\n\n" + "\n".join([f"🆔 {o['id']} | Qty: {o['qty']} | {o['status']}" for o in u_orders])
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": o_text})
                        continue

                    if data.startswith("blkusr_"):
                        target_email = data.replace("blkusr_", "")
                        if target_email in db['blocked'][p_id]: db['blocked'][p_id].remove(target_email)
                        else: db['blocked'][p_id].append(target_email)
                        save_db()
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"⚠️ USER BLOCKED/UNBLOCKED!\n✉️ Email: {target_email}"})
                        continue

                    if "_" in data and data.split('_')[0] in ["app", "rej", "blk"]:
                        action, utr = data.split('_', 1)
                        email_match = re.search(r'User:\s*([^\n]+)', text_content)
                        email = email_match.group(1).strip() if email_match else "Unknown"
                        
                        if action == "blk":
                            if email not in db['blocked'][p_id]: db['blocked'][p_id].append(email)
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": f"🚫 USER BLOCKED & DELETED!\n👤 User: {email}"})
                            continue
                            
                        amt_match = re.search(r'Amount: ₹([\d\.]+)', text_content)
                        amount = float(amt_match.group(1)) if amt_match else 0.0
                        
                        if action == "app":
                            db['balances'][p_id][email] = db['balances'][p_id].get(email, 0.0) + amount
                            for t in db['txns']:
                                if t['utr'] == utr: t['status'] = "Approved"
                            if not any(t['utr'] == utr for t in db['txns']): db['txns'].append({"status": "Approved", "email": email, "panel": p_id, "amount": amount, "utr": utr})
                            save_db()
                            text_msg = f"✅ APPROVED!\n👤 User: {email}\n💰 New Bal: ₹{db['balances'][p_id][email]}"
                        
                        elif action == "rej":
                            for t in db['txns']:
                                if t['utr'] == utr: t['status'] = "Rejected"
                            if not any(t['utr'] == utr for t in db['txns']): db['txns'].append({"status": "Rejected", "email": email, "panel": p_id, "amount": amount, "utr": utr})
                            save_db()
                            text_msg = f"❌ REJECTED!\n👤 User: {email}"
                        
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
    if user in db['users'][p_id] or any(u['email'] == email for u in db['users'][p_id].values()): return jsonify({"error": "Username or Email already exists!"}), 400
    
    api_key = str(uuid.uuid4()).replace('-', '')
    db['users'][p_id][user] = {"email": email, "password": pwd, "ref_by": ref_by, "ordered": False, "ref_signups": 0, "ref_active": 0, "first_claim": False, "discount": 0, "api_key": api_key}
    
    if ref_by and ref_by in db['users'][p_id]:
        db['users'][p_id][ref_by]['ref_signups'] += 1
        
    save_db()
    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": f"💎 NEW SIGNUP\n👤 {user}\n✉️ {email}"})
    return jsonify({"status": "success"})

@app.route("/api/login", methods=["POST"])
def login():
    d = request.json
    p_id, user, pwd = str(d['panel']), d['username'].lower().strip(), d['pass']
    if user not in db['users'][p_id] or db['users'][p_id][user]["password"] != pwd: return jsonify({"error": "Invalid Username or Password!"}), 400
    email = db['users'][p_id][user]["email"]
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    return jsonify({"status": "success", "email": email})

@app.route("/api/google-auth", methods=["POST"])
def google_auth():
    d = request.json
    p_id, email, req_username = str(d['panel']), d['email'].lower().strip(), d['username'].lower().strip()
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    for u, details in db['users'][p_id].items():
        if details['email'] == email:
            if u != req_username: return jsonify({"error": "Username does not match this Email!"}), 400
            return jsonify({"status": "success", "email": email, "username": u})
    if req_username in db['users'][p_id]: return jsonify({"error": "Username taken."}), 400
    api_key = str(uuid.uuid4()).replace('-', '')
    db['users'][p_id][req_username] = {"email": email, "password": "GoogleLogin", "ref_by": "", "ordered": False, "ref_signups": 0, "ref_active": 0, "first_claim": False, "discount": 0, "api_key": api_key}
    save_db()
    return jsonify({"status": "success", "email": email, "username": req_username})

@app.route("/api/change-password", methods=["POST"])
def change_pass():
    d = request.json
    p_id, email, old, new = str(d['panel']), d['email'], d['old_pass'], d['new_pass']
    for u, details in db['users'][p_id].items():
        if details['email'] == email:
            if details['password'] != old and details['password'] != 'GoogleLogin': return jsonify({"error": "Wrong old password"}), 400
            db['users'][p_id][u]['password'] = new
            save_db()
            return jsonify({"status": "success"})
    return jsonify({"error": "User not found"}), 400

@app.route("/api/ai-chat", methods=["POST"])
def ai_chat():
    msg = request.json['message'].lower()
    if "admin" in msg or "contact" in msg: return jsonify({"reply": "You can contact admin by clicking the 'SUPPORT MAILBOX' button on the home page or via Telegram @zr3v_x."})
    elif "fund" in msg or "pay" in msg: return jsonify({"reply": "To add funds, go to Home > Add Funds. Scan the QR code, pay the amount, and submit your 12-digit UTR number."})
    elif "order" in msg or "use" in msg: return jsonify({"reply": "To order, go to the Services tab, select a service, paste your link, enter quantity, and click BUY!"})
    elif "fast" in msg or "drop" in msg: return jsonify({"reply": "Most orders start instantly and finish within 5-10 minutes. Premium services are non-drop!"})
    else: return jsonify({"reply": "I am the Malik App AI. I only know about using this app, adding funds, and placing orders. Please ask me something related to our services!"})

@app.route("/api/get-services", methods=["POST"])
def get_services():
    p_id = str(request.json.get("panel"))
    email = request.json.get("email", "")
    
    global_disc = db['config'][p_id].get('global_discount', 0.0)
    user_disc = 0.0
    for u, d in db['users'][p_id].items():
        if d['email'] == email: user_disc = d.get('discount', 0.0)
        
    total_disc = global_disc + user_disc
    
    res = requests.post(PANELS[p_id]["url"], data={"key": PANELS[p_id]["key"], "action": "services"}, headers={'User-Agent': 'Mozilla/5.0'}).json()
    if type(res) == list and total_disc > 0:
        for s in res:
            s['rate'] = float(s['rate']) * (1 - (total_disc/100))
    return jsonify(res if type(res) == list else [])

@app.route("/api/add-funds", methods=["POST"])
def add_funds():
    data = request.json
    p_id, email, amt, utr = str(data['panel']), data['email'], float(data['amount']), data['utr']
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    db['txns'].append({"status": "Pending", "email": email, "panel": p_id, "amount": amt, "utr": utr})
    save_db()
    text = f"🚨 FUND REQUEST\n👤 User: {email}\n💰 Amt: ₹{amt}\n🧾 UTR: {utr}"
    markup = {"inline_keyboard": [[{"text": "✅ APP", "callback_data": f"app_{utr}"}, {"text": "❌ REJ", "callback_data": f"rej_{utr}"}]]}
    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": text, "reply_markup": markup})
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
    db['orders'].append({"email": email, "panel": p_id, "id": order_id, "name": s_name, "qty": qty, "charge": charge, "status": "Pending", "refunded": False, "username": user, "notified": True})
    
    if user in db['users'][p_id] and not db['users'][p_id][user].get('ordered', False):
        db['users'][p_id][user]['ordered'] = True
        ref_by = db['users'][p_id][user].get('ref_by')
        if ref_by and ref_by in db['users'][p_id]: db['users'][p_id][ref_by]['ref_active'] = db['users'][p_id][ref_by].get('ref_active', 0) + 1
            
    save_db()
    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": f"🚀 ORDER RECEIVED\n👤 {user}\n🆔 {s_id}\n🔗 {link}\n🔢 {qty}\n🟡 Status: Pending"})
    return jsonify({"status": "success", "order": order_id})

@app.route("/api/cancel-order", methods=["POST"])
def cancel_order():
    d = request.json
    p_id, email, oid = str(d['panel']), d['email'], d['order_id']
    
    for o in db['orders']:
        if str(o['id']) == str(oid) and o['email'] == email and o['panel'] == p_id:
            if o['status'] in ['Pending', 'In progress']:
                try:
                    res = requests.post(PANELS[p_id]["url"], data={"key": PANELS[p_id]["key"], "action": "cancel", "order": oid}).json()
                    return jsonify({"status": "requested"})
                except: pass
    return jsonify({"error": "Order cannot be canceled"}), 400

@app.route("/api/send-mail", methods=["POST"])
def send_mail():
    d = request.json
    p_id, email, message = str(d['panel']), d['email'], d['message']
    if email not in db['mails'][p_id]: db['mails'][p_id][email] = []
    db['mails'][p_id][email].append({"from": "user", "msg": message, "read": True})
    save_db()
    markup = {"inline_keyboard": [[{"text": "✉️ REPLY", "callback_data": f"replymail_{email}"}]]}
    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": f"📬 NEW MAIL\n👤 {email}\n💬 {message}", "reply_markup": markup})
    return jsonify({"status": "success"})

@app.route("/api/sync", methods=["POST"])
def sync():
    email, p_id = request.json['email'], str(request.json['panel'])
    if email in db['blocked'][p_id]: return jsonify({"status": "blocked"}), 403
    
    user_orders = [o for o in db['orders'] if o['email'] == email and o['panel'] == p_id]
    
    # ORDER NOTIFICATION LOGIC
    completed_notifications = []
    for o in user_orders:
        if o['status'].lower() == 'completed' and not o.get('notified', True):
            completed_notifications.append(f"ID {o['id']} - {o['name'][:20]}...")
            o['notified'] = True
    if completed_notifications: save_db()
            
    user_txns = [t for t in db['txns'] if t['email'] == email and t['panel'] == p_id]
    
    user_info = {}
    for u, details in db['users'][p_id].items():
        if details['email'] == email:
            user_info = details; break
            
    user_mails = db['mails'][p_id].get(email, [])
    unread_admin_mails = [m['msg'] for m in user_mails if m['from'] == 'admin' and not m.get('read', False)]
    for m in user_mails:
        if m['from'] == 'admin': m['read'] = True
    if unread_admin_mails: save_db()
            
    return jsonify({
        "balance": db['balances'][p_id].get(email, 0.0), 
        "txns": user_txns, 
        "orders": user_orders, 
        "user_info": user_info,
        "unread_mails": unread_admin_mails,
        "all_mails": user_mails,
        "notifications": completed_notifications,
        "config": db['config'][p_id]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

