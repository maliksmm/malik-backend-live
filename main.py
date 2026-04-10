import json, os, threading, time, requests, re, uuid
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

PANELS = {
    "1": {"url": "https://xmediasmm.in/api/v2", "key": "TERI_KEY_1", "bot": "TERA_BOT_1", "chat": "7044754988"},
    "2": {"url": "https://wowsmmpanel.com/api/v2", "key": "9ddd128b2174a854bb4c3c97a7769ebe", "bot": "TERA_BOT_2", "chat": "7044754988"}
}

DB_FILE = "malik_db.json"
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                if "mails" not in data: data["mails"] = {"1": {}, "2": {}}
                if "config" not in data: data["config"] = {"1": {"qr":"", "upi":"followersincrease870@oksbi", "discount":0, "whatsapp":""}, "2": {"qr":"", "upi":"followersincrease870@oksbi", "discount":0, "whatsapp":""}}
                return data
        except: pass
    return {"users": {"1": {}, "2": {}}, "balances": {"1": {}, "2": {}}, "txns": [], "orders": [], "blocked": {"1": [], "2": []}, "mails": {"1": {}, "2": {}}, "config": {"1": {"qr":"", "upi":"followersincrease870@oksbi", "discount":0, "whatsapp":""}, "2": {"qr":"", "upi":"followersincrease870@oksbi", "discount":0, "whatsapp":""}}}

db = load_db()

def save_db():
    with open(DB_FILE, "w") as f: json.dump(db, f)

def keep_awake():
    while True:
        time.sleep(120)
        try: requests.get("http://localhost:8000/api/ping")
        except: pass
threading.Thread(target=keep_awake, daemon=True).start()

@app.route("/api/ping", methods=["GET"])
def ping(): return "Alive"

# --- TELEGRAM BOT DYNAMIC COMMANDS ---
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
                    
                    # ⚙️ SUPER ADMIN COMMANDS
                    if msg_text == '/users':
                        total = len(db['users'][p_id])
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"👑 Total Users (P{p_id}): {total}"})
                    
                    elif msg_text.startswith('/discount '):
                        parts = msg_text.split()
                        if len(parts) == 3:
                            target, pct = parts[1], float(parts[2])
                            if target.lower() == "all":
                                db['config'][p_id]['discount'] = pct
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Global discount set to {pct}%"})
                            elif target in db['users'][p_id]:
                                db['users'][p_id][target]['personal_discount'] = pct
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Discount of {pct}% applied to {target}"})
                            save_db()

                    elif msg_text.startswith('/setqr '):
                        db['config'][p_id]['qr'] = msg_text.replace('/setqr ', '')
                        save_db(); requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "✅ QR Updated!"})
                        
                    elif msg_text.startswith('/setupi '):
                        db['config'][p_id]['upi'] = msg_text.replace('/setupi ', '')
                        save_db(); requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "✅ UPI Updated!"})

                    elif msg_text.startswith('/broadcast '):
                        b_msg = msg_text.replace('/broadcast ', '')
                        count = 0
                        for u_name, u_details in db['users'][p_id].items():
                            em = u_details['email']
                            if em not in db['mails'][p_id]: db['mails'][p_id][em] = []
                            db['mails'][p_id][em].append({"from": "admin", "msg": f"📢 BROADCAST: {b_msg}", "read": False})
                            count += 1
                        save_db(); requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Broadcast sent to {count} users."})

                    elif msg_text.startswith('/reply '):
                        parts = msg_text.split(' ', 2)
                        if len(parts) >= 3:
                            target_email, reply_msg = parts[1].strip(), parts[2].strip()
                            if target_email not in db['mails'][p_id]: db['mails'][p_id][target_email] = []
                            db['mails'][p_id][target_email].append({"from": "admin", "msg": reply_msg, "read": False})
                            save_db(); requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Reply sent to {target_email}!"})

                # ... (Purana Approve/Reject/Block Button Code Yahan Same Rahega, Jagah bachane ke liye main skip kar raha hu, apna pichla block buttons wala code iske neeche exactly paste karna) ...
                
        except: pass
        time.sleep(1.5)

threading.Thread(target=poll_telegram, args=("1",), daemon=True).start()
threading.Thread(target=poll_telegram, args=("2",), daemon=True).start()

# --- ROUTES ---
@app.route("/api/signup", methods=["POST"])
def signup():
    d = request.json
    p_id, user, email, pwd = str(d['panel']), d['username'].lower().strip(), d['email'].lower().strip(), d['pass']
    ref_by = d.get('ref', '')
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    if user in db['users'][p_id] or any(u['email'] == email for u in db['users'][p_id].values()): return jsonify({"error": "Username or Email already exists!"}), 400
    
    # User ko Reseller API key di
    api_key = str(uuid.uuid4().hex)
    db['users'][p_id][user] = {"email": email, "password": pwd, "ref_by": ref_by, "ordered": False, "ref_signups": 0, "ref_active": 0, "first_claim": False, "api_key": api_key, "personal_discount": 0}
    save_db(); return jsonify({"status": "success"})

@app.route("/api/login", methods=["POST"])
def login():
    d = request.json
    p_id, user, pwd = str(d['panel']), d['username'].lower().strip(), d['pass']
    if user not in db['users'][p_id] or db['users'][p_id][user]["password"] != pwd: return jsonify({"error": "Invalid Credentials!"}), 400
    email = db['users'][p_id][user]["email"]
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    return jsonify({"status": "success", "email": email})

@app.route("/api/get-services", methods=["POST"])
def get_services():
    p_id = str(request.json.get("panel"))
    user = request.json.get("username", "")
    res = requests.post(PANELS[p_id]["url"], data={"key": PANELS[p_id]["key"], "action": "services"}, headers={'User-Agent': 'Mozilla/5.0'})
    if res.status_code == 200:
        services = res.json()
        global_discount = db['config'][p_id].get('discount', 0)
        personal_discount = db['users'][p_id].get(user, {}).get('personal_discount', 0)
        final_discount = max(global_discount, personal_discount)
        
        # Apply discount logic
        for s in services:
            base_rate = float(s['rate'])
            s['rate'] = base_rate - (base_rate * (final_discount / 100))
        return jsonify(services)
    return jsonify([])

# Sync mein Config aur App Settings bhej rahe hain
@app.route("/api/sync", methods=["POST"])
def sync():
    email, p_id = request.json['email'], str(request.json['panel'])
    if email in db['blocked'][p_id]: return jsonify({"status": "blocked"}), 403
    user_orders = [o for o in db['orders'] if o['email'] == email and o['panel'] == p_id]
    user_txns = [t for t in db['txns'] if t['email'] == email and t['panel'] == p_id]
    
    user_info = {}
    for u, details in db['users'][p_id].items():
        if details['email'] == email: user_info = details; break
            
    user_mails = db['mails'][p_id].get(email, [])
    unread_admin_mails = [m['msg'] for m in user_mails if m['from'] == 'admin' and not m.get('read', False)]
    for m in user_mails:
        if m['from'] == 'admin': m['read'] = True
    if unread_admin_mails: save_db()
            
    return jsonify({
        "balance": db['balances'][p_id].get(email, 0.0), 
        "txns": user_txns, "orders": user_orders, 
        "user_info": user_info, "unread_mails": unread_admin_mails,
        "all_mails": user_mails, "config": db['config'][p_id]
    })

# Pura purana Place Order, Cancel, Add Funds wala logic yahan neeche paste karna
# ...
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
