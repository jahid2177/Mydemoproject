
import asyncio
import aiohttp

async def check_url(session, url):
    try:
        async with session.get(url, timeout=10) as response:
            return response.status == 200
    except:
        return False

async def check_streams(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [check_url(session, u) for u in urls]
        return await asyncio.gather(*tasks)
