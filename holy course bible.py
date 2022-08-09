import requests, json, csv
import urllib3, http
from time import *


def log(*s, t=None, end='\n', sep=' '):
    a = ''
    if t is None: t = strftime("%X")
    elif t == False:
        t = ''
        a = ' '*4 +'-'
    print('%-9s'%t, a, *s, end=end, sep=sep)


class csv_handle: # for overwrite method
    field = ['subject id', 'section', 'sec pair', 'credit', 'type', 'limit', 'count', 'time', 'mid exam', 'late exam']
    day = [None, 'อาทิตย์', 'จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์']
    
    @staticmethod
    def teach_time_format(data):
        day = self.day[int(data['teach_day'])]
        start_time = data['teach_time'][:5]
        end_time = data['teach_time2'][:5]     
        other_time = data['teachtime_str']
        
        date = f"{day} {start_time}-{end_time}"
        
        if 'x' in other_time:
            thisday, teach_time = other_time.split('x')
            if thisday == day:
                return f"{date}, {teach_time}"
            else:
                other_day = day[int(thisday)]
                return f"{date}, {other_day} {teach_time}" 
             
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


class subjects_detection:    
    errorlist = [
        ('not in the course schedule', 'Not open yet'),
        ('not pass rule in the course', 'Not pass rule'),
        ('not still registered subject (Prerequisite)', 'Require precourse'),
        ('Not found Data', 'No data'),
        ]
    
    exception = (
        requests.exceptions.ConnectTimeout,
        requests.exceptions.ConnectionError,
        urllib3.exceptions.ProtocolError,
        http.client.RemoteDisconnected,
        )
    
    common_header = {
        'Accept-Language': 'en-us',
        'Host': 'k8s.reg.kmitl.ac.th',
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
    # ------ example ------ (No. run from 001 to 999)
    # 01 07 6 xxx -> CE subject
    # maingroup branch degree No.
    # 
    # 90 64 5 xxx -> gen-ed subject
    # maingroup year group No.
    
    def __init__(
            self, 
            student_id, 
            password,
            year = 2565,
            semester = 1,
            lookup_id = lookup_id,
            level = 1,
            csv = csv_handle # False = Not export to csv
        ):
        self.student_id = student_id
        self.password = password
        self.year = year
        self.semester = semester
        self.lookup_id = lookup_id
        self.level = level
        self.csv = csv
        
    
    @staticmethod
    def strange(s):
        if isinstance(s, str):
            if '-' in s:
                start, end = s.split('-')
                le = len(start)
                for i in range(int(start), int(end)+1): 
                    yield str(i).zfill(le)
            else: yield s
        else: yield from s
    
    @staticmethod
    def time_period(t):
        tl = '12:00', '16:00'
        for n, time in enumerate(tl):
            if t < time: return n
        return 2
        # 0 -> beforenoon, 1 -> afternoon, 2 -> evening
   
    def occupy_time(self, registered):
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
            
            day = subject['teach_day']
            start_time = subject['teach_time'][:5]
            period = time_period(start_time)
            k['teach'][(day, period)] = id, sec
            
        return k  
    
    def check_overlap(self, datalist, seq):
        time_period = self.time_period
        occ = self.occ
        
        def sub(subject):
            for s in 'mexam', 'exam':
                date = subject[s+'_date']
                period = time_period(subject[s+'_time'])
                l = date, period
                if l in occ[s]:
                    return occ[s][l]
            
            day = subject['teach_day']
            period = time_period(subject['teach_time'])
            l = day, period
            if l in occ['teach']:
                return occ['teach'][l]
        
        this_subject = datalist[seq]
        this_id = this_subject['subject_id']
        check1 = sub(this_subject)
        if check1: return check1
        else:
            pack_sec = this_subject['sec_pair']
            if pack_sec is not None:
                for subject in datalist:
                    if subject['section'] == pack_sec:
                        check2 = sub(subject)
                        if check2: return check2
                        break
                else:
                    print(f"can't find sec: {pack_sec} in subject: {this_id}")
    
    def main(self, id, session):
        url = 'https://k8s.reg.kmitl.ac.th/reg/api/?function=get-can-register-by-student-id-and-subject-id'\
            f'&subject_id={id}&student_id={self.student_id}&year={self.year}&semester={self.semester}'
        
        with session.get(url) as res:
            rawdata = json.loads(res.text)
            error = rawdata['error']
        
        if error is None:
            for n, subject in enumerate(rawdata['data']):
                eng_name = subject["subject_ename"]
                count = subject['COUNT']
                limit = subject['LIMIT'] if subject['LIMIT'] != 0 else 'NoLimit'
                sec = subject['section']
                
                is_lap = self.check_overlap(rawdata['data'], n)
                log(f'{id}: __ {eng_name} __({sec})', end= ' ')
                if isinstance(count, str) and 'Full' in count:
                    print(
                        f'Full! [{limit}]'
                        )
                elif is_lap: 
                    print(
                        f'Overlap! [{count}/{limit}]: {is_lap[0]} ({is_lap[1]})'
                        )
                else:
                    print(
                        f'Open! [{count}/{limit}]'
                        )
                
                if self.csv: 
                    self.writer(self.csv.format(subject))
        
        else:
            log(id, end=': ')
            Err = error['message_en']                                                                   
            for part, reply in self.errorlist:
                if part in Err: 
                    print(reply)
                    break
            else: print(f'unknow error => {Err}')
    
    def run(self):
        try:
            if self.csv: 
                file = open('data_table.csv', 'w')
                self.writer = csv.writer(file).writerow
                self.writer(self.csv.field)

            loginjson = json.dumps({
                'function': 'login-jwt',
                'email': f'{self.student_id}@kmitl.ac.th',
                'password': self.password
                })
            
            with requests.post('https://k8s.reg.kmitl.ac.th/api/user/', data=loginjson, headers=self.common_header | {
                    'Content-Length': str(loginjson.__len__()),
                    'Accept': 'application/json, text/plain, */*',
                    'Content-Type': 'application/json;charset=utf-8'}) as token_res:
                
                q = False
                try:
                    token = json.loads(token_res.text)['token']
                except: 
                    log('student-id or password not correct')
                    q = True
                if q: quit()

            with requests.Session() as session:
                session.headers.update(
                    self.common_header | {
                    'Authorization': f"Bearer {token}",
                    'Accept': '*/*',
                    })   
                my_registered = session.get(
                    'https://k8s.reg.kmitl.ac.th/reg/api/?function=get-regis-result&'
                    f'student_id={self.student_id}&year={self.year}&semester={self.semester}&level_id={self.level}')
                self.registered_data = json.loads(my_registered.text)
                self.occ = self.occupy_time(self.registered_data)    

                strange = self.strange     
                for D1, D2, D3 in self.lookup_id:
                    for d1 in strange(D1):
                        for d2 in strange(D2):
                            for d3 in strange(D3):
                                for order in strange('001-999'): 
                                    subject_id = d1+d2+d3+order
                                    while 1:
                                        try: 
                                            self.main(subject_id, session)
                                        except self.exception as e: 
                                            log(f'Connection Error: {e}')
                                        else: break
        finally:
            if self.csv: file.close()


if __name__ == '__main__':
    id = ''
    password = ''
    mysubject = subjects_detection(id, password, csv=False)
    mysubject.run()
