"""ICAO variants belong to editorial families, not ICAO parking categories."""
import re

FAMILIES=[
 ('JS41','Jetstream 41','JS41','AB','prop',19.25),
 ('B737','Boeing 737 NG','B737 B738 B739 B737F','CD','jet',39.47),
 ('B38M','Boeing 737 MAX','B37M B38M B39M B3XM','CD','jet',39.52),
 ('A320','Airbus A320ceo','A318 A319 A320 A321','CD','jet',37.57),
 ('A20N','Airbus A320neo','A19N A20N A21N','CD','jet',37.57),
 ('B752','Boeing 757','B752 B753','CD','long',47.32),
 ('BCS3','Airbus A220','BCS1 BCS3','CD','jet',38.70),
 ('C919','COMAC C919','C919','CD','jet',38.90),
 ('AJ27','COMAC C909 / ARJ21','AJ27 C909 ARJ21','AB','rear',33.46),
 ('E195','Embraer E190','E190 E195','AB','jet',38.65),
 ('E170','Embraer E170','E170 E175','AB','jet',29.90),
 ('E290','Embraer E190-E2','E290 E295','AB','jet',36.24),
 ('DH8D','Dash 8','DH8A DH8B DH8C DH8D','AB','prop',32.84),
 ('AT42','ATR 42','AT42 AT43 AT44 AT45 AT46','AB','prop',22.67),
 ('AT72','ATR 72','AT72 AT73 AT75 AT76','AB','prop',27.17),
 ('BA46','BAe 146','B461 B462 B463 RJ70 RJ85 RJ1H','AB','high',31.00),
 ('CRJ7','Bombardier CRJ700','CRJ7','AB','rear',32.51),
 ('CRJ9','Bombardier CRJ900','CRJ9 CRJX','AB','rear',36.37),
 ('F100','Fokker F100','F100 F70','AB','rear',35.53),
 ('B777','Boeing 777','B772 B773 B77L B77W','EF','wide',73.86),
 ('B787','Boeing 787','B788 B789 B78X','EF','wide',62.81),
 ('A330','Airbus A330','A332 A333','EF','wide',63.66),
 ('A339','Airbus A330neo','A338 A339','EF','wide',63.66),
 ('A340','Airbus A340','A342 A343 A345 A346','EF','wide',63.69),
 ('B767','Boeing 767','B762 B763 B764','EF','wide',54.94),
 ('A350','Airbus A350','A359 A35K','EF','wide',66.80),
 ('B747','Boeing 747','B741 B742 B743 B744 B748','EF','jumbo',70.66),
 ('A380','Airbus A380','A388','EF','double',72.72),
]
SHORT={'B737':'B737-700','B738':'B737-800','B739':'B737-900','B737F':'B737','B37M':'B737 MAX 7','B38M':'B737 MAX 8','B39M':'B737 MAX 9','B3XM':'B737 MAX 10','A318':'A318','A319':'A319','A320':'A320','A321':'A321','A19N':'A319neo','A20N':'A320neo','A21N':'A321neo','B752':'B757-200','B753':'B757-300','BCS1':'A220-100','BCS3':'A220-300','C919':'C919','AJ27':'C909','E170':'E170','E175':'E175','E190':'E190','E195':'E195','E290':'E190-E2','E295':'E195-E2','DH8D':'Dash 8-Q400','DH8A':'Dash 8-100','DH8B':'Dash 8-200','DH8C':'Dash 8-300','JS41':'J41','B772':'B777-200','B773':'B777-300','B77L':'B777-200LR','B77W':'B777-300ER','B788':'B787-8','B789':'B787-9','B78X':'B787-10','A332':'A330-200','A333':'A330-300','A338':'A330-800','A339':'A330-900','A342':'A340-200','A343':'A340-300','A345':'A340-500','A346':'A340-600','A359':'A350-900','A35K':'A350-1000','B762':'B767-200','B763':'B767-300','B764':'B767-400','B741':'B747-100','B742':'B747-200','B743':'B747-300','B744':'B747-400','B748':'B747-8','A388':'A380-800','AT42':'ATR 42','AT43':'ATR 42-300','AT45':'ATR 42-500','AT46':'ATR 42-600','AT72':'ATR 72','AT73':'ATR 72-200','AT75':'ATR 72-500','AT76':'ATR 72-600','B461':'BAe 146-100','B462':'BAe 146-200','B463':'BAe 146-300','RJ70':'Avro RJ70','RJ85':'Avro RJ85','RJ1H':'Avro RJ100','CRJ7':'CRJ700','CRJ9':'CRJ900','CRJX':'CRJ1000','F100':'F100','F70':'F70'}
GENERIC={'B737MAX':'B737MAXF','B777':'B777F','B787':'B787F','B747':'B747F','B767':'B767F','A330':'A330F','A330NEO':'A330NEOF','A340':'A340F','A350':'A350F','BAE146':'BA46F','DASH8':'DH8F'}
GENERIC_FAMILY={'B737MAXF':'B38M','B777F':'B777','B787F':'B787','B747F':'B747','B767F':'B767','A330F':'A330','A330NEOF':'A339','A340F':'A340','A350F':'A350','BA46F':'BA46','DH8F':'DH8D'}
for generic,family in GENERIC_FAMILY.items():
    FAMILIES=[(k,t,c+' '+generic if k==family else c,g,kind,length) for k,t,c,g,kind,length in FAMILIES]
    SHORT[generic]=next(name for name,code in GENERIC.items() if code==generic)+'（子型号未记录）'
