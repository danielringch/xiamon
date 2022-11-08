from datetime import datetime, timedelta
from ...core import Siablockdata, ApiRequestFailedException, Plugin

class Siablocks:

    def __init__(self, plugin, api, database):
        self.__plugin = plugin
        self.__api = api
        self.__db = database

    async def update(self, consensus):
        await self.__get_newest_blocks(consensus.height)

    async def at_time(self, timestamp, consensus):
        current_height = consensus.height
        now = datetime.now()
        if timestamp > now:
            return current_height + int(timestamp - now).total_seconds() / 600
        else:
            await self.__get_newest_blocks(current_height)
            height = self.__db.get_height(timestamp)
            if height is not None:
                return height
            while True:
                oldest_height, oldest_cache_time = self.__db.get_oldest_height()
                if oldest_cache_time < timestamp:
                    break
                end = oldest_height - 1
                begin = end - 35
                self.__plugin.msg.debug(f'Blocks cache miss ({oldest_cache_time} vs. {timestamp}), loading heights {begin} - {end}.')
                if begin < 0:
                    raise Exception('Blocks with height < 0 are not possible.')
                await self.__get_blocks_from_consensus(begin, end)
            height = self.__db.get_height(timestamp)
            if height is None:
                raise Exception('Blocks cache miss after cache update.')
            return height

    async def at_height(self, height, consensus):
        current_height = consensus.height
        await self.__get_newest_blocks(current_height)
        if height > current_height:
            timestamp = self.__db.get_timestamp(current_height)
            if timestamp is None:
                raise Exception('Blocks cache miss after cache update.')
            return timestamp + timedelta(minutes=(10 * (height - current_height)))
        else:
            timestamp = self.__db.get_timestamp(height)
            if timestamp is not None:
                return timestamp
            oldest_height = self.__db.get_oldest_height()[0]
            for i in reversed(range(height, oldest_height, 36)):
                end = i + 35
                self.__plugin.msg.debug(f'Blocks cache miss ({oldest_height} vs. {height}), loading heights {i} - {end}.')
                await self.__get_blocks_from_consensus(i, end)
            timestamp = self.__db.get_timestamp(height)
            if timestamp is None:
                raise Exception('Blocks cache miss after cache update.')
            return timestamp

    async def duration(self, begin, end, consensus):
        return await self.at_height(end, consensus) - await self.at_height(begin, consensus)       

    async def __get_newest_blocks(self, current_height):
        begin, _ = self.__db.get_newest_height()
        if begin is None:
            begin = current_height
        elif begin >= current_height:
            return
        else:
            begin += 1
        self.__plugin.msg.debug(f'Updating blocks cache, loading heights {begin} - {current_height}.')
        await self.__get_blocks_from_consensus(begin, current_height)

    async def __get_blocks_from_consensus(self, begin, end):
        async with self.__api.create_session() as session:
            try:
                blocks = []
                for i in reversed(range(begin, end + 1)):
                    json = await self.__api.get(session, '/consensus/blocks', {'height': i})
                    block = Siablockdata(json)
                    blocks.append((block.height, block.timestamp))
                self.__db.add_blocks(blocks)
            except ApiRequestFailedException:
                raise
