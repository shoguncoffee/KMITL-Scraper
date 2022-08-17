import json, csv, os
import urllib3, http, requests
import asyncio, aiohttp
from time import strftime, sleep
from itertools import product


def log(*s, t=None, multiline=False, end='\n', sep=' '):
    dash = ' '*13 + '-'
    if t is None: 
        t = strftime("%X")
        a = ''
    elif t is False:
        t = ''
        a = dash
    if multiline: 
        sep = '\n' + dash
        
    print('%-7s'%t, a, sep.join(str(q) for q in s), end=end, sep='')

class FormatError(Exception): 
    def __init__(self, arg: object) -> None:
        self.arg = arg
        super().__init__(arg)
    
    def __str__(self) -> str:
        return self.arg


class csv_handle: # for overwrite method (unusable yet)
    field = [
        'subject id', 
        'section', 
        'sec pair', 
        'credit', 
        'type', 
        'limit', 
        'count', 
        'time', 
        'mid exam', 
        'late exam'
        ]
    day = [
        None, # for reserve index 0
        'อาทิตย์', 
        'จันทร์', 
        'อังคาร', 
        'พุธ', 
        'พฤหัสบดี', 
        'ศุกร์', 
        'เสาร์'
        ]
    
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


class Subjects_detection:
    host = 'k8s.reg.kmitl.ac.th'
    URL = f'https://{host}/'
    directory_token = 'api/user/'
    directory_data = 'reg/api/' 
    common_header = {
        'Accept-Language': 'en-us',
        'Host': host,
        'Referer': 'https://new.reg.kmitl.ac.th/',
        'Origin': 'https://new.reg.kmitl.ac.th',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
        }
    
    lookup_id = [
            # ('01-89', '01-99', '1-9'),
            # ('91-99', '01-99', '1-9'),
            ('01', '07', '6'),
            ('90', ('64','59','57'), '1-5'),
            ]
        # -------- example -------- (No. run from 001 to 999)
        # 01 07 6 xxx -> CE subject
        # maingroup branch degree No.
        # 
        # 90 64 5 xxx -> gen-ed subject
        # maingroup year group No.
    
    reason_why_cannot = [
            ('not in the course schedule', 'Close'),
            ('not pass rule in the course', 'Not qualified'),
            ('not still registered subject (Prerequisite)', 'Require prerequisite'),
            ('Not found Data', 'N/A'),
            ]

    exception = (
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ConnectionError,
            urllib3.exceptions.ProtocolError,
            http.client.RemoteDisconnected,
            #aiohttp.client_exceptions.ClientConnectorError,
            )
    
    
    def __init__(self, student_id, password,
            year = 2565, semester = 1, level = 1,
            lookup_id = lookup_id, csv = csv_handle): # if csv = False -> Not export to csv
        
        registered_url_params = {
            'funtion': 'get-regis-result',
            'student_id': student_id,
            'year': year,
            'semester': semester,
            'level_id': level,
            }
        core_url_params = lambda id:{
            'funtion': 'get-can-register-by-student-id-and-subject-id',
            'subject_id': id,
            'student_id': student_id,
            'year': year,
            'semester': semester,
            }
        token_json = json.dumps({
            'function': 'login-jwt',
            'email': f'{student_id}@kmitl.ac.th',
            'password': password
            })        
        token_header = self.common_header | {
            'Content-Length': str(token_json.__len__()),
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json;charset=utf-8'
            }
        for k, v in locals().items():
            if k != 'self': setattr(self, k, v)
    
    
    def get_url(self, directory):
        return self.URL + directory
        
    @staticmethod
    def time_period(t):
        tl = '12:00', '16:00', '19:00'
        for n, time in enumerate(tl):
            if t < time: return n
        # 0 -> beforenoon, 1 -> afternoon, 2 -> evening
    
    
    @staticmethod
    def str_range(s):
        if isinstance(s, str):
            if '-' in s:
                start, end = s.split('-')
                l = len(start)
                for i in range(int(start), int(end)+1): 
                    yield str(i).zfill(l)
            else: yield s
        else: yield from s
    
    
    def id_selecter(self, id):        
        condition = (
            True
            ) 
        if all(condition): 
            return True
    
    
    def generate_id(self, r):            
        l = (*r, '001-999') if len(r) == 3 else r
        seq = [self.str_range(q) for q in l]
        for d in product(*seq):
            id = ''.join(d)
            if self.id_selecter(id): yield id


    def get_occupy(self, registered):
        k = {'teach':{}, 'mexam':{}, 'exam':{}}
        time_period = self.time_period
        
        for subject in registered:
            id = subject['subject_id']
            sec = subject['section']
            
            for s in 'mexam', 'exam':
                date = subject[s+'_date']
                start_time = subject[s+'_time'][:5]
                
                if date != '0000-00-00': 
                    period = time_period(start_time)
                    k[s][(date, period)] = id, sec
            
            start_time = subject['teach_time'][:5]
            day = subject['teach_day']
            period = time_period(start_time)
            k['teach'][(day, period)] = id, sec
            
        return k  
    
    
    def check_overlap(self, datalist, seq):
        time_period = self.time_period
        occ = self.occupied_time
        
        def sub(subject):
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
        
        this_subject = datalist[seq]
        this_id = this_subject['subject_id']
        pack_sec = this_subject['sec_pair']
        check1 = sub(this_subject)
        
        if check1: return check1
        elif pack_sec is not None:
            for subject in datalist:
                if subject['section'] == pack_sec:
                    check2 = sub(subject)
                    if check2: return check2
                    break
            else:
                log(f"can't find sec {pack_sec} in {this_id} (original_sec: {this_subject['section']})")


    def apply_respone(self, id, data):
        loglist = []
        for n, subject in enumerate(data):
            eng_name = subject["subject_ename"]
            thai_name = subject["subject_tname"]
            count = subject['COUNT']
            limit = subject['LIMIT'] if subject['LIMIT'] != 0 else 'Unlimit'
            sec = subject['section']
            
            is_lap = self.check_overlap(data, n)
            
            if isinstance(count, str) and 'Full' in count: 
                text = f'Full! [{limit}]'
            elif is_lap: 
                text = f'Overlap! [{count}/{limit}] with {is_lap[0]}({is_lap[1]})'
            else:
                text = f'Open! [{count}/{limit}]'
            
            loglist.append('%-6s%s'%(f'({sec})', text))
            
        log(f'{id}: ___{eng_name}___', *loglist, multiline=True)
        if self.csv: 
            self.writer(self.csv.format(data))
                
    
    def handle_respone(self, id, error, data):
        if error is not None:
            Err = error['message_en']                                     
            for part, reply in self.reason_why_cannot:
                if part in Err: 
                    log(f'{id}: {reply}')
                    break
            else: 
                log(f'{id}: unknow error => {Err}')
        else:
            self.apply_respone(id, data)
    
    
    async def core(self, id): 
        async with self.session.get(self.core_url(id)) as res:
            rawdata = json.loads(await res.text())
        
        try: 
            error, infomation = rawdata['error'], rawdata['data']
        except KeyError:
            if 'many request' in rawdata:
                raise FormatError('TooManyRequest')
            else:
                log(f'{id}: Respone format Error', json.dumps(rawdata, indent=3), sep='\n', end='\n\n')
                raise FormatError('')
        else:
            self.handle_respone(id, error, infomation)


    async def try_loop(self, id):
        while 1:
            try: 
                await self.core(id)
            except FormatError as e:
                if e == 'TooManyRequest':
                    log(e, ', reconnect in 12 sec: ')
                    for _ in range(12):
                        sleep(1)
                        print('.', end='')
                    print()
                
            except self.exception as e: 
                log(f'{id}: Connection Error', e, sep='\n', end='\n\n')
            else: 
                break
    
    
    async def main(self, token):
        kwarg = {
            'header': self.common_header | {
                'Authorization': f"Bearer {token}",
                'Accept': '*/*'
                },
            'connector': aiohttp.TCPConnector(limit=16),
            'timeout': aiohttp.ClientTimeout(total=8),
        }
        async with aiohttp.ClientSession(**kwarg) as session:
            my_registered =  await session.get(self.get_url(self.directory_data), 
                                               params=self.registered_url_params
                                               )
            self.registered_class = json.loads(await my_registered.text())
            self.occupied_time = self.get_occupy(self.registered_class) 
            self.session = session
            
            for r in self.lookup_id:
                await asyncio.gather(
                    *[self.try_loop(id) for id in self.generate_id(r)]
                    )
    

    def run(self):
        try:
            file = False
            res = requests.post(self.get_url(self.directory_token), 
                data=self.token_json, headers=self.token_header
                )
            token = json.loads(res.text)['token']
        except KeyError: 
            log('student-id or password incorrect')
        else:
            if self.csv: 
                file = open('data_table.csv', 'w')
                self.writer = csv.writer(file).writerow
                self.writer(self.csv.field)
            asyncio.run(self.main(token))
        finally:
            res.close()
            if file: file.close()


if __name__ == '__main__':
    id = ''
    password = ''
    mysubject = Subjects_detection(id, password, csv=False)
    mysubject.run()
