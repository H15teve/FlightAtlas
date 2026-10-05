"""Read-only dependency check for a local runtime."""
import importlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine'))
from fonts import font_path
missing=[]
for module in ['PIL','openpyxl','xlrd','defusedxml','airportsdata','pyecharts','tzdata']:
    try:importlib.import_module(module)
    except ImportError:missing.append(module)
try:font=font_path()
except ValueError as e:font=str(e);missing.append('CJK font')
print(json.dumps({'python':sys.version.split()[0],'missing':missing,'font':font},ensure_ascii=False))
sys.exit(1 if missing else 0)
