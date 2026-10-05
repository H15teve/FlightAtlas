import pytest
from airframe_cards import load_cards


def candidate(**overrides):
    return {'registration':'TEST-ONE','msn':'1234','user_verified':True,
            'delivery_source':'https://example.org/delivery',
            'delivery_date_range':['2019-11-01','2019-11-30'],**overrides}


def data():
    return {'rows':[{'K':'TEST-ONE','Q':'1234','Y':'','N':'B77W','AD':'Example'}]}


def test_month_precision_produces_bounded_age_without_inventing_delivery_day():
    facts,_,_=load_cards(data(),{'age_as_of':'2026-10-08','aircraft_details':[candidate()]})
    fact=facts['TEST-ONE']
    assert fact['delivery_date']==''
    assert fact['age']==6.9 and fact['age_display']=='≈6.9'
    assert fact['age_approximate'] and fact['age_interval']==[6.9,6.9]


@pytest.mark.parametrize('override',[{'user_verified':False},{'msn':'9999'},
    {'delivery_source':''},{'delivery_date_range':['2019-11-30','2019-11-01']},
    {'delivery_date_range':['2027-01-01','2027-01-02']}])
def test_invalid_or_unaccepted_delivery_range_is_rejected(override):
    with pytest.raises(ValueError):
        load_cards(data(),{'age_as_of':'2026-10-08','aircraft_details':[candidate(**override)]})


def test_wider_range_is_shown_as_range_not_an_exact_age():
    facts,_,_=load_cards(data(),{'age_as_of':'2026-10-08','aircraft_details':[
        candidate(delivery_date_range=['2019-08-01','2019-08-31'])]})
    assert facts['TEST-ONE']['age'] is None
    assert facts['TEST-ONE']['age_display']=='7.1–7.2'


def test_status_coverage_is_distinct_from_age_and_card_coverage():
    rows=data();rows['rows']*=2
    _,_,audit=load_cards(rows,{'age_as_of':'2026-10-08','include_repeated':True,'aircraft_status':[{'registration':'TEST-ONE','msn':'1234','source':'synthetic registry','checked_on':'2026-10-01','status':'Active'}]})
    assert audit['coverage']['verified_registrations']==1
    assert audit['age_coverage']['selected_cards_with_age']==0
    assert audit['age_coverage']['selected_cards_missing_age']==['TEST-ONE']


def test_conflicting_delivery_intervals_are_not_overwritten():
    with pytest.raises(ValueError,match='区间不一致'):
        load_cards(data(),{'age_as_of':'2026-10-08','aircraft_details':[candidate(),candidate(delivery_date_range=['2019-10-01','2019-10-31'])]})


@pytest.mark.parametrize('bounds',[['2019-11-01'],['2019-11-01','2019-11-30','2019-12-01'],'2019-11'])
def test_malformed_intervals_rejected(bounds):
    with pytest.raises(ValueError,match='两个日期'):
        load_cards(data(),{'age_as_of':'2026-10-08','aircraft_details':[candidate(delivery_date_range=bounds)]})
