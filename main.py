from asyncio import run, create_task
from api import KmitlAPI

async def main():
    kmitl = KmitlAPI()
    async for i in kmitl.lookup():
        print(i)
        
        
if __name__ == '__main__':
    run(main())