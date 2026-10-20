def test_three_templates_and_approval_resume(client):
    support=client.post('/api/v1/templates/support/run',json={'subject':'Billing issue','description':'Duplicate charge on invoice.'})
    assert support.status_code==201
    sw=support.json['workflow'];assert sw['status']=='waiting_approval'
    approval=sw['approvals'][0]
    denied=client.post(f"/api/v1/approvals/{approval['id']}/decision",json={'decision':'approve','payload_hash':'wrong'})
    assert denied.status_code==409
    approved=client.post(f"/api/v1/approvals/{approval['id']}/decision",json={'decision':'approve','payload_hash':approval['payload_hash']})
    assert approved.status_code==200 and approved.json['workflow']['status']=='completed'
    assert approved.json['workflow']['steps'][-1]['result']['confirmed'] is True
    assert client.post('/api/v1/approvals/'+approval['id']+'/decision',json={'decision':'approve','payload_hash':approval['payload_hash']}).status_code==409
    doc=client.post('/api/v1/templates/document/run',json={'text':'vendor: Paper Co\namount: 145','fields':['vendor','amount','date']})
    assert doc.status_code==201 and doc.json['workflow']['status']=='completed'
    assert doc.json['workflow']['steps'][-1]['result']['missing']==['date']
    lead=client.post('/api/v1/templates/lead/run',json={'name':'Avery Chen','company':'Acme Test','interest':'workflow automation','email':'a@example.test'})
    assert lead.status_code==201 and lead.json['workflow']['status']=='waiting_approval'

def test_unknown_tools_are_rejected(client):
    r=client.post('/api/v1/workflows',json={'plan':{'steps':[{'id':'s1','tool_id':'shell.execute'}]}})
    assert r.status_code==400

def test_dashboard_is_persisted_data(client):
    client.post('/api/v1/templates/lead/run',json={'name':'Ada','company':'Example','interest':'test'})
    d=client.get('/api/v1/dashboard').json
    assert d['metrics']['total']==1 and d['metrics']['pending_approvals']==1
