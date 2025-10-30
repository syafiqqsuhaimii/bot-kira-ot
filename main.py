import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)

TOKEN = os.getenv("BOT_TOKEN")

user_ot = {}
user_state = {}

def kira_weekday(jam, rate): return jam * rate * 1.5
def kira_weekend(jam, rate):
    if jam <= 4: return jam * rate * 0.5
    elif jam <= 8: return jam * rate
    else: return (8 * rate) + ((jam - 8) * rate * 2.0)
def kira_public(jam, rate):
    if jam <= 8: return jam * rate * 2.0
    else: return (8 * rate * 2.0) + ((jam - 8) * rate * 3.0)

def tambah_rekod(uid, jenis, jumlah):
    if uid not in user_ot:
        user_ot[uid] = {"rate": None, "weekday": 0.0, "weekend": 0.0, "public": 0.0}
    user_ot[uid][jenis] += jumlah

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_state[uid] = "ASK_RATE"
    await update.message.reply_text("👋 Hai! Sila masukkan kadar sejam (contoh: 12).")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    state = user_state.get(uid)
    if state == "ASK_RATE":
        try:
            rate = float(text)
            user_ot[uid] = {"rate": rate, "weekday": 0.0, "weekend": 0.0, "public": 0.0}
            user_state[uid] = "READY"
            await update.message.reply_text(f"Kadar sejam diset pada RM{rate:.2f}. Gunakan /weekday, /weekend, /public atau /total.")
        except ValueError:
            await update.message.reply_text("Masukkan nombor yang sah, contoh: 12")
        return
    elif state in ["ASK_HOURS_weekday", "ASK_HOURS_weekend", "ASK_HOURS_public"]:
        try:
            jam = float(text)
            rate = user_ot[uid]["rate"]
            if state == "ASK_HOURS_weekday":
                jumlah = kira_weekday(jam, rate); tambah_rekod(uid, "weekday", jumlah)
                await update.message.reply_text(f"Weekday OT {jam} jam = RM {jumlah:.2f}")
            elif state == "ASK_HOURS_weekend":
                jumlah = kira_weekend(jam, rate); tambah_rekod(uid, "weekend", jumlah)
                await update.message.reply_text(f"Weekend OT {jam} jam = RM {jumlah:.2f}")
            else:
                jumlah = kira_public(jam, rate); tambah_rekod(uid, "public", jumlah)
                await update.message.reply_text(f"Public Holiday OT {jam} jam = RM {jumlah:.2f}")
            user_state[uid] = "READY"
        except ValueError:
            await update.message.reply_text("Masukkan nombor jam yang sah.")
        return
    await update.message.reply_text("Taip /weekday, /weekend, /public, atau /total.")

async def cmd_weekday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not user_ot.get(uid) or user_ot[uid]["rate"] is None:
        user_state[uid] = "ASK_RATE"
        await update.message.reply_text("Masukkan kadar sejam dahulu.")
    else:
        user_state[uid] = "ASK_HOURS_weekday"
        await update.message.reply_text("Berapa jam OT weekday?")

async def cmd_weekend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not user_ot.get(uid) or user_ot[uid]["rate"] is None:
        user_state[uid] = "ASK_RATE"
        await update.message.reply_text("Masukkan kadar sejam dahulu.")
    else:
        user_state[uid] = "ASK_HOURS_weekend"
        await update.message.reply_text("Berapa jam OT weekend?")

async def cmd_public(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not user_ot.get(uid) or user_ot[uid]["rate"] is None:
        user_state[uid] = "ASK_RATE"
        await update.message.reply_text("Masukkan kadar sejam dahulu.")
    else:
        user_state[uid] = "ASK_HOURS_public"
        await update.message.reply_text("Berapa jam OT public holiday?")

async def cmd_total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    data = user_ot.get(uid)
    if not data:
        await update.message.reply_text("Tiada rekod. /start untuk mula.")
        return
    total = data['weekday'] + data['weekend'] + data['public']
    msg = (f"💰 Jumlah OT anda:\n"           f"- Weekday: RM {data['weekday']:.2f}\n"           f"- Weekend: RM {data['weekend']:.2f}\n"           f"- Public: RM {data['public']:.2f}\n"           f"----------------------\nTotal: RM {total:.2f}")
    await update.message.reply_text(msg)

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("weekday", cmd_weekday))
    app.add_handler(CommandHandler("weekend", cmd_weekend))
    app.add_handler(CommandHandler("public", cmd_public))
    app.add_handler(CommandHandler("total", cmd_total))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
