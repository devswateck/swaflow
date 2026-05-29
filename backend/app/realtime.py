import asyncio
from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import decode_token
from app.users.models import User


class RealtimeManager:
    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def register(self, company_id: UUID, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections[company_id].add(websocket)

    async def unregister(self, company_id: UUID, websocket: WebSocket) -> None:
        async with self._lock:
            sockets = self._connections.get(company_id)
            if not sockets:
                return
            sockets.discard(websocket)
            if not sockets:
                self._connections.pop(company_id, None)

    async def _broadcast(self, company_id: UUID, payload: dict) -> None:
        async with self._lock:
            sockets = list(self._connections.get(company_id, set()))

        stale: list[WebSocket] = []
        for socket in sockets:
            try:
                await socket.send_json(payload)
            except RuntimeError:
                stale.append(socket)

        if stale:
            async with self._lock:
                current = self._connections.get(company_id)
                if current:
                    for socket in stale:
                        current.discard(socket)

    def publish(self, company_id: UUID, event_type: str, payload: dict) -> None:
        if self._loop is None:
            return
        message = {"type": event_type, "payload": payload}
        asyncio.run_coroutine_threadsafe(self._broadcast(company_id, message), self._loop)


realtime_manager = RealtimeManager()
router = APIRouter(tags=["realtime"])


def _authenticate_socket(token: str | None) -> User | None:
    if not token:
        return None
    try:
        payload = decode_token(token)
        user_id = UUID(payload["sub"])
        company_id = UUID(payload["company_id"])
    except (KeyError, TypeError, ValueError):
        return None

    with SessionLocal() as db:
        return db.scalar(
            select(User).where(
                User.id == user_id,
                User.company_id == company_id,
                User.status == "active",
            )
        )


@router.websocket("/realtime/ws")
async def realtime_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    company_id: UUID | None = None
    try:
        auth_message = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        user = _authenticate_socket(auth_message.get("token"))
        if user is None:
            await websocket.close(code=1008)
            return

        company_id = user.company_id
        await realtime_manager.register(company_id, websocket)
        await websocket.send_json({"type": "ready"})

        while True:
            message = await websocket.receive_json()
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except (asyncio.TimeoutError, WebSocketDisconnect):
        return
    finally:
        if company_id is not None:
            await realtime_manager.unregister(company_id, websocket)
