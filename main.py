import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

user_sessions = {}

# ====== Fungsi Kiraan OT ======
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


# ====== Fungsi Menu Pilihan ======
def menu_ot():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("🏢 Weekday", callback_data="weekday"),
        InlineKeyboardButton("📅 Weekend", callback_data="weekend"),
        InlineKeyboardButton("🎉 Public Holiday", callback_data="ph"),
        InlineKeyboardButton("📊 Lihat Total", callback_data="total"),
        InlineKeyboardButton("🔄 Reset Semua", callback_data="reset")
    )
    return markup


# ====== START ======
@bot.message_handler(commands=["start"])
def start(message):
    user_sessions[message.chat.id] = {"rate": None, "weekday": 0, "weekend": 0, "ph": 0}
    bot.send_message(
        message.chat.id,
        "👋 Hai! Saya *Bot Kira OT DBSB Kuantan*.\n\n"
        "Untuk mula, sila masukkan kadar OT sejam anda (contoh: `10.5`).\n\n"
        "📌 *Contoh penggunaan:*\n"
        "1️⃣ Masukkan rate (contoh: 10)\n"
        "2️⃣ Tekan jenis OT (Weekday / Weekend / Public Holiday)\n"
        "3️⃣ Ikut arahan yang diberi untuk kira jumlah jam atau hari OT anda.",
        parse_mode="Markdown",
    )


# ====== Set Rate ======
@bot.message_handler(func=lambda m: m.text.replace(".", "", 1).isdigit())
def set_rate(message):
    rate = float(message.text)
    user_sessions[message.chat.id]["rate"] = rate
    bot.send_message(
        message.chat.id,
        f"✅ Kadar OT diset kepada *RM {rate:.2f}/jam*.\n\n"
        "Sekarang pilih jenis OT untuk mula kira:",
        parse_mode="Markdown",
        reply_markup=menu_ot(),
    )


# ====== Callback Button ======
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    data = call.data
    user_data = user_sessions.get(chat_id)

    if not user_data or not user_data.get("rate"):
        bot.send_message(chat_id, "⚠️ Sila masukkan kadar OT dahulu (contoh: 10.5)")
        return

    if data == "weekday":
        bot.send_message(
            chat_id,
            "🏢 *Kiraan OT Weekday*\n\n"
            "Masukkan bilangan hari mengikut kategori berikut:\n"
            "• OT1 = 3 jam/hari\n"
            "• OT2 = 4 jam/hari\n"
            "• OT3 = 5 jam/hari\n\n"
            "📌 *Contoh input:* `20,5,5`\n"
            "➡️ (Maksudnya 20 hari OT1, 5 hari OT2, 5 hari OT3)",
            parse_mode="Markdown",
        )
        bot.register_next_step_handler(call.message, proses_weekday)

    elif data == "weekend":
        bot.send_message(
            chat_id,
            "📅 *Kiraan OT Weekend*\n\n"
            "Masukkan jumlah jam OT anda (contoh: `6`)",
            parse_mode="Markdown",
        )
        bot.register_next_step_handler(call.message, proses_weekend)

    elif data == "ph":
        bot.send_message(
            chat_id,
            "🎉 *Kiraan OT Public Holiday*\n\n"
            "Masukkan jumlah jam OT pada cuti umum (contoh: `9`)",
            parse_mode="Markdown",
        )
        bot.register_next_step_handler(call.message, proses_ph)

    elif data == "total":
        tunjuk_total(chat_id)

    elif data == "reset":
        tanya_reset(chat_id)


# ====== Proses Weekday ======
def proses_weekday(message):
    chat_id = message.chat.id
    try:
        ot1, ot2, ot3 = [int(x.strip()) for x in message.text.split(",")]
    except:
        bot.send_message(chat_id, "❌ Format salah. Contoh betul: `20,5,5`")
        return

    rate = user_sessions[chat_id]["rate"]
    total_ot1 = kira_ot(rate, 3, "weekday") * ot1
    total_ot2 = kira_ot(rate, 4, "weekday") * ot2
    total_ot3 = kira_ot(rate, 5, "weekday") * ot3
    total = total_ot1 + total_ot2 + total_ot3
    user_sessions[chat_id]["weekday"] += total

    msg = (
        f"✅ *Weekday OT dikira!*\n\n"
        f"- {ot1}x OT1 (3 jam) = RM {total_ot1:.2f}\n"
        f"- {ot2}x OT2 (4 jam) = RM {total_ot2:.2f}\n"
        f"- {ot3}x OT3 (5 jam) = RM {total_ot3:.2f}\n\n"
        f"💵 *Jumlah Weekday:* RM {total:.2f}"
    )
    bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=menu_ot())


# ====== Proses Weekend ======
def proses_weekend(message):
    chat_id = message.chat.id
    try:
        jam = float(message.text)
    except:
        bot.send_message(chat_id, "❌ Masukkan angka jam sahaja (contoh: 6).")
        return

    rate = user_sessions[chat_id]["rate"]
    total = kira_ot(rate, jam, "weekend")
    user_sessions[chat_id]["weekend"] += total

    bot.send_message(
        chat_id,
        f"✅ Weekend OT ({jam} jam): RM {total:.2f}",
        parse_mode="Markdown",
        reply_markup=menu_ot(),
    )


# ====== Proses PH ======
def proses_ph(message):
    chat_id = message.chat.id
    try:
        jam = float(message.text)
    except:
        bot.send_message(chat_id, "❌ Masukkan angka jam sahaja (contoh: 9).")
        return

    rate = user_sessions[chat_id]["rate"]
    total = kira_ot(rate, jam, "public holiday")
    user_sessions[chat_id]["ph"] += total

    bot.send_message(
        chat_id,
        f"✅ Public Holiday OT ({jam} jam): RM {total:.2f}",
        parse_mode="Markdown",
        reply_markup=menu_ot(),
    )


# ====== Total ======
def tunjuk_total(chat_id):
    data = user_sessions.get(chat_id)
    if not data:
        bot.send_message(chat_id, "⚠️ Tiada data OT lagi.")
        return

    total_all = data["weekday"] + data["weekend"] + data["ph"]
    msg = (
        f"📊 *Ringkasan OT Anda:*\n\n"
        f"🏢 Weekday: RM {data['weekday']:.2f}\n"
        f"📅 Weekend: RM {data['weekend']:.2f}\n"
        f"🎉 Public Holiday: RM {data['ph']:.2f}\n\n"
        f"💵 *Total Keseluruhan:* RM {total_all:.2f}"
    )
    bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=menu_ot())


# ====== Reset Semua ======
def tanya_reset(chat_id):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Ya, Reset", callback_data="confirm_reset"),
        InlineKeyboardButton("❌ Batal", callback_data="cancel_reset")
    )
    bot.send_message(
        chat_id,
        "⚠️ Adakah anda pasti mahu *reset semua data OT*?\n\nTindakan ini tidak boleh diundur.",
        parse_mode="Markdown",
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: call.data in ["confirm_reset", "cancel_reset"])
def handle_reset_confirmation(call):
    chat_id = call.message.chat.id

    if call.data == "confirm_reset":
        user_sessions[chat_id]["weekday"] = 0
        user_sessions[chat_id]["weekend"] = 0
        user_sessions[chat_id]["ph"] = 0
        bot.send_message(chat_id, "✅ Semua data OT telah direset!", reply_markup=menu_ot())
    else:
        bot.send_message(chat_id, "❌ Reset dibatalkan.", reply_markup=menu_ot())


# ====== Flask untuk Koyeb ======
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
    print("✅ Bot OT (Wizard + Reset) is running on Koyeb!")
