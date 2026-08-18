import json, os, threading, time, requests, re, random, string
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

# =========================================================================
# 🔴 MONGODB LIFETIME DATA ENGINE (Data amar rakhne ke liye) 🔴
MONGO_URI = "mongodb+srv://USERNAME:PASSWORD@cluster0.mongodb.net/?retryWrites=true&w=majority"
# =========================================================================

USE_MONGO = False
try:
    if "mongodb+srv" in MONGO_URI and "USERNAME" not in MONGO_URI:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        mongo_db = client["malik_smm_pro"]
        db_collection = mongo_db["database"]
        USE_MONGO = True
except Exception:
    USE_MONGO = False

DB_FILE = "malik_db.json"

def generate_api_key():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=15))

def load_db():
    data = None
    if USE_MONGO:
        try:
            doc = db_collection.find_one({"_id": "core_db"})
            if doc and "data" in doc:
                data = doc["data"]
        except Exception: 
            pass

    if data is None and os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
        except Exception: 
            pass

    if data is not None:
        try:
            if "panels" not in data:
                data["panels"] = {
                    "1": {"name": "P1", "color": "#00f3ff", "url": "https://xmediasmm.in/api/v2", "key": "52bf994ea9b8fd9c173ace0f0080285e", "bot": "8291687285:AAFDWBGzzaKtQsoGa5ipaYt-dYCpUs7W2aU", "chat": "7044754988"},
                    "2": {"name": "P2", "color": "#ff1493", "url": "https://wowsmmpanel.com/api/v2", "key": "ac53a5c8d669a155fca7c70733ff77c1", "bot": "8611984647:AAEvQQy_Vcz9P3s2Zj0Zq7fn2sMxryk1nuA", "chat": "7044754988"}
                }
            else:
                if "2" in data["panels"]:
                    data["panels"]["2"]["url"] = "https://wowsmmpanel.com/api/v2"
                    data["panels"]["2"]["key"] = "ac53a5c8d669a155fca7c70733ff77c1"

            if "coupons" not in data: data["coupons"] = {}
            if "mails" not in data: data["mails"] = {}
            if "users" not in data: data["users"] = {}
            if "balances" not in data: data["balances"] = {}
            if "blocked" not in data: data["blocked"] = {}
            if "orders" not in data: data["orders"] = []
            if "txns" not in data: data["txns"] = []

            if "config" not in data: 
                data["config"] = {
                    "qr_1": "./AccountQRCodeJ&K Bank - 6648_DARK_THEME (13).png", 
                    "qr_2": "./AccountQRCodeJ&K Bank - 6648_DARK_THEME (13).png",
                    "socials": {"tg": "https://t.me/zr3v_x", "yt": "https://youtube.com/@z3rv_x?si=ayQnR40t-521AFTb", "ig": "", "wp": ""},
                    "mail_theme": "1",
                    "app_name": "MALIK PROXY SMM",
                    "log_system": "1",
                    "auto_system": False,
                    "admins": ["7044754988"]
                }
            else:
                if "app_name" not in data["config"]: data["config"]["app_name"] = "MALIK PROXY SMM"
                if "log_system" not in data["config"]: data["config"]["log_system"] = "1"
                if "auto_system" not in data["config"]: data["config"]["auto_system"] = False
                if "admins" not in data["config"]: data["config"]["admins"] = ["7044754988"]

            if "discounts" not in data: data["discounts"] = {"users": {}, "all": {}}
            
            for p_id in data["panels"]:
                if p_id not in data["users"]: data["users"][p_id] = {}
                if p_id not in data["balances"]: data["balances"][p_id] = {}
                if p_id not in data["blocked"]: data["blocked"][p_id] = []
                if p_id not in data["mails"]: data["mails"][p_id] = {}
                if p_id not in data["discounts"]["users"]: data["discounts"]["users"][p_id] = {}
                if p_id not in data["discounts"]["all"]: data["discounts"]["all"][p_id] = {"percent": 0, "exp": 0}
            return data
        except Exception: 
            pass
            
    default_panels = {
        "1": {"name": "P1", "color": "#00f3ff", "url": "https://xmediasmm.in/api/v2", "key": "52bf994ea9b8fd9c173ace0f0080285e", "bot": "8291687285:AAFDWBGzzaKtQsoGa5ipaYt-dYCpUs7W2aU", "chat": "7044754988"},
        "2": {"name": "P2", "color": "#ff1493", "url": "https://wowsmmpanel.com/api/v2", "key": "ac53a5c8d669a155fca7c70733ff77c1", "bot": "8611984647:AAEvQQy_Vcz9P3s2Zj0Zq7fn2sMxryk1nuA", "chat": "7044754988"}
    }
    return {
        "panels": default_panels, "users": {"1": {}, "2": {}}, "balances": {"1": {}, "2": {}}, 
        "txns": [], "orders": [], "blocked": {"1": [], "2": []}, "mails": {"1": {}, "2": {}}, 
        "coupons": {},
        "config": {
            "qr_1": "./AccountQRCodeJ&K Bank - 6648_DARK_THEME (13).png", 
            "qr_2": "./AccountQRCodeJ&K Bank - 6648_DARK_THEME (13).png",
            "socials": {"tg": "https://t.me/zr3v_x", "yt": "https://youtube.com/@z3rv_x?si=ayQnR40t-521AFTb", "ig": "", "wp": ""},
            "mail_theme": "1",
            "app_name": "MALIK PROXY SMM",
            "log_system": "1",
            "auto_system": False,
            "admins": ["7044754988"]
        },
        "discounts": {"users": {"1": {}, "2": {}}, "all": {"1": {"percent": 0, "exp": 0}, "2": {"percent": 0, "exp": 0}}}
    }

