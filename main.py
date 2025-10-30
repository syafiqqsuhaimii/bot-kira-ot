import telebot
from flask import Flask, request
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

user_sessions = {}

# Fungsi kira OT
def kira_ot(rate, jam, jenis):
    rate = float(rate)
    jam = float(jam)

    if jenis == "weekday":
        total = rate * 1.5 * jam
    elif jenis == "weekend":
        if jam <= 4:
            total = rate * 0.5 * jam
        elif jam <= 8:
            total = rate * jam
        else:
            total = (rate * 8) + (rate * 2.0 * (jam - 8))
    elif jenis == "public holiday":
        if jam <= 8:
            total = rate * 2.0 * jam
        else:
            total = (rate * 2.0 * 8) + (rate * 3.0 * (jam - 8))
    else:
        total = 0
    return round(total,2)

# Start bot
@bot.message_handler(commands=["start"])
def start(message):
    user_sessions[message.chat.id] = {"weekday": 0, "weekend": 0, "ph": 0, "rate": None}
    bot.send_message(
        message.chat.id,
        "👋 Hai! Saya bot kira OT DBSB Kuantan.\n\n"
        "Sila masukkan kadar OT per jam (contoh: 12)",
    )

# Set rate
@bot.message_handler(func=lambda m: m.text.replace('.','',1).isdigit())
def set_rate(message):
    rate = float(message.text)
    user_sessions[message.chat.id]["rate"] = rate
    bot.send_message(
        message.chat.id,
        f"✅ Rate OT disetkan kepada RM {rate:.2f}/jam.\n\n"
        "Sila pilih jenis OT:\n- Weekday\n- Weekend\n- Public Holiday"
    )

# Weekday OT (preset)
@bot.message_handler(func=lambda m: m.text.lower() == "weekday")
def weekday(message):
    chat_id = message.chat.id
    bot.send_message(
        chat_id,
        "Masukkan bilangan hari untuk OT1(3h), OT2(4h), OT3(5h)\nFormat: OT1 OT2 OT3\nContoh: 2 1 3"
    )

@bot.message_handler(func=lambda m: len(m.text.split())==3 and all(x.isdigit() for x in m.text.split()))
def weekday_ot(message):
    chat_id = message.chat.id
    data = user_sessions.get(chat_id)
    if not data or not data["rate"]:
        bot.send_message(chat_id, "⚠️ Sila set rate dulu.")
        return
    ot1, ot2, ot3 = map(int, message.text.split())
    rate = data["rate"]
    total_ot1 = kira_ot(rate, ot1*3, "weekday")
    total_ot2 = kira_ot(rate, ot2*4, "weekday")
    total_ot3 = kira_ot(rate, ot3*5, "weekday")
    total_weekday = total_ot1 + total_ot2 + total_ot3
    data["weekday"] = total_weekday
    bot.send_message(
        chat_id,
        f"💰 Jumlah OT Weekday:\nOT1: RM {total_ot1:.2f}\nOT2: RM {total_ot2:.2f}\nOT3: RM {total_ot3:.2f}\n✅ Total Weekday: RM {total_weekday:.2f}"
    )

# Weekend OT (jumlah hari)
@bot.message_handler(func=lambda m: m.text.lower() == "weekend")
def weekend(message):
    bot.send_message(message.chat.id, "Masukkan bilangan hari OT weekend (1 hari = 8 jam)")

@bot.message_handler(func=lambda m: m.text.isdigit())
def weekend_ot(message):
    chat_id = message.chat.id
    data = user_sessions.get(chat_id)
    if not data or not data["rate"]:
        return
    if message.text.isdigit() and "weekend_done" not in data:
        days = int(message.text)
        rate = data["rate"]
        total_weekend = kira_ot(rate, days*8, "weekend")
        data["weekend"] = total_weekend
        data["weekend_done"] = True
        bot.send_message(chat_id, f"💰 Jumlah OT Weekend ({days} hari): RM {total_weekend:.2f}")

# Public Holiday OT
@bot.message_handler(func=lambda m: m.text.lower() == "public holiday")
def ph(message):
    bot.send_message(message.chat.id, "Masukkan jumlah jam OT Public Holiday")

@bot.message_handler(func=lambda m: m.text.replace('.','',1).isdigit() and "weekend_done" in user_sessions.get(m.chat.id,{}))
def ph_ot(message):
    chat_id = message.chat.id
    data = user_sessions.get(chat_id)
    rate = data["rate"]
    jam = float(message.text)
    total_ph = kira_ot(rate, jam, "public holiday")
    data["ph"] = total_ph
    bot.send_message(chat_id, f"💰 Jumlah OT Public Holiday: RM {total_ph:.2f}")

# Total
@bot.message_handler(commands=["total"])
def total(message):
    data = user_sessions.get(message.chat.id)
    if not data or not data["rate"]:
        bot.send_message(message.chat.id, "⚠️ Sila set rate dulu")
        return
    total_all = data["weekday"] + data["weekend"] + data["ph"]
    bot.send_message(
        message.chat.id,
        f"📊 Ringkasan OT Anda:\n🏢 Weekday: RM {data['weekday']:.2f}\n📅 Weekend: RM {data['weekend']:.2f}\n🎉 Public Holiday: RM {data['ph']:.2f}\n💵 Total Keseluruhan: RM {total_all:.2f}"
    )

# Flask server
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/webhook', methods=["POST"])
def webhook():
    json_str = request.stream.read().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT",8000))
    print("✅ Bot OT is starting on port", port)
    app.run(host="0.0.0.0", port=port)
