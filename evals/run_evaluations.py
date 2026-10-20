import json
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app import create_app

cases=json.loads((Path(__file__).parent/'fixtures/cases.json').read_text(encoding='utf-8'))
with tempfile.TemporaryDirectory() as tmp:
    client=create_app({'TESTING':True,'DATABASE_URL':f"sqlite:///{Path(tmp)/'eval.db'}"}).test_client()
    outcomes=[]
    for case in cases:
        if case['name']=='unsupported tool':
            response=client.post('/api/v1/workflows',json={'plan':{'steps':[{'id':'s1','tool_id':case['tool']}]}})
            actual='rejected' if response.status_code==400 else 'accepted'
            expected=case['expected']
        else:
            response=client.post(f"/api/v1/templates/{case['template']}/run",json=case['input'])
            actual=response.json['workflow']['status'] if case['template']=='support' else response.json['workflow']['steps'][-1]['result']['missing']
            expected=case.get('expected_status',case.get('expected_missing'))
        ok=actual==expected;outcomes.append(ok)
        print(f"{'PASS' if ok else 'FAIL'} {case['name']}: expected={expected!r} actual={actual!r}")
    # Close SQLite handles before TemporaryDirectory removes the database on Windows.
    client.application.extensions['db_engine'].dispose()
passed=sum(outcomes);print(json.dumps({'cases':len(cases),'passed':passed,'pass_rate':passed/len(cases) if cases else 0},indent=2))
raise SystemExit(0 if passed==len(cases) else 1)