db = load_db()
active_bots = {}
bot_lock = threading.Lock()

def save_db():
    if USE_MONGO:
        try:
            db_collection.update_one({"_id": "core_db"}, {"$set": {"data": db}}, upsert=True)
        except Exception: pass
    try:
        with open(DB_FILE, "w") as f: 
            json.dump(db, f, indent=2)
    except Exception: pass

def keep_awake():
    while True:
        time.sleep(120)
        try: requests.get("https://malik-proxy-smm.onrender.com/api/ping", timeout=5)
        except Exception: pass
threading.Thread(target=keep_awake, daemon=True).start()

@app.route("/api/ping", methods=["GET"])
def ping(): return "Alive"

def background_order_sync():
    while True:
        time.sleep(15)
        for p_id, p_data in list(db['panels'].items()):
            pending_orders = [o for o in db.get('orders', []) if o.get('panel') == p_id and str(o.get('status', '')).lower() not in ['completed', 'canceled', 'cancelled', 'partial']]
            if pending_orders:
                order_ids = ",".join([str(o['id']) for o in pending_orders])
                try:
                    res = requests.post(p_data["url"], data={"key": p_data["key"], "action": "status", "orders": order_ids}, timeout=10).json()
                    for o in pending_orders:
                        oid = str(o['id'])
                        if oid in res and type(res[oid]) == dict:
                            real_status = res[oid].get("status", o['status'])
                            if real_status.lower() != o['status'].lower():
                                if real_status.lower() in ['completed', 'canceled', 'cancelled', 'partial']:
                                    status_emo = "🟢" if real_status.lower() == 'completed' else ("🔴" if real_status.lower() in ['canceled', 'cancelled'] else "🟡")
                                    msg = f"🔱 ⍟ ORDER UPDATE ({p_data['name']}) ⍟ 🔱\n\n👤 User: {o['username']}\n🛒 Service: {o['name'][:30]}...\n🆔 Order ID: {oid}\n{status_emo} Status: {real_status.upper()}"
                                    requests.post(f"https://api.telegram.org/bot{p_data['bot']}/sendMessage", json={"chat_id": p_data['chat'], "text": msg})
                                    
                                    o['status'] = real_status
                                    if real_status.lower() in ['canceled', 'cancelled'] and not o.get('refunded', False):
                                        db['balances'][p_id][o['email']] = db['balances'][p_id].get(o['email'], 0.0) + o['charge']
                                        o['refunded'] = True
                                    elif real_status.lower() == 'partial' and not o.get('refunded', False):
                                        remains = float(res[oid].get("remains", 0))
                                        if remains > 0 and float(o.get('qty', 1)) > 0:
                                            refund_amt = (remains / float(o['qty'])) * o['charge']
                                            db['balances'][p_id][o['email']] = db['balances'][p_id].get(o['email'], 0.0) + refund_amt
                                        o['refunded'] = True
                                    save_db()
                except Exception: pass

