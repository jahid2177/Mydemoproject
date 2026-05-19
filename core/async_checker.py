"""
Async Stream Checker — aiohttp ClientTimeout fix সহ
"""
import asyncio
from typing import Iterable

import aiohttp

USER_AGENT = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) IPTVChecker/1.0'}


async def _check_url(session: aiohttp.ClientSession, url: str, timeout: int = 10):
    # ✅ FIX: plain int নয়, ClientTimeout object ব্যবহার করতে হবে
    ct = aiohttp.ClientTimeout(total=timeout)
    result = {
        'url': url, 'alive': False, 'status': None,
        'error': '', 'final_url': url, 'content_type': '',
    }
    # HEAD দিয়ে প্রথমে চেষ্টা
    try:
        async with session.head(
            url, allow_redirects=True, timeout=ct, headers=USER_AGENT
        ) as response:
            result['status'] = response.status
            result['final_url'] = str(response.url)
            result['content_type'] = response.headers.get('Content-Type', '')
            if response.status < 400:
                result['alive'] = True
                return result
    except Exception as exc:
        result['error'] = str(exc)

    # HEAD fail হলে GET fallback
    try:
        async with session.get(
            url, allow_redirects=True, timeout=ct,
            headers={**USER_AGENT, 'Range': 'bytes=0-512'},
        ) as response:
            result['status'] = response.status
            result['final_url'] = str(response.url)
            result['content_type'] = response.headers.get('Content-Type', '')
            body = await response.text(errors='ignore')
            result['alive'] = response.status < 400 and (
                bool(body) or 'mpegurl' in result['content_type'].lower()
            )
            return result
    except Exception as exc:
        result['error'] = str(exc)
        return result


async def check_streams(streams: Iterable, concurrency: int = 50, timeout: int = 10):
    semaphore = asyncio.Semaphore(concurrency)
    # ✅ FIX: TCPConnector ssl=False যোগ করা হয়েছে — self-signed cert crash এড়াতে
    connector = aiohttp.TCPConnector(limit=concurrency, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        async def runner(item):
            url = item.get('url') if isinstance(item, dict) else str(item)
            if not url:
                return {'url': '', 'alive': False, 'status': None, 'error': 'no url'}
            async with semaphore:
                return await _check_url(session, url, timeout=timeout)
        return await asyncio.gather(*(runner(item) for item in streams))
