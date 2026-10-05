"""Read-only input assessment before asking about enrichment or rendering."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'engine'))
from reader import read_flights
from data import adapt
from models import CODE_FAMILY
from carriers import apply_carriers,flight_key
from identity import identity_defaults
from report_assets import requirements
from build import stats
import datetime as dt

def assess(source,config=None):
    source=Path(source);before=hashlib.sha256(source.read_bytes()).hexdigest()
    config=config or {}
    rows,import_audit=read_flights(source,config.get('column_map'))
    fields=import_audit['schema']['fields']
    data=adapt(rows,config)
    carrier_audit=apply_carriers(rows,config);data=adapt(rows,config)
    identity=identity_defaults(rows,config.get('report_date',dt.date.today().isoformat()))
    shared=[{'key':flight_key(r),'row':r['row'],'date':r['date'],'exported_flight':r['flight'],'route':[r['_dep'],r['_arr']],'registration':r['registration'],'scheduled_departure':str(r.get('scheduled_departure') or ''),'scheduled_arrival':str(r.get('scheduled_arrival') or ''),'user_verification_required':not bool(r.get('operating_flight'))} for r in rows if r.get('codeshare') is True]
    missing={key:[r['row'] for r in rows if key not in fields or r.get(key) in [None,'','UNKNOWN','未记录']] for key in ['model','registration','delivery','msn','carrier']}
    missing['distance']=[r['row'] for r in rows if r.get('distance') is None or str(r.get('distance')).strip() in {'','-','—'}]
    missing['model']=[r['row'] for r in rows if r.get('model') not in CODE_FAMILY]
    by_row={r['row']:r for r in rows}
    duration=[]
    for n in data['duration']['missing_rows']:
        r=by_row[n]
        duration.append({'row':n,'date':r['date'],'flight':r['flight'],'departure':r['_dep'],'arrival':r['_arr'],'departure_time':str(r.get('departure_time') or ''),'arrival_time':str(r.get('arrival_time') or '')})
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before
    return {'flights':len(rows),'input_sha256':before,'input_unchanged':True,'import':import_audit,'missing_fields':missing,'missing_field_counts':{k:len(v) for k,v in missing.items()},'missing_duration_segments':duration,'duration_complete':data['duration']['complete'],'identity_proposals':identity,'codeshares':shared,'carrier_audit':carrier_audit,'asset_requirements':requirements(data,stats(data),config),'requires_user_decision_before_enrichment':bool(any(missing.values()) or duration or shared or not config.get('identity_confirmed'))}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--output',required=True);p.add_argument('--config');a=p.parse_args()
    output=Path(a.output).resolve()
    if output==Path(a.input).resolve() or output.exists():p.error('选择新的预检JSON路径；不得覆盖输入或已有文件')
    config=json.loads(Path(a.config).read_text(encoding='utf-8')) if a.config else {}
    result=assess(a.input,config)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    print(json.dumps({'flights':result['flights'],'missing_field_counts':result['missing_field_counts'],'missing_duration_segments':result['missing_duration_segments'],'input_unchanged':True},ensure_ascii=False))

if __name__=='__main__':main()
