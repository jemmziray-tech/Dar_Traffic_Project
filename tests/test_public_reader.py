from unittest.mock import Mock
import pytest
from firestore_public import PublicTrafficReader


def test_reads_fresh_project_without_old_secrets(monkeypatch):
    response = Mock()
    response.json.return_value = [{'document': {
        'name': 'projects/dar-traffic/databases/(default)/documents/live_traffic/ubungo',
        'fields': {'road_id': {'stringValue': 'ubungo'},
                   'delay_mins': {'doubleValue': 1.25},
                   'timestamp': {'timestampValue': '2026-10-30T19:56:56Z'},
                   'schema_version': {'integerValue': '2'}}}}]
    request = Mock(return_value=response)
    monkeypatch.setattr('firestore_public.requests.post', request)
    monkeypatch.setenv('FIREBASE_KEY_JSON', '{"project_id":"dar-traffic-command"}')
    doc = list(PublicTrafficReader().collection('live_traffic').stream())[0]
    assert doc.id == 'ubungo'
    assert doc.to_dict()['delay_mins'] == 1.25
    assert doc.to_dict()['timestamp'].utcoffset().total_seconds() == 0
    assert request.call_args.args[0].startswith('https://firestore.googleapis.com/v1/projects/dar-traffic/')
    assert 'headers' not in request.call_args.kwargs


def test_query_preserves_filter_order_and_limit(monkeypatch):
    response = Mock()
    response.json.return_value = []
    request = Mock(return_value=response)
    monkeypatch.setattr('firestore_public.requests.post', request)
    query = PublicTrafficReader().collection('traffic_history')
    list(query.where('road_id', '==', 'ubungo').order_by('timestamp', 'DESCENDING').limit(100).stream())
    body = request.call_args.kwargs['json']['structuredQuery']
    assert body['limit'] == 100
    assert body['where']['fieldFilter']['value'] == {'stringValue': 'ubungo'}
    assert body['orderBy'][0]['direction'] == 'DESCENDING'
    assert query.equality is None


def test_reader_has_no_arbitrary_collections_or_write_methods():
    reader = PublicTrafficReader()
    with pytest.raises(ValueError):
        reader.collection('secrets')
    assert not hasattr(reader.collection('live_traffic'), 'add')
    with pytest.raises(ValueError):
        reader.collection('traffic_history').limit(5001)
