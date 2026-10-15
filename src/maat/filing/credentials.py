"""E-file credential management.

SETUP FLOW (for the user, once per court):
    1. Run:  maat creds setup --court <court-id>
             (e.g. --court in-odyssey, --court insd-cmecf)
       For a payment method:  maat creds setup-payment --id <method-id>
    2. Credentials are entered via getpass (no echo, never displayed).
    3. The tool stores them encrypted; at e-file time the filing pipeline
       looks up the right credentials for the target court automatically.

STORAGE CHOICE (and why):
    - First: the system keyring via the `keyring` library (macOS Keychain,
      Windows Credential Manager, Linux Secret Service). The OS vault is
      the right home for secrets when it exists.
    - Fallback (headless Linux with no working keyring backend): a
      Fernet-encrypted JSON file at ~/.config/house-of-maat/credentials.enc
      (directory 0700, file 0600). The encryption key comes from the
      MAAT_CREDENTIALS_KEY environment variable (a Fernet key) or from a
      setup-time passphrase (PBKDF2-HMAC-SHA256, 600k iterations, random
      salt stored in the file header). The key is NEVER written next to
      the file.
    Fernet is authenticated encryption (tampering is detected), which is
    why it is the fallback instead of any home-rolled scheme. A probe
    round-trip decides which backend is used; the file backend is only a
    fallback, never a silent downgrade from a working keyring.

WHAT IS STORED:
    - Per court_id: {"username": <reference in cleartext>, "secret": <encrypted>}
      court_id examples: "in-odyssey" (Indiana Tyler/Odyssey e-filing),
      "insd-cmecf", "innd-cmecf".
    - Per payment method id: {"label": ..., "ref_type": ..., "reference": <encrypted>}
      The reference is a PORTAL TOKEN or masked identifier (e.g. last-4) —
      NEVER a full card number. This tool has no PCI scope and will refuse
      to store anything that looks like a PAN (13-19 digits). Tyler/Odyssey
      and CM/ECF collect fees inside their own portals; the tool passes the
      filer's stored payment reference and displays the exact verified fee,
      then waits for the user's explicit confirmation (GATE 2).

SECURITY RULES:
    - NEVER hardcode credentials — not in code, not in tests, not in docs,
      not in example configs.
    - Tests use FAKE credentials ("testuser"/"fakepass") and MUST point the
      store at a tmp dir (CredentialStore(store_dir=tmp_path)); they never
      touch the real location.
    - Secrets are never printed, logged, or included in error messages.
"""

from __future__ import annotations

