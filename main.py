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
except:
    pass

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
        except: pass

    if data is None and os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
        except: pass

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
            if "mails" not in data: data["mails"] = {"1": {}, "2": {}}
            if "config" not in data: 
                data["config"] = {
                    "qr_1": "./AccountQRCodeJ&K Bank - 6648_DARK_THEME (13).png", 
                    "qr_2": "./AccountQRCodeJ&K Bank - 6648_DARK_THEME (13).png",
                    "socials": {"tg": "https://t.me/zr3v_x", "yt": "https://youtube.com/@z3rv_x?si=ayQnR40t-521AFTb", "ig": "", "wp": ""},
                    "mail_theme": "1",
                    "app_name": "MALIK PROXY SMM",
                    "log_system": "1",
                    "auto_system": False,
                    "admins": ["7044754988"],
                    "owner": "7044754988"
                }
            else:
                if "app_name" not in data["config"]: data["config"]["app_name"] = "MALIK PROXY SMM"
                if "log_system" not in data["config"]: data["config"]["log_system"] = "1"
                if "auto_system" not in data["config"]: data["config"]["auto_system"] = False
                if "admins" not in data["config"]: data["config"]["admins"] = ["7044754988"]
                data["config"]["owner"] = "7044754988"

            if "discounts" not in data: data["discounts"] = {"users": {}, "all": {}}
            
            for p_id in data["panels"]:
                if p_id not in data["users"]: data["users"][p_id] = {}
                if p_id not in data["balances"]: data["balances"][p_id] = {}
                if p_id not in data["blocked"]: data["blocked"][p_id] = []
                if p_id not in data["mails"]: data["mails"][p_id] = {}
                if p_id not in data["discounts"]["users"]: data["discounts"]["users"][p_id] = {}
                if p_id not in data["discounts"]["all"]: data["discounts"]["all"][p_id] = {"percent": 0, "exp": 0}
            return data
        except Exception as e: 
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
            "admins": ["7044754988"],
            "owner": "7044754988"
        },
        "discounts": {"users": {"1": {}, "2": {}}, "all": {"1": {"percent": 0, "exp": 0}, "2": {"percent": 0, "exp": 0}}}
    }

db = load_db()
active_bots = {}

def save_db():
    if USE_MONGO:
        try:
            db_collection.update_one({"_id": "core_db"}, {"$set": {"data": db}}, upsert=True)
        except: pass
    try:
        with open(DB_FILE, "w") as f: json.dump(db, f)
    except: pass

def keep_awake():
    while True:
        time.sleep(120)
        try: requests.get("https://malik-proxy-smm.onrender.com/api/ping", timeout=5)
        except: pass
threading.Thread(target=keep_awake, daemon=True).start()

@app.route("/api/ping", methods=["GET"])
def ping(): return "Alive"

def background_order_sync():
    while True:
        time.sleep(15)
        for p_id, p_data in list(db['panels'].items()):
            pending_orders = [o for o in db['orders'] if o['panel'] == p_id and o['status'].lower() not in ['completed', 'canceled', 'cancelled', 'partial']]
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

def is_owner(chat_id):
    return str(chat_id) == "7044754988" or str(chat_id) == str(db["config"].get("owner", "7044754988"))

def is_admin(chat_id):
    return is_owner(chat_id) or str(chat_id) in db['config'].get('admins', ["7044754988"])

