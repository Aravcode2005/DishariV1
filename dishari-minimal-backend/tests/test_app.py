import io
from pathlib import Path

from fastapi.testclient import TestClient

from app import app
from engine import build_review
from gemini import AIError, extract_names

client = TestClient(app)
DEMO = Path(__file__).resolve().parents[1] / 'demo_docs'


def form(files=True):
    fields = {
        "consent": "true", "applicant_type": "owner", "crop_or_activity": "Boro paddy",
        "requested_loan_amount": "40000", "preferred_language": "bn",
    }
    return fields


def images():
    return [
        ('aadhaar', ('aadhaar_front.jpg', (DEMO/'aadhaar_front.jpg').read_bytes(), 'image/jpeg')),
        ('aadhaar', ('aadhaar_back.png', (DEMO/'aadhaar_back.png').read_bytes(), 'image/png')),
        ('bank_passbook', ('passbook.jpg', (DEMO/'passbook.jpg').read_bytes(), 'image/jpeg')),
        ('khatian', ('khatian.png', (DEMO/'khatian.png').read_bytes(), 'image/png')),
    ]


def test_complete_demo(monkeypatch):
    monkeypatch.setenv('AI_MODE', 'demo')
    result = client.post('/api/dishari/v1/documents', data=form(), files=images())
    assert result.status_code == 200, result.text
    data = result.json()
    assert data['analysisOrigin'] == 'sample'
    assert data['reviewRequired'] is True
    assert len(data['mismatches']) == 1
    assert data['mismatches'][0]['likelyOutlier'] == 'khatian'
    assert {row['status'] for row in data['schemes']} == {'cannot_determine'}
    assert data['citizenSummary']['language'] == 'bn'
    assert len(data['extracted']) == 4
    assert [r['doc'] for r in data['extracted']] == ['aadhaar','aadhaar','passbook','khatian']


def test_consent_required():
    fields = form()
    fields['consent'] = 'false'
    assert client.post('/api/dishari/v1/documents', data=fields, files=images()).status_code == 400


def test_all_doc_categories_required():
    files = [f for f in images() if f[0] != 'khatian']
    assert client.post('/api/dishari/v1/documents', data=form(), files=files).status_code == 422


def test_mime_signature_checked():
    files = images()
    files[-1] = ('khatian', ('fake.png', b'not a real png', 'image/png'))
    assert client.post('/api/dishari/v1/documents', data=form(), files=files).status_code == 415


def test_missing_name_no_mismatch():
    docs = [dict(category=c, filename=f'{c}.png') for c in ['aadhaar','bank_passbook','khatian']]
    result = build_review('1','owner','Paddy',40000,[None,None,None],docs,'live')
    assert result['mismatches'] == []
    assert result['schemes'][0]['status'] == 'cannot_determine'


def test_gemini_error_does_not_fake_demo(monkeypatch):
    monkeypatch.setenv('AI_MODE', 'gemini')
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    result = client.post('/api/dishari/v1/documents', data=form(), files=images())
    assert result.status_code == 502
    assert 'GEMINI_API_KEY' in result.json()['detail']


def test_health():
    assert client.get('/health').json()['status'] == 'ok'


def test_gemini_json_parse_using_fake_provider(monkeypatch):
    # Proves API payload and response parser without a real API key/network.
    import json
    import httpx
    from gemini import extract_names

    captured = {}

    def responder(request):
        captured['method'] = request.method
        payload = json.loads(request.content)
        captured['inline_images'] = len([
            p for p in payload['contents'][0]['parts'] if 'inlineData' in p
        ])
        result = {'candidates': [{'content': {'parts': [{'text': json.dumps({
            'names': [{'index': 0, 'name': 'Test Person'}, {'index': 1, 'name': None}]
        })}]}}]}
        return httpx.Response(200, json=result)

    native = httpx.Client

    def fake_client(**kwargs):
        kwargs['transport'] = httpx.MockTransport(responder)
        return native(**kwargs)

    monkeypatch.setattr(httpx, 'Client', fake_client)
    monkeypatch.setenv('GEMINI_API_KEY', 'synthetic-not-real')
    docs = [
        {'category':'aadhaar','mime_type':'image/jpeg','bytes':b'\xff\xd8\xffdummy'},
        {'category':'khatian','mime_type':'image/png','bytes':b'\x89PNG\r\n\x1a\ndummy'},
    ]
    assert extract_names(docs, 'gemini') == ['Test Person', None]
    assert captured == {'method':'POST','inline_images':2}
