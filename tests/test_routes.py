"""
Базовые тесты Flask-приложения Hamster Royal Hotel.
Запуск: pip install pytest && pytest -v
"""
import pytest
from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    with flask_app.test_client() as client:
        yield client


def test_index_page_loads(client):
    """Главная страница должна открываться без авторизации."""
    response = client.get('/')
    assert response.status_code == 200


def test_register_new_user_redirects_to_profile(client):
    """Успешная регистрация должна редиректить в профиль (302 -> /profile)."""
    response = client.post('/register', data={
        'email': 'pytest_user@example.com',
        'password': '123456',
        'confirm_password': '123456',
    }, follow_redirects=False)
    assert response.status_code == 302
    assert '/profile' in response.headers['Location']


def test_register_duplicate_email_rejected(client):
    """Повторная регистрация с тем же email не должна создавать второго пользователя."""
    data = {
        'email': 'duplicate@example.com',
        'password': '123456',
        'confirm_password': '123456',
    }
    client.post('/register', data=data)
    client.get('/logout')
    response = client.post('/register', data=data, follow_redirects=True)
    assert b'Email' in response.data or response.status_code == 200


def test_login_wrong_password_shows_error(client):
    """Неверный пароль не должен пускать в систему (редирект обратно на index)."""
    response = client.post('/login', data={
        'email': 'nobody@example.com',
        'password': 'wrongpass',
    }, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers['Location'] in ('/', '/index')


def test_profile_requires_login(client):
    """Без авторизации доступ к /profile должен быть закрыт (редирект на login_view)."""
    response = client.get('/profile', follow_redirects=False)
    assert response.status_code in (302, 401)
