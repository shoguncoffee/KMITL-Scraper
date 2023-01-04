from __future__ import annotations
from multidict import CIMultiDict as __MultiDict
from base import *
if TYPE_CHECKING:
    from protocol import _BaseProtocol

class MultiDict(__MultiDict):
    def __init__(self, Protocal: _BaseProtocol, arg: Opt[Iter] = None, **kw):
        super().__init__(arg or [], **kw)
        self.protocol = Protocal

def __warp(f: Call):
    def new(self: MultiDict, *arg, **kw):
        if hasattr(self.protocol, 'session'):
            header = self.protocol.session.headers
            f(header, *arg, **kw)
            
        return f(self, *arg, **kw)
    return new

for attr in dir(MultiDict):
    if not attr.startswith('_'):
        f = getattr(MultiDict, attr)
        if callable(f):
            setattr(MultiDict, attr, __warp(f))

if __name__ == '__main__':
    d = MultiDict('')
    print(d)
    d.add('q', 'e')
    print('add')