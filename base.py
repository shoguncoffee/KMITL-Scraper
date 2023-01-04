import sys, warnings, os
import numpy, random, math
import tqdm
import json, csv
from typing import Any, Callable as Call, Type, TYPE_CHECKING, Iter as Iter, Optional as Opt, Coroutine as Coro, Awaitable as Await, Concatenate as Concat
from itertools import cycle, product, count, chain
from dataclasses import dataclass, field, KW_ONLY
from copy import copy
from calendar import *
from datetime import datetime, date, time
from time import time as times, strftime, sleep

if TYPE_CHECKING:
    from typing import TypeVar, ParamSpec
    P = ParamSpec("P")
    T = TypeVar("T")
    StrInt = str | int

strptime = datetime.strptime
TODAY = datetime.today()

class log:
    dashline = '-' * 100
    dash = ' '*13 + '-'
    
    def __new__(cls, 
        *s, 
        t = None, 
        end: str = '\n', 
        sep: str = ' '
    ):
        if t is None: 
            t = strftime("%X")
            a = ''
        elif t is False:
            t = ''
            a = cls.dash
        
        print('%-8s'%t, a, end='')
        print(*s, end=end, sep=sep)
        return cls
        
    @classmethod
    def doting(cls, n: int = 3):
        print(end=' ')
        for _ in range(n):
            sleep(1)
            print('.', end='')
        print()
        
    @classmethod
    def line(cls, s: str = ''):
        print(cls.dashline)
        if s: cls(s)
        




def raiser(exception):
    raise exception


def json_to_items(file: str):
    with open(file) as f:
        d: dict[str, Any] = json.load(f)
    return d.items()
    
    
def repeat(n: int, func: Call):
    for _ in range(n): func()
        

def cls_from_module(*modules, folder=''):
    if folder:
        files = __import__(folder).__all__        
        modules = [getattr((__import__(f'{folder}.{f}')), f) for f in files]
        yield from cls_from_module(*modules)
        
    else:
        for module in modules:
            for obj in module.__dict__.values():
                if isinstance(obj, type) \
                        and obj.__module__ == module.__name__ \
                        and not obj.__name__.startswith('_'):
                    yield obj
           
                
def all_neat_value(obj: Iter): 
    iterater = (dict, list, tuple)
    assert obj not in iterater, f'Not iterable: {obj}'
    
    for q in (obj if not isinstance(obj, dict) else obj.values()):
        if isinstance(q, iterater):
            yield from all_neat_value(q)
        else: 
            yield q
        
            
def get_from_neat_dict(d: dict, key: Any): #!
    # all neat key shouldn't duplicate
    for k, v in d.items():
        if k == key:
            return v
        
        elif isinstance(v, dict):
            r = get_from_neat_dict(v, key)
            if r: return r
            
    raise KeyError


'''
def dict_insert(d: dict, dept: list[str], value):
    last = dept[-1]
    l = d
    for k in dept:
        p = l
        l = l.get(k)
        assert l is not None or k == last, f'{d}, {dept}'
        
    if k is None:
        p[last] = value
    else:
        p[last]
'''         
    
            
def updater(objmap: dict[str, Any], sample: dict[str, Any]):
    for key, val in sample.items():
        i = objmap.get(key)
        
        if i is None:
            objmap[key] = val
        
        elif isinstance(i, dict):
            assert isinstance(val, dict)
            updater(i, val)
              
        elif isinstance(i, list):
            if isinstance(val, list):
                i.extend(val)
            else:
                i.append(val)
        
        else:
            raise TypeError(
                f'{type(i)} not updatable \n >>> {objmap} \n >>> {sample}'
            )

  
def nowtime():
    return strftime('%X')
    
    
def mountain_function(input, peak=1, thickness=1, base=0):
    return (peak - base)/(input**2 /thickness + 1) + base


def anyin(d: dict, *sample):
    return any(q in d for q in sample)


def set_attr(
        obj: object, 
        include_None: bool = True,
        include_dict: bool = False, 
        include_dunder: bool = False,
        **kw
    ):
    for k, v in kw.items():
        if not any([
            v is obj,
            not include_dict and isinstance(v, dict),
            not include_None and v is None,
            not include_dunder and k.startswith('_')
        ]):
            setattr(obj, k, v)


def copy_attr(haveattr: object, wantattr: object, *attrname: str):
    for n in attrname:
        setattr(wantattr, n, getattr(haveattr, n))
        
        
def condition_path(*arg, call=False): # avoid long if else
    for b, f in zip(arg[::2], arg[1::2]):
        if b: 
            return f() if call else f    
        

def do(*q, func: str, **arg):
    for obj in all_neat_value(q):
        getattr(obj, func)(**arg)
            
    return q


def sign(n: float):
    return (n>0) - (n<0)


def merge_dict(*d: dict):
    new = {}
    for i in d:
        new.update(**i)
    return new


def enumerate_dict(d: dict[Any, dict]):
    new = {}
    for v in d.values():
        new.update(v)

    return new


def has_attr(obj: object, *attr: str):
    for n in attr:
        if not hasattr(obj, n):
            yield n


def trying(f: Call):
    try: 
        return f()
    except:
        pass
        
        
def clockTominute(t: str):
    """arg format: '12:00', '16:30', '19:00:00'"""
    return sum(
        int(n)*i for i, n in zip((60, 1), t.split(':'))
    )


def convert_default(obj, func: Call, *attr):
    for n in attr:
        if v := getattr(obj, n):
            setattr(obj, n, func(v))

def sort(*s):
    return sorted(s)


if __name__ == '__main__':
    # l = cycle(range(3))
    # while 1:
    #     print(next(l))
    #     sleep(1)
    # print(*product([9,8,7], [1
    #                          ]))
    j = enumerate_dict({
        'head': {
            1: 11,
            2:3
        },
        'hand': {
            9: 99,
            4: 0
        }
    })
    print(j)
    