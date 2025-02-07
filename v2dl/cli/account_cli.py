import os
import sys
import getpass
import logging
import platform
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

import questionary

from ..common import EncryptionConfig
from ..utils import AccountManager, KeyManager
from ..version import __package_name__


class MenuAction(Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    PASSWORD = "password"
    LIST = "list"
    QUIT = "quit"


@dataclass
class UIStrings:
    menu_create = "Create Account"
    menu_read = "Read Account"
    menu_update = "Update Account"
    menu_delete = "Delete Account"
    menu_password = "Password Test"
    menu_list = "List All Accounts"
    menu_quit = "Quit"
    menu_prompt = "Please choose an action:"

    prompt_username = "Please enter the username: "
    prompt_password = "Please enter the password: "
    prompt_cookies = "Please enter the cookies: "
    prompt_old_username = "Please enter the old username: "
    prompt_new_username = "Please enter the new username (leave blank to not update): "
    prompt_new_password = "Please enter the new password (leave blank to not update): "
    prompt_new_cookies = "Please enter the new cookies (leave blank to not update): "
    prompt_password_test = "Enter password (leave blank to not update): "

    msg_account_not_found = "Account not found."
    msg_no_accounts = "No accounts available."
    msg_operation_canceled = "Operation canceled."
    msg_exit = "Exiting the account management of v2dl."
    msg_invalid_choice = "Invalid choice, please try again."

    confirm_delete = "Are you sure you want to delete the account {username}?"
    confirm_yes = "Confirm"
    CONFIRM_NO = "Cancel"

    LIST_FORMAT = "Email: {username}, Exceed quota: {quota}, Exceed time: {time}, Created At: {created_at}, \nCookies: {cookies}\n"


class AccountManagerCLI:
    action_map: dict[str, Callable[..., Any]] = {}

    def __init__(self, encrypt_config: EncryptionConfig):
        self.logger = logging.getLogger(__package_name__)
        self.logger.setLevel(logging.INFO)
        self.strings = UIStrings()
        self.key_manager = KeyManager(self.logger, encrypt_config)
        self.account_manager = AccountManager(self.logger, self.key_manager)
        key_pair = self.key_manager.load_keys()
        self.private_key, self.public_key = key_pair.private_key, key_pair.public_key

    def clean_terminal(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")  # nosec

    def get_pass(self, prompt: str = "Password: ") -> str:
        if platform.system() == "Windows":
            return input(prompt)
        return getpass.getpass(prompt)

    def get_menu_choices(self) -> list[dict[str, str]]:
        return [
            {"name": self.strings.menu_create, "value": MenuAction.CREATE.value},
            {"name": self.strings.menu_read, "value": MenuAction.READ.value},
            {"name": self.strings.menu_update, "value": MenuAction.UPDATE.value},
            {"name": self.strings.menu_delete, "value": MenuAction.DELETE.value},
            {"name": self.strings.menu_password, "value": MenuAction.PASSWORD.value},
            {"name": self.strings.menu_list, "value": MenuAction.LIST.value},
            {"name": self.strings.menu_quit, "value": MenuAction.QUIT.value},
        ]

    def display_menu(self) -> Any:
        return questionary.select(self.strings.menu_prompt, choices=self.get_menu_choices()).ask()

    def create_account(self) -> None:
        self.clean_terminal()
        print(self.strings.menu_create)
        username = input(self.strings.prompt_username)
        if username == "":
            return
        password = self.get_pass(self.strings.prompt_password)
        cookies = input(self.strings.prompt_cookies)
        self.account_manager.create(username, password, cookies, self.public_key)

    def read_account(self) -> None:
        self.clean_terminal()
        print(self.strings.menu_read)
        username = input(self.strings.prompt_username)
        account = self.account_manager.read(username)
        if account:
            ordered_dict = OrderedDict()
            ordered_dict["username"] = username
            ordered_dict["encrypted_password"] = account["encrypted_password"]
            for key, value in account.items():
                if key not in ["username", "encrypted_password"]:
                    ordered_dict[key] = value

            for key, value in ordered_dict.items():
                print(f"{key}: {value}")
        else:
            print(self.strings.msg_account_not_found)

    def update_account(self) -> None:
        self.clean_terminal()
        print(self.strings.menu_update)
        old_username = input(self.strings.prompt_old_username)
        password = self.get_pass(self.strings.prompt_password)
        if not self.account_manager.verify_password(old_username, password, self.private_key):
            return
        new_username = input(self.strings.prompt_new_username)
        password = self.get_pass(self.strings.prompt_new_password)
        cookies = input(self.strings.prompt_cookies)
        self.account_manager.edit(self.public_key, old_username, new_username, password, cookies)

    def delete_account(self) -> None:
        self.clean_terminal()
        print(self.strings.menu_delete)
        username = input(self.strings.prompt_username)
        if username in self.account_manager.accounts:
            password = self.get_pass(self.strings.prompt_password)
            if not self.account_manager.verify_password(username, password, self.private_key):
                return

            confirm_delete = questionary.select(
                self.strings.confirm_delete.format(username=username),
                choices=[
                    self.strings.confirm_yes,
                    self.strings.CONFIRM_NO,
                ],
            ).ask()

            if confirm_delete == self.strings.confirm_yes:
                self.account_manager.delete(username)
            else:
                print(self.strings.msg_operation_canceled)
        else:
            print(self.strings.msg_account_not_found)

    def password_test(self) -> None:
        self.clean_terminal()
        print(self.strings.menu_password)
        username = input(self.strings.prompt_username)
        account = self.account_manager.read(username)
        if account:
            password = self.get_pass(self.strings.prompt_password_test)
            self.account_manager.verify_password(username, password, self.private_key)
        else:
            print(self.strings.msg_account_not_found)

    def list_accounts(self) -> None:
        self.clean_terminal()
        print(self.strings.menu_list)
        accounts = self.account_manager.accounts
        if accounts:
            for username, info in accounts.items():
                print(
                    self.strings.LIST_FORMAT.format(
                        username=username,
                        quota=info["exceed_quota"],
                        time=info["exceed_time"],
                        created_at=info["created_at"],
                        cookies=info["cookies"],
                    ),
                )
        else:
            print(self.strings.msg_no_accounts)

    def execute_action(self, choice: str) -> bool:
        if choice == MenuAction.QUIT.value:
            self.clean_terminal()
            print(self.strings.msg_exit)
            return True

        action = self.action_map.get(choice)
        if action:
            action(self)
        else:
            print(self.strings.msg_invalid_choice)
        return False

    @classmethod
    def initialize_action_map(cls) -> None:
        cls.action_map = {
            MenuAction.CREATE.value: cls.create_account,
            MenuAction.READ.value: cls.read_account,
            MenuAction.UPDATE.value: cls.update_account,
            MenuAction.DELETE.value: cls.delete_account,
            MenuAction.PASSWORD.value: cls.password_test,
            MenuAction.LIST.value: cls.list_accounts,
        }

    def run(self) -> None:
        self.clean_terminal()
        while True:
            choice = self.display_menu()
            if self.execute_action(choice):
                break
        sys.exit(0)


def cli(encrypt_config: EncryptionConfig) -> None:
    cli = AccountManagerCLI(encrypt_config)
    cli.initialize_action_map()
    cli.run()
