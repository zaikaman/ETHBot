from fastapi import FastAPI, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncpg
import json
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection pool
db_pool = None

@app.on_event("startup")
async def startup():
    global db_pool
    db_pool = await asyncpg.create_pool(os.getenv('DATABASE_URL'))

@app.on_event("shutdown")
async def shutdown():
    if db_pool:
        await db_pool.close()

@app.get("/api/signals")
async def get_signals():
    async with db_pool.acquire() as connection:
        signals = await connection.fetch("""
            SELECT 
                id,
                type,
                entry_price,
                take_profit,
                stop_loss,
                timestamp,
                status,
                risk_percent,
                current_price
            FROM signals
            ORDER BY timestamp DESC
            LIMIT 100
        """)
        
        return [{
            "id": str(signal['id']),
            "type": signal['type'],
            "entryPrice": float(signal['entry_price']),
            "takeProfit": [float(tp) for tp in signal['take_profit']],
            "stopLoss": float(signal['stop_loss']),
            "timestamp": signal['timestamp'].isoformat(),
            "status": signal['status'],
            "riskPercent": float(signal['risk_percent']) if signal['risk_percent'] else None,
            "currentPrice": float(signal['current_price']) if signal['current_price'] else None
        } for signal in signals]

@app.get("/api/signals/stats")
async def get_signal_stats():
    async with db_pool.acquire() as connection:
        # Get counts for different statuses
        stats = await connection.fetchrow("""
            SELECT 
                COUNT(*) FILTER (WHERE status = 'ACTIVE') as active_count,
                COUNT(*) FILTER (WHERE status = 'COMPLETED') as completed_count,
                COUNT(*) FILTER (WHERE status = 'STOPPED') as stopped_count
            FROM signals
        """)
        
        return {
            "activeCount": stats['active_count'],
            "completedCount": stats['completed_count'],
            "stoppedCount": stats['stopped_count']
        }

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except:
        manager.disconnect(websocket)

# Function to broadcast new signals to all connected clients
async def broadcast_signal(signal_data: dict):
    await manager.broadcast(json.dumps(signal_data))

@app.post("/broadcast")
async def broadcast_new_signal(signal_data: dict):
    await broadcast_signal(signal_data)
    return {"status": "ok"}

# Mount static files AFTER all other routes
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 