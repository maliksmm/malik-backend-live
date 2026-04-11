import json, os, threading, time, requests, re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_FILE = "malik_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                
                if "panels" not in data:
                    data["panels"] = {
                        "1": {"name": "P1", "color": "#00f3ff", "url": "https://xmediasmm.in/api/v2", "key": "52bf994ea9b8fd9c173ace0f0080285e", "bot": "8291687285:AAFDWBGzzaKtQsoGa5ipaYt-dYCpUs7W2aU", "chat": "7044754988"},
                        "2": {"name": "P2", "color": "#ff1493", "url": "https://wowsmmpanel.com/api/v2", "key": "3e3ed3099b90f481aa88e85d692b67a3", "bot": "8611984647:AAEvQQy_Vcz9P3s2Zj0Zq7fn2sMxryk1nuA", "chat": "7044754988"}
                    }
                else:
                    if "2" in data["panels"]:
                        data["panels"]["2"]["url"] = "https://wowsmmpanel.com/api/v2"
                        data["panels"]["2"]["key"] = "3e3ed3099b90f481aa88e85d692b67a3"

                if "coupons" not in data: data["coupons"] = {}
                if "mails" not in data: data["mails"] = {"1": {}, "2": {}}
                if "config" not in data: 
                    data["config"] = {
                        "qr_1": "./AccountQRCodeJ&K Bank - 6648_DARK_THEME (13).png", 
                        "qr_2": "./AccountQRCodeJ&K Bank - 6648_DARK_THEME (13).png",
                        "socials": {"tg": "https://t.me/zr3v_x", "yt": "https://youtube.com/@z3rv_x?si=ayQnR40t-521AFTb", "ig": "", "wp": ""},
                        "mail_theme": "1"
                    }
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
        "2": {"name": "P2", "color": "#ff1493", "url": "https://wowsmmpanel.com/api/v2", "key": "3e3ed3099b90f481aa88e85d692b67a3", "bot": "8611984647:AAEvQQy_Vcz9P3s2Zj0Zq7fn2sMxryk1nuA", "chat": "7044754988"}
    }
    return {
        "panels": default_panels, "users": {"1": {}, "2": {}}, "balances": {"1": {}, "2": {}}, 
        "txns": [], "orders": [], "blocked": {"1": [], "2": []}, "mails": {"1": {}, "2": {}}, 
        "coupons": {},
        "config": {
            "qr_1": "./AccountQRCodeJ&K Bank - 6648_DARK_THEME (13).png", 
            "qr_2": "./AccountQRCodeJ&K Bank - 6648_DARK_THEME (13).png",
            "socials": {"tg": "https://t.me/zr3v_x", "yt": "https://youtube.com/@z3rv_x?si=ayQnR40t-521AFTb", "ig": "", "wp": ""},
            "mail_theme": "1"
        },
        "discounts": {"users": {"1": {}, "2": {}}, "all": {"1": {"percent": 0, "exp": 0}, "2": {"percent": 0, "exp": 0}}}
    }

db = load_db()
active_bots = {}

def save_db():
    with open(DB_FILE, "w") as f: json.dump(db, f)

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

