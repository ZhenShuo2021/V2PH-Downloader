import os
import sys
import atexit
import base64
import ctypes
import random
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime
from logging import Logger
from typing import Any, Literal, overload

import yaml
from dotenv import load_dotenv, set_key
from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.pwhash import argon2id
from nacl.secret import SecretBox
from nacl.utils import EncryptedMessage, random as nacl_random

from v2dl.common import ConfigManager, EncryptionConfig, SecurityError, cookies


@dataclass
class KeyPair:
    private_key: PrivateKey
    public_key: PublicKey


class Encryptor:
    """Managing encryption and decryption operations."""

    def __init__(self, logger: Logger, encrypt_config: EncryptionConfig) -> None:
        self.logger = logger
        self.encrypt_config = encrypt_config

    def encrypt_master_key(self, master_key: bytes) -> tuple[bytes, bytes, bytes]:
        salt = secrets.token_bytes(self.encrypt_config.salt_bytes)
        encryption_key = secrets.token_bytes(self.encrypt_config.key_bytes)
        derived_key = self.derive_key(encryption_key, salt)

        box = SecretBox(derived_key)
        nonce = nacl_random(self.encrypt_config.nonce_bytes)
        encrypted_master_key = box.encrypt(master_key, nonce)

        derived_key = bytearray(len(derived_key))
        self.logger.info("Master key encryption successful")
        return encrypted_master_key, salt, encryption_key

    def decrypt_master_key(
        self,
        encrypted_master_key: bytes,
        salt: str,
        encryption_key: str,
    ) -> bytes:
        salt_b64 = base64.b64decode(salt)
        enc_key_b64 = base64.b64decode(encryption_key)
        derived_key = self.derive_key(enc_key_b64, salt_b64)
        box = SecretBox(derived_key)

        master_key = box.decrypt(encrypted_master_key)

        self.logger.info("Master key decryption successful")
        return master_key

    def encrypt_private_key(self, private_key: PrivateKey, master_key: bytes) -> EncryptedMessage:
        box = SecretBox(master_key)
        nonce = nacl_random(self.encrypt_config.nonce_bytes)
        return box.encrypt(private_key.encode(), nonce)

    def decrypt_private_key(self, encrypted_private_key: bytes, master_key: bytes) -> PrivateKey:
        box = SecretBox(master_key)
        private_key_bytes = box.decrypt(encrypted_private_key)
        private_key = PrivateKey(private_key_bytes)
        cleanup([private_key_bytes])
        return private_key

    def encrypt_password(self, password: str, public_key: PublicKey) -> str:
        sealed_box = SealedBox(public_key)
        encrypted = sealed_box.encrypt(password.encode())
        self.logger.info("Password encryption successful")
        return base64.b64encode(encrypted).decode("utf-8")

    def decrypt_password(self, encrypted_password: str, private_key: PrivateKey) -> str:
        try:
            encrypted = base64.b64decode(encrypted_password)
            sealed_box = SealedBox(private_key)
            decrypted = sealed_box.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            self.logger.error("Password decryption failed: %s", str(e))
            raise SecurityError from e

    def derive_key(self, encryption_key: bytes, salt: bytes) -> bytes:
        return argon2id.kdf(
            self.encrypt_config.key_bytes,
            encryption_key,
            salt,
            opslimit=self.encrypt_config.kdf_ops_limit,
            memlimit=self.encrypt_config.kdf_mem_limit,
        )

    def validate_keypair(self, private_key: PrivateKey, public_key: PublicKey) -> None:
        try:
            test_data = b"test"
            sealed_box = SealedBox(public_key)
            sealed_box_priv = SealedBox(private_key)

            encrypted = sealed_box.encrypt(test_data)
            decrypted = sealed_box_priv.decrypt(encrypted)

            if decrypted != test_data:
                raise SecurityError
        except Exception as e:
            self.logger.error("Key pair validation failed: %s", str(e))
            raise SecurityError from e