CODE_FAMILY={c:f for f in FAMILIES for c in f[2].split()}
MAINSTREAM={'B737':'B738','B38M':'B38M','A320':'A320','A20N':'A20N','B777':'B77W','B787':'B789','A350':'A359','B747':'B744','A330':'A333','A339':'A339'}
# Approximate overall lengths for editorial sizing, not engineering measurements.
VARIANT_LENGTHS={'E170':29.90,'E175':31.68,'E190':36.24,'E195':38.65,'E290':36.24,'E295':41.60,'DH8A':22.25,'DH8B':22.25,'DH8C':25.68,'DH8D':32.84,'BCS1':35.00,'BCS3':38.70,'B752':47.32,'B753':54.47,'A342':59.40,'A343':63.69,'A345':67.93,'A346':75.36,'B762':48.51,'B763':54.94,'B764':61.37,'B461':26.19,'B462':28.55,'B463':31.00,'RJ70':26.19,'RJ85':28.55,'RJ1H':31.00,'CRJ7':32.51,'CRJ9':36.37,'CRJX':39.13,'F70':30.91,'F100':35.53}
def representative(key,parts):
    family=next(f for f in FAMILIES if f[0]==key)
    code=MAINSTREAM.get(key) or sorted(parts,key=lambda p:(-p[1],p[0]))[0][0]
    length=family[5] if key in MAINSTREAM else VARIANT_LENGTHS.get(code,family[5])
    return {'code':code,'length_m':length,'selection':'user-template mainstream' if key in MAINSTREAM else 'most-flown observed subtype; deterministic ties','art':'fixed family profile, approximate scaling; subtype-specific doors/wings not redrawn'}
