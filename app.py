from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncpg
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import threading
import telebot
import imaplib
import email
from email.header import decode_header
import asyncio
import aiohttp
from typing import List, Dict

# Load environment variables
load_dotenv()

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
GMAIL_USER = os.getenv('GMAIL_USER')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
PORT = int(os.getenv('PORT', 8000))

# Initialize FastAPI app
app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Initialize Telegram bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Database pool
db_pool = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Database initialization
async def init_db():
    global db_pool
    print("\n=== Initializing Database ===")
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL)
        print("Database connection pool created successfully")
        
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

# FastAPI routes
@app.get("/", response_class=HTMLResponse)
async def get_html(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/signals")
async def get_signals():
    async with db_pool.acquire() as connection:
        signals = await connection.fetch('''
            SELECT * FROM signals 
            ORDER BY timestamp DESC 
            LIMIT 100
        ''')
        return [dict(signal) for signal in signals]

@app.get("/api/signals/stats")
async def get_signal_stats():
    async with db_pool.acquire() as connection:
        stats = await connection.fetchrow('''
            SELECT 
                COUNT(*) FILTER (WHERE status = 'ACTIVE') as active_count,
                COUNT(*) FILTER (WHERE status = 'COMPLETED') as completed_count,
                COUNT(*) FILTER (WHERE status = 'STOPPED') as stopped_count
            FROM signals
        ''')
        return dict(stats)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        manager.disconnect(websocket)

@app.post("/broadcast")
async def broadcast_signal(signal: dict):
    await manager.broadcast(signal)
    return {"status": "ok"}

# Email processing functions
async def store_signal(signal_data):
    try:
        async with db_pool.acquire() as connection:
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
            
            signal_data['id'] = result['id']
            await manager.broadcast(signal_data)
            
    except Exception as e:
        print(f"Database error in store_signal: {e}")
        raise

async def process_email(subject, body):
    try:
        if "hit" in body.lower():
            if body.strip():
                bot.send_message(TELEGRAM_CHAT_ID, body)
            return

        if "reversal" in body.lower():
            if body.strip():
                bot.send_message(TELEGRAM_CHAT_ID, body)
                async with db_pool.acquire() as connection:
                    await connection.execute('''
                        UPDATE signals 
                        SET status = 'STOPPED' 
                        WHERE status = 'ACTIVE'
                    ''')
            return

        if "#ETHUSD" in body:
            lines = body.strip().split("\n")
            
            try:
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
                    signal_data = {
                        'type': 'LONG' if trade_type == 'buy' else 'SHORT',
                        'entry_price': float(current_price if entry_str == 'now' else entry_str),
                        'take_profit': [take_profit],
                        'stop_loss': stop_loss,
                        'timestamp': datetime.utcnow(),
                        'risk_percent': risk_percent,
                        'current_price': current_price
                    }

                    await store_signal(signal_data)

                    if body.strip():
                        bot.send_message(TELEGRAM_CHAT_ID, body)

            except Exception as e:
                print(f"Error processing signal: {e}")

    except Exception as e:
        print(f"Error processing message: {e}")

async def check_email():
    mail = await asyncio.to_thread(imaplib.IMAP4_SSL, "imap.gmail.com")
    await asyncio.to_thread(mail.login, GMAIL_USER, GMAIL_APP_PASSWORD)
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

# Email checking loop
async def email_checker():
    while True:
        try:
            await check_email()
        except Exception as e:
            print(f"Error checking emails: {e}")
        await asyncio.sleep(1)

# Startup event
@app.on_event("startup")
async def startup_event():
    await init_db()
    
    # Start the Telegram bot polling in a separate thread
    telegram_thread = threading.Thread(target=bot.polling, args=(), daemon=True)
    telegram_thread.start()
    
    # Start the email checker
    asyncio.create_task(email_checker()) 