class KeyIOHelper(Encryptor):
    """Manage the loading, saving, and validation of cryptographic keys."""

    def __init__(
        self,
        logger: Logger,
        static_config: dict[str, str] | None,
        encrypt_config: EncryptionConfig,
    ) -> None:
        super().__init__(logger, encrypt_config)
        self.logger = logger
        self.static_config = self.init_conf(static_config)

    def init_conf(self, static_config: dict[str, str] | None) -> dict[str, str]:
        if static_config is None:
            base_dir = ConfigManager.get_system_config_dir()
            self.logger.debug("Initializing config with base directory: %s", base_dir)
            return {
                "key_folder": os.path.join(base_dir, ".keys"),
                "env_path": os.path.join(base_dir, ".env"),
                "master_key_file": os.path.join(base_dir, ".keys", "master_key.enc"),
                "private_key_file": os.path.join(base_dir, ".keys", "private_key.pem"),
                "public_key_file": os.path.join(base_dir, ".keys", "public_key.pem"),
            }
        else:
            return static_config

    def load_keys(self) -> KeyPair:
        self.logger.debug("Loading and validating keys")
        master_key = self.load_master_key()
        private_key = self.load_private_key(master_key)
        public_key = self.load_public_key()

        self.validate_keypair(private_key, public_key)
        cleanup([master_key])

        self.logger.info("Keys loaded and validated successfully")
        return KeyPair(private_key, public_key)

    def load_secret(self, env_path: str) -> tuple[str, str]:
        """Load and validate salt and encryption_key from .env file."""
        load_dotenv(env_path)
        salt_base64 = SecureFileHandler.read_env("SALT")
        encryption_key_base64 = SecureFileHandler.read_env("ENCRYPTION_KEY")
        return salt_base64, encryption_key_base64

    def load_master_key(self, path: str | None = None) -> bytes:
        _path = self.static_config["master_key_file"] if path is None else path
        encrypted_master_key = SecureFileHandler.read_file(_path, False)
        salt, encryption_key = self.load_secret(self.static_config["env_path"])
        return self.decrypt_master_key(encrypted_master_key, salt, encryption_key)

    def load_public_key(self, path: str | None = None) -> PublicKey:
        _path = self.static_config["public_key_file"] if path is None else path
        public_key_bytes = SecureFileHandler.read_file(_path, False)
        return PublicKey(public_key_bytes)

    def load_private_key(self, master_key: bytes, path: str | None = None) -> PrivateKey:
        _path = self.static_config["private_key_file"] if path is None else path
        encrypted_private_key = SecureFileHandler.read_file(_path, False)
        return self.decrypt_private_key(encrypted_private_key, master_key)

    def save_keys(self, keys: tuple[bytes, bytes, PublicKey, bytes, bytes]) -> None:
        SecureFileHandler.write_file(self.static_config["master_key_file"], keys[0])
        SecureFileHandler.write_file(self.static_config["private_key_file"], keys[1])
        SecureFileHandler.write_file(self.static_config["public_key_file"], keys[2].encode(), 0o644)
        SecureFileHandler.write_env(self.static_config["env_path"], "SALT", keys[3])
        SecureFileHandler.write_env(self.static_config["env_path"], "ENCRYPTION_KEY", keys[4])

    def check_folder(self) -> None:
        folder_path = self.static_config["key_folder"]
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, mode=0o700)
            self.logger.info("Secure folder created at %s", folder_path)
        else:
            current_permissions = os.stat(folder_path).st_mode & 0o777
            if current_permissions != 0o700:
                os.chmod(folder_path, 0o700)
                self.logger.info("Permissions updated for folder at %s", folder_path)

    def check_permission(self, folder_path: str) -> bool:
        folder_permission = 0o700
        current_permissions = os.stat(folder_path).st_mode & 0o777
        return current_permissions == folder_permission


class KeyManager(KeyIOHelper):
    """Top level class managing key generation."""

    def __init__(
        self,
        logger: Logger,
        encrypt_config: EncryptionConfig,
        path_dict: dict[str, str] | None = None,
    ) -> None:
        super().__init__(logger, path_dict, encrypt_config)
        self.check_folder()

        keys = self._init_keys()
        if keys is not None:
            self.save_keys(keys)

    def _init_keys(self) -> tuple[bytes, bytes, PublicKey, bytes, bytes] | None:
        if self._keys_exist():
            self.logger.info("Key pair already exists")
            return None

        return self._generate_and_encrypt_keys()

    def _keys_exist(self) -> bool:
        return os.path.exists(self.static_config["private_key_file"]) and os.path.exists(
            self.static_config["public_key_file"],
        )

    def _generate_and_encrypt_keys(self) -> tuple[bytes, bytes, PublicKey, bytes, bytes]:
        keys = self._generate_key_pair()
        master_key = secrets.token_bytes(self.encrypt_config.key_bytes)
        encrypted_master_key, salt, encryption_key = self.encrypt_master_key(master_key)
        encrypted_private_key = self.encrypt_private_key(keys.private_key, master_key)

        cleanup([master_key])
        self.logger.info("Key pair has been successfully generated")
        return (
            encrypted_master_key,
            encrypted_private_key,
            keys.public_key,
            salt,
            encryption_key,
        )

    def _generate_key_pair(self) -> KeyPair:
        private_key = PrivateKey.generate()
        return KeyPair(private_key, private_key.public_key)


