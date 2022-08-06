import requests, json, csv
from time import *

#######################################################
year = 2565
semester = 1
level = 1
# for login & check table
studentid = 
password = ''

# for better lookup
look_subject_id = (
    # ('01-89', '01-99', '1-9'),
    # ('91-99', '01-99', '1-9'),
    ('01', '07', '6'),
    ('90', ('64','59','57'), '1-5'),
    )
# ------ example ------ (No. run from 001 to 999 or break on condition)
# 01 07 6 xxx -> CE
# maingroup branch degree No.
# 
# 90 64 5 xxx -> gen-ed
# maingroup year group No.


# for save as csv file
save_csv = False

#######################################################                
errorlist = [
    ('not in the course schedule', 'Not open yet'),
    ('not pass rule in the course', 'Not pass rule'),
    ('not still registered subject (Prerequisite)', 'require precourse'),
    ('Not found', 'Empty'),
    ('', ''),
    ]
sameheader = {
    'Accept-Language': 'en-us',
    'Host': 'k8s.reg.kmitl.ac.th',
    'Referer': 'https://new.reg.kmitl.ac.th/',
    'Origin': 'https://new.reg.kmitl.ac.th',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive'
    }
day = [None, 'อาทิตย์', 'จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์']
field = ['subject id', 'section', 'sec pair', 'credit', 'type', 'limit', 'count', 'time', 'mid exam', 'late exam']

def log(*s, t=None, end='\n', sep=' '):
    a = ''
    if t is None: t = strftime("%X")
    elif t == False:
        t = ''
        a = ' '*4 +'-'
    print('%-8s'%t, a, *s, end=end, sep=sep)

def strange(s):
    if isinstance(s, str):
        if '-' in s:
            start, end = s.split('-')
            le = len(start)
            for i in range(int(start), int(end)+1): 
                yield str(i).zfill(le)
        else: yield s
    else: yield from s
    
def csvfomat1(data):
    k = [data[q] for q in field[:4]]
    k.extend([
        ('ปฏิบัติ', 'ทฤษฎี')[data['lect_or_prac'] == 'ท'],
        (data['LIMIT'], '-')[data['LIMIT'] == '0'],
        (data['COUNT'], 'Full')['Full' in data['COUNT']],
        ])
    
    date = f"{day[int(data['teach_day'])]} {data['teach_time'][:5]}-{data['teach_time2'][:5]}"
    if 'x' in data['teachtime_str']:
        day, teach_time = data['teachtime_str'].split('x')
        if day == data['teach_day']:
            date += f", {teach_time}"
        else:
            date += f", {day[int(day)]} {teach_time}"
    k.append(date)
    
    for s in 'mexam', 'exam':
        if data[s+'_date'] == '0000-00-00': 
            k.append('จัดสอบเอง')
        else: 
            k.append(f"{data[s+'_date']} {data[s+'_time'][:5]}-{data[s+'_time2'][:5]}")
        
    return k

def time_period(t):
    tl = '12:00', '16:00'
    for n, time in enumerate(tl):
        if t < time: return n
    return 2
# 0 -> beforenoon, 1 -> afternoon, 2 -> evening

def occupy_time(data):
    k = {'mexam':{}, 'teach':{}, 'exam':{}}
    for subject in data:
        id = subject['subject_id']
        sec = subject['section']
        for s in 'mexam', 'exam':
            date = subject[s+'_date']
            if date != '0000-00-00': 
                period = time_period(subject[s+'_time'])
                k[s][(date, period)] = id, sec
        
        day = subject['teach_day']
        period = time_period(subject['teach_time'])
        k['teach'][(day, period)] = id, sec
        
    return k
    

if __name__ == '__main__':
    with requests.Session() as session:
        if save_csv: 
            file = open('data_table.csv', 'w')
            writer = csv.writer(file)
            writer(field)
            
        loginauth = json.dumps({
            'function': 'login-jwt',
            'email': f'{studentid}@kmitl.ac.th',
            'password': password
            })
        
        token_res = requests.post(
            'https://k8s.reg.kmitl.ac.th/api/user/', 
            data=loginauth,
            headers= sameheader | {
                'Content-Length': str(loginauth.__len__()),
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json;charset=utf-8',
                }
            )

        session.headers.update(
            sameheader | {
            'Authorization': f"Bearer {json.loads(token_res.text)['token']}",
            'Accept': '*/*',
            })
        
        mytable = session.get(
            'https://k8s.reg.kmitl.ac.th/reg/api/?function=get-regis-result&'
            f'student_id={studentid}&year={year}&semester={semester}&level_id={level}')
        table = json.loads(mytable.text)
        occ = occupy_time(table)
        
        def check_overlap(datalist, seq):
            def sub(subject):
                for s in 'mexam', 'exam':
                    date = subject[s+'_date']
                    period = time_period(subject[s+'_time'])
                    if (date, period) in occ[s]:
                        return occ[s][(date, period)]
                
                day = subject['teach_day']
                period = time_period(subject['teach_time'])
                if (day, period) in occ['teach']:
                    return occ['teach'][(day, period)]
            
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
                        
        
        def main(id):
            res = session.get(
                'https://k8s.reg.kmitl.ac.th/reg/api/?function=get-can-register-by-student-id-and-subject-id'
                f'&subject_id={id}&student_id={studentid}&year={year}&semester={semester}'
                )
            rawdata = json.loads(res.text)
            try: error = rawdata['error']
            except KeyError as e:
                print(e, rawdata, sep='\n')
                quit()
            
            if error == None:
                for n, subject in enumerate(rawdata['data']):
                    log(id, end=': ')
                    eng_name = subject["subject_ename"]
                    count = subject['COUNT']
                    limit = subject['LIMIT'] if subject['LIMIT'] != 0 else 'infinite'
                    sec = subject['section']
                    is_lap = check_overlap(rawdata['data'], n)
                    
                    
                    if isinstance(count, str) and 'Full' in count:
                        print(
                            f'__{eng_name}__ ({sec}) Full'
                            )
                    elif is_lap: 
                        print(
                            f'__{eng_name}__ ({sec}) overlap schedule'
                            )
                    else:
                        print(
                            f'__{eng_name}__ ({sec}) available {count}/{limit}'
                            )
                    if save_csv: 
                        writer(csvfomat1(subject))
                
            else:
                log(id, end=': ')
                Err = error['message_en']                                                                   
                for part, reply in errorlist:
                    if part in Err: 
                        print(reply)
                        if part == 'Not found': 
                            raise StopIteration
                        break
                else: print('unknow => ', subject, end='\n\n')
            
            
        for D1, D2, D3 in look_subject_id:
            for d1 in strange(D1):
                for d2 in strange(D2):
                    for d3 in strange(D3):
                        count = 0
                        for order in strange('001-999'): 
                            subject_id = d1+d2+d3+order
                            try: 
                                main(subject_id)
                                sleep(0.5) 
                            except StopIteration: 
                                count += 1
                                if count > 5: break
                            except requests.exceptions.ConnectTimeout:
                                continue
                                                            
        if save_csv: file.close()
