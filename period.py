from __future__ import annotations
from base import *

if TYPE_CHECKING:
    Time =  datetime | time | Iterable[StrInt] | tuple[StrInt, StrInt]

'''
class ClassTable:
    def __init__(self, *t: TimePeriod):
        self
    
    def __contains__(self, time: Time | TimePeriod):
        if isinstance(time, TimePeriod):
            return 
        else:
            return self.start < convert(time) < self.end
    
    def overlap(self, time: ClassTable):
        
        return

    def __repr__(self):
        ...
        return super().__repr__()
'''

class TimePeriod:
    def __init__(self, start: Time, end: Time):
        _t = convert(start), convert(end)
        self.start, self.end = sorted(_t)
    
    def __contains__(self, time: Time):
        return self.start < convert(time) < self.end
    
    def overlap(self, time: TimePeriod): 
        """
        [11:00-12:00] not overlap with [12:00-13:00]
        """
        before = self.start >= time.end
        after = self.end <= time.start
        return not (before or after)
    
    
def convert(t: Time) -> time:
    if isinstance(t, datetime):
        return t.time()
    
    elif isinstance(t, time):
        return t
    
    else:
        arg = [int(n) for n in t]
        return time(*arg) # type: ignore
    
    
if TYPE_CHECKING:
    Period = TimePeriod | ClassTable

def overlap(t1: Period, t2: Period):
    return t1.overlap(t2)


if __name__ == '__main__':
    t1 = TimePeriod((12, 0), (13, 0))
    print(t1.overlap(TimePeriod((14, 0), (15, 0))))
    print(t1.overlap(TimePeriod((13, 0), (15, 0))))
    print(t1.overlap(TimePeriod((12, 59), (15, 0))))