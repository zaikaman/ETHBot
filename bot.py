import imaplib
import email
from email.header import decode_header
import telebot
import asyncio

# Telegram bot token and chat ID
TOKEN = '7594762357:AAGCP0Lx-qjZIspsOH4eaC8bcVqwZIivWDo'
CHAT_ID = '-1002277376839'  # Replace with your Telegram chat ID

# Gmail Setup
IMAP_SERVER = "imap.gmail.com"
IMAP_USER = "thinhgpt1706@gmail.com"  # Replace with your Gmail account
IMAP_PASS = "xgxn kjcv haqf sjxz"   # Replace with your Gmail app-specific password

# Email checking interval (in seconds)
CHECK_INTERVAL = 1

# Initialize Telegram bot
bot = telebot.TeleBot(TOKEN)

# Async function to check email
async def check_email():
    mail = await asyncio.to_thread(imaplib.IMAP4_SSL, IMAP_SERVER)
    await asyncio.to_thread(mail.login, IMAP_USER, IMAP_PASS)
    await asyncio.to_thread(mail.select, "inbox")
    status, messages = await asyncio.to_thread(mail.search, None, 'UNSEEN')
    email_ids = messages[0].split()

    if not email_ids:
        return

    for email_id in email_ids:
        res, msg = await asyncio.to_thread(mail.fetch, email_id, "(RFC822)")
        for response_part in msg:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])

                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding)

                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            await process_email(subject, body)
                else:
                    body = msg.get_payload(decode=True).decode()
                    await process_email(subject, body)

async def process_email(subject, body):
    try:
        # Check if the email contains the word "hit"
        if "hit" in body.lower():
            # Send the whole body to the Telegram channel if "hit" is found
            if body.strip():  # Ensure the body is not empty before sending
                bot.send_message(CHAT_ID, body)
            else:
                print("Email body is empty, skipping...")
            return  # Skip further processing if "hit" is found

        # Check if the email contains the word "reversal"
        if "reversal" in body.lower():
            # Send the entire body to the Telegram channel
            if body.strip():  # Ensure the body is not empty before sending
                bot.send_message(CHAT_ID, body)
            else:
                print("Email body is empty, skipping...")
            return  # Skip further processing if "reversal" is found

        # Process the email if it contains "#ETHUSD"
        if "#ETHUSD" in body:
            # Send the entire body to the Telegram channel
            if body.strip():  # Ensure the body is not empty before sending
                bot.send_message(CHAT_ID, body)
            else:
                print("Email body is empty, skipping...")

        else:
            print("Email does not contain #ETHUSD, skipping...")

    except Exception as e:
        print(f"Error processing message: {e}")

# Main email checking loop
async def main():
    while True:
        try:
            await check_email()
            print("Checked emails, waiting for next interval...")
        except Exception as e:
            print(f"Error checking emails: {e}")
        
        await asyncio.sleep(CHECK_INTERVAL)

# Start the Telegram bot polling in a separate thread
if __name__ == "__main__":
    import threading
    telegram_thread = threading.Thread(target=bot.polling, args=(), daemon=True)
    telegram_thread.start()

    # Run the async email checker loop
    asyncio.run(main()) 
