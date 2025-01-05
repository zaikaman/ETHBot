import imaplib
import email
from email.header import decode_header
import telebot
import asyncio
import asyncpg
from datetime import datetime
import json
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Telegram bot token and chat ID
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Gmail Setup
IMAP_SERVER = "imap.gmail.com"
IMAP_USER = os.getenv('GMAIL_USER')
IMAP_PASS = os.getenv('GMAIL_APP_PASSWORD')

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL')

# Email checking interval (in seconds)
CHECK_INTERVAL = 1

# Initialize Telegram bot
bot = telebot.TeleBot(TOKEN)

# Database connection pool
db_pool = None

async def init_db():
    global db_pool
    print("\n=== Initializing Database ===")
    try:
        # Create connection pool
        db_pool = await asyncpg.create_pool(DATABASE_URL)
        print("Database connection pool created successfully")
        
        # Create tables if they don't exist
        async with db_pool.acquire() as connection:
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id SERIAL PRIMARY KEY,
                    type VARCHAR(10) NOT NULL,
                    entry_price DECIMAL NOT NULL,
                    take_profit DECIMAL[] NOT NULL,
                    stop_loss DECIMAL NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
                    risk_percent DECIMAL,
                    current_price DECIMAL
                )
            ''')
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

async def store_signal(signal_data):
    try:
        async with db_pool.acquire() as connection:
            # Convert take_profit list to PostgreSQL array
            take_profit_array = signal_data['take_profit']
            if not isinstance(take_profit_array, list):
                take_profit_array = [take_profit_array]
            
            result = await connection.fetchrow('''
                INSERT INTO signals (type, entry_price, take_profit, stop_loss, timestamp, risk_percent, current_price)
                VALUES ($1, $2, $3::decimal[], $4, $5, $6, $7)
                RETURNING id
            ''', 
            signal_data['type'],
            signal_data['entry_price'],
            take_profit_array,
            signal_data['stop_loss'],
            signal_data['timestamp'],
            signal_data['risk_percent'],
            signal_data['current_price']
            )
            
            print(f"Insert successful, got ID: {result['id']}")
            
    except Exception as e:
        print(f"Database error in store_signal: {e}")
        raise

# Async function to check email
async def check_email():
    mail = await asyncio.to_thread(imaplib.IMAP4_SSL, IMAP_SERVER)
    await asyncio.to_thread(mail.login, IMAP_USER, IMAP_PASS)
    await asyncio.to_thread(mail.select, "inbox")
    status, messages = await asyncio.to_thread(mail.search, None, 'UNSEEN')
    email_ids = messages[0].split()

    if not email_ids:
        return

    print(f"Found {len(email_ids)} new emails")  # Debug log
    for email_id in email_ids:
        print(f"Processing email ID: {email_id}")  # Debug log
        res, msg = await asyncio.to_thread(mail.fetch, email_id, "(RFC822)")
        for response_part in msg:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])

                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding)
                
                print(f"Processing email with subject: {subject}")  # Debug log

                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            print("Found text/plain part in multipart message")  # Debug log
                            await process_email(subject, body)
                else:
                    body = msg.get_payload(decode=True).decode()
                    print("Processing single part message")  # Debug log
                    await process_email(subject, body)

async def process_email(subject, body):
    try:
        print("\n=== Starting Email Processing ===")  # Debug log
        print(f"Email Body:\n{body}")  # Debug log

        # Check if the email contains the word "closed"
        if "closed" in body.lower():
            print("Found 'closed' in email")  # Debug log
            if body.strip():
                bot.send_message(CHAT_ID, body)
                print("Sent closed message to Telegram")  # Debug log
                
                # Extract exit price from the message
                exit_price = None
                for line in body.strip().split("\n"):
                    if "CLOSE PRICE:" in line:
                        try:
                            exit_price = float(line.split(":", 1)[1].strip())
                            break
                        except (ValueError, IndexError):
                            print("Failed to parse exit price")
                
                async with db_pool.acquire() as connection:
                    await connection.execute('''
                        UPDATE signals 
                        SET status = 'STOPPED',
                            exit_price = $1
                        WHERE status = 'ACTIVE'
                    ''', exit_price)
                    print(f"Updated active signals to STOPPED with exit price: {exit_price}")  # Debug log
            else:
                print("Email body is empty, skipping...")
            return

        # Check if the email contains the word "reversal"
        if "reversal" in body.lower():
            print("Found 'reversal' in email")  # Debug log
            if body.strip():
                bot.send_message(CHAT_ID, body)
                print("Sent reversal message to Telegram")  # Debug log
                
                # Extract exit price from the message
                exit_price = None
                for line in body.strip().split("\n"):
                    if "CLOSE PRICE:" in line:
                        try:
                            exit_price = float(line.split(":", 1)[1].strip())
                            break
                        except (ValueError, IndexError):
                            print("Failed to parse exit price")
                
                async with db_pool.acquire() as connection:
                    await connection.execute('''
                        UPDATE signals 
                        SET status = 'STOPPED',
                            exit_price = $1
                        WHERE status = 'ACTIVE'
                    ''', exit_price)
                    print(f"Updated active signals to STOPPED with exit price: {exit_price}")  # Debug log
            else:
                print("Email body is empty, skipping...")
            return

        # Process the email if it contains "#ETHUSD"
        if "#ETHUSD" in body:
            print("\n=== Processing #ETHUSD Signal ===")  # Debug log
            lines = body.strip().split("\n")
            print(f"Signal lines: {lines}")  # Debug log
            
            try:
                # Parse each line with exact case matching
                pair = None
                trade_type = None
                entry_str = None
                stop_loss = None
                take_profit = None
                current_price = None
                risk_percent = None

                for line in lines:
                    if line.startswith("PAIR:"):
                        pair = line.split(":", 1)[1].strip()
                    elif line.startswith("TYPE:"):
                        trade_type = line.split(":", 1)[1].strip().lower()
                    elif line.startswith("ENTRY:"):
                        entry_str = line.split(":", 1)[1].strip().lower()
                    elif line.startswith("STOPLOSS:"):
                        stop_loss = float(line.split(":", 1)[1].strip())
                    elif line.startswith("TAKEPROFIT:"):
                        take_profit = float(line.split(":", 1)[1].strip())
                    elif line.startswith("CURRENT PRICE:"):
                        current_price = float(line.split(":", 1)[1].strip())
                    elif line.startswith("RISK:"):
                        risk_str = line.split(":", 1)[1].strip()
                        risk_percent = float(risk_str.replace("%", ""))

                if all([pair, trade_type, entry_str, stop_loss, take_profit, current_price, risk_percent]):
                    print("\n=== Parsed Signal Data ===")
                    print(f"Pair: {pair}")
                    print(f"Type: {trade_type}")
                    print(f"Entry: {entry_str}")
                    print(f"Stop Loss: {stop_loss}")
                    print(f"Take Profit: {take_profit}")
                    print(f"Current Price: {current_price}")
                    print(f"Risk: {risk_percent}%")

                    signal_data = {
                        'type': 'LONG' if trade_type == 'buy' else 'SHORT',
                        'entry_price': float(current_price if entry_str == 'now' else entry_str),
                        'take_profit': [take_profit],
                        'stop_loss': stop_loss,
                        'timestamp': datetime.utcnow(),
                        'risk_percent': risk_percent,
                        'current_price': current_price
                    }

                    print("\n=== Signal Data for Database ===")
                    print(json.dumps(signal_data, default=str, indent=2))

                    await store_signal(signal_data)
                    print("Signal stored successfully")

                    # Send to Telegram once
                    if body.strip():
                        bot.send_message(CHAT_ID, body)
                        print("Signal sent to Telegram")
                    else:
                        print("Email body is empty, skipping Telegram...")
                else:
                    print("Missing required fields in signal data")
                    print(f"Pair: {pair}")
                    print(f"Type: {trade_type}")
                    print(f"Entry: {entry_str}")
                    print(f"Stop Loss: {stop_loss}")
                    print(f"Take Profit: {take_profit}")
                    print(f"Current Price: {current_price}")
                    print(f"Risk: {risk_percent}")

            except IndexError as e:
                print(f"Error parsing signal data: {e}")
                print(f"Available lines: {len(lines)}")
            except ValueError as e:
                print(f"Error converting values: {e}")
            except Exception as e:
                print(f"Unexpected error processing signal: {e}")
                import traceback
                print(traceback.format_exc())

        else:
            print("Email does not contain #ETHUSD, skipping...")

    except Exception as e:
        print(f"Error processing message: {e}")
        import traceback
        print(traceback.format_exc())

    print("=== Email Processing Complete ===\n")  # Debug log

# Main email checking loop
async def main():
    # Initialize database
    await init_db()
    
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
