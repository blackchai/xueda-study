import ssl
import sys
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import NullPool

from app.config import Settings, get_settings
from app.database import build_engine
from app.main import create_app
from app.startup import configure_runtime, main


@pytest.mark.asyncio
async def test_cloud_url_keeps_encoded_password_and_verifies_tls():
    engine = build_engine('postgresql://demo:p%40%25%3Aa@ep-test.neon.tech/study?sslmode=require&channel_binding=prefer')
    try:
        assert engine.url.password == 'p@%:a'
        assert engine.url.drivername == 'postgresql+asyncpg'
        assert 'sslmode' not in engine.url.query and 'channel_binding' not in engine.url.query
        _, options = engine.sync_engine.dialect.create_connect_args(engine.url)
        assert options['password'] == 'p@%:a'
        # Exercise the actual engine-to-driver boundary without opening a network connection.
        with patch.object(engine.sync_engine.dialect, 'connect', side_effect=RuntimeError('capture')) as connect:
            with pytest.raises(RuntimeError, match='capture'):
                await engine.connect()
            context = connect.call_args.kwargs['ssl']
            assert isinstance(context, ssl.SSLContext)
            assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
    finally:
        await engine.dispose()


@pytest.mark.parametrize('query', ['sslmode=disable', 'sslmode=prefer', 'channel_binding=require', 'sslmode=invalid', 'sslmode=require&ssl=verify-full'])
def test_insecure_or_unsupported_remote_options_fail_explicitly(query):
    with pytest.raises(ValueError):
        build_engine('postgresql+asyncpg://demo:example@db.example/study?' + query)


def test_migrations_reject_neon_transaction_pooler():
    with pytest.raises(ValueError, match='direct database URL'):
        build_engine('postgresql+asyncpg://demo:example@ep-test-pooler.neon.tech/study?sslmode=require', migrations=True)


@pytest.mark.asyncio
async def test_direct_migration_engine_uses_no_session_pool():
    engine = build_engine('postgresql+asyncpg://demo:example@db.example/study?sslmode=verify-full', migrations=True)
    try:
        assert isinstance(engine.sync_engine.pool, NullPool)
    finally:
        await engine.dispose()


def test_cloud_startup_uses_platform_origin_and_dynamic_port(tmp_path, monkeypatch):
    (tmp_path / 'index.html').write_text('<h1>StudyMate</h1>')
    values = {
        'STUDYMATE_APP_ENV': 'production', 'STUDYMATE_DATABASE_URL': 'postgresql://demo:example@db.example/study?sslmode=require',
        'STUDYMATE_AUTH_SIGNING_SECRET': 'test-only-unique-signing-secret-longer-than-32-bytes',
        'STUDYMATE_AUTH_COOKIE_SECURE': 'true', 'STUDYMATE_FRONTEND_DIST_DIR': str(tmp_path),
        'RENDER_EXTERNAL_URL': 'https://xueda-study.onrender.com', 'PORT': '10000',
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv('STUDYMATE_PUBLIC_ORIGIN', raising=False)
    try:
        with patch('app.startup.command.upgrade') as upgrade, patch('app.startup.os.execvp') as execute:
            main()
        assert get_settings().public_origin == values['RENDER_EXTERNAL_URL']
        upgrade.assert_called_once()
        args = execute.call_args.args[1]
        assert args[:3] == [sys.executable, '-m', 'uvicorn']
        assert args[args.index('--port') + 1] == '10000'
        assert '--no-proxy-headers' in args and '*' not in args
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize('origin', ['http://example.com', 'https://example.com/path', 'https://user@example.com', 'https://example.com?token=value'])
def test_startup_rejects_non_origin_platform_url(monkeypatch, origin):
    monkeypatch.setenv('STUDYMATE_PUBLIC_ORIGIN', origin)
    with pytest.raises(ValueError, match='HTTPS origin'):
        configure_runtime()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_explicit_public_origin_survives_tls_termination_and_ignores_forged_headers():
    app = create_app(Settings(app_env='test', database_url='sqlite+aiosqlite:///:memory:',
                              public_origin='https://xueda-study.onrender.com', cors_origins=''))
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://internal:10000') as client:
            # Missing authentication returns 401 after the legitimate HTTPS origin passes.
            allowed = await client.patch('/api/v1/notifications/read-all', headers={'Origin': 'https://xueda-study.onrender.com'})
            assert allowed.status_code == 401
            denied = await client.patch('/api/v1/notifications/read-all', headers={
                'Origin': 'https://evil.example', 'Host': 'evil.example', 'X-Forwarded-Proto': 'https', 'X-Forwarded-Host': 'evil.example'})
            assert denied.status_code == 403 and denied.json()['code'] == 'CSRF_ORIGIN_REJECTED'
    finally:
        await app.state.engine.dispose()


@pytest.mark.asyncio
async def test_same_service_serves_spa_assets_but_never_fake_api_or_missing_javascript(tmp_path):
    (tmp_path / 'index.html').write_text('<h1>StudyMate routing test</h1>')
    (tmp_path / 'assets').mkdir()
    (tmp_path / 'assets' / 'app-test.js').write_text('window.studymate = true')
    app = create_app(Settings(app_env='production', database_url='postgresql+asyncpg://demo@localhost/study',
                              auth_signing_secret='test-only-unique-secret-longer-than-32-bytes', auth_cookie_secure=True,
                              public_origin='https://xueda-study.onrender.com', frontend_dist_dir=str(tmp_path)))
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='https://xueda-study.onrender.com') as client:
            page = await client.get('/groups/example')
            assert page.status_code == 200 and 'StudyMate' in page.text and page.headers['cache-control'] == 'no-cache'
            asset = await client.get('/assets/app-test.js')
            assert asset.status_code == 200 and 'immutable' in asset.headers['cache-control']
            assert (await client.get('/api/v1/auth/me')).status_code == 401
            assert (await client.put('/api/v1/profiles/00000000-0000-0000-0000-000000000000', json={})).status_code == 404
            assert (await client.post('/api/v1/notifications', json={})).status_code == 405
            assert (await client.head('/dashboard')).status_code == 200
            for path in ['/api', '/api/v1/missing', '/health', '/assets/missing.js', '/api/docs', '/api/openapi.json']:
                assert (await client.get(path)).status_code == 404
    finally:
        await app.state.engine.dispose()