def poll_telegram(p_id):
    if p_id not in db['panels']: return
    bot_token = db['panels'][p_id]["bot"]
    offset = 0
    while p_id in db['panels']:
        try:
            res = requests.get(f"https://api.telegram.org/bot{bot_token}/getUpdates?offset={offset}&timeout=10", timeout=15).json()
            for update in res.get('result', []):
                offset = update['update_id'] + 1
                
                try:
                    if 'message' in update and 'text' in update['message']:
                        msg_text = update['message']['text']
                        chat_id = update['message']['chat']['id']
                        
                        if msg_text == '/start':
                            markup = {"keyboard": [[{"text": "/users"}, {"text": "/help_commands"}]], "resize_keyboard": True}
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"👑 Welcome Admin! Connected to {db['panels'][p_id]['name']}.", "reply_markup": markup})
                        
                        elif msg_text == '/help_commands':
                            txt = "🛠️ *VIP COMMANDS*\n\n`/users` - List users\n`/appinfo` - App stats\n`/setqr <url>` - Set QR\n`/discount <email> <time> <unit> <percent>`\n`/discountall <time> <unit> <percent> <reason>`\n`/broadcast <msg>`\n`/reply <email> <msg>`\n\n*NEW COMMANDS:*\n`/addcoupon <code> <amount>`\n`/changepanel <new_api_url> <new_api_key>`\n`/addpanel <id> <name> <color> <api_url> <api_key> <bot_token> <chat_id>`\n`/removepanel <id>`\n`/setig <url>`, `/setyt <url>`, `/setwp <url>`, `/settg <url>`\n`/mailtheme <1/2/3>`\n`/api_approve <email>`, `/api_reject <email>`"
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": txt, "parse_mode": "Markdown"})

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
                            total_u = len(db['users'][p_id])
                            total_bal = sum(db['balances'][p_id].values())
                            txt = f"📊 *APP STATS ({db['panels'][p_id]['name']})*\n\n👥 Total Users: {total_u}\n💰 Total Balances: ₹{total_bal:.2f}"
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
                                list_msg = f"👑 TOTAL USERS ({db['panels'][p_id]['name']}): {total_users} 👑\n\n⚡ Click a user below:"
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": list_msg, "reply_markup": markup})
                        
                        elif msg_text.startswith('/reply '):
                            parts = msg_text.split(' ', 2)
                            target_email = parts[1].strip()
                            reply_msg = parts[2].strip()
                            if target_email not in db['mails'][p_id]: db['mails'][p_id][target_email] = []
                            db['mails'][p_id][target_email].append({"from": "admin", "msg": reply_msg, "read": False})
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Reply sent to {target_email}!"})

                        elif msg_text.startswith('/setqr '):
                            new_url = msg_text.replace('/setqr ', '').strip()
                            db['config'][f"qr_{p_id}"] = new_url
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ QR Code updated successfully for {db['panels'][p_id]['name']}!"})

                        elif msg_text.startswith('/broadcast '):
                            msg = msg_text.replace('/broadcast ', '').strip()
                            count = 0
                            for u_name, u_details in db['users'][p_id].items():
                                em = u_details['email']
                                if em not in db['mails'][p_id]: db['mails'][p_id][em] = []
                                db['mails'][p_id][em].append({"from": "admin", "msg": msg, "read": False})
                                count += 1
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Broadcast sent to {count} users!"})

                        elif msg_text.startswith('/discountall '):
                            parts = msg_text.split(' ', 4)
                            t_val, t_unit, perc = int(parts[1]), parts[2].lower(), int(parts[3])
                            reason = parts[4] if len(parts) > 4 else "Special Offer"
                            multiplier = 1
                            if 'day' in t_unit or t_unit == 'd': multiplier = 86400
                            elif 'hour' in t_unit or t_unit == 'h': multiplier = 3600
                            elif 'min' in t_unit or t_unit == 'm': multiplier = 60
                            
                            db['discounts']['all'][p_id] = {"percent": perc, "exp": time.time() + (t_val * multiplier)}
                            for u_name, u_details in db['users'][p_id].items():
                                em = u_details['email']
                                bmsg = f"Hey dear {u_name}, {reason}! Enjoy the {perc}% discount valid for {t_val} {t_unit}!"
                                if em not in db['mails'][p_id]: db['mails'][p_id][em] = []
                                db['mails'][p_id][em].append({"from": "admin", "msg": bmsg, "read": False})
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ {perc}% Global Discount applied!"})

                        elif msg_text.startswith('/discount '):
                            parts = msg_text.split(' ')
                            em, t_val, t_unit, perc = parts[1], int(parts[2]), parts[3].lower(), int(parts[4])
                            multiplier = 1
                            if 'day' in t_unit or t_unit == 'd': multiplier = 86400
                            elif 'hour' in t_unit or t_unit == 'h': multiplier = 3600
                            elif 'min' in t_unit or t_unit == 'm': multiplier = 60
                            
                            db['discounts']['users'][p_id][em] = {"percent": perc, "exp": time.time() + (t_val * multiplier)}
                            if em not in db['mails'][p_id]: db['mails'][p_id][em] = []
                            db['mails'][p_id][em].append({"from": "admin", "msg": f"🎁 Special gift only for you! Enjoy a {perc}% discount valid for {t_val} {t_unit}.", "read": False})
                            save_db()
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ {perc}% Discount given to {em}!"})

                        elif msg_text.startswith('/api_approve '):
                            em = msg_text.replace('/api_approve ', '').strip()
                            found = False
                            for u, details in db['users'][p_id].items():
                                if details['email'] == em:
                                    details['api_key'] = 'API_' + em.split('@')[0].upper()[:10] + str(time.time()).replace('.','')[-5:]
                                    details['api_req_pending'] = False
                                    found = True
                                    if em not in db['mails'][p_id]: db['mails'][p_id][em] = []
                                    db['mails'][p_id][em].append({"from": "admin", "msg": "✅ Your API Key Request has been APPROVED! Check Settings.", "read": False})
                                    break
                            if found:
                                save_db()
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ API Approved for {em}"})
                            
                        elif msg_text.startswith('/api_reject '):
                            em = msg_text.replace('/api_reject ', '').strip()
                            found = False
                            for u, details in db['users'][p_id].items():
                                if details['email'] == em:
                                    details['api_req_pending'] = False
                                    found = True
                                    if em not in db['mails'][p_id]: db['mails'][p_id][em] = []
                                    db['mails'][p_id][em].append({"from": "admin", "msg": "❌ Your API Key Request has been REJECTED.", "read": False})
                                    break
                            if found:
                                save_db()
                                requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"❌ API Rejected for {em}"})

                except Exception as loop_e:
                    pass

                try:
                    if 'callback_query' in update:
                        data = update['callback_query']['data']
                        msg = update['callback_query']['message']
                        chat_id = msg['chat']['id']
                        msg_id = msg['message_id']
                        text_content = msg.get('text', '')
                        
                        if data.startswith("replymail_"):
                            target_email = data.replace("replymail_", "")
                            info_text = f"💬 To reply to {target_email}, copy and send:\n\n`/reply {target_email} Your reply message here`"
                            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": info_text, "parse_mode": "Markdown"})
                            continue
                            
                        if data.startswith("apiapp_"):
                            target_email = data.replace("apiapp_", "")
                            for u, details in db['users'][p_id].items():
                                if details['email'] == target_email:
                                    details['api_key'] = 'API_' + target_email.split('@')[0].upper()[:10] + str(time.time()).replace('.','')[-5:]
                                    details['api_req_pending'] = False
                                    if target_email not in db['mails'][p_id]: db['mails'][p_id][target_email] = []
                                    db['mails'][p_id][target_email].append({"from": "admin", "msg": "✅ Your API Key Request has been APPROVED! Check Settings.", "read": False})
                                    save_db()
                                    requests.post(f"https://api.telegram.org/bot{bot_token}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": f"✅ API Approved for {target_email}"})
                                    break
                            continue
                            
                        if data.startswith("apirej_"):
                            target_email = data.replace("apirej_", "")
                            for u, details in db['users'][p_id].items():
                                if details['email'] == target_email:
                                    details['api_req_pending'] = False
                                    if target_email not in db['mails'][p_id]: db['mails'][p_id][target_email] = []
                                    db['mails'][p_id][target_email].append({"from": "admin", "msg": "❌ Your API Key Request has been REJECTED.", "read": False})
                                    save_db()
                                    requests.post(f"https://api.telegram.org/bot{bot_token}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": f"❌ API Rejected for {target_email}"})
                                    break
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
                except Exception as e_cb:
                    pass
        except Exception: 
            time.sleep(2)
            pass
        time.sleep(1.5)

