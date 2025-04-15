import os
import atexit
import base64
import shutil
import logging
import secrets
from datetime import datetime, timedelta

import pytest
from nacl.public import PrivateKey

from v2dl.common import EncryptionConfig, SecurityError
from v2dl.security import AccountManager, Encryptor, KeyManager


@pytest.fixture
def encryption_config():
    return EncryptionConfig(
        key_bytes=32,
        salt_bytes=16,
        nonce_bytes=24,
        kdf_ops_limit=2**6,
        kdf_mem_limit=2**13,
    )


@pytest.fixture
def logger():
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.INFO)
    return logger


@pytest.fixture
def encryptor(encryption_config, logger):
    return Encryptor(logger, encryption_config)


def test_master_key_decryption(encryptor: Encryptor):
    master_key = secrets.token_bytes(32)
    encrypted_key, salt, encryption_key = encryptor.encrypt_master_key(master_key)

    decrypted_key = encryptor.decrypt_master_key(
        encrypted_master_key=encrypted_key,
        salt=base64.b64encode(salt).decode("utf-8"),
        encryption_key=base64.b64encode(encryption_key).decode("utf-8"),
    )

    assert decrypted_key == master_key, "master key decryption error"


def test_keypair(encryptor: Encryptor):
    test_message = "test message."

    # 正確的 keypair
    private_key = PrivateKey.generate()
    public_key = private_key.public_key

    encrypted_message = encryptor.encrypt_password(test_message, public_key)
    decrypted_message = encryptor.decrypt_password(encrypted_message, private_key)
    assert decrypted_message == test_message, "message decryption error"

    encryptor.validate_keypair(private_key, public_key)

    # 錯誤私鑰驗證
    wrong_private_key = PrivateKey.generate()
    with pytest.raises(SecurityError):
        encryptor.validate_keypair(wrong_private_key, public_key)

    # 錯誤私鑰解密
    encrypted_password = encryptor.encrypt_password("test_password", wrong_private_key.public_key)
    with pytest.raises(SecurityError):
        encryptor.decrypt_password(encrypted_password, PrivateKey.generate())


@pytest.fixture
def account_manager(encryption_config, logger, tmp_path):
    path_config = {
        "key_folder": str(tmp_path / ".keys"),
        "env_path": str(tmp_path / ".env"),
        "master_key_file": str(tmp_path / ".keys" / "master_key.enc"),
        "private_key_file": str(tmp_path / ".keys" / "private_key.pem"),
        "public_key_file": str(tmp_path / ".keys" / "public_key.pem"),
    }
    yaml_path = str(tmp_path / "accounts.yaml")

    key_manager = KeyManager(logger, encryption_config, path_config)
    account_manager_instance = AccountManager(logger, key_manager, yaml_path)

    yield account_manager_instance

    atexit.unregister(account_manager_instance._save_yaml)
    if os.name != "nt":
        shutil.rmtree(tmp_path)


def test_create_account(account_manager: AccountManager):
    username = "test_user"
    password = "test_password"
    public_key = PrivateKey.generate().public_key

    account_manager.create(username, password, "", public_key)

    account = account_manager.read(username)
    assert account is not None
    assert "encrypted_password" in account
    assert "created_at" in account
    assert account["exceed_quota"] is False
    assert account["exceed_time"] == ""


def test_delete_account(account_manager: AccountManager):
    username = "test_user"
    password = "test_password"
    public_key = PrivateKey.generate().public_key

    account_manager.create(username, password, "", public_key)
    account_manager.delete(username)

    account = account_manager.read(username)
    assert account is None


def test_edit_account(account_manager: AccountManager):
    old_username = "old_user"
    new_username = "new_user"
    new_password = "new_password"
    public_key = PrivateKey.generate().public_key

    account_manager.create(old_username, "old_password", "", public_key)
    account_manager.edit(public_key, old_username, new_username, new_password, None)

    account = account_manager.read(new_username)
    assert account is not None
    assert "encrypted_password" in account
    assert account_manager.read(old_username) is None


def test_update_status(account_manager: AccountManager):
    username = "test_user"
    password = "test_password"
    public_key = PrivateKey.generate().public_key

    account_manager.create(username, password, "", public_key)
    account_manager.update_account(username, "exceed_quota", True)
    account_manager.update_account(
        username,
        "exceed_time",
        datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    )

    account = account_manager.read(username)
    assert account is not None
    assert account["exceed_quota"] is True
    assert account["exceed_time"] != ""


def test_verify_password(account_manager: AccountManager):
    username = "test_user"
    password = "test_password"
    private_key = PrivateKey.generate()
    public_key = private_key.public_key

    account_manager.create(username, password, "", public_key)

    assert account_manager.verify_password(username, password, private_key) is True
    assert account_manager.verify_password(username, "wrong_password", private_key) is False


def test_check(account_manager: AccountManager):
    username = "test_user"
    password = "test_password"
    public_key = PrivateKey.generate().public_key

    account_manager.create(username, password, "", public_key)
    account_manager.update_account(
        username,
        "exceed_time",
        (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
    )
    account_manager.update_account(username, "exceed_quota", True)

    account_manager.check()
    account = account_manager.read(username)
    assert account is not None
    assert account["exceed_quota"] is False
    assert account["exceed_time"] == ""
