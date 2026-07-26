import importlib
import os


def test_fernet_falls_back_to_secret_key(monkeypatch) -> None:
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("SECRET_KEY", "demo-secret")

    import backend.auth as auth_module

    reloaded = importlib.reload(auth_module)
    fernet = reloaded.get_fernet()
    token = fernet.encrypt(b"hello")

    assert fernet.decrypt(token) == b"hello"
