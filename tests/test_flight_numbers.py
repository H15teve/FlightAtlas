from domestic_map import top_flight_numbers,build_map


def test_normalization_missing_and_deterministic_top_three():
    rows=[{'C':n} for n in ['mf 8101','MF8101','MF8101','ca1234','CA1234','HU7001','HU7001','ZH9001','ZH9001','',None,'—','N/A','未知']]
    assert top_flight_numbers(rows)==[
        {'flight_number':'MF8101','flights':3},
        {'flight_number':'CA1234','flights':2},
        {'flight_number':'HU7001','flights':2},
    ]
    assert top_flight_numbers([{}, {'C':''}])==[]
    assert top_flight_numbers([{'C':'AB0001'}])==[{'flight_number':'AB0001','flights':1}]


def test_all_record_scope_independent_of_route_threshold_and_height(tmp_path):
    airports={'PEK':{'country':'CN','lon':116.6,'lat':40.1},'XMN':{'country':'CN','lon':118.1,'lat':24.5},'HND':{'country':'JP','lon':139.8,'lat':35.5}}
    rows=[{'C':'JL001','_dep':'PEK','_arr':'HND'} for _ in range(5)]
    rows += [{ 'C':'MF8101','_dep':'PEK','_arr':'XMN'} for _ in range(3)]
    s=build_map({'rows':rows,'airports':airports},tmp_path,height=100,route_min=4)
    assert s['frequent_routes']==[]
    assert s['top_flight_numbers']==[{'flight_number':'JL001','flights':5},{'flight_number':'MF8101','flights':3}]
    assert s['flight_number_scope']=='all exported records'
    import json
    layout=json.loads((tmp_path/'map_layout.json').read_text())
    assert layout['height']==s['height'] and layout['height']>=layout['ranking_box'][3]+15
