from __future__ import annotations
from base import *
from period import TimePeriod

if TYPE_CHECKING:
    period = tuple[datetime, datetime]

THEORY = 'ทฤษฎี'
PRATIC = 'ปฎิบัติ'

class Subject:
    def __init__(self,
        id: StrInt,
        section: StrInt,
        engname: str,
        thainame: str,
        credit: StrInt,
        day: StrInt,
        time: Iter[period],
        genre: Opt[str] = None,
        sec_pair: Opt[StrInt] = None,
        mid_date: Opt[datetime] = None,
        mid_time: Opt[period] = None,
        final_date: Opt[datetime] = None,
        final_time: Opt[period] = None,
        slot: Opt[tuple[tuple[str, tuple[str, str]], ...]] = None,
        count: Opt[StrInt] = None,
        limit: Opt[StrInt] = None,
    ):
        self.slot = slot
        self.engname = engname.strip()
        self.thainame = thainame.strip()
        self.id = int(id)
        self.credit = int(credit)
        self.section = int(section)
        self.midExam_date = mid_date.date()
        self.midExam_time = TimePeriod(*mid_time) if mid_time else None
        self.finalExam_date = final_date.date()
        self.finalExam_time = TimePeriod(*final_time) if final_time else None
        self.period = [
            TimePeriod(*period) for period in time
        ]
        toint = lambda q: int(q) if q else None
        self.sec_pair = toint(sec_pair)
        self.count = toint(count)
        self.limit = toint(limit)
        
        if isinstance(day, str):
            day = day.title()
            if day not in day_name:
                if day in day_abbr:
                    day = day_abbr.index(day) + 1
                else:
                    day = int(day)
        if isinstance(day, int):
            day = day_name[day-1]
        self.day = day
        
        if genre:
            if genre in THEORY: genre = THEORY 
            elif genre in PRATIC: genre = PRATIC
            else: genre = None
        else: genre = None
        self.genre = genre
        
        
    def overlap(self, v: Subject):
        self.
        

class SubjectTable:
    def __init__(self, *subject: Subject):
        self.subjects = list(subject)
        
    
    def add(self, subject: Subject):
        self.subjects.append(subject)
        
        
if __name__ == '__main__':
    ...