def start_polling_for_panel(p_id):
    if p_id not in active_bots:
        active_bots[p_id] = True
        threading.Thread(target=poll_telegram, args=(p_id,), daemon=True).start()

for pid in db['panels']:
    start_polling_for_panel(pid)

@app.route("/api/init-app", methods=["GET"])
def init_app():
    panels_list = [{"id": k, "name": v["name"], "color": v.get("color", "#00f3ff")} for k, v in db['panels'].items()]
    return jsonify({"panels": panels_list})

@app.route("/api/signup", methods=["POST"])
def signup():
    d = request.json
    p_id = str(d['panel'])
    user = d['username'].lower().strip()
    email = d['email'].lower().strip()
    pwd = d['pass'].strip()
    ref_by = d.get('ref', '')
    
    if p_id not in db['panels']: return jsonify({"error": "Invalid Panel"}), 400
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    if user in db['users'][p_id] or any(u['email'] == email for u in db['users'][p_id].values()): return jsonify({"error": "Username or Email already exists!"}), 400
    
    db['users'][p_id][user] = {"email": email, "password": pwd, "ref_by": ref_by, "ordered": False, "ref_signups": 0, "ref_active": 0, "first_claim": False, "avatar": ""}
    if ref_by and ref_by in db['users'][p_id]: db['users'][p_id][ref_by]['ref_signups'] += 1
    save_db()
    
    msg = f"💎 ⍟ NEW SIGNUP ({db['panels'][p_id]['name']}) ⍟ 💎\n\n👤 Name: {user}\n✉️ Email: {email}\n🔗 Ref by: {ref_by or 'None'}"
    markup = {"inline_keyboard": [[{"text": "🚫 BLOCK USER", "callback_data": f"blkusr_{email}"}]]}
    requests.post(f"https://api.telegram.org/bot{db['panels'][p_id]['bot']}/sendMessage", json={"chat_id": db['panels'][p_id]['chat'], "text": msg, "reply_markup": markup})
    return jsonify({"status": "success"})

