import pytest
from fastapi.testclient import TestClient

from llm_guard_proxy.config import get_settings
from llm_guard_proxy.main import create_app


@pytest.fixture
def editor(monkeypatch, tmp_path):
    monkeypatch.setenv('GUARD_ADMIN_ENABLED', 'true')
    monkeypatch.setenv('GUARD_ADMIN_POLICY_PATH', str(tmp_path / 'saved.yaml'))
    monkeypatch.setenv('GUARD_POLICY_PATH', 'permissive')
    get_settings.cache_clear()
    with TestClient(create_app(), base_url='http://127.0.0.1', client=('127.0.0.1', 12345)) as client:
        yield client
    get_settings.cache_clear()


def save(client, state):
    return client.put('/admin/policy', json={k: state[k] for k in ('policy', 'revision')},
                      headers={'x-editor-token': state['token']})


def test_save_applies_persists_and_rejects_stale_edits(editor, monkeypatch):
    state = editor.get('/admin/policy').json()
    assert set(state['templates']) == {'permissive', 'school', 'enterprise', 'coding_agent'}
    state['policy']['terms']['critical'] = ['custom blocked phrase']
    assert save(editor, state).status_code == 200
    assert create_app().state.policy.terms.critical == ['custom blocked phrase']
    assert save(editor, state).status_code == 409

    async def fail_if_called(self, body):
        raise AssertionError('Blocked request must not reach the model')

    monkeypatch.setattr('llm_guard_proxy.clients.upstream.OpenAICompatibleClient.chat_completions', fail_if_called)
    response = editor.post('/v1/chat/completions', json={'model': 'test', 'messages': [
        {'role': 'user', 'content': 'custom blocked phrase'}]})
    assert response.json()['id'].startswith('guard-blocked-')


@pytest.mark.parametrize('invalid', ['regex', 'classifier', 'name'])
def test_invalid_policy_does_not_replace_active_policy(editor, invalid):
    state = editor.get('/admin/policy').json()
    if invalid == 'regex':
        state['policy']['regex']['rules'][0]['pattern'] = '['
    elif invalid == 'classifier':
        state['policy']['stages']['input']['enabled_classifiers'] = ['missing']
    else:
        state['policy']['name'] = ' '
    assert save(editor, state).status_code == 422
    assert editor.get('/admin/policy').json()['revision'] == state['revision']


def test_editor_access_controls(editor, monkeypatch):
    assert editor.get('/admin').status_code == 200
    assert editor.get('/admin', headers={'host': 'evil.example'}).status_code == 403
    assert editor.get('/admin', headers={'origin': 'http://evil.example'}).status_code == 403
    state = editor.get('/admin/policy').json()
    state['token'] = 'wrong'
    assert save(editor, state).status_code == 403
    with TestClient(editor.app, base_url='http://localhost', client=('192.168.1.2', 12345)) as remote:
        assert remote.get('/admin/policy').status_code == 403
    monkeypatch.setenv('GUARD_ADMIN_ENABLED', 'false')
    get_settings.cache_clear()
    assert TestClient(create_app()).get('/admin').status_code == 404


def test_failed_write_keeps_active_policy(editor, monkeypatch):
    state = editor.get('/admin/policy').json()
    state['policy']['name'] = 'unsaved'

    def fail(*args, **kwargs):
        raise OSError('Disk full')

    monkeypatch.setattr('llm_guard_proxy.routes.admin.tempfile.NamedTemporaryFile', fail)
    assert save(editor, state).status_code == 500
    assert editor.get('/admin/policy').json()['revision'] == state['revision']
