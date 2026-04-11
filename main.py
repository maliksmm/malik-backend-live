import json, os, threading, time, requests, re
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
                if "config" not in data: data["config"] = {"qr_1": "./AccountQRCodeJ&K Bank - 6648_DARK_THEME (13).png", "qr_2": "./AccountQRCodeJ&K Bank - 6648_DARK_THEME (13).png"}
                if "discounts" not in data: data["discounts"] = {"users": {"1": {}, "2": {}}, "all": {"1": {"percent": 0, "exp": 0}, "2": {"percent": 0, "exp": 0}}}
                return data
        except: pass
    return {"users": {"1": {}, "2": {}}, "balances": {"1": {}, "2": {}}, "txns": [], "orders": [], "blocked": {"1": [], "2": []}, "mails": {"1": {}, "2": {}}, "config": {"qr_1": "./AccountQRCodeJ&K Bank - 6648_DARK_THEME (13).png", "qr_2": "./AccountQRCodeJ&K Bank - 6648_DARK_THEME (13).png"}, "discounts": {"users": {"1": {}, "2": {}}, "all": {"1": {"percent": 0, "exp": 0}, "2": {"percent": 0, "exp": 0}}}}

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
                                if real_status.lower() in ['completed', 'canceled', 'cancelled', 'partial']:
                                    status_emo = "🟢" if real_status.lower() == 'completed' else ("🔴" if real_status.lower() in ['canceled', 'cancelled'] else "🟡")
                                    msg = f"🔱 ⍟ ORDER UPDATE (P{p_id}) ⍟ 🔱\n\n👤 User: {o['username']}\n🛒 Service: {o['name'][:30]}...\n🆔 Order ID: {oid}\n{status_emo} Status: {real_status.upper()}"
                                    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": msg})
                                    
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
            res = requests.get(f"https://api.telegram.org/bot{bot_token}/getUpdates?offset={offset}&timeout=5").json()
            for update in res.get('result', []):
                offset = update['update_id'] + 1
                
                if 'message' in update and 'text' in update['message']:
                    msg_text = update['message']['text']
                    chat_id = update['message']['chat']['id']
                    
                    if msg_text == '/start':
                        markup = {"keyboard": [[{"text": "/users"}, {"text": "/help_commands"}]], "resize_keyboard": True}
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "👑 Welcome Admin! System active.", "reply_markup": markup})
                    
                    elif msg_text == '/help_commands':
                        txt = "🛠️ *VIP COMMANDS*\n\n`/users` - List all users\n`/appinfo` - View app stats\n`/setqr <url>` - Change QR image\n`/discount <email> <time> <unit> <percent>`\n`/discountall <time> <unit> <percent> <reason>`\n`/broadcast <msg>` - Send mail to everyone\n`/reply <email> <msg>` - Reply to specific user"
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": txt, "parse_mode": "Markdown"})

                    elif msg_text == '/appinfo':
                        total_u = len(db['users'][p_id])
                        total_bal = sum(db['balances'][p_id].values())
                        txt = f"📊 *APP STATS (P{p_id})*\n\n👥 Total Users: {total_u}\n💰 Total User Balances: ₹{total_bal:.2f}"
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": txt, "parse_mode": "Markdown"})

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
                            list_msg = f"👑 TOTAL USERS (P{p_id}): {total_users} 👑\n\n⚡ Click a user below:"
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": list_msg, "reply_markup": markup})
                    
                    elif msg_text.startswith('/reply '):
                        try:
                            parts = msg_text.split(' ', 2)
                            target_email = parts[1].strip()
                            reply_msg = parts[2].strip()
                            if target_email not in db['mails'][p_id]: db['mails'][p_id][target_email] = []
                            db['mails'][p_id][target_email].append({"from": "admin", "msg": reply_msg, "read": False})
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Reply sent to {target_email}!"})
                        except:
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "❌ Format Error. Use: `/reply user@email.com message`", "parse_mode": "Markdown"})

                    elif msg_text.startswith('/setqr '):
                        try:
                            new_url = msg_text.replace('/setqr ', '').strip()
                            db['config'][f"qr_{p_id}"] = new_url
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ QR Code updated successfully for Panel {p_id}!"})
                        except: pass

                    elif msg_text.startswith('/broadcast '):
                        try:
                            msg = msg_text.replace('/broadcast ', '').strip()
                            count = 0
                            for u_name, u_details in db['users'][p_id].items():
                                em = u_details['email']
                                if em not in db['mails'][p_id]: db['mails'][p_id][em] = []
                                db['mails'][p_id][em].append({"from": "admin", "msg": msg, "read": False})
                                count += 1
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Broadcast sent to {count} users!"})
                        except:
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "❌ Error in broadcast format."})

                    elif msg_text.startswith('/discountall '):
                        try:
                            parts = msg_text.split(' ', 4)
                            t_val = int(parts[1])
                            t_unit = parts[2].lower()
                            perc = int(parts[3])
                            reason = parts[4] if len(parts) > 4 else "Special Offer"

                            multiplier = 1
                            if 'day' in t_unit or t_unit == 'd': multiplier = 86400
                            elif 'hour' in t_unit or t_unit == 'h': multiplier = 3600
                            elif 'min' in t_unit or t_unit == 'm': multiplier = 60
                            elif 'sec' in t_unit or t_unit == 's': multiplier = 1

                            duration = t_val * multiplier
                            db['discounts']['all'][p_id] = {"percent": perc, "exp": time.time() + duration}
                            
                            for u_name, u_details in db['users'][p_id].items():
                                em = u_details['email']
                                bmsg = f"Hey dear {u_name}, {reason}! Enjoy the {perc}% discount valid for {t_val} {t_unit}!"
                                if em not in db['mails'][p_id]: db['mails'][p_id][em] = []
                                db['mails'][p_id][em].append({"from": "admin", "msg": bmsg, "read": False})
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ {perc}% Global Discount applied for {t_val} {t_unit}!\nReason sent: {reason}"})
                        except Exception as e:
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "❌ Format Error. Use: `/discountall 1 day 20 Eid Mubarak`", "parse_mode": "Markdown"})

                    elif msg_text.startswith('/discount '):
                        try:
                            parts = msg_text.split(' ')
                            em = parts[1]
                            t_val = int(parts[2])
                            t_unit = parts[3].lower()
                            perc = int(parts[4])

                            multiplier = 1
                            if 'day' in t_unit or t_unit == 'd': multiplier = 86400
                            elif 'hour' in t_unit or t_unit == 'h': multiplier = 3600
                            elif 'min' in t_unit or t_unit == 'm': multiplier = 60
                            elif 'sec' in t_unit or t_unit == 's': multiplier = 1

                            duration = t_val * multiplier
                            db['discounts']['users'][p_id][em] = {"percent": perc, "exp": time.time() + duration}
                            
                            if em not in db['mails'][p_id]: db['mails'][p_id][em] = []
                            db['mails'][p_id][em].append({"from": "admin", "msg": f"🎁 Special gift only for you! Enjoy a {perc}% discount valid for {t_val} {t_unit}.", "read": False})
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ {perc}% Discount given to {em} for {t_val} {t_unit}!"})
                        except Exception as e:
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "❌ Format Error. Use: `/discount user@mail.com 10 min 20`", "parse_mode": "Markdown"})

                if 'callback_query' in update:
                    data = update['callback_query']['data']
                    msg = update['callback_query']['message']
                    chat_id = msg['chat']['id']
                    msg_id = msg['message_id']
                    text_content = msg.get('text', '')
                    
                    if data.startswith("replymail_"):
                        target_email = data.replace("replymail_", "")
                        info_text = f"💬 To reply to {target_email}, copy and send this command exactly:\n\n`/reply {target_email} Your reply message here`"
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": info_text, "parse_mode": "Markdown"})
                        continue

                    if data.startswith("uinfo_"):
                        target_email = data.replace("uinfo_", "")
                        uname = next((u for u, d in db['users'][p_id].items() if d['email'] == target_email), "Unknown")
                        bal = db['balances'][p_id].get(target_email, 0.0)
                        stat = "🚫 BLOCKED" if target_email in db['blocked'][p_id] else "✅ ACTIVE"
                        b_text = "✅ UNBLOCK" if target_email in db['blocked'][p_id] else "🚫 BLOCK"
                        markup = {"inline_keyboard": [
                            [{"text": b_text, "callback_data": f"blkusr_{target_email}"}],
                            [{"text": "📦 VIEW LAST ORDERS", "callback_data": f"uord_{target_email}"}],
                        ]}
                        text = f"🪬 USER PROFILE\n\n👤 Name: {uname}\n✉️ Email: {target_email}\n💰 Balance: ₹{bal}\n📊 Status: {stat}"
                        requests.post(f"https://api.telegram.org/bot{bot_token}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": text, "reply_markup": markup})
                        continue
                        
                    if data.startswith("uord_"):
                        target_email = data.replace("uord_", "")
                        u_orders = [o for o in db['orders'] if o['email'] == target_email and o['panel'] == p_id][-5:]
                        if not u_orders:
                            o_text = f"⚠️ User has no orders yet."
                        else:
                            o_text = f"📦 LAST 5 ORDERS\n\n"
                            for o in u_orders: o_text += f"🆔 {o['id']} | Qty: {o['qty']} | {o['status']}\n"
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": o_text})
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
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"⚠️ STATUS UPDATED: {stat}!\n✉️ Email: {target_email}"})
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
                            if not any(t['utr'] == utr for t in db['txns']):
                                db['txns'].append({"status": "Approved", "email": email, "panel": p_id, "amount": amount, "utr": utr})
                            save_db()
                            text_msg = f"✅ APPROVED!\n👤 User: {email}\n💰 New Bal: ₹{db['balances'][p_id][email]}"
                        
                        elif action == "rej":
                            for t in db['txns']:
                                if t['utr'] == utr: t['status'] = "Rejected"
                            if not any(t['utr'] == utr for t in db['txns']):
                                db['txns'].append({"status": "Rejected", "email": email, "panel": p_id, "amount": amount, "utr": utr})
                            save_db()
                            text_msg = f"❌ REJECTED!\n👤 User: {email}"
                        
                        requests.post(f"https://api.telegram.org/bot{bot_token}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": text_msg})
        except Exception as e: 
            pass
        time.sleep(1.5)

