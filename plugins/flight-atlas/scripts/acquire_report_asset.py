"""Acquire one user-accepted asset into a private directory with rights evidence."""
import argparse,hashlib,ipaddress,json,re,shutil,socket,sys,tempfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request,urlopen,HTTPRedirectHandler,build_opener
from generate_report import _local_asset

MAX_BYTES=20000000

def safe_url(url,allowed):
    parsed=urlparse(url);host=parsed.hostname or ''
    if parsed.scheme!='https' or parsed.username or parsed.password or parsed.port not in [None,443] or host not in allowed:raise ValueError('下载URL必须为用户允许的HTTPS主机，不含登录凭据')
    for info in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(info[4][0]).is_global:raise ValueError('不访问内网/本机素材地址')
    return url

class Redirects(HTTPRedirectHandler):
    def __init__(self,allowed):self.allowed=allowed
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        safe_url(newurl,self.allowed)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def acquire(candidate,out):
    if candidate.get('accepted_by_user') is not True or candidate.get('rights_confirmed') is not True:raise ValueError('下载前须用户采纳候选并确认使用权利；网页内容不能代替用户授权')
    if not all(candidate.get(k) for k in ['kind','id','source','credit','license']):raise ValueError('素材缺少类型、标识、来源、作者或许可')
    if candidate['kind'] not in ['airline_logo','aircraft_photo']:raise ValueError('素材类型无效')
    if not re.fullmatch(r'[A-Za-z0-9_-]{2,40}',candidate['id']):raise ValueError('素材标识不可含路径')
    extension=candidate.get('extension','.svg' if candidate['kind']=='airline_logo' else '.jpg').lower()
    if extension not in (['.svg','.png','.jpg','.jpeg'] if candidate['kind']=='airline_logo' else ['.png','.jpg','.jpeg']):raise ValueError('素材扩展名无效')
    if candidate['kind']=='aircraft_photo' and not all(candidate.get(k) for k in ['registration','msn']):raise ValueError('飞机照片须提供注册号及核验MSN')
    out=Path(out).resolve();target=out/(candidate['id']+extension);proof_file=out/(candidate['id']+'.json')
    if target.exists() or proof_file.exists():raise ValueError('目标已存在；不覆盖已有素材')
    out.mkdir(parents=True,exist_ok=True)
    if candidate.get('local_file'):
        data=Path(candidate['local_file']).read_bytes()
    else:
        allowed=set(candidate.get('allowed_hosts',[]));url=safe_url(candidate.get('download_url',''),allowed)
        opener=build_opener(Redirects(allowed))
        with opener.open(Request(url,headers={'User-Agent':'FlightAtlas/0.1 asset acquisition'}),timeout=30) as response:data=response.read(MAX_BYTES+1)
    if len(data)>MAX_BYTES:raise ValueError('素材超过20MB限制')
    # Validate in a private temporary file before publishing a usable config fragment.
    with tempfile.TemporaryDirectory(prefix='flightatlas-asset-') as work:
        temp=Path(work)/('asset'+extension);temp.write_bytes(data)
        _local_asset(temp,Path(work),candidate['kind']=='airline_logo')
        if extension!='.svg':
            from PIL import Image
            with Image.open(temp) as image:image.verify()
        target.write_bytes(data)
    proof={k:v for k,v in candidate.items() if k not in ['local_file','download_url','allowed_hosts']};proof['sha256']=hashlib.sha256(data).hexdigest()
    if candidate['kind']=='airline_logo':fragment={'logos':{candidate['id']:str(target)},'logo_evidence':{candidate['id']:proof}}
    else:fragment={'photos':[{**proof,'file':str(target)}]}
    proof_file.write_text(json.dumps(fragment,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {'file':str(target),'config_fragment':str(proof_file),'sha256':proof['sha256']}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    result=acquire(json.loads(Path(a.candidate).read_text(encoding='utf-8')),a.output_dir);print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
