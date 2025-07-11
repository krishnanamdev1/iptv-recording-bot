import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Database connection function
def get_db_connection():
    conn = sqlite3.connect('data.db')
    conn.row_factory = sqlite3.Row  # Dictionary format mein results
    return conn

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f"""
Namaste {user.first_name}! 🙏
Main ek sample bot hoon jo SQLite database se data fetch karta hoon.

Aap yeh poochh sakte hain:
• /products - Saare products dikhane ke liye
• /faqs - Common FAQs ke liye
• "iPhone ka price batao" - Specific product ke liye
""")

# Products command handler
async def products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    
    response = "🛍️ Available Products:\n\n"
    for item in products:
        response += f"• {item['name']}\nPrice: ₹{item['price']}\nStock: {item['stock']} units\n\n"
    
    await update.message.reply_text(response)

# FAQs command handler
async def faqs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db_connection()
    faqs = conn.execute('SELECT * FROM faqs').fetchall()
    conn.close()
    
    response = "❓ Frequently Asked Questions:\n\n"
    for item in faqs:
        response += f"Q: {item['question']}\nA: {item['answer']}\n\n"
    
    await update.message.reply_text(response)

# Message handler for dynamic queries
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.lower()
    conn = get_db_connection()
    
    # Price check logic
    if 'price' in user_input:
        product_name = None
        if 'iphone' in user_input:
            product_name = 'iPhone 15'
        elif 'samsung' in user_input:
            product_name = 'Samsung S23'
        elif 'oneplus' in user_input:
            product_name = 'OnePlus 11'
            
        if product_name:
            product = conn.execute('SELECT * FROM products WHERE name LIKE ?', 
                                 (f'%{product_name}%',)).fetchone()
            if product:
                await update.message.reply_text(f"{product['name']} ka price hai ₹{product['price']}")
            else:
                await update.message.reply_text("Sorry, yeh product available nahi hai")
        else:
            await update.message.reply_text("Kripya product ka sahi naam likhein")
    
    # FAQ logic
    elif 'delivery' in user_input:
        faq = conn.execute("SELECT answer FROM faqs WHERE question LIKE '%Delivery%'").fetchone()
        await update.message.reply_text(f"Delivery ke bare mein: {faq['answer']}")
    
    else:
        await update.message.reply_text("Mujhe samajh nahi aaya, kripya /help dekhein")
    
    conn.close()

# Main function
def main():
    print("Starting bot...")
    app = Application.builder().token("5887522488:AAEeSPScvFp4hBOiYtCQX6iDV-XUCIHWIqM").build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("products", products))
    app.add_handler(CommandHandler("faqs", faqs))
    
    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Polling...")
    app.run_polling(poll_interval=3)

if __name__ == "__main__":
    main()
