"""Tests for maat.filing.credentials.

ALL credentials here are FAKE ("testuser"/"fakepass"). The store is always
pointed at a tmp dir — these tests never touch the real credential store.
"""

import json
import os
import stat

import pytest
from cryptography.fernet import Fernet, InvalidToken

from maat.filing.credentials import (
    CredentialStore,
    CredentialError,
    keyring_usable,
    _FileBackend,
)


@pytest.fixture()
def env_key(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("MAAT_CREDENTIALS_KEY", key)
    monkeypatch.delenv("MAAT_CREDENTIALS_BACKEND", raising=False)
    monkeypatch.delenv("MAAT_CREDENTIALS_DIR", raising=False)
    return key


@pytest.fixture()
def store(tmp_path, env_key):
    return CredentialStore(store_dir=tmp_path / "store", backend="file")


def test_efile_roundtrip_fake_credentials(store):
    store.set_efile("in-odyssey", username="testuser", secret="fakepass")
    got = store.get_efile("in-odyssey")
    assert got == {"username": "testuser", "secret": "fakepass"}
    assert store.has_efile("in-odyssey")


def test_efile_missing_returns_none(store):
    assert store.get_efile("nope") is None
    assert not store.has_efile("nope")


def test_secrets_encrypted_at_rest(tmp_path, env_key):
    s = CredentialStore(store_dir=tmp_path / "store", backend="file")
    s.set_efile("in-odyssey", username="testuser", secret="fakepass")
    raw = (tmp_path / "store" / "credentials.enc").read_text()
    assert "fakepass" not in raw  # secret never in cleartext
    assert "testuser" not in raw  # username reference is inside the encrypted payload too


def test_store_file_permissions(tmp_path, env_key):
    s = CredentialStore(store_dir=tmp_path / "store", backend="file")
    s.set_efile("in-odyssey", username="testuser", secret="fakepass")
    mode = stat.S_IMODE(os.stat(tmp_path / "store" / "credentials.enc").st_mode)
    assert mode == 0o600
    dmode = stat.S_IMODE(os.stat(tmp_path / "store").st_mode)
    assert dmode == 0o700


def test_wrong_key_fails(tmp_path, env_key, monkeypatch):
    s = CredentialStore(store_dir=tmp_path / "store", backend="file")
    s.set_efile("in-odyssey", username="testuser", secret="fakepass")
    monkeypatch.setenv("MAAT_CREDENTIALS_KEY", Fernet.generate_key().decode())
    s2 = CredentialStore(store_dir=tmp_path / "store", backend="file")
    with pytest.raises(CredentialError):
        s2.get_efile("in-odyssey")


def test_payment_reference_roundtrip(store):
    store.set_payment("main", label="Test token", reference="tok_test_123", ref_type="portal-token")
    got = store.get_payment("main")
    assert got["label"] == "Test token"
    assert got["reference"] == "tok_test_123"
    assert got["ref_type"] == "portal-token"


def test_payment_rejects_full_card_number(store):
    with pytest.raises(CredentialError):
        store.set_payment("bad", label="Card", reference="4111111111111111")
    with pytest.raises(CredentialError):
        store.set_payment("bad2", label="Card", reference="4111 1111 1111 1111")


def test_list_shows_labels_not_secrets(store):
    store.set_efile("in-odyssey", username="testuser", secret="fakepass")
    store.set_payment("main", label="Test token", reference="tok_test_123")
    efile = store.list_efile()
    assert efile == [{"court_id": "in-odyssey", "username": "testuser"}]
    payment = store.list_payment()
    assert payment == [{"method_id": "main", "label": "Test token", "ref_type": "portal-token"}]
    assert "fakepass" not in json.dumps(efile)
    assert "tok_test_123" not in json.dumps(payment)


def test_delete_efile(store):
    store.set_efile("in-odyssey", username="testuser", secret="fakepass")
    assert store.delete_efile("in-odyssey") is True
    assert not store.has_efile("in-odyssey")
    assert store.delete_efile("in-odyssey") is False


def test_env_dir_override(tmp_path, env_key, monkeypatch):
    monkeypatch.setenv("MAAT_CREDENTIALS_DIR", str(tmp_path / "envstore"))
    s = CredentialStore(backend="file")
    assert s.store_dir == tmp_path / "envstore"


def test_empty_username_rejected(store):
    with pytest.raises(CredentialError):
        store.set_efile("in-odyssey", username="", secret="fakepass")


def test_keyring_probe_does_not_crash():
    # Just exercises the probe; result depends on the machine.
    assert isinstance(keyring_usable(), bool)
