from __future__ import annotations
from base import *
from exceptions import *
import asyncio, aiohttp
from _multidict import MultiDict
from subject import *

ID = 'studentID'
KEY = 'password'
YEAR = 'year'
SEMESTER = 'semester'


class CSV: # unready
    def teach_time_format(self, data):
        day_index = int(data['teach_day'])
        day = self.day[day_index]
        
        start_time = data['teach_time'][:5]
        end_time = data['teach_time2'][:5]     
        other_time = data['teachtime_str']
        
        date = f"{day} {start_time}-{end_time}"
        
        if 'x' in other_time:
            thatday, teach_time = other_time.split('x')
            if thatday == day:
                return f"{date} {teach_time}"
            else:
                other_day = day[int(thatday)]
                return f"{date}, {other_day} {teach_time}"
        else: 
            return date
        
             
    @staticmethod
    def exam_time_format(data):
        for s in 'mexam', 'exam':
            date = data[s+'_date']
            start = data[s+'_time'][:5]
            end = data[s+'_time2'][:5]
            
            if date == '0000-00-00': 
                return 'จัดสอบเอง'
            else: 
                return f"{date} {start}-{end}"
    
    
    def format(self, data): 
        k = [data[q] for q in self.field[:4]]
        k.extend([
            'ทฤษฎี' if data['lect_or_prac'] == 'ท' else 'ปฏิบัติ',
            'no limit' if data['LIMIT'] == 0 else data['LIMIT'],
            'Full' if 'Full' in data['COUNT'] else data['COUNT'],
            ])
        k.append(self.teach_time_format(data))
        k.append(self.exam_time_format(data)) 
        
        return k
    
    def update_csv(self, ):
        ...
    

def connection_loop(f: Call[P, Await[None]]) -> Call[P, Await[None]]:
    async def _(*arg: P.args, **kw: P.kwargs):
        log.line(f'Start {f.__qualname__}')
        self: _BaseProtocol = arg[0] # type: ignore
        while 1:
            self.new_session()
            try: 
                await f(*arg, **kw)
                            
            except aiohttp.ClientConnectorError:
                log('ERROR: Check your connection')
                
            except Wrong as info:
                log(info)
                
            except Exit as info:
                log(info)
                break
            
        self.close()
    
    return _ # type: ignore 


def str_range(s: str | Iter[str]):
    """
    generate str ...
    """
    if isinstance(s, str):
        if '-' in s:
            start, end = s.split('-')
            bit = len(start)
            assert bit == len(end)
            for i in range(int(start), int(end)+1): 
                yield str(i).zfill(bit)
        else: yield s
    else: yield from s
    
    
def id_range(
    r: list[str], 
    filter: Call[[str], bool] = lambda _: True
): 
    """
    generate id ex. subject id ...
    """
    l = (*r, '001-999') if len(r) == 3 else r
    seq = [str_range(q) for q in l]
    for d in product(*seq):
        id = ''.join(d)
        if filter(id): 
            yield id


