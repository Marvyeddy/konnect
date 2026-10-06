import asyncio


class SSEConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[asyncio.Queue]] = {}

    async def connect(self, user_id: str) -> asyncio.Queue:
        queue = asyncio.Queue()

        self.active_connections.setdefault(
            user_id,
            [],
        ).append(queue)

        return queue

    def disconnect(
        self,
        user_id: str,
        queue: asyncio.Queue,
    ):
        connections = self.active_connections.get(user_id)

        if connections and queue in connections:
            connections.remove(queue)

            if not connections:
                del self.active_connections[user_id]

    async def broadcast(
        self,
        user_ids: list[str],
        data: dict,
    ):
        for user_id in user_ids:
            queues = self.active_connections.get(
                user_id,
                [],
            )

            for queue in queues:
                await queue.put(data)

    async def broadcast_to_admins(
        self,
        admins_list: list[str],
        data: dict,
    ):
        await self.broadcast(
            admins_list,
            data,
        )

    async def broadcast_to_client(
        self,
        client_id: str,
        data: dict,
    ):
        await self.broadcast(
            [client_id],
            data,
        )


notification_manager = SSEConnectionManager()