import base64
import getpass
import json
import os
import re
import secrets
from pathlib import Path

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class CredentialError(Exception):
    """Raised for any credential-store problem (missing key, bad passphrase,
    missing entry). Messages never include secret values."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SERVICE_NAME = "house-of-maat"
STORE_DIR_DEFAULT = Path.home() / ".config" / "house-of-maat"
STORE_FILENAME = "credentials.enc"
ENV_KEY_VAR = "MAAT_CREDENTIALS_KEY"
ENV_BACKEND_VAR = "MAAT_CREDENTIALS_BACKEND"  # "keyring" | "file" (testing/override)
ENV_DIR_VAR = "MAAT_CREDENTIALS_DIR"  # override store dir (testing)
KDF_ITERATIONS = 600_000

_PAN_RE = re.compile(r"^\d{13,19}$")


def _looks_like_pan(value: str) -> bool:
    digits = re.sub(r"[\s\-]", "", value or "")
    return bool(_PAN_RE.match(digits))


# ---------------------------------------------------------------------------
# Backend probing
# ---------------------------------------------------------------------------


def keyring_usable() -> bool:
    """True when the system keyring can actually store and return a secret."""
    try:
        import keyring

        probe_service = SERVICE_NAME + "-probe"
        probe_user = "probe"
        probe_value = secrets.token_hex(16)
        keyring.set_password(probe_service, probe_user, probe_value)
        try:
            ok = keyring.get_password(probe_service, probe_user) == probe_value
        finally:
            try:
                keyring.delete_password(probe_service, probe_user)
            except Exception:
                pass
        return bool(ok)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Fernet file backend
# ---------------------------------------------------------------------------


def _fernet_from_env_or_passphrase(passphrase: str | None = None):
    """Build a Fernet instance from MAAT_CREDENTIALS_KEY or a passphrase."""
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    raw = os.environ.get(ENV_KEY_VAR)
    if raw:
        try:
            return Fernet(raw.encode()), {"kdf": "none"}
        except Exception as exc:
            raise CredentialError(
                f"{ENV_KEY_VAR} is set but is not a valid Fernet key."
            ) from exc
    if passphrase is None:
        raise CredentialError(
            f"No {ENV_KEY_VAR} set and no passphrase provided. Set "
            f"{ENV_KEY_VAR} to a Fernet key or run setup interactively."
        )
    # Caller supplies salt on load; on fresh setup we generate one.
    return None, {"kdf": "pbkdf2-sha256", "iterations": KDF_ITERATIONS}


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))


class _FileBackend:
    """Fernet-encrypted JSON store. Used only when no keyring works."""

    def __init__(self, store_dir: Path):
        self.store_dir = Path(store_dir)
        self.path = self.store_dir / STORE_FILENAME
        self._fernet = None
        self._header: dict = {}

    # -- key management ----------------------------------------------------
    def _load_or_init(self, passphrase: str | None = None):
        from cryptography.fernet import Fernet, InvalidToken

        if self._fernet is not None:
            return
        if self.path.exists():
            envelope = json.loads(self.path.read_text())
            self._header = envelope.get("header", {})
            if self._header.get("kdf") == "none":
                fernet, _ = _fernet_from_env_or_passphrase()
                self._fernet = fernet
            else:
                salt = base64.b64decode(self._header["salt"])
                pw = passphrase or _prompt_passphrase(confirm=False)
                self._fernet = Fernet(_derive_key(pw, salt))
            # Validate the key immediately so a wrong key/passphrase fails
            # here instead of deep inside a decrypt.
            try:
                self._fernet.decrypt(envelope["data"].encode())
            except InvalidToken as exc:
                raise CredentialError(
                    "Could not decrypt the credential store — wrong "
                    f"{ENV_KEY_VAR} or passphrase."
                ) from exc
        else:
            self.store_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(self.store_dir, 0o700)
            raw = os.environ.get(ENV_KEY_VAR)
            if raw:
                fernet, header = _fernet_from_env_or_passphrase()
                self._fernet, self._header = fernet, header
            else:
                pw = passphrase or _prompt_passphrase(confirm=True)
                salt = secrets.token_bytes(16)
                self._fernet = __import__(
                    "cryptography.fernet", fromlist=["Fernet"]
                ).Fernet(_derive_key(pw, salt))
                self._header = {
                    "kdf": "pbkdf2-sha256",
                    "iterations": KDF_ITERATIONS,
                    "salt": base64.b64encode(salt).decode(),
                }

    def _read_all(self, passphrase: str | None = None) -> dict:
        from cryptography.fernet import InvalidToken

        self._load_or_init(passphrase)
        if not self.path.exists():
            return {"efile": {}, "payment": {}}
        envelope = json.loads(self.path.read_text())
        try:
            raw = self._fernet.decrypt(envelope["data"].encode()).decode()
        except InvalidToken as exc:
            raise CredentialError(
                "Could not decrypt the credential store — wrong "
                f"{ENV_KEY_VAR} or passphrase."
            ) from exc
        data = json.loads(raw)
        data.setdefault("efile", {})
        data.setdefault("payment", {})
        return data

    def _write_all(self, data: dict, passphrase: str | None = None):
        self._load_or_init(passphrase)
        envelope = {
            "header": self._header,
            "data": self._fernet.encrypt(
                json.dumps(data).encode()
            ).decode(),
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(envelope))
        os.chmod(tmp, 0o600)
        tmp.replace(self.path)
        os.chmod(self.path, 0o600)


def _prompt_passphrase(confirm: bool = True) -> str:
    pw = getpass.getpass("Credential store passphrase: ")
    if confirm:
        pw2 = getpass.getpass("Confirm passphrase: ")
        if pw != pw2:
            raise CredentialError("Passphrases did not match.")
    if not pw:
        raise CredentialError("Empty passphrase not allowed.")
    return pw


# ---------------------------------------------------------------------------
# CredentialStore — the public API
# ---------------------------------------------------------------------------


class CredentialStore:
    """Encrypted per-court e-file credentials + payment method references.

    Args:
        store_dir: override the config dir (tests MUST use a tmp dir).
        backend: "keyring" | "file" | None (auto: keyring if usable, else file).
        passphrase: only used with the file backend when no env key is set.
    """

    def __init__(
        self,
        store_dir: Path | str | None = None,
        backend: str | None = None,
        passphrase: str | None = None,
    ):
        env_dir = os.environ.get(ENV_DIR_VAR)
        self.store_dir = Path(store_dir or env_dir or STORE_DIR_DEFAULT)
        self.passphrase = passphrase
        forced = backend or os.environ.get(ENV_BACKEND_VAR)
        if forced == "keyring":
            self.backend_name = "keyring"
        elif forced == "file":
            self.backend_name = "file"
        elif forced:
            raise CredentialError(
                f"Unknown {ENV_BACKEND_VAR}={forced!r} (expected 'keyring' or 'file')."
            )
        else:
            self.backend_name = "keyring" if keyring_usable() else "file"
        self._file = _FileBackend(self.store_dir) if self.backend_name == "file" else None

    # -- e-file credentials -------------------------------------------------
    def set_efile(
        self,
        court_id: str,
        username: str | None = None,
        secret: str | None = None,
    ) -> None:
        """Store (or replace) e-file credentials for a court.

        With username/secret omitted, prompts securely via getpass.
        """
        if username is None:
            username = input(f"E-file username for [{court_id}]: ").strip()
        if secret is None:
            secret = getpass.getpass(f"E-file password/API secret for [{court_id}]: ")
        if not username or not secret:
            raise CredentialError("Username and secret must both be non-empty.")
        if self.backend_name == "keyring":
            import keyring

            keyring.set_password(f"{SERVICE_NAME}:efile:{court_id}", username, secret)
            # Username reference kept in a sidecar so list/get can find it.
            keyring.set_password(f"{SERVICE_NAME}:efile-user:{court_id}", "username", username)
        else:
            data = self._file._read_all(self.passphrase)
            data["efile"][court_id] = {"username": username, "secret": secret}
            self._file._write_all(data, self.passphrase)

    def get_efile(self, court_id: str) -> dict | None:
        """Return {'username': ..., 'secret': ...} or None if not configured."""
        if self.backend_name == "keyring":
            import keyring

            username = keyring.get_password(f"{SERVICE_NAME}:efile-user:{court_id}", "username")
            if not username:
                return None
            secret = keyring.get_password(f"{SERVICE_NAME}:efile:{court_id}", username)
            if secret is None:
                return None
            return {"username": username, "secret": secret}
        data = self._file._read_all(self.passphrase)
        return data["efile"].get(court_id)

    def has_efile(self, court_id: str) -> bool:
        return self.get_efile(court_id) is not None

    def delete_efile(self, court_id: str) -> bool:
        if self.backend_name == "keyring":
            import keyring

            username = keyring.get_password(f"{SERVICE_NAME}:efile-user:{court_id}", "username")
            if not username:
                return False
            for service, user in [
                (f"{SERVICE_NAME}:efile:{court_id}", username),
                (f"{SERVICE_NAME}:efile-user:{court_id}", "username"),
            ]:
                try:
                    keyring.delete_password(service, user)
                except Exception:
                    pass
            return True
        data = self._file._read_all(self.passphrase)
        removed = data["efile"].pop(court_id, None) is not None
        if removed:
            self._file._write_all(data, self.passphrase)
        return removed

    def list_efile(self) -> list[dict]:
        """List configured courts with username references only (no secrets)."""
        if self.backend_name == "keyring":
            # Keyring has no enumeration; report what this process configured.
            # (Documented limitation; the file backend enumerates fully.)
            return [{"note": "keyring backend does not support enumeration"}]
        data = self._file._read_all(self.passphrase)
        return [
            {"court_id": cid, "username": v.get("username")}
            for cid, v in sorted(data["efile"].items())
        ]

    # -- payment methods (references only; never full card numbers) ---------
    def set_payment(
        self,
        method_id: str,
        label: str | None = None,
        reference: str | None = None,
        ref_type: str = "portal-token",
    ) -> None:
        """Store a payment method REFERENCE (portal token / masked id).

        ref_type: "portal-token" (a token the portal issued) or "masked"
        (e.g. last-4). Full card numbers are rejected — this tool has no
        PCI scope.
        """
        if label is None:
            label = input(f"Label for payment method [{method_id}]: ").strip()
        if reference is None:
            reference = getpass.getpass(
                f"Payment reference for [{method_id}] (portal token or masked id, NOT a card number): "
            ).strip()
        if not label or not reference:
            raise CredentialError("Label and reference must both be non-empty.")
        if _looks_like_pan(reference):
            raise CredentialError(
                "That looks like a full card number. This tool stores only "
                "portal tokens or masked references — never card numbers."
            )
        if self.backend_name == "keyring":
            import keyring

            keyring.set_password(
                f"{SERVICE_NAME}:pay:{method_id}",
                "reference",
                json.dumps({"label": label, "ref_type": ref_type, "reference": reference}),
            )
        else:
            data = self._file._read_all(self.passphrase)
            data["payment"][method_id] = {
                "label": label,
                "ref_type": ref_type,
                "reference": reference,
            }
            self._file._write_all(data, self.passphrase)

    def get_payment(self, method_id: str) -> dict | None:
        if self.backend_name == "keyring":
            import keyring

            raw = keyring.get_password(f"{SERVICE_NAME}:pay:{method_id}", "reference")
            return json.loads(raw) if raw else None
        data = self._file._read_all(self.passphrase)
        return data["payment"].get(method_id)

    def list_payment(self) -> list[dict]:
        """List payment methods with labels only (references stay encrypted)."""
        if self.backend_name == "keyring":
            return [{"note": "keyring backend does not support enumeration"}]
        data = self._file._read_all(self.passphrase)
        return [
            {"method_id": mid, "label": v.get("label"), "ref_type": v.get("ref_type")}
            for mid, v in sorted(data["payment"].items())
        ]