@dataclass
class _BaseProtocol:
    studentID: StrInt
    password: StrInt
    year: StrInt = TODAY.year + 543
    semester: StrInt = 1 if 12 > TODAY.month > 5 else 2
    level: StrInt = 1
    
    _: KW_ONLY
    taskgroup: asyncio.TaskGroup
    auth_expiration: int = 600
    
    base_url: Opt[str] = None
    connection_limit: int = 10
    timeout: int = 15
    ratelimit: int = 60
    
    def __post_init__(self):
        self.default_header = MultiDict(self)
        self._cookie: Opt[dict] = None
        self.email = f'{self.studentID}@kmitl.ac.th'
        self.task = []
        
    def update_header(self, **kw):
        self.default_header.update(**kw)
        if hasattr(self, 'session'):
            self.session.headers.extend(**kw)
        
    @property
    def cookie(self):
        return self._cookie
    
    @cookie.setter
    def cookie(self, value: dict):
        self._cookie = value
        self.new_session()

    def new_session(self):
        """
        "ClientSession" require to have running event loop ?
        """
        log('New session')
        # asyncio.get_running_loop()
        trying(self.close)
        self.session = aiohttp.ClientSession(
            base_url = self.base_url,
            headers = self.default_header,
            cookies = self.cookie,
            connector = aiohttp.TCPConnector(
                limit = self.connection_limit
            ),
            timeout = aiohttp.ClientTimeout(self.timeout),
        )
    
    def open_session(self):
        """
        create new session if there is no session
        """
        if hasattr(self, 'session'):
            if self.session.closed:
                self.new_session()
        else:
            self.new_session()
        
    def close(self):
        asyncio.create_task(self.session.close())
        log('add session.close task')
    
    def C429(self, content):
        """
        handle HTTP:
        Too Many Requests
        """
        log()
        
    def C200(self, content):
        """
        handle HTTP:
        OK
        """
        return content
    
    @staticmethod
    def request(f: Call[P, Await[dict | None]]) -> Call[P, Await[Any]]:
        async def _(self: _BaseProtocol, *arg: P.args, **kw: P.kwargs):
            self.open_session()
            f_name = f.__name__.replace('_', '')
            method: Call[
                ..., aiohttp.client._RequestContextManager
            ] = getattr(self.session, f_name)

            if dict := await f(*arg, **kw):
                del dict['self'], dict['url']
            
            async with method(*arg, **(dict or kw)) as response:
                type, subtype = response.content_type.split('/')
                data = await response.read()
                match subtype:
                    case 'json':
                        content = json.loads(data)
                    case 'plain':
                        content = data.decode()
                    case _:
                        raise Wrong(f'Unsupport content_type {type}/{subtype}: {data}')
                
                code = str(response.status)
                if handle := getattr(self, f'C{code}', None):
                    return handle(content)
                elif code.startswith('2'):
                    log(f':')
                    return content
                else:
                    raise Wrong(f'Unknow HTTP code "{code}": {content}')                

        return _ # type: ignore
    
    @request
    async def _get(self, url: str = ..., *, params: dict[str, Any], **kw): ...
    @request
    async def _post(self, url: str = ..., *, data: str, **kw): ...
    @request
    async def get(self, url: str = ..., **params): return locals()
    @request
    async def post(self, url: str = ..., **json): return locals()
        
    
def From(url: str) -> Type[_BaseProtocol]:
    return type(
        'BaseProtocol', 
        (_BaseProtocol,), 
        {'base_url': url}
    )
    
