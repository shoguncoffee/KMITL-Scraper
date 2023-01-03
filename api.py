from protocol import *

def require_id(func: Call):
    def new(self: KmitlAPI, *arg, **kw):
        if not self.username and self.password:
            raise Missing(
                f'"{func.__name__}" require username and password'
            )
        else:
            func(self, *arg, **kw)
    
    return new
        
def require(*attr: str):
    def warp(f: Call):
        def new(self: KmitlAPI):
            if any([
                getattr()
            ]):
                raise 
        return new
    return warp


class KmitlAPI:
    
    def __init__(self,
        student_id: Opt[StrInt] = None,
        password: Opt[StrInt] = None,
        year:  Opt[StrInt] = None,
        semester: Opt[StrInt] = None,
        
    ):
        self.username = f'{student_id}@kmitl.ac.th'
        self.password = password
        

    @require_id
    async def lookup(self, 
        inOrder: bool = True,
        protocol: Type[BaseProtocol] = Simple
    ):
        """
        
        """
        async for i in protocol():
            yield i
            
            
if __name__ == '__main__':
    ...