def poll_telegram(p_id):
    if p_id not in db['panels']: return
    bot_token = db['panels'][p_id]["bot"]
    offset = 0
    while p_id in db['panels']:
        try:
            res = requests.get(f"https://api.telegram.org/bot{bot_token}/getUpdates?offset={offset}&timeout=10", timeout=15).json()
            for update in res.get('result', []):
                offset = update['update_id'] + 1
                
                # Callback Query Handler for Buttons
                if 'callback_query' in update:
                    cb = update['callback_query']
                    cb_id = cb['id']
                    cb_data = cb.get('data', '')
                    from_id = str(cb['from']['id'])
                    
                    if not is_admin(from_id):
                        requests.post(f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery", json={"callback_query_id": cb_id, "text": "❌ Unauthorized Admin!"})
                        continue
                        
                    if cb_data.startswith("app_"):
                        utr = cb_data.replace("app_", "")
                        for t in db["txns"]:
                            if t["utr"] == utr and t["status"] == "Pending":
                                t["status"] = "Approved"
                                u_email = t["email"]
                                t_panel = t["panel"]
                                amt = float(t["amount"])
                                db["balances"][t_panel][u_email] = db["balances"][t_panel].get(u_email, 0.0) + amt
                                save_db()
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": cb["message"]["chat"]["id"], "text": f"✅ Payment UTR <code>{utr}</code> Approved! ₹{amt} added.", "parse_mode": "HTML"})
                                break
                    elif cb_data.startswith("rej_"):
                        utr = cb_data.replace("rej_", "")
                        for t in db["txns"]:
                            if t["utr"] == utr and t["status"] == "Pending":
                                t["status"] = "Rejected"
                                save_db()
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": cb["message"]["chat"]["id"], "text": f"❌ Payment UTR <code>{utr}</code> Rejected!", "parse_mode": "HTML"})
                                break
                    requests.post(f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery", json={"callback_query_id": cb_id, "text": "Done!"})

                # Text Message Commands Handler
                elif 'message' in update and 'text' in update['message']:
                    msg_text = update['message']['text']
                    chat_id = str(update['message']['chat']['id'])
                    
                    if not is_admin(chat_id):
                        continue
                    
                    try:
                        if msg_text == '/start':
                            markup = {"keyboard": [[{"text": "/users"}, {"text": "/help_commands"}]], "resize_keyboard": True}
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"👑 Welcome Admin! Connected to {db['panels'][p_id]['name']}.", "reply_markup": markup})
                        
                        elif msg_text == '/help_commands':
                            txt = "🛠️ *VIP COMMANDS*\n\n`/users` - List users\n`/appinfo` - App stats\n`/setqr <url>` - Set QR\n`/discount <email> <percent>`\n`/discountall <time> <unit> <percent> <reason>`\n`/broadcast <msg>`\n`/reply <email> <msg>`\n\n*NEW SUPER COMMANDS:*\n`/changename <New_Name>`\n`/logsystem 1` or `/logsystem 2`\n`/autosystem on` or `/autosystem off`\n`/addcoupon <code> <amount>`\n`/changepanel <url> <key>`\n`/addpanel <id> <name> <color> <url> <key> <bot> <chat>`\n`/removepanel <id>`\n`/setig <url>`, `/setyt <url>`, `/setwp <url>`, `/settg <url>`\n`/mailtheme <1/2/3>`\n`/api_approve <email>`, `/api_reject <email>`\n`/addadmin <chat_id>`, `/removeadmin <chat_id>`"
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": txt, "parse_mode": "Markdown"})
                            
                        elif msg_text.startswith('/addadmin ') and is_owner(chat_id):
                            new_admin = msg_text.replace('/addadmin ', '').strip()
                            if new_admin not in db['config']['admins']:
                                db['config']['admins'].append(new_admin)
                                save_db()
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Admin {new_admin} added successfully!"})
                            else:
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"⚠️ Admin {new_admin} already exists!"})
                                
                        elif msg_text.startswith('/removeadmin ') and is_owner(chat_id):
                            rem_admin = msg_text.replace('/removeadmin ', '').strip()
                            if rem_admin == "7044754988":
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "❌ OWNER CANNOT BE REMOVED!"})
                            elif rem_admin in db['config']['admins']:
                                db['config']['admins'].remove(rem_admin)
                                save_db()
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Admin {rem_admin} removed successfully!"})

                        elif msg_text == '/users':
                            p_users = db['users'].get(p_id, {})
                            if not p_users:
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"👤 No users registered in {db['panels'][p_id]['name']}."})
                            else:
                                txt = f"👥 <b>USERS LIST ({db['panels'][p_id]['name']})</b>\n\n"
                                for em, info in p_users.items():
                                    bal = db['balances'].get(p_id, {}).get(em, 0.0)
                                    status = "🔴 Blocked" if em in db['blocked'].get(p_id, []) else "🟢 Active"
                                    txt += f"📧 {em}\n👤 Username: {info.get('username','N/A')}\n💰 Balance: ₹{bal:.2f}\n🔑 API Key: <code>{info.get('api_key','N/A')}</code>\n⚡ Status: {status}\n--------------------\n"
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": txt, "parse_mode": "HTML"})

                        elif msg_text.startswith('/addpanel '):
                            parts = msg_text.split(maxsplit=7)
                            if len(parts) >= 8:
                                n_id, n_name, n_color, n_url, n_key, n_bot, n_chat = parts[1], parts[2], parts[3], parts[4], parts[5], parts[6], parts[7]
                                db['panels'][n_id] = {"name": n_name, "color": n_color, "url": n_url, "key": n_key, "bot": n_bot, "chat": n_chat}
                                for k in ["users", "balances", "blocked", "mails"]:
                                    if n_id not in db[k]: db[k][n_id] = {} if k != "blocked" else []
                                save_db()
                                start_bot_threads()
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Panel {n_id} ({n_name}) added successfully!"})

                        elif msg_text.startswith('/removepanel '):
                            r_id = msg_text.replace('/removepanel ', '').strip()
                            if r_id in db['panels'] and len(db['panels']) > 1:
                                del db['panels'][r_id]
                                save_db()
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Panel {r_id} removed successfully!"})
                            else:
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": "❌ Cannot remove main panel!"})

                    except Exception as e: pass
        except Exception as e:
            time.sleep(3)

def start_bot_threads():
    for p_id in list(db.get('panels', {}).keys()):
        if p_id not in active_bots:
            t = threading.Thread(target=poll_telegram, args=(p_id,), daemon=True)
            t.start()
            active_bots[p_id] = t

start_bot_threads()

# Server API Endpoints
@app.route('/api/init-app', methods=['GET'])
def init_app():
    panels_list = [{"id": k, "name": v["name"], "color": v["color"]} for k, v in db["panels"].items()]
    return jsonify({"panels": panels_list, "config": db["config"]})

@app.route('/api/add-funds', methods=['POST'])
def add_funds():
    data = request.json or {}
    p_id = str(data.get("panel") or "1")
    email = (data.get("email") or "").lower().strip()
    amt = data.get("amount")
    utr = str(data.get("utr") or "").strip()
    
    if not amt or not utr: return jsonify({"error": "Invalid Details"}), 400
        
    txn = {"panel": p_id, "email": email, "amount": amt, "utr": utr, "status": "Pending"}
    db["txns"].append(txn)
    save_db()
    
    bot_token = db["panels"].get(p_id, {}).get("bot")
    admin_chat = db["panels"].get(p_id, {}).get("chat", "7044754988")
    if bot_token and admin_chat:
        markup = {
            "inline_keyboard": [[
                {"text": "✅ Approve", "callback_data": f"app_{utr}"},
                {"text": "❌ Reject", "callback_data": f"rej_{utr}"}
            ]]
        }
        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
            "chat_id": admin_chat, 
            "text": f"💰 <b>NEW PAYMENT REQUEST</b>\n\nPanel: {p_id}\nUser: {email}\nAmount: ₹{amt}\nUTR: <code>{utr}</code>", 
            "parse_mode": "HTML",
            "reply_markup": markup
        })
        
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