threading.Thread(target=poll_telegram, args=("1",), daemon=True).start()
threading.Thread(target=poll_telegram, args=("2",), daemon=True).start()


@app.route("/api/signup", methods=["POST"])
def signup():
    d = request.json
    p_id = str(d['panel'])
    user = d['username'].lower().strip()
    email = d['email'].lower().strip()
    pwd = d['pass'].strip()
    ref_by = d.get('ref', '')
    
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    if user in db['users'][p_id] or any(u['email'] == email for u in db['users'][p_id].values()): return jsonify({"error": "Username or Email already exists!"}), 400
    
    db['users'][p_id][user] = {"email": email, "password": pwd, "ref_by": ref_by, "ordered": False, "ref_signups": 0, "ref_active": 0, "first_claim": False}
    
    if ref_by and ref_by in db['users'][p_id]:
        db['users'][p_id][ref_by]['ref_signups'] += 1
        
    save_db()
    msg = f"💎 ⍟ NEW SIGNUP (P{p_id}) ⍟ 💎\n\n👤 Name: {user}\n✉️ Email: {email}\n🔗 Ref by: {ref_by or 'None'}"
    markup = {"inline_keyboard": [[{"text": "🚫 BLOCK USER", "callback_data": f"blkusr_{email}"}]]}
    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": msg, "reply_markup": markup})
    return jsonify({"status": "success"})

