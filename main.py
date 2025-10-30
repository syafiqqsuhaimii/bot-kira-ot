import telebot
from flask import Flask, request
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# Simpan data sementara untuk setiap user
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

    return round(total, 2)


# Start bot
@bot.message_handler(commands=["start"])
def start(message):
    user_sessions[message.chat.id] = {"weekday": 0, "weekend": 0, "ph": 0, "rate": None}
    bot.send_message(
        message.chat.id,
        "👋 Hai! Saya bot kira OT DBSB Kuantan.\n\n"
        "Sila masukkan kadar OT per jam (contoh: 10.5)\n\n"
        "Format: `rate 10.5`",
        parse_mode="Markdown",
    )


# Set rate
@bot.message_handler(func=lambda m: m.text.lower().startswith("rate"))
def set_rate(message):
    try:
        rate = float(message.text.split()[1])
        user_sessions[message.chat.id]["rate"] = rate
        bot.send_message(
            message.chat.id,
            f"✅ Rate OT disetkan kepada RM {rate:.2f}/jam.\n\n"
            "Sekarang masukkan kiraan OT:\n"
            "- `weekday 5`\n- `weekend 6`\n- `ph 9`",
            parse_mode="Markdown",
        )
    except:
        bot.send_message(message.chat.id, "❌ Format salah. Contoh: `rate 12.5`", parse_mode="Markdown")


# Kira OT ikut hari
@bot.message_handler(func=lambda m: any(x in m.text.lower() for x in ["weekday", "weekend", "ph"]))
def kira(message):
    chat_id = message.chat.id
    teks = message.text.lower().split()

    if len(teks) < 2:
        bot.send_message(chat_id, "❌ Sila taip format betul. Contoh: `weekday 5`")
        return

    jenis = teks[0]
    jam = teks[1]
    rate = user_sessions[chat_id].get("rate")

    if rate is None:
        bot.send_message(chat_id, "⚠️ Sila set dulu kadar rate guna arahan: `rate 10.5`")
        return

    if jenis == "ph":
        jenis_full = "public holiday"
    else:
        jenis_full = jenis

    jumlah = kira_ot(rate, jam, jenis_full)
    user_sessions[chat_id][jenis] += jumlah

    bot.send_message(chat_id, f"💰 Jumlah OT {jenis_full} ({jam} jam): RM {jumlah:.2f}")


# Kira total semua
@bot.message_handler(commands=["total"])
def total(message):
    data = user_sessions.get(message.chat.id)
    if not data or not data["rate"]:
        bot.send_message(message.chat.id, "⚠️ Sila set rate dulu: `rate 10.5`")
        return

    total_all = data["weekday"] + data["weekend"] + data["ph"]
    msg = (
        f"📊 *Ringkasan OT Anda:*\n\n"
        f"🏢 Weekday: RM {data['weekday']:.2f}\n"
        f"📅 Weekend: RM {data['weekend']:.2f}\n"
        f"🎉 Public Holiday: RM {data['ph']:.2f}\n\n"
        f"💵 *Total Keseluruhan:* RM {total_all:.2f}"
    )
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")


# Flask mini server (untuk Koyeb)
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
    import threading

    def run_flask():
        app.run(host="0.0.0.0", port=8000)

    threading.Thread(target=run_flask).start()
    print("✅ Bot OT is running on Koyeb!")
