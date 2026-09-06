import asyncio


class SSEConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[asyncio.Queue]] = {}

    async def connect(self, admin_id: str) -> asyncio.Queue:
        queue = asyncio.Queue()

        if admin_id not in self.active_connections:
            self.active_connections[admin_id] = []
        self.active_connections[admin_id].append(queue)
        return queue

    def disconnect(self, admin_id: str, queue: asyncio.Queue):
        if admin_id in self.active_connections:
            self.active_connections[admin_id].remove(queue)
            if not self.active_connections[admin_id]:
                del self.active_connections[admin_id]

    async def broadcast_to_admins(self, admins_list: list[str], data: dict):
        for admin_id in admins_list:
            if admin_id in self.active_connections:
                for queue in self.active_connections[admin_id]:
                    await queue.put(data)


notification_manager = SSEConnectionManager()