threading.Thread(target=background_order_sync, daemon=True).start()

def poll_telegram(p_id):
    offset = 0
    while True:
        with bot_lock:
            if p_id not in db['panels']:
                active_bots.pop(p_id, None)
                break
            bot_token = db['panels'][p_id].get("bot")

        if not bot_token:
            time.sleep(5)
            continue

        try:
            res = requests.get(f"https://api.telegram.org/bot{bot_token}/getUpdates?offset={offset}&timeout=5", timeout=10).json()
            if not res.get('ok'):
                time.sleep(3)
                continue

            for update in res.get('result', []):
                offset = update['update_id'] + 1
                
                if 'message' in update and 'text' in update['message']:
                    msg_text = update['message']['text'].strip()
                    chat_id = str(update['message']['chat']['id'])
                    
                    admins = db['config'].get('admins', ["7044754988"])
                    if chat_id not in admins:
                        continue
                    
                    try:
                        if msg_text == '/start':
                            markup = {"keyboard": [[{"text": "/users"}, {"text": "/help_commands"}]], "resize_keyboard": True}
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"👑 Welcome Admin! Connected to {db['panels'][p_id]['name']}.", "reply_markup": markup})
                        
                        elif msg_text == '/help_commands':
                            txt = "🛠️ *VIP COMMANDS*\n\n`/users` - List users\n`/appinfo` - App stats\n`/setqr <url>` - Set QR\n`/discount <email> <percent>`\n`/discountall <time> <unit> <percent> <reason>`\n`/broadcast <msg>`\n`/reply <email> <msg>`\n\n*NEW SUPER COMMANDS:*\n`/changename <New_Name>`\n`/logsystem 1` or `/logsystem 2`\n`/autosystem on` or `/autosystem off`\n`/addcoupon <code> <amount>`\n`/changepanel <url> <key>`\n`/addpanel <id> <name> <color> <url> <key> <bot> <chat>`\n`/removepanel <id>`\n`/setig <url>`, `/setyt <url>`, `/setwp <url>`, `/settg <url>`\n`/mailtheme <1/2/3>`\n`/api_approve <email>`, `/api_reject <email>`\n`/addadmin <chat_id>`, `/removeadmin <chat_id>`"
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": txt, "parse_mode": "Markdown"})

                        elif msg_text.startswith('/addadmin '):
                            new_admin = msg_text.replace('/addadmin ', '').strip()
                            if new_admin not in db['config']['admins']:
                                db['config']['admins'].append(new_admin)
                                save_db()
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Admin {new_admin} added successfully!"})
                            else:
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"⚠️ Admin {new_admin} already exists!"})

                        elif msg_text.startswith('/removeadmin '):
                            rem_admin = msg_text.replace('/removeadmin ', '').strip()
                            if rem_admin in db['config']['admins'] and len(db['config']['admins']) > 1:
                                db['config']['admins'].remove(rem_admin)
                                save_db()
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Admin {rem_admin} removed!"})
                            else:
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"⚠️ Cannot remove. Admin not found or it's the only admin left!"})

                        elif msg_text.startswith('/changename '):
                            new_name = msg_text.replace('/changename ', '').strip()
                            db['config']['app_name'] = new_name
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ App Name changed globally to: {new_name}"})

                        elif msg_text == '/autosystem on':
                            db['config']['auto_system'] = True
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"⚡ Auto-System is now ON. API Requests will be auto-approved."})

                        elif msg_text == '/autosystem off':
                            db['config']['auto_system'] = False
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"🛑 Auto-System is now OFF. Manual approval required."})

                        elif msg_text in ['/logsystem 1', '/logsystem 2']:
                            sys_num = msg_text.split(' ')[1]
                            db['config']['log_system'] = sys_num
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Login System changed to Type {sys_num}!"})

                        elif msg_text.startswith('/addcoupon '):
                            parts = msg_text.split(' ')
                            code = parts[1].strip().upper()
                            amt = float(parts[2])
                            db['coupons'][code] = amt
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Coupon {code} created for ₹{amt}!"})

                        elif msg_text.startswith('/changepanel '):
                            parts = msg_text.split(' ')
                            new_url = parts[1].strip()
                            new_key = parts[2].strip()
                            db['panels'][p_id]['url'] = new_url
                            db['panels'][p_id]['key'] = new_key
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Connected Panel API updated successfully!"})

                        elif msg_text.startswith('/addpanel '):
                            parts = msg_text.split(' ')
                            nid = parts[1].strip()
                            db['panels'][nid] = {
                                "name": parts[2].strip(), "color": parts[3].strip(), 
                                "url": parts[4].strip(), "key": parts[5].strip(), 
                                "bot": parts[6].strip(), "chat": parts[7].strip()
                            }
                            if nid not in db["users"]: db["users"][nid] = {}
                            if nid not in db["balances"]: db["balances"][nid] = {}
                            if nid not in db["blocked"]: db["blocked"][nid] = []
                            if nid not in db["mails"]: db["mails"][nid] = {}
                            if nid not in db["discounts"]["users"]: db["discounts"]["users"][nid] = {}
                            if nid not in db["discounts"]["all"]: db["discounts"]["all"][nid] = {"percent": 0, "exp": 0}
                            save_db()
                            start_polling_for_panel(nid)
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Panel {nid} added successfully!"})

                        elif msg_text.startswith('/removepanel '):
                            nid = msg_text.split(' ')[1].strip()
                            if nid in db['panels']:
                                del db['panels'][nid]
                                save_db()
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Panel {nid} removed!"})

                        elif msg_text.startswith('/setig '):
                            db['config']['socials']['ig'] = msg_text.replace('/setig ', '').strip()
                            save_db(); requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "✅ IG Link Updated"})
                        elif msg_text.startswith('/setyt '):
                            db['config']['socials']['yt'] = msg_text.replace('/setyt ', '').strip()
                            save_db(); requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "✅ YT Link Updated"})
                        elif msg_text.startswith('/settg '):
                            db['config']['socials']['tg'] = msg_text.replace('/settg ', '').strip()
                            save_db(); requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "✅ TG Link Updated"})
                        elif msg_text.startswith('/setwp '):
                            db['config']['socials']['wp'] = msg_text.replace('/setwp ', '').strip()
                            save_db(); requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "✅ WP Link Updated"})
                        
                        elif msg_text.startswith('/mailtheme '):
                            db['config']['mail_theme'] = msg_text.replace('/mailtheme ', '').strip()
                            save_db(); requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "✅ Mail Theme Updated"})

                        elif msg_text == '/appinfo':
                            total_u = len(db['users'].get(p_id, {}))
                            total_bal = sum(db['balances'].get(p_id, {}).values())
                            txt = f"📊 *APP STATS ({db['panels'][p_id]['name']})*\n\n👥 Total Users: {total_u}\n💰 Total Balances: ₹{total_bal:.2f}"
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": txt, "parse_mode": "Markdown"})

                        elif msg_text == '/users':
                            total_users = len(db['users'].get(p_id, {}))
                            if total_users == 0:
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "⚠️ No users found."})
                            else:
                                keys = []
                                for u_name, u_details in db['users'][p_id].items():
                                    em = u_details['email']
 
