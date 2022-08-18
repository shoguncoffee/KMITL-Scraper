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
        
    print(
        '%-7s'%t, a, sep.join(str(q) for q in s), 
        end=end, sep='')


class Retrying(Exception): 
    pass


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
            aiohttp.ClientConnectorError,
            
            )
    
    
    def __init__(self, student_id, password,
            year = 2565, semester = 1, level = 1,
            lookup_id = lookup_id, csv = csv_handle): # if csv = False -> Not export to csv
        
        registered_arg = {
            'url': self.URL + self.directory_data,
            'params': {
                'funtion': 'get-regis-result',
                'student_id': student_id,
                'year': year,
                'semester': semester,
                'level_id': level
                }
            }
        core_arg = lambda id: {
            'url': self.URL + self.directory_data,
            'params': {
                'funtion': 'get-can-register-by-student-id-and-subject-id',
                'subject_id': id,
                'student_id': student_id,
                'year': year,
                'semester': semester,
                }
            }
        token_arg = {
            'url': self.URL + self.directory_token,
            'data': json.dumps({
                'function': 'login-jwt',
                'email': f'{student_id}@kmitl.ac.th',
                'password': password
                }),
            }
        for k, v in locals().items():
            if k != 'self': setattr(self, k, v)
    
    
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
    

    def display_respone(self, id, data):
        seclist = {s['section']: s for s in data}
        loglist = ['']
        
        def sub(subject):
            eng_name = subject["subject_ename"]
            thai_name = subject["subject_tname"]
            count = subject['COUNT']
            limit = subject['LIMIT'] if subject['LIMIT'] != 0 else 'Unlimit'
            sec = subject['section']
            pair = subject['sec_pair']
            
            is_lap = self.check_overlap(data)
            if isinstance(count, str) and 'Full' in count: 
                text = f'Full! [{limit}]'
            elif is_lap: 
                text = f'Overlap! [{count}/{limit}] with {is_lap[0]}({is_lap[1]})'
            else:
                text = f'Open! [{count}/{limit}]'
            
            loglist.append(
                f"{' '*10}%-{9+len(eng_name)}s {text}'%f'({sec})__{eng_name}__"
                )
            return pair
        
        for sec, subject in seclist:
            othersec = sub(subject)                
            if othersec is not None:
                sub(seclist.pop(othersec))                
        
        log(*loglist, multiline=True)
                
    
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
            log(f'{id}: Available', end='')
            self.display_respone(id, data)
            if self.csv: 
                self.writer(self.csv.format(data))
    
    
    async def core(self, id): 
        async with self.session.get(**self.core_arg(id)) as res:
            rawdata = json.loads(await res.text())
        try: 
            error = rawdata['error']
            infomation = rawdata['data']
        except KeyError:
            if 'many request' in rawdata:
                raise Retrying('Too many request')
            else:
                log(
                    f'{id}: Respone format Error', 
                    json.dumps(rawdata, indent=3), 
                    sep='\n', 
                    end='\n\n'
                    )
                raise Retrying
        else:
            self.handle_respone(id, error, infomation)


    async def try_loop(self, id, limit=6):
        for _ in range(limit):
            try: 
                await self.core(id)
            except Retrying as e:
                if e == 'Too many request':
                    log(f'{id}: {e}, reconnect in 12 sec', end=' ')
                    for _ in range(3):
                        await asyncio.sleep(1)
                        print('.', end='')
                    print()

            except self.exception as e: 
                log(f'{id}: Connection Error', e, sep='\n', end='\n\n')
            else: 
                break
            
        else:
            log(f'{id}: exceed trying for {limit} times')
    
    
    async def main(self, token):
        kwarg = {
            'header': {'Authorization': f"Bearer {token}"},
            'connector': aiohttp.TCPConnector(limit=16),
            'timeout': aiohttp.ClientTimeout(total=8),
            }
        async with aiohttp.ClientSession(**kwarg) as session:
            async with session.get(**self.registered_arg) as res:
                self.registered_class = json.loads(await res.text())
            self.occupied_time = self.get_occupy(self.registered_class) 
            self.session = session
            
            for r in self.lookup_id:
                await asyncio.gather(
                    *[self.try_loop(id) for id in self.generate_id(r)]
                    )
    

    def run(self):
        try:
            file = False
            with requests.post(**self.token_arg) as res:
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
            if file: file.close()


if __name__ == '__main__':
    id = ''
    password = ''
    mysubject = Subjects_detection(id, password, csv=False)
    mysubject.run()
