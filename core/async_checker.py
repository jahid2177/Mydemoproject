import asyncio
from typing import Iterable

import aiohttp

USER_AGENT = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) IPTVChecker/1.0'}


async def _check_url(session: aiohttp.ClientSession, url: str, timeout: int = 10):
    result = {'url': url, 'alive': False, 'status': None, 'error': '', 'final_url': url, 'content_type': ''}
    try:
        async with session.head(url, allow_redirects=True, timeout=timeout, headers=USER_AGENT) as response:
            result['status'] = response.status
            result['final_url'] = str(response.url)
            result['content_type'] = response.headers.get('Content-Type', '')
            if response.status < 400:
                result['alive'] = True
                return result
    except Exception as exc:
        result['error'] = str(exc)

    try:
        async with session.get(url, allow_redirects=True, timeout=timeout, headers={**USER_AGENT, 'Range': 'bytes=0-512'}) as response:
            result['status'] = response.status
            result['final_url'] = str(response.url)
            result['content_type'] = response.headers.get('Content-Type', '')
            body = await response.text(errors='ignore')
            result['alive'] = response.status < 400 and (bool(body) or 'mpegurl' in result['content_type'].lower())
            return result
    except Exception as exc:
        result['error'] = str(exc)
        return result


async def check_streams(urls: Iterable, concurrency: int = 50, timeout: int = 10):
    semaphore = asyncio.Semaphore(concurrency)
    async with aiohttp.ClientSession() as session:
        async def runner(item):
            url = item.get('url') if isinstance(item, dict) else str(item)
            async with semaphore:
                return await _check_url(session, url, timeout=timeout)
        return await asyncio.gather(*(runner(item) for item in urls))
