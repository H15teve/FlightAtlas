"""Read-only matching of independently researched historical aircraft/schedule evidence."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine'))
from reader import read_flights
from data import adapt
from codeshares import candidates

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--evidence',required=True);p.add_argument('--output',required=True);p.add_argument('--config');p.add_argument('--tolerance',type=int,default=30);a=p.parse_args()
    output=Path(a.output)
    if output.exists():p.error('选择新的候选文件；不覆盖输入或已有文件')
    config=json.loads(Path(a.config).read_text(encoding='utf-8')) if a.config else {}
    rows,_=read_flights(a.input,config.get('column_map'));adapt(rows,config)
    evidence=json.loads(Path(a.evidence).read_text(encoding='utf-8'))
    result={'codeshares':candidates(rows,evidence,a.tolerance),'network':False,'automatic_acceptance':False}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    print(json.dumps({'codeshares':len(result['codeshares']),'candidate_file':str(output),'automatic_acceptance':False}))
if __name__=='__main__':main()
