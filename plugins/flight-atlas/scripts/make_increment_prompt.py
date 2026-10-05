"""Replace only the extraction prompt's first sentence for a date-range export."""
import argparse,datetime,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TEMPLATE=ROOT/'skills/flight-report/references/extraction-prompt.txt'

def build(start,end):
    a,b=datetime.date.fromisoformat(start),datetime.date.fromisoformat(end)
    if a>b:raise ValueError('起始日期不能晚于结束日期')
    def cn(day):return f'{day.year}年{day.month}月{day.day}日'
    first=f'请导出我在{cn(a)}至{cn(b)}（按出发机场当地出发日期，含起止日期）乘坐过的全部航班，后文的“全部历史行程”和“全量”均仅指此范围，输出为【逗号分隔CSV】，可直接复制保存为 .csv。'
    original=TEMPLATE.read_bytes();line,separator,rest=original.partition(b'\n')
    return first.encode('utf-8')+(b'\r' if line.endswith(b'\r') else b'')+separator+rest

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--from',dest='start',required=True);p.add_argument('--through',dest='end',required=True);p.add_argument('--output',required=True)
    args=p.parse_args();text=build(args.start,args.end);output=Path(args.output).resolve()
    if output.exists():raise ValueError('提示词输出已存在；请选择新文件')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as target:target.write(text)
    print(str(output))

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr,'reconfigure'):sys.stderr.reconfigure(encoding='utf-8')
    try:main()
    except (ValueError,OSError) as error:print('FlightAtlas: '+str(error),file=sys.stderr);sys.exit(2)