class AccountManager:
    MAX_QUOTA = 16
    DEFAULT_RUNTIME_STATUS = {
        "cookies_valid": True,
        "password_valid": True,
        "exceed_quota": False,
    }

    def __init__(
        self, logger: Logger, key_manager: KeyManager, yaml_path: str = "", cookies_path: str = ""
    ) -> None:
        self.logger = logger
        self.yaml_file_path = (
            yaml_path
            if yaml_path
            else os.path.join(ConfigManager.get_system_config_dir(), "accounts.yaml")
        )
        self.key_manager = key_manager
        self.lock = threading.RLock()

        self.yaml_accounts = self._load_yaml_accounts()
        self.cli_accounts = self.load_runtime_account(cookies_path)

        atexit.register(self.finalize)

    # === YAML 帳號管理方法 (具備CRUD功能，會持久化) ===
    def _load_yaml_accounts(self) -> dict[str, Any]:
        """從 YAML 檔案載入帳號資料"""
        try:
            with open(self.yaml_file_path) as file:
                return yaml.safe_load(file) or {}
        except FileNotFoundError:
            return {}

    def _save_yaml_accounts(self) -> None:
        if self.yaml_accounts:
            with self.lock:
                with open(self.yaml_file_path, "w") as file:
                    yaml.dump(self.yaml_accounts, file, default_flow_style=False)

    def create_yaml_account(
        self, username: str, password: str, cookies: str, public_key: PublicKey
    ) -> None:
        with self.lock:
            encrypted_password = self.key_manager.encrypt_password(password, public_key)
            self.yaml_accounts[username] = {
                "encrypted_password": encrypted_password,
                "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "cookies": cookies,
                **self.DEFAULT_RUNTIME_STATUS,
            }
        self.logger.info("Account %s has been created.", username)
        self._save_yaml_accounts()

    def read_yaml_account(self, username: str) -> dict[str, Any] | None:
        return self.yaml_accounts.get(username)

    def update_yaml_account(self, username: str, field: str, value: Any) -> None:
        with self.lock:
            account_info = self.yaml_accounts.get(username)
            if account_info is not None:
                account_info[field] = value
                self.logger.debug(
                    "Updated field '%s' for account '%s' with value: %s", field, username, value
                )
                self._save_yaml_accounts()
            else:
                self.logger.error("Account '%s' not found.", username)

    def delete_yaml_account(self, username: str) -> None:
        with self.lock:
            if username in self.yaml_accounts:
                del self.yaml_accounts[username]
                self.logger.info("Account %s has been deleted.", username)
                self._save_yaml_accounts()
            else:
                self.logger.error("Account %s not found.", username)

    def list_yaml_accounts(self) -> dict[str, Any]:
        return self.yaml_accounts.copy()

    # === CLI 帳號管理方法 (僅記憶體操作，不持久化) ===
    def create_cli_account(self, username: str, account_data: dict[str, Any]) -> None:
        # 確保資料結構與 YAML 帳號一致
        default_data = {
            "encrypted_password": "",
            "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "cookies": "",
            **self.DEFAULT_RUNTIME_STATUS,
        }
        default_data.update(account_data)
        self.cli_accounts[username] = default_data
        self.logger.info("CLI account %s has been added.", username)

    def read_cli_account(self, username: str) -> dict[str, Any] | None:
        return self.cli_accounts.get(username)

    def update_cli_account(self, username: str, field: str, value: Any) -> None:
        account_info = self.cli_accounts.get(username)
        if account_info:
            account_info[field] = value
            self.logger.debug(
                "Updated CLI account field '%s' for account '%s' with value: %s",
                field,
                username,
                value,
            )
        else:
            self.logger.error("CLI account '%s' not found.", username)

    def delete_cli_account(self, username: str) -> None:
        if username in self.cli_accounts:
            del self.cli_accounts[username]
            self.logger.info("CLI account %s has been deleted.", username)
        else:
            self.logger.error("CLI account %s not found.", username)

    def list_cli_accounts(self) -> dict[str, Any]:
        return self.cli_accounts.copy()

    def clear_cli_accounts(self) -> None:
        self.cli_accounts.clear()
        self.logger.info("All CLI accounts have been cleared.")

    def load_runtime_account(self, cookies_path: str) -> dict[str, dict[str, Any]]:
        """載入執行時期帳號（從 cookies 路徑）"""
        if cookies_path:
            paths = cookies.find_cookies_files(cookies_path)
            cli_accounts = {}

            for path in paths:
                # 確保 CLI 帳號與 YAML 帳號有相同的資料結構
                cli_accounts[path] = {
                    "encrypted_password": "",
                    "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                    "cookies": path,
                    **self.DEFAULT_RUNTIME_STATUS,
                }
            return cli_accounts
        else:
            return {}

    # === 通用 CRUD 功能 (支援兩種帳號類型) ===
    def create_account(self, account_type: str, username: str, **kwargs: Any) -> None:
        """通用帳號建立方法"""
        if account_type == "yaml":
            password = kwargs.get("password", "")
            cookies = kwargs.get("cookies", "")
            public_key = kwargs.get("public_key")
            if isinstance(public_key, PublicKey):
                self.create_yaml_account(username, password, cookies, public_key)
        elif account_type == "cli":
            account_data = kwargs.get("account_data", {})
            self.create_cli_account(username, account_data)
        else:
            self.logger.error("Invalid account type: %s", account_type)

    def read_account(self, username: str, account_type: str | None = None) -> dict[str, Any] | None:
        """通用帳號讀取方法"""
        if account_type == "yaml":
            return self.read_yaml_account(username)
        elif account_type == "cli":
            return self.read_cli_account(username)
        else:
            # 如果未指定類型，優先搜尋 CLI 再搜尋 YAML
            return self.get_account(username)

    def update_account(
        self, username: str, field: str, value: Any, account_type: str | None = None
    ) -> None:
        """通用帳號更新方法"""
        if account_type == "yaml":
            self.update_yaml_account(username, field, value)
        elif account_type == "cli":
            self.update_cli_account(username, field, value)
        else:
            # 如果未指定類型，根據帳號存在位置進行更新
            if username in self.cli_accounts:
                self.update_cli_account(username, field, value)
            elif username in self.yaml_accounts:
                self.update_yaml_account(username, field, value)
            else:
                self.logger.error("Account '%s' not found in any source.", username)

    def delete_account(self, username: str, account_type: str | None = None) -> None:
        """通用帳號刪除方法"""
        if account_type == "yaml":
            self.delete_yaml_account(username)
        elif account_type == "cli":
            self.delete_cli_account(username)
        else:
            # 如果未指定類型，從兩個來源中刪除
            deleted = False
            if username in self.cli_accounts:
                self.delete_cli_account(username)
                deleted = True
            if username in self.yaml_accounts:
                self.delete_yaml_account(username)
                deleted = True
            if not deleted:
                self.logger.error("Account '%s' not found in any source.", username)

    # === 統合查詢方法 ===
    def get_account(self, username: str) -> dict[str, Any] | None:
        """從兩種來源中查找帳號（CLI 優先）"""
        # CLI 帳號優先
        account = self.cli_accounts.get(username)
        if account:
            return account
        return self.yaml_accounts.get(username)

    def list_all_accounts(self) -> dict[str, dict[str, Any]]:
        """返回所有帳號(YAML + CLI)的合併清單，標記帳號來源類型"""
        all_accounts = {}

        # 添加 YAML 帳號並標記來源
        for username, account_data in self.yaml_accounts.items():
            account_with_source = account_data.copy()
            account_with_source["_source"] = "yaml"
            all_accounts[username] = account_with_source

        # 添加 CLI 帳號並標記來源（CLI 會覆蓋同名的 YAML 帳號）
        for username, account_data in self.cli_accounts.items():
            account_with_source = account_data.copy()
            account_with_source["_source"] = "cli"
            all_accounts[username] = account_with_source

        return all_accounts

    def account_exists(self, username: str) -> bool:
        """檢查帳號是否存在於任一來源"""
        return username in self.yaml_accounts or username in self.cli_accounts

    def get_account_source(self, username: str) -> str | None:
        """返回帳號來源類型: 'yaml', 'cli', 或 None"""
        sources = []
        if username in self.yaml_accounts:
            sources.append("yaml")
        if username in self.cli_accounts:
            sources.append("cli")

        if not sources:
            return None
        elif len(sources) == 1:
            return sources[0]
        else:
            return "both"  # 帳號存在於兩個來源中

    def finalize(self) -> None:
        self._save_yaml_accounts()

    # === 原有功能保持不變 ===
    def verify_password(self, account: str, password: str, private_key: PublicKey) -> bool:
        """驗證帳號密碼"""
        account_info = self.yaml_accounts.get(account)
        if not account_info:
            self.logger.error("Account does not exist.")
            return False

        encrypted_password = account_info.get("encrypted_password")
        decrypted_password = self.key_manager.decrypt_password(encrypted_password, private_key)
        if decrypted_password == password:
            print("*----------------*")
            print("|Password correct|")
            print("*----------------*")
            return True
        else:
            print("*------------------*")
            print("|Incorrect password|")
            print("*------------------*")
            return False

    def random_pick(self) -> str:
        """隨機選擇有效帳號"""
        all_accounts = self.list_all_accounts()
        valid_accounts = {k: v for k, v in all_accounts.items() if self.is_valid_account(k)}

        if not valid_accounts:
            self.logger.info("No eligible accounts available for login. Existing.")
            sys.exit(0)

        account, _ = random.choice(list(valid_accounts.items()))
        return account

    def get_pw(self, account: str, private_key: PrivateKey) -> str:
        account_info = self.yaml_accounts[account]
        enc_pw = account_info["encrypted_password"]
        return self.key_manager.decrypt_password(enc_pw, private_key)

    def is_valid_account(self, account: str) -> bool:
        if account in self.cli_accounts:
            state = self.cli_accounts[account]
        elif account in self.yaml_accounts:
            yaml_account = self.yaml_accounts[account]
            if "cookies_valid" not in yaml_account:
                return True
            state = yaml_account
        else:
            return False

        return (
            state.get("cookies_valid", True) or state.get("password_valid", True)
        ) and not state.get("exceed_quota", False)

    def edit_yaml_account(
        self,
        public_key: PublicKey,
        old_username: str,
        new_username: str | None,
        new_password: str | None,
        new_cookies: str | None,
    ) -> None:
        """編輯 YAML 帳號"""
        with self.lock:
            if old_username in self.yaml_accounts:
                if new_username:
                    self.yaml_accounts[new_username] = self.yaml_accounts.pop(old_username)
                if new_password:
                    encrypted_password = self.key_manager.encrypt_password(new_password, public_key)
                    self.yaml_accounts[new_username or old_username]["encrypted_password"] = (
                        encrypted_password
                    )
                if new_cookies:
                    self.yaml_accounts[new_username or old_username]["cookies"] = new_cookies
                self.logger.info("Account %s has been updated.", old_username)
                self._save_yaml_accounts()
            else:
                self.logger.error("Account not found.")

    def update_cli_account_status(self, account: str, field: str, value: Any) -> None:
        """更新 CLI 帳號狀態 - 原 update_runtime_state 方法"""
        self.update_cli_account(account, field, value)

    def get_all_accounts(self) -> dict[str, dict[str, Any]]:
        """取得所有帳號（合併兩種來源）- 向後相容"""
        all_accounts = {}
        all_accounts.update(self.yaml_accounts)
        all_accounts.update(self.cli_accounts)  # CLI 會覆蓋同名的 YAML 帳號
        return all_accounts

    def list_account_sources(self, username: str) -> list[str]:
        """查詢帳號的來源類型"""
        sources = []
        if username in self.yaml_accounts:
            sources.append("yaml")
        if username in self.cli_accounts:
            sources.append("cli")
        return sources

    def get_yaml_accounts(self) -> dict[str, Any]:
        return self.yaml_accounts.copy()

    def get_cli_accounts(self) -> dict[str, Any]:
        return self.cli_accounts.copy()

    # === 通用方法（支援兩種帳號類型） ===
    def create(
        self,
        username: str,
        password: str = "",
        cookies: str = "",
        public_key: PublicKey | None = None,
        account_type: str = "yaml",
    ) -> None:
        """通用建立方法 - 支援 YAML 和 CLI 帳號"""
        if account_type == "yaml":
            self.create_yaml_account(username, password, cookies, public_key)
        elif account_type == "cli":
            account_data = {
                "encrypted_password": "",
                "cookies": cookies,
            }
            self.create_cli_account(username, account_data)
        else:
            self.logger.error("Invalid account type: %s. Must be 'yaml' or 'cli'.", account_type)

    def delete(self, username: str, account_type: str | None = None) -> None:
        """通用刪除方法 - 支援 YAML 和 CLI 帳號"""
        self.delete_account(username, account_type)

    def read(self, username: str, account_type: str | None = None) -> dict[str, Any] | None:
        """通用讀取方法 - 支援 YAML 和 CLI 帳號"""
        return self.read_account(username, account_type)

    def edit(
        self,
        public_key: PublicKey,
        old_username: str,
        new_username: str | None = None,
        new_password: str | None = None,
        new_cookies: str | None = None,
        account_type: str | None = None,
    ) -> None:
        with self.lock:
            target_accounts = None
            is_yaml = False

            if account_type == "yaml":
                target_accounts = self.yaml_accounts
                is_yaml = True
            elif account_type == "cli":
                target_accounts = self.cli_accounts
                is_yaml = False
            elif old_username in self.yaml_accounts:
                target_accounts = self.yaml_accounts
                is_yaml = True
            elif old_username in self.cli_accounts:
                target_accounts = self.cli_accounts
                is_yaml = False

            if target_accounts is None or old_username not in target_accounts:
                self.logger.error("Account not found.")
                return

            if new_username:
                target_accounts[new_username] = target_accounts.pop(old_username)

            target_username = new_username or old_username

            if new_password:
                if is_yaml:
                    encrypted_password = self.key_manager.encrypt_password(new_password, public_key)
                    target_accounts[target_username]["encrypted_password"] = encrypted_password
                else:
                    target_accounts[target_username]["encrypted_password"] = ""

            if new_cookies:
                target_accounts[target_username]["cookies"] = new_cookies

            self.logger.info("Account %s has been updated.", old_username)

            if is_yaml:
                self._save_yaml_accounts()

    def update_runtime_state(self, account: str, field: str, value: Any) -> None:
        updated = False

        if account in self.cli_accounts:
            self.update_cli_account(account, field, value)
            updated = True

        if account in self.yaml_accounts:
            self.update_yaml_account(account, field, value)
            updated = True

        if not updated:
            self.logger.error("Account '%s' not found in any source.", account)


