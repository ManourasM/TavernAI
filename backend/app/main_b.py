from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid

app = FastAPI()

# Allow frontend ports (waiter UI, grill UI, kitchen UI)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, set to your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory order storage
orders = []

# Connection manager for multiple stations
class ConnectionManager:
    def __init__(self):
        # Keep track of connections by station name
        self.active_connections: dict[str, list[WebSocket]] = {
            "waiter": [],
            "grill": [],
            "kitchen": []
        }

    async def connect(self, station: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[station].append(websocket)
        print(f"✅ {station} connected ({len(self.active_connections[station])} clients)")

    def disconnect(self, station: str, websocket: WebSocket):
        self.active_connections[station].remove(websocket)
        print(f"❌ {station} disconnected ({len(self.active_connections[station])} clients left)")

    async def broadcast(self, station: str, message: dict):
        """Send a message to all clients connected to one station."""
        for connection in self.active_connections.get(station, []):
            await connection.send_json(message)

    async def broadcast_all(self, message: dict):
        """Send a message to all stations."""
        for station in self.active_connections:
            await self.broadcast(station, message)


manager = ConnectionManager()

# Data models
class OrderItem(BaseModel):
    id: str
    name: str

class Order(BaseModel):
    id: str
    table: int
    items: list[OrderItem]


@app.websocket("/ws/{station}")
async def websocket_endpoint(websocket: WebSocket, station: str):
    if station not in manager.active_connections:
        await websocket.close()
        return
    await manager.connect(station, websocket)
    try:
        while True:
            await websocket.receive_text()  # We don't expect incoming messages yet
    except WebSocketDisconnect:
        manager.disconnect(station, websocket)


@app.post("/order")
async def create_order(order: dict):
    # Generate unique ID for order and each item
    order_id = str(uuid.uuid4())
    items = [
        {"id": str(uuid.uuid4()), "name": item.strip()}
        for item in order.get("items", [])
        if item.strip()
    ]
    new_order = {"id": order_id, "table": order["table"], "items": items}
    orders.append(new_order)

    # Broadcast new order to all stations
    await manager.broadcast_all({"type": "new_order", "order": new_order})

    print(f"📦 New order for table {order['table']}: {items}")
    return new_order


@app.delete("/order/{order_id}/item/{item_id}")
async def complete_item(order_id: str, item_id: str):
    for order in orders:
        if order["id"] == order_id:
            order["items"] = [i for i in order["items"] if i["id"] != item_id]

            # If no items remain, remove order
            if not order["items"]:
                orders.remove(order)
                await manager.broadcast_all({"type": "remove_order", "order_id": order_id})
                print(f"✅ Order {order_id} completed and removed")
            else:
                await manager.broadcast_all({"type": "update_order", "order": order})
                print(f"✏️ Order {order_id} updated")

            break
    return {"status": "ok"}


@app.get("/orders")
async def get_orders():
    """Return all active orders (for page reloads)."""
    return orders