ALIASES={re.sub('[^A-Z0-9]','',v.upper()):k for k,v in SHORT.items()}
ALIASES.update({re.sub('[^A-Z0-9]','',v.upper())[1:]:k for k,v in SHORT.items() if v.startswith('B7')})
ALIASES.update(GENERIC)
ALIASES.update({'737':'B737F','BOEING737':'B737F','波音737':'B737F','320':'A320','319':'A319','321':'A321','738':'B738','739':'B739','737800':'B738','737700':'B737','A330900NEO':'A339','Q400':'DH8D','DASH8Q400':'DH8D','ARJ21':'AJ27','C909':'AJ27'})
ALIASES.update({'B737NG':'B737F','737NG':'B737F','737MAX':'B737MAXF','7378MAX':'B38M','B7378MAX':'B38M'})
def normalize_model(value):
    raw=str(value or '').strip().upper();s=re.sub('[^A-Z0-9]','',raw)
    if raw in ['', '-', '—', '--', 'NONE', 'NAN']:return '未记录'
    if raw in CODE_FAMILY:return raw
    for prefix in ['AIRBUS','BOEING','EMBRAER','BOMBARDIER','FOKKER','ATR','空客','波音']:s=s.removeprefix(prefix)
    if s in CODE_FAMILY:return s
    if s in ALIASES:return ALIASES[s]
    # Umetrip uses a slash between family and manufacturer variant. Parenthetic
    # engine/customer/winglet descriptors are not additional aircraft families.
    if m:=re.fullmatch(r'(?:A)?(318|319|320|321|330|340|350|380|220)/([0-9]{3,4})(.*)',raw):
        family,variant,suffix=m.groups();full='A'+family+variant
        if family in ['319','320','321']:
            if re.fullmatch(r'\(N\)(?:\(X\))?|\(NX\)',suffix):return {'319':'A19N','320':'A20N','321':'A21N'}[family]
            if suffix in ['', '(SL)'] and variant[0] in '12':return 'A'+family
        if family=='220' and suffix=='':return {'100':'BCS1','300':'BCS3'}.get(variant,raw)
        if suffix in ['', '(X)']:return normalize_model(full)
    if m:=re.fullmatch(r'B?(737|747|757|767|777|787)/([0-9][0-9A-Z]{2})(.*)',raw):
        family,variant,suffix=m.groups()
        if suffix not in ['', '(WL)', '(ER)', '(LR)', '(PCF)']:return raw
        digit=variant[0]
        if family=='777':
            return {('2','(LR)'):'B77L',('3','(ER)'):'B77W'}.get((digit,suffix),{'2':'B772','3':'B773'}.get(digit,raw))
        return {'737':{'7':'B737','8':'B738','9':'B739'},'747':{'1':'B741','2':'B742','3':'B743','4':'B744','8':'B748'},'757':{'2':'B752','3':'B753'},'767':{'2':'B762','3':'B763','4':'B764'},'787':{'8':'B788','9':'B789','1':'B78X'}}.get(family,{}).get(digit,raw)
    if raw in ['DHC/8','DHC-8']:return 'DH8F'
    if s in ['BAEJETSTREAM41','JETSTREAM41']:return 'JS41'
    if re.fullmatch(r'ERJ195(?:\(LR\))?',raw):return 'E195'
    if re.fullmatch(r'C919/700(?:ER)?',raw):return 'C919'
    if s=='330':return 'A330F'
    if m:=re.fullmatch(r'B?767([234])[0-9A-Z]{2}(?:ER)?',s):return {'2':'B762','3':'B763','4':'B764'}[m[1]]
    if m:=re.fullmatch(r'B?737([789])[0-9A-Z]{2}',s):return {'7':'B737','8':'B738','9':'B739'}[m[1]]
    if re.fullmatch(r'A3(18|19|20|21)[12]\d{2}',s):return 'A'+s[1:4]
    if re.fullmatch(r'A3(19|20|21)2\d{2}N',s):return {'A319':'A19N','A320':'A20N','A321':'A21N'}[s[:4]]
    for prefix,code in [('A3302','A332'),('A3303','A333'),('A3308','A338'),('A3309','A339'),('A3509','A359'),('A35010','A35K'),('A3402','A342'),('A3403','A343'),('A3405','A345'),('A3406','A346')]:
        if re.fullmatch(prefix+r'\d{2}',s):return code
    if s in ['42','72']:return 'AT'+s
    return raw or '未记录'
def manufacturer(code):
    family=CODE_FAMILY.get(code)
    if not family:return '未记录'
    if family[0]=='BCS3' or family[0].startswith('A3') or family[0] in ['A320','A20N']:return 'Airbus'
    return {'JS41':'British Aerospace','BA46':'British Aerospace','AJ27':'COMAC','C919':'COMAC','E195':'Embraer','E170':'Embraer','E290':'Embraer','DH8D':'Bombardier','CRJ7':'Bombardier','CRJ9':'Bombardier','AT42':'ATR','AT72':'ATR','F100':'Fokker'}.get(family[0],'Boeing')