@app.route("/api/login", methods=["POST"])
def login():
    d = request.json
    p_id = str(d['panel'])
    user = d['username'].lower().strip()
    pwd = d['pass'].strip()
    
    if user not in db['users'][p_id] or db['users'][p_id][user]["password"] != pwd:
        return jsonify({"error": "Invalid Username or Password!"}), 400
    email = db['users'][p_id][user]["email"]
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    return jsonify({"status": "success", "email": email})

@app.route("/api/change-password", methods=["POST"])
def change_pass():
    d = request.json
    p_id, email, old, new = str(d['panel']), d['email'], d['old'].strip(), d['new'].strip()
    for u, details in db['users'][p_id].items():
        if details['email'] == email:
            if details['password'] == old:
                db['users'][p_id][u]['password'] = new
                save_db()
                return jsonify({"status": "success"})
            return jsonify({"error": "Old password incorrect!"}), 400
    return jsonify({"error": "User not found!"}), 400

@app.route("/api/google-auth", methods=["POST"])
def google_auth():
    d = request.json
    p_id, email, req_username = str(d['panel']), d['email'].lower().strip(), d['username'].lower().strip()
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    for u, details in db['users'][p_id].items():
        if details['email'] == email:
            if u != req_username:
                return jsonify({"error": "Security Alert: Username does not match this Email!"}), 400
            return jsonify({"status": "success", "email": email, "username": u})
    if req_username in db['users'][p_id]: 
        return jsonify({"error": "Username already taken. Please choose another."}), 400
    db['users'][p_id][req_username] = {"email": email, "password": "GoogleLogin", "ref_by": "", "ordered": False, "ref_signups": 0, "ref_active": 0, "first_claim": False}
    save_db()
    msg = f"💠 ⍟ SECURE GOOGLE LOGIN (P{p_id}) ⍟ 💠\n\n👤 Name: {req_username}\n✉️ Email: {email}"
    markup = {"inline_keyboard": [[{"text": "🚫 BLOCK USER", "callback_data": f"blkusr_{email}"}]]}
    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": msg, "reply_markup": markup})
    return jsonify({"status": "success", "email": email, "username": req_username})

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
    text = f"🚨 ⍟ FUND REQUEST ⍟ 🚨\n\n👤 User: {email}\n💰 Amount: ₹{amt}\n🧾 UTR/TXN: {utr}\n🎛️ Panel: {p_id}"
    markup = {"inline_keyboard": [[{"text": "✅ APPROVE", "callback_data": f"app_{utr}"}, {"text": "❌ REJECT", "callback_data": f"rej_{utr}"}], [{"text": "🚫 BLOCK & DELETE USER", "callback_data": f"blk_{utr}"}]]}
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
    db['orders'].append({"email": email, "panel": p_id, "id": order_id, "name": s_name, "qty": qty, "charge": charge, "status": "Pending", "refunded": False, "username": user})
    
    if user in db['users'][p_id] and not db['users'][p_id][user].get('ordered', False):
        db['users'][p_id][user]['ordered'] = True
        ref_by = db['users'][p_id][user].get('ref_by')
        if ref_by and ref_by in db['users'][p_id]:
            db['users'][p_id][ref_by]['ref_active'] = db['users'][p_id][ref_by].get('ref_active', 0) + 1
            
    save_db()
    msg = f"🚀 ⍟ ORDER RECEIVED (P{p_id}) ⍟ 🚀\n\n👤 User: {user}\n🛒 Service: {s_name[:30]}...\n🆔 ID: {s_id}\n🔗 Link: {link}\n🔢 Qty: {qty}\n💸 Amt: ₹{charge}\n🟡 Status: Pending"
    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": msg})
    return jsonify({"status": "success", "order": order_id})

