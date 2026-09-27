import asyncio


class SSEConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[asyncio.Queue]] = {}

    async def connect(self, id: str) -> asyncio.Queue:
        queue = asyncio.Queue()
        self.active_connections.setdefault(id, []).append(queue)
        return queue

    def disconnect(self, id: str, queue: asyncio.Queue):
        connections = self.active_connections.get(id)
        if connections and queue in connections:
            connections.remove(queue)
            if not connections:
                del self.active_connections[id]

    async def broadcast_to_admins(self, admins_list: list[str], data: dict):
        for admin_id in admins_list:
            queues = self.active_connections.get(admin_id, [])
            for queue in queues:
                await queue.put(data)

    async def broadcast_to_client(self, client_id: str, data: dict):
        queues = self.active_connections.get(client_id, [])
        for queue in queues:
            await queue.put(data)


notification_manager = SSEConnectionManager()
