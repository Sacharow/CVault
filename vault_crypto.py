import base64
import binascii
import os

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST = 65536
ARGON2_PARALLELISM = 1
KEY_SIZE = 32
SALT_SIZE = 16
NONCE_SIZE = 12


def derive_keys(password, salt=None):
    if not isinstance(password, str) or not password:
        raise ValueError("A non-empty master password is required")
    salt = os.urandom(SALT_SIZE) if salt is None else salt
    if not isinstance(salt, bytes) or len(salt) != SALT_SIZE:
        raise ValueError("The Argon2id salt has an invalid length")
    root_key = hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST,
        parallelism=ARGON2_PARALLELISM,
        hash_len=KEY_SIZE,
        type=Type.ID,
    )
    settings_key = _derive_subkey(root_key, b"cvault settings")
    data_key = _derive_subkey(root_key, b"cvault data")
    return salt, settings_key, data_key


def _derive_subkey(root_key, purpose):
    return HKDF(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=None,
        info=purpose,
    ).derive(root_key)


def encrypt_bytes(plaintext, key):
    nonce = os.urandom(NONCE_SIZE)
    encrypted = AESGCM(key).encrypt(nonce, plaintext, None)
    return base64.b64encode(nonce + encrypted).decode("ascii")


def decrypt_bytes(encoded, key):
    if not isinstance(encoded, str):
        raise ValueError("Encrypted data must be a Base64 string")
    try:
        encrypted = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("Encrypted data is not valid Base64") from error
    if len(encrypted) < NONCE_SIZE + 16:
        raise ValueError("Encrypted data is incomplete")
    try:
        return AESGCM(key).decrypt(encrypted[:NONCE_SIZE], encrypted[NONCE_SIZE:], None)
    except InvalidTag as error:
        raise ValueError("Incorrect master password or encrypted data was modified") from error


def encrypt_text(text, key):
    return encrypt_bytes(text.encode("utf-8"), key)


def decrypt_text(encoded, key):
    try:
        return decrypt_bytes(encoded, key).decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("Decrypted data is not valid UTF-8") from error