@app.route("/api/claim-reward", methods=["POST"])
def claim_reward():
    d = request.json
    p_id, email, v_link, f_link = str(d['panel']), d['email'], d['views_link'], d['followers_link']
    user_key = None
    for u, details in db['users'][p_id].items():
        if details['email'] == email:
            user_key = u; break
            
    if not user_key: return jsonify({"error": "User not found"}), 400
    u_data = db['users'][p_id][user_key]
    first_claim = u_data.get('first_claim', False)
    
    if not first_claim:
        if u_data.get('ref_signups', 0) < 10: return jsonify({"error": "Need 10 signups!"}), 400
        db['users'][p_id][user_key]['first_claim'] = True
        claim_type = "First 10 Signups"
    else:
        if u_data.get('ref_active', 0) < 10: return jsonify({"error": "Need 10 active ordering referrals!"}), 400
        db['users'][p_id][user_key]['ref_active'] -= 10
        claim_type = "10 Active Orders"
        
    save_db()
    msg = f"🎁 ⍟ REWARD CLAIMED (P{p_id}) ⍟ 🎁\n\n👤 User: {user_key}\n✉️ Email: {email}\n👥 Type: {claim_type}\n🔗 Followers: {f_link}\n🔗 Views: {v_link}"
    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": msg})
    return jsonify({"status": "success"})

@app.route("/api/send-mail", methods=["POST"])
def send_mail():
    d = request.json
    p_id, email, message = str(d['panel']), d['email'], d['message']
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    
    if email not in db['mails'][p_id]: db['mails'][p_id][email] = []
    db['mails'][p_id][email].append({"from": "user", "msg": message, "read": True})
    save_db()
    
    text = f"📬 ⍟ NEW SUPPORT MAIL (P{p_id}) ⍟ 📬\n\n👤 User: {email}\n💬 Msg: {message}"
    markup = {"inline_keyboard": [[{"text": "✉️ REPLY TO USER", "callback_data": f"replymail_{email}"}]]}
    requests.post(f"https://api.telegram.org/bot{PANELS[p_id]['bot']}/sendMessage", json={"chat_id": PANELS[p_id]['chat'], "text": text, "reply_markup": markup})
    return jsonify({"status": "success"})

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
    unread_admin_mails = [m['msg'] for m in user_mails if m['from'] == 'admin' and not m.get('read', False)]
    for m in user_mails:
        if m['from'] == 'admin': m['read'] = True
    if unread_admin_mails: save_db()

    active_discount = 0
    t_now = time.time()
    
    g_disc = db['discounts']['all'][p_id]
    if g_disc['exp'] > t_now: active_discount = g_disc['percent']
    
    if email in db['discounts']['users'][p_id]:
        u_disc = db['discounts']['users'][p_id][email]
        if u_disc['exp'] > t_now and u_disc['percent'] > active_discount:
            active_discount = u_disc['percent']
            
    return jsonify({
        "balance": db['balances'][p_id].get(email, 0.0), 
        "txns": user_txns, 
        "orders": user_orders, 
        "user_info": user_info,
        "unread_mails": unread_admin_mails,
        "all_mails": user_mails,
        "config": db['config'],
        "discount": active_discount
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