class SecureFileHandler:
    @staticmethod
    def write_file(path: str, data: str | bytes, permissions: int = 0o400) -> None:
        if isinstance(data, str):
            data = data.encode("utf-8")

        with open(path, "wb") as f:
            f.write(data)
        os.chmod(path, permissions)

    @staticmethod
    @overload
    def read_file(path: str, decode: Literal[True]) -> str: ...

    @staticmethod
    @overload
    def read_file(path: str, decode: Literal[False]) -> bytes: ...

    @staticmethod
    def read_file(path: str, decode: bool = False) -> str | bytes:
        with open(path, "rb") as f:
            _data = f.read()

        return _data.decode("utf-8") if decode else _data

    @staticmethod
    def write_env(env_path: str, key: str, value: str | bytes) -> None:
        if isinstance(value, bytes):
            value = base64.b64encode(value).decode("utf-8")

        load_dotenv(env_path)
        set_key(env_path, key, value)

    @staticmethod
    def read_env(key: str) -> str:
        value = os.getenv(key)
        if value is None:
            raise SecurityError(
                f"Missing required environment variable: {key}, please check your key files"
            )
        return value


def cleanup(sensitive_data: list[bytes]) -> None:
    for data in sensitive_data:
        length = len(data)
        buffer = ctypes.create_string_buffer(length)
        ctypes.memmove(ctypes.addressof(buffer), data, length)
        ctypes.memset(ctypes.addressof(buffer), 0, length)
        del buffer
