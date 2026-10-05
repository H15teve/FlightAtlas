"""Merge a new CSV into private history without replacing either source."""
import argparse,copy,datetime,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'engine'))
from reader import read_flights
from history import merge,snapshot

def run(args):
    history=Path(args.history).resolve();incoming=Path(args.input).resolve()
    if incoming.suffix.lower() not in ['.csv','.tsv']:raise ValueError('增量主输入需要小横CSV/TSV，APP XLS仅作辅助印证')
    before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in [history,incoming]}
    config={};config_path=None
    if args.config:
        config_path=Path(args.config).resolve();config=json.loads(config_path.read_text(encoding='utf-8'))
        if not isinstance(config,dict):raise ValueError('配置需为JSON对象')
        for field in ['logos','alliance_logos']:
            config[field]={k:str((config_path.parent/v).resolve()) for k,v in config.get(field,{}).items()}
        for photo in config.get('photos',[]):photo['file']=str((config_path.parent/photo['file']).resolve())
        for field in ['signature_svg','tpm_cache']:
            if config.get(field):config[field]=str((config_path.parent/config[field]).resolve())
    existing,old_audit=read_flights(history,config.get('column_map') if history.suffix.lower()!='.json' else None)
    rows,new_audit=read_flights(incoming,config.get('column_map'))
    if not existing:raise ValueError('历史记录为空；首次生成请使用完整CSV')
    decisions=[];decision_path=None
    if args.resolutions:
        decision_path=Path(args.resolutions).resolve();value=json.loads(decision_path.read_text(encoding='utf-8'))
        decisions=value.get('decisions') if isinstance(value,dict) else None
        if not isinstance(decisions,list):raise ValueError('决定文件需decisions列表')
    output=Path(args.output).resolve()
    protected=[history,incoming,config_path,decision_path]
    if any(p and (output==p or output in p.parents) for p in protected):raise ValueError('合并输出目录不能包含输入/配置/决定文件')
    if output.exists() and any(output.iterdir()):raise ValueError('合并输出目录非空；请使用新目录')
    merged,audit=merge(existing,rows,config,decisions)
    day=args.report_date;datetime.date.fromisoformat(day)
    audit.update({'history_sha256':before[history],'increment_sha256':before[incoming],'report_date':day,'input_import':new_audit,'sources_unchanged':True})
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==sha for p,sha in before.items())
    output.mkdir(parents=True,exist_ok=True)
    (output/'increment-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    if audit['pending_count']:
        print(json.dumps({'status':'needs-review','pending_count':audit['pending_count'],'audit':str(output/'increment-audit.json')},ensure_ascii=False));return 2
    config=copy.deepcopy(config)
    config.update(report_date=day,valid_until=day,age_as_of=day)
    sources=old_audit.get('sources') or [{'sha256':before[history],'records':len(existing),'role':'previous primary source'}]
    sources=[*sources,{'sha256':before[incoming],'records':len(rows),'role':'increment','added_count':audit['added_count']}]
    (output/'flight-history.json').write_text(json.dumps(snapshot(merged,sources),ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'report-config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':'merged',**{k:audit[k] for k in ['previous_count','incoming_count','added_count','duplicate_count','merged_count']},'output':str(output)},ensure_ascii=False))
    return 0

def parser():
    p=argparse.ArgumentParser(description=__doc__)
    for field in ['history','input','output','report-date']:p.add_argument('--'+field,required=True)
    p.add_argument('--config');p.add_argument('--resolutions');return p

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr,'reconfigure'):sys.stderr.reconfigure(encoding='utf-8')
    try:sys.exit(run(parser().parse_args()))
    except (ValueError,OSError) as error:print('FlightAtlas: '+str(error),file=sys.stderr);sys.exit(2)
