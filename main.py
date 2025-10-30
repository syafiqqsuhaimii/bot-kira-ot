import telebot
from telebot import types
from flask import Flask, request
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# Simpan session sementara setiap user
user_sessions = {}

# OT preset weekday
PRESET_WEEKDAY = {"OT1": 3, "OT2": 4, "OT3": 5}

# Fungsi kira OT
def kira_ot(rate, jam, jenis):
    rate = float(rate)
    jam = float(jam)
    if jenis == "weekday":
        return round(rate * 1.5 * jam, 2)
    elif jenis == "weekend":
        if jam <= 4:
            return round(rate * 0.5 * jam, 2)
        elif jam <= 8:
            return round(rate * jam, 2)
        else:
            return round((rate * 8) + (rate * 2 * (jam - 8)), 2)
    elif jenis == "public holiday":
        if jam <= 8:
            return round(rate * 2 * jam, 2)
        else:
            return round((rate * 2 * 8) + (rate * 3 * (jam - 8)), 2)
    else:
        return 0

# Start bot
@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id
    user_sessions[chat_id] = {"weekday":0,"weekend":0,"ph":0,"rate":None,"waiting_for":None}

    # Inline button 2 baris
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("🏢 Weekday","📅 Weekend","🎉 Public Holiday","💵 Total")

    bot.send_message(chat_id,
        "👋 Hai! Saya bot kira OT DBSB Kuantan.\n\nMasukkan kadar OT per jam (contoh: 10.5):",
        reply_markup=markup
    )

# Set rate
@bot.message_handler(func=lambda m: m.text.replace(".","",1).isdigit() and (user_sessions.get(m.chat.id, {}).get("waiting_for") is None))
def set_rate(message):
    chat_id = message.chat.id
    rate = float(message.text)
    user_sessions[chat_id]["rate"] = rate
    bot.send_message(chat_id, f"✅ Rate OT disetkan kepada RM {rate:.2f}/jam.\nSila pilih jenis OT:",
                     reply_markup=types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
                     .add("🏢 Weekday","📅 Weekend","🎉 Public Holiday","💵 Total"))

# Button pilih OT
@bot.message_handler(func=lambda m: m.text in ["🏢 Weekday","📅 Weekend","🎉 Public Holiday","💵 Total"])
def pilih_ot(message):
    chat_id = message.chat.id
    rate = user_sessions[chat_id].get("rate")
    if rate is None:
        bot.send_message(chat_id,"⚠️ Sila set rate dulu. Contoh: 10.5")
        return

    text = message.text
    if text == "🏢 Weekday":
        user_sessions[chat_id]["waiting_for"] = "weekday"
        bot.send_message(chat_id, "Masukkan bilangan hari untuk setiap preset OT (OT1=3h, OT2=4h, OT3=5h)\nContoh: 2 1 0\nFormat: OT1 OT2 OT3")
    elif text == "📅 Weekend":
        user_sessions[chat_id]["waiting_for"] = "weekend"
        bot.send_message(chat_id, "Masukkan jumlah hari kerja weekend (contoh: 2 hari)")
    elif text == "🎉 Public Holiday":
        user_sessions[chat_id]["waiting_for"] = "ph"
        bot.send_message(chat_id, "Masukkan jumlah jam OT untuk Public Holiday")
    elif text == "💵 Total":
        kiratotal(chat_id)

# Terima input OT
@bot.message_handler(func=lambda m: True)
def terima_ot(message):
    chat_id = message.chat.id
    data = user_sessions.get(chat_id)
    if not data or not data.get("waiting_for"):
        return

    jenis = data["waiting_for"]
    rate = data["rate"]

    try:
        if jenis == "weekday":
            vals = list(map(int,message.text.strip().split()))
            if len(vals) != 3:
                bot.send_message(chat_id,"❌ Format salah. Contoh: 2 1 0")
                return
            total = 0
            msg = "💰 Jumlah OT Weekday:\n"
            for i,ot_key in enumerate(["OT1","OT2","OT3"]):
                jam = PRESET_WEEKDAY[ot_key]
                hari = vals[i]
                subtotal = kira_ot(rate,jam,"weekday")*hari
                msg += f"{ot_key} ({jam} jam x {hari} hari): RM {subtotal:.2f}\n"
                total += subtotal
            data["weekday"] += total
            bot.send_message(chat_id, msg+f"\n✅ Total Weekday OT: RM {total:.2f}")

        elif jenis == "weekend":
            hari = int(message.text.strip())
            subtotal = kira_ot(rate,8,"weekend")*hari
            data["weekend"] += subtotal
            bot.send_message(chat_id,f"💰 Jumlah OT Weekend:\n{hari} hari x 8 jam/hari\n✅ Total Weekend OT: RM {subtotal:.2f}")

        elif jenis == "ph":
            jam = float(message.text.strip())
            subtotal = kira_ot(rate,jam,"public holiday")
            data["ph"] += subtotal
            bot.send_message(chat_id,f"💰 Jumlah OT Public Holiday: RM {subtotal:.2f}")

    except:
        bot.send_message(chat_id,"❌ Format salah. Sila taip nombor sahaja.")

    data["waiting_for"] = None

def kiratotal(chat_id):
    data = user_sessions.get(chat_id)
    if not data or not data["rate"]:
        bot.send_message(chat_id,"⚠️ Sila set rate dulu")
        return
    total_all = data["weekday"]+data["weekend"]+data["ph"]
    msg = f"""📊 Ringkasan OT Anda:
🏢 Weekday: RM {data['weekday']:.2f}
📅 Weekend: RM {data['weekend']:.2f}
🎉 Public Holiday: RM {data['ph']:.2f}
💵 Total Keseluruhan: RM {total_all:.2f}"""
    bot.send_message(chat_id,msg)

# Flask server untuk Koyeb
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is running!"
@app.route('/webhook',methods=["POST"])
def webhook():
    json_str = request.stream.read().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK",200

if __name__=="__main__":
    import threading
    port = int(os.environ.get("PORT",8000))
    threading.Thread(target=lambda: app.run(host="0.0.0.0",port=port)).start()
    print("✅ Bot OT is running on Koyeb!")
