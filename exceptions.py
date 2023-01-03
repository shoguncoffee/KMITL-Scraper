import aiohttp
import asyncio

class Missing(Exception):
    ...
    
class Wrong(Exception):
    ...
    
class Retrying(Exception): 
    ...
    
class Exit(Exception):
    ...
    
Connection = (
    aiohttp.ClientConnectorError, 
    asyncio.TimeoutError
)