@app.route("/api/login", methods=["POST"])
def login():
    d = request.json
    p_id = str(d['panel'])
    user = d['username'].lower().strip()
    pwd = d['pass'].strip()
    
    if p_id not in db['users'] or user not in db['users'][p_id] or db['users'][p_id][user]["password"] != pwd:
        return jsonify({"error": "Invalid Username or Password!"}), 400
    email = db['users'][p_id][user]["email"]
    avatar = db['users'][p_id][user].get("avatar", "")
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    return jsonify({"status": "success", "email": email, "username": user, "avatar": avatar})

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

@app.route("/api/update-profile", methods=["POST"])
def update_profile():
    d = request.json
    p_id = str(d['panel'])
    old_email = d['old_email']
    new_username = d['new_username'].lower().strip()
    new_email = d['new_email'].lower().strip()
    avatar = d.get('avatar', '').strip()

    if p_id not in db['panels']: return jsonify({"error": "Invalid Panel"}), 400

    user_key = None
    for u, details in db['users'][p_id].items():
        if details['email'] == old_email:
            user_key = u
            break
    
    if not user_key: return jsonify({"error": "User not found!"}), 400
    
    if new_username != user_key and new_username in db['users'][p_id]:
        return jsonify({"error": "Username already taken!"}), 400
    if new_email != old_email and any(u['email'] == new_email for u in db['users'][p_id].values()):
        return jsonify({"error": "Email already registered!"}), 400

    user_data = db['users'][p_id].pop(user_key)
    user_data['email'] = new_email
    user_data['avatar'] = avatar
    
    db['users'][p_id][new_username] = user_data

    if new_email != old_email:
        if old_email in db['balances'][p_id]:
            db['balances'][p_id][new_email] = db['balances'][p_id].pop(old_email)
        if old_email in db['blocked'][p_id]:
            db['blocked'][p_id].remove(old_email)
            db['blocked'][p_id].append(new_email)
        if old_email in db['mails'][p_id]:
            db['mails'][p_id][new_email] = db['mails'][p_id].pop(old_email)
        if old_email in db['discounts']['users'][p_id]:
            db['discounts']['users'][p_id][new_email] = db['discounts']['users'][p_id].pop(old_email)
        
        for o in db['orders']:
            if o['panel'] == p_id and o['email'] == old_email: o['email'] = new_email
        for t in db['txns']:
            if t['panel'] == p_id and t['email'] == old_email: t['email'] = new_email

    save_db()
    return jsonify({"status": "success", "username": new_username, "email": new_email, "avatar": avatar})

@app.route("/api/google-auth", methods=["POST"])
def google_auth():
    d = request.json
    p_id, email, req_username = str(d['panel']), d['email'].lower().strip(), d['username'].lower().strip()
    if p_id not in db['panels']: return jsonify({"error": "Invalid Panel"}), 400
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    
    for u, details in db['users'][p_id].items():
        if details['email'] == email:
            if u != req_username: return jsonify({"error": "Username does not match this Email!"}), 400
            return jsonify({"status": "success", "email": email, "username": u, "avatar": details.get("avatar", "")})
            
    if req_username in db['users'][p_id]: return jsonify({"error": "Username already taken."}), 400
    db['users'][p_id][req_username] = {"email": email, "password": "GoogleLogin", "ref_by": "", "ordered": False, "ref_signups": 0, "ref_active": 0, "first_claim": False, "avatar": ""}
    save_db()
    
    msg = f"💠 ⍟ SECURE GOOGLE LOGIN ({db['panels'][p_id]['name']}) ⍟ 💠\n\n👤 Name: {req_username}\n✉️ Email: {email}"
    markup = {"inline_keyboard": [[{"text": "🚫 BLOCK USER", "callback_data": f"blkusr_{email}"}]]}
    requests.post(f"https://api.telegram.org/bot{db['panels'][p_id]['bot']}/sendMessage", json={"chat_id": db['panels'][p_id]['chat'], "text": msg, "reply_markup": markup})
    return jsonify({"status": "success", "email": email, "username": req_username, "avatar": ""})

@app.route("/api/get-services", methods=["POST"])
def get_services():
    p_id = str(request.json.get("panel"))
    if p_id not in db['panels']: return jsonify([])
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }
        res = requests.post(db['panels'][p_id]["url"], data={"key": db['panels'][p_id]["key"], "action": "services"}, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            return jsonify(data if isinstance(data, list) else [])
        return jsonify([])
    except: 
        return jsonify([])

@app.route("/api/add-funds", methods=["POST"])
def add_funds():
    data = request.json
    p_id, email, amt, utr = str(data['panel']), data['email'], float(data['amount']), data['utr']
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    db['txns'].append({"status": "Pending", "email": email, "panel": p_id, "amount": amt, "utr": utr})
    save_db()
    text = f"🚨 ⍟ FUND REQUEST ⍟ 🚨\n\n👤 User: {email}\n💰 Amount: ₹{amt}\n🧾 UTR/TXN: {utr}\n🎛️ Panel: {db['panels'][p_id]['name']}"
    markup = {"inline_keyboard": [[{"text": "✅ APPROVE", "callback_data": f"app_{utr}"}, {"text": "❌ REJECT", "callback_data": f"rej_{utr}"}], [{"text": "🚫 BLOCK USER", "callback_data": f"blk_{utr}"}]]}
    requests.post(f"https://api.telegram.org/bot{db['panels'][p_id]['bot']}/sendMessage", json={"chat_id": db['panels'][p_id]['chat'], "text": text, "reply_markup": markup})
    return jsonify({"status": "success"})

@app.route("/api/req-api", methods=["POST"])
def req_api():
    d = request.json
    p_id, email = str(d['panel']), d['email']
    for u, details in db['users'][p_id].items():
        if details['email'] == email:
            details['api_req_pending'] = True
            save_db()
            text = f"🔑 ⍟ API KEY REQUEST ⍟ 🔑\n\n👤 User: {email}\n🎛️ Panel: {db['panels'][p_id]['name']}"
            markup = {"inline_keyboard": [[{"text": "✅ APPROVE", "callback_data": f"apiapp_{email}"}, {"text": "❌ REJECT", "callback_data": f"apirej_{email}"}]]}
            requests.post(f"https://api.telegram.org/bot{db['panels'][p_id]['bot']}/sendMessage", json={"chat_id": db['panels'][p_id]['chat'], "text": text, "reply_markup": markup})
            return jsonify({"status": "success"})
    return jsonify({"error": "User not found!"}), 400

@app.route("/api/reset-api", methods=["POST"])
def reset_api():
    d = request.json
    p_id, email = str(d['panel']), d['email']
    for u, details in db['users'][p_id].items():
        if details['email'] == email:
            details['api_key'] = ""
            details['api_req_pending'] = True
            save_db()
            text = f"🔄 ⍟ API RESET REQUEST ⍟ 🔄\n\n👤 User: {email}\n🎛️ Panel: {db['panels'][p_id]['name']}"
            markup = {"inline_keyboard": [[{"text": "✅ APPROVE", "callback_data": f"apiapp_{email}"}, {"text": "❌ REJECT", "callback_data": f"apirej_{email}"}]]}
            requests.post(f"https://api.telegram.org/bot{db['panels'][p_id]['bot']}/sendMessage", json={"chat_id": db['panels'][p_id]['chat'], "text": text, "reply_markup": markup})
            return jsonify({"status": "success"})
    return jsonify({"error": "User not found!"}), 400

@app.route("/api/apply-coupon", methods=["POST"])
def apply_coupon():
    d = request.json
    p_id, email, code = str(d['panel']), d['email'], d['code'].strip().upper()
    if code in db['coupons']:
        amt = db['coupons'][code]
        db['balances'][p_id][email] = db['balances'][p_id].get(email, 0.0) + amt
        del db['coupons'][code]
        save_db()
        
        user_name = next((u for u, det in db['users'][p_id].items() if det['email'] == email), "Unknown")
        msg = f"🎟️ ⍟ COUPON CLAIMED ⍟ 🎟️\n\n👤 User: {user_name}\n✉️ Email: {email}\n🔢 Code: {code}\n💰 Amount: ₹{amt}"
        requests.post(f"https://api.telegram.org/bot{db['panels'][p_id]['bot']}/sendMessage", json={"chat_id": db['panels'][p_id]['chat'], "text": msg})
        
        return jsonify({"status": "success", "amount": amt})
    return jsonify({"error": "Invalid or Expired Coupon!"}), 400

@app.route("/api/place-order", methods=["POST"])
def place_order():
    d = request.json
    p_id, email, user, s_id, s_name, link, qty, charge = str(d['panel']), d['email'], d['username'], d['service'], d['service_name'], d['link'], int(d['qty']), float(d['charge'])
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    if db['balances'][p_id].get(email, 0.0) < charge: return jsonify({"error": "Insufficient Wallet Balance!"}), 400
    
    try:
        res = requests.post(db['panels'][p_id]["url"], data={"key": db['panels'][p_id]["key"], "action": "add", "service": s_id, "link": link, "quantity": qty}, timeout=10).json()
        if "error" in res: return jsonify({"error": res['error']}), 400
        
        db['balances'][p_id][email] -= charge
        order_id = res.get("order")
        db['orders'].append({"email": email, "panel": p_id, "id": order_id, "name": s_name, "qty": qty, "charge": charge, "status": "Pending", "refunded": False, "username": user})
        
        if user in db['users'][p_id] and not db['users'][p_id][user].get('ordered', False):
            db['users'][p_id][user]['ordered'] = True
            ref_by = db['users'][p_id][user].get('ref_by')
            if ref_by and ref_by in db['users'][p_id]: db['users'][p_id][ref_by]['ref_active'] += 1
                
        save_db()
        msg = f"🚀 ⍟ ORDER RECEIVED ({db['panels'][p_id]['name']}) ⍟ 🚀\n\n👤 User: {user}\n🛒 Service: {s_name[:30]}...\n🆔 ID: {s_id}\n🔗 Link: {link}\n🔢 Qty: {qty}\n💸 Amt: ₹{charge}\n🟡 Status: Pending"
        requests.post(f"https://api.telegram.org/bot{db['panels'][p_id]['bot']}/sendMessage", json={"chat_id": db['panels'][p_id]['chat'], "text": msg})
        return jsonify({"status": "success", "order": order_id})
    except: return jsonify({"error": "API Connection Failed!"}), 500

@app.route("/api/claim-reward", methods=["POST"])
def claim_reward():
    d = request.json
    p_id, email, v_link, f_link = str(d['panel']), d['email'], d['views_link'], d['followers_link']
    user_key = next((u for u, details in db['users'][p_id].items() if details['email'] == email), None)
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
    msg = f"🎁 ⍟ REWARD CLAIMED ({db['panels'][p_id]['name']}) ⍟ 🎁\n\n👤 User: {user_key}\n✉️ Email: {email}\n👥 Type: {claim_type}\n🔗 Followers: {f_link}\n🔗 Views: {v_link}"
    requests.post(f"https://api.telegram.org/bot{db['panels'][p_id]['bot']}/sendMessage", json={"chat_id": db['panels'][p_id]['chat'], "text": msg})
    return jsonify({"status": "success"})

@app.route("/api/send-mail", methods=["POST"])
def send_mail():
    d = request.json
    p_id, email, message = str(d['panel']), d['email'], d['message']
    if email in db['blocked'][p_id]: return jsonify({"error": "Blocked"}), 403
    
    if email not in db['mails'][p_id]: db['mails'][p_id][email] = []
    db['mails'][p_id][email].append({"from": "user", "msg": message, "read": True})
    save_db()
    
    text = f"📬 ⍟ NEW SUPPORT MAIL ({db['panels'][p_id]['name']}) ⍟ 📬\n\n👤 User: {email}\n💬 Msg: {message}"
    markup = {"inline_keyboard": [[{"text": "✉️ REPLY TO USER", "callback_data": f"replymail_{email}"}]]}
    requests.post(f"https://api.telegram.org/bot{db['panels'][p_id]['bot']}/sendMessage", json={"chat_id": db['panels'][p_id]['chat'], "text": text, "reply_markup": markup})
    return jsonify({"status": "success"})

@app.route("/api/delete-mail", methods=["POST"])
def delete_mail():
    d = request.json
    p_id = str(d.get('panel'))
    email = d.get('email')
    index = d.get('index')

    if p_id in db['mails'] and email in db['mails'][p_id]:
        if index is not None and 0 <= index < len(db['mails'][p_id][email]):
            db['mails'][p_id][email].pop(index)
            save_db()
            return jsonify({"status": "success"})
            
    return jsonify({"error": "Failed"}), 400

@app.route("/api/sync", methods=["POST"])
def sync():
    email, p_id = request.json['email'], str(request.json['panel'])
    if p_id not in db['panels']: return jsonify({"error": "Invalid Panel"}), 400
    if email in db['blocked'][p_id]: return jsonify({"status": "blocked"}), 403
    
    user_orders = [o for o in db['orders'] if o['email'] == email and o['panel'] == p_id]
    user_txns = [t for t in db['txns'] if t['email'] == email and t['panel'] == p_id]
    user_info = next((details for u, details in db['users'][p_id].items() if details['email'] == email), {})
    
    user_mails = db['mails'][p_id].get(email, [])
    unread_admin_mails = [m['msg'] for m in user_mails if m['from'] == 'admin' and not m.get('read', False)]
    for m in user_mails:
        if m['from'] == 'admin': m['read'] = True
    if unread_admin_mails: save_db()

    active_discount = 0
    t_now = time.time()
    if db['discounts']['all'][p_id]['exp'] > t_now: active_discount = db['discounts']['all'][p_id]['percent']
    if email in db['discounts']['users'][p_id]:
        if db['discounts']['users'][p_id][email]['exp'] > t_now and db['discounts']['users'][p_id][email]['percent'] > active_discount:
            active_discount = db['discounts']['users'][p_id][email]['percent']
            
    return jsonify({
        "balance": db['balances'][p_id].get(email, 0.0), "txns": user_txns, "orders": user_orders, 
        "user_info": user_info, "unread_mails": unread_admin_mails, "all_mails": user_mails,
        "config": db['config'], "discount": active_discount
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