class Simple(From('https://k8s.reg.kmitl.ac.th')):
    """
    Seem like this site doesn't use IP or Student ID to identify client (maybe session or cookie ?)
    So we can avoid HTTP: 429 by create new session every ~200 requests
    """
    dir_data = '/reg/api/'
    response_shorten = {
        'not in the course schedule': 
            'Close',
        'not pass rule in the course': 
            'Not qualified',
        'not still registered subject (Prerequisite)': 
            'Require prerequisite',
        'Not found Data': 
            'N/A',
        'cannot be repeated register':
            'Can\'t re-register'
    }
    def __post_init__(self):
        super().__post_init__()
        if self.csv:
            self.data = asyncio.Queue()
        self.csv
    
    
    def filter(self, id):        
        condition = (
            True,
            ...
        )
        if all(condition): 
            return True


    def get_occupy(self, registered):
        k = {'teach': {}, 'exam': {}}        
        for subject in registered:
            id = subject['subject_id']
            sec = subject['section']
            
            for exam in 'mexam', 'exam':
                date = subject[f'{exam}_date']
                start_time = subject[f'{exam}_time'][:5]
                if date != '0000-00-00': 
                    period = clockTominute(start_time)
                    k['exam'][(date, period)] = id, sec
            
            start_time = subject['teach_time'][:5]
            day = subject['teach_day']
            period = clockTominute(start_time)
            k['teach'][day] = id, sec
            
        return k
    
    
    def check_overlap(self, subject):
        time_period = self.time_period
        occ = self.occupied_time.copy()
        
        for s in 'mexam', 'exam':
            date = subject[s+'_date']
            period = time_period(subject[s+'_time'])
            l = date, period
            exist = occ[s].pop(l, None)
            if exist: return exist
        
        day = subject['teach_day']
        period = time_period(subject['teach_time'])
        l = day, period
        return occ['teach'].pop(l, None)
    
    
    def check_overlap(self, subject):
        ...
        

    def display_respone(self, data):
        def sub(subject, follow=False):
            try:
                engname = subject["subject_ename"]
                thainame = subject["subject_tname"]
                count = subject['COUNT']
                limit = subject['LIMIT'] if subject['LIMIT'] != 0 else 'Unlimit'
                sec = subject['section']
                pair = subject['sec_pair']                
            except KeyError as e:
                print(e, json.dumps(subject, indent=3), sep='\n')
            else: 
                is_lap = self.check_overlap(subject)
                if isinstance(count, str) and 'Full' in count: 
                    text = f'Full! [{limit}]'
                elif is_lap: 
                    text = f'Overlap! [{count}/{limit}] with {is_lap[0]}({is_lap[1]})'
                else:
                    text = f'Open! [{count}/{limit}]'
                
                if follow:
                    s = f"%-5s%-{9+len(engname)}s {text}/n" % (f'({sec})', f'__{engname}__')
                else: 
                    s = f"%-5s%-{9+len(engname)}s {text}" % (f'({sec})', f'__{engname}__')
                    
                loglist.append(s)
                return pair
        
        loglist = ['']
        for subject in data:
            othersec = sub(subject)                
            if othersec is not None:
                for n, i in enumerate(data):
                    if i['section'] == othersec: 
                        sub(data.pop(n), True)
                        break
        
        log(*loglist, t=False)
        
    
    def handle_respone(self, id, error, data):
        if error is not None:
            Err = error['message_en']                                     
            for part, reply in self.response_shorten:
                if part in Err: 
                    e = reply
                    break
            else: 
                e = f'unknow error => {Err}'
            log(f'{id}: {e}')
            
        else:
            log(f'{id}: Available')
            self.display_respone(data)
            if self.csv: 
                self.writer(self.csv.format(data))
    
    
    async def take_response(self, id: StrInt):
        rawdata = await self.get(self.dir_data,
            function = 'get-can-register-by-student-id-and-subject-id',
            subject_id = id,
            student_id = self.studentID,
            year = self.year,
            semester = self.semester
        )
        try: 
            error = rawdata['error']
            infomation = rawdata['data']
            self.handle_respone(id, error, infomation)
            
        except KeyError:
            if TMR in rawdata:
                raise Retrying(TMR)
            else:
                log(
                    *json.dumps(rawdata, indent=3).split('\n'), 
                    t=False, sep=log.dash, end='\n'*2
                )
                raise Retrying(f'{id}: Respone format Error')            


    async def manage_exception(self, id: StrInt, limit: int = 6):
        """limit: 0 -> infinity"""
        for l in count(1):
            try: 
                await self.take_response(id)
                break
            
            except Retrying as e:
                if e == TMR:
                    log(f'{id}: {e}, reconnect in 6 sec', end=' ')
                    log.doting(6)

            except Connection as e: 
                log(f'{id}: Connection Error', e, sep='\n', end='\n\n')
                log.doting(3)

            finally:
                if l == limit:
                    log(f'{id}: exceed trying for {limit} times')
                    break
    
    
    async def get_registered(self):
        registered_class = await self.get(self.dir_data,
            function = 'get-regis-result',
            student_id = self.studentID,
            year = self.year,
            semester = self.semester,
            level_id = self.level
        )
        self.get_table(registered_class)
        #self.occupied_time = self.get_occupy(registered_class)
        
    def get_table(self, c):
        ...
        
    '''
    if self.csv:
        file = open('data_table.csv', 'w')
        idlist = open('id_table.csv', 'w')
        self.writer = csv.writer(file).writerow
        self.writer(self.csv.field)
    await self.main2()
    
    if self.csv: 
        file.close()
    '''
    
    async def auth(self):
        response = await self.post('/api/user/',
            function = 'login-jwt',
            email = self.email,
            password = self.password
        )
        try: 
            self.token: str = response['token']
            self.header = {
                'Authorization': f"Bearer {self.token}"
            }
        except KeyError:            
            log(json.dumps(response, indent=3))
            raise Exit('Authorization failed')
    

    @connection_loop
    async def look_up(self, group: asyncio.TaskGroup, l: Iter[tuple]):
        await self.auth()
        await self.get_registered()
        
        for r in l:
            group.create_task(self.manage_exception(r))
    
    
           
if __name__ == '__main__':
    lookup_id = [
        # ('01-89', '01-99', '1-9'),
        # ('91-99', '01-99', '1-9'),
        ('01', '07', '6'),
        ('90', ('64','59','57'), '1-5'),
    ]
    # --------- example --------- (No. run from 001 to 999)
    # 01 07 6 xxx -> CE subject
    # maingroup branch degree No.
    # 
    # 90 64 5 xxx -> gen-ed subject
    # maingroup year group No.
    import temp_user
    mysubject = Simple(
        temp_user.id, 
        temp_user.password, 
        lookup_id,
        csv=False
    )
    asyncio.run(mysubject.run())