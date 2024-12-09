import sys
import time
import random
from datetime import datetime
from logging import Logger
from subprocess import Popen
from typing import TYPE_CHECKING, Any

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .base import BaseBehavior, BaseBot, BaseScroll, get_chrome_version
from .cookies import load_cookies
from ..common import SELENIUM_AGENT

if TYPE_CHECKING:
    from ..common import BaseConfig, RuntimeConfig
    from ..utils import AccountManager, KeyManager

DEFAULT_BOT_OPT = [
    "--remote-debugging-port=9222",
    "--disable-gpu",
    "--disable-infobars",
    "--disable-extensions",
    "--disable-dev-shm-usage",
    "--start-maximized",
]


class SeleniumBot(BaseBot):
    def __init__(
        self,
        runtime_config: "RuntimeConfig",
        base_config: "BaseConfig",
        key_manager: "KeyManager",
        account_manager: "AccountManager",
    ) -> None:
        super().__init__(runtime_config, base_config, key_manager, account_manager)
        self.init_driver()
        self.scroller = SelScroll(self.driver, self.base_config, self.logger)
        self.cloudflare = SelCloudflareHandler(self.driver, self.logger)

    def init_driver(self) -> None:
        self.driver: WebDriver
        options = Options()

        chrome_path = [self.base_config.chrome.exec_path]
        # commands for running subprocess
        subprocess_cmd = chrome_path + (self.runtime_config.chrome_args or DEFAULT_BOT_OPT)
        subprocess_cmd = [
            *subprocess_cmd,
            self.runtime_config.user_agent or SELENIUM_AGENT.format(get_chrome_version()),
        ]

        if not self.runtime_config.use_chrome_default_profile:
            user_data_dir = self.prepare_chrome_profile()
            subprocess_cmd.append(f"--user-data-dir={user_data_dir}")

        for arg in subprocess_cmd:
            options.add_argument(arg)

        # additional args for webdriver.Chrome to takeover the control of created browser
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        try:
            self.chrome_process = Popen(subprocess_cmd)  # subprocess.run fails
            self.driver = webdriver.Chrome(service=Service(), options=options)
        except Exception as e:
            self.logger.error("Unable to start Selenium WebDriver: %s", e)
            sys.exit("Unable to start Selenium WebDriver")

    def close_driver(self) -> None:
        if self.close_browser:
            self.driver.quit()
            self.chrome_process.terminate()

    def auto_page_scroll(
        self,
        url: str,
        max_retry: int = 3,
        page_sleep: int = 5,
        fast_scroll: bool = False,
    ) -> str:
        response: str = ""
        for attempt in range(max_retry):
            try:
                self.driver.get(url)
                SelBehavior.random_sleep(0.1, 0.5)

                if not self.handle_redirection_fail(url, max_retry, page_sleep):
                    self.logger.error(
                        "Reconnection fail for URL %s. Please check your network status.",
                        url,
                    )
                    break

                if self.cloudflare.handle_simple_block(attempt, max_retry):
                    continue

                # main business
                self.handle_login()
                self.handle_read_limit()
                self.driver.execute_script("document.body.style.zoom='50%'")
                self.scroller.scroll_to_bottom()
                SelBehavior.random_sleep(5, 15)

                response = self.driver.page_source
                break

            except Exception as e:
                self.logger.exception(
                    "Request failed for URL %s - Attempt %d/%d. Error: %s",
                    url,
                    attempt + 1,
                    max_retry,
                    e,
                )

            self.logger.debug("Scrolling finished, pausing to avoid blocking")
            SelBehavior.random_sleep(page_sleep, page_sleep + 5)

        if not response:
            error_template = "Failed to retrieve URL after {} attempts: '{}'"
            error_msg = error_template.format(max_retry, url)
            self.logger.error(error_msg)
            return error_msg
        return response

    def handle_redirection_fail(self, url: str, max_retry: int, sleep_time: int) -> bool:
        if self.driver.current_url == url:
            return True
        retry = 1
        while retry <= max_retry:
            self.logger.warning("Connection failed - Attempt %d/%d", retry, max_retry)
            SelBehavior.random_sleep(sleep_time, sleep_time + 5 * random.uniform(1, retry * 5))

            if self.cloudflare.handle_simple_block(retry, max_retry):
                self.logger.warning("Failed to solve Cloudflare turnstile challenge")
                continue

            self.driver.get(url)
            retry += 1
            if self.driver.current_url == url:
                return True

        return self.driver.current_url == url

    def handle_login(self) -> None:
        success = False
        if self.driver.find_elements(
            By.XPATH,
            "//h1[@class='h4 text-secondary mb-4 login-box-msg']",
        ):
            self.logger.info("Login page detected - Starting login process")
            try:
                for _ in self.account_manager.accounts:
                    # this will update self.email and cookies_valid
                    # if no accounts available, `AccountManager.random_pick` will execute sys.exit
                    if self.cookies_login():
                        return

                    self.email, self.password = self.account_manager.random_pick(self.private_key)
                    email_field = self.driver.find_element(By.ID, "email")
                    password_field = self.driver.find_element(By.ID, "password")
                    BaseBehavior.random_sleep(0.5, 1)

                    password_field.send_keys(Keys.SHIFT, Keys.TAB)
                    BaseBehavior.random_sleep(0.5, 1)
                    SelBehavior.human_like_type(email_field, self.email)
                    SelBehavior.random_sleep(0.01, 0.3)

                    email_field.send_keys(Keys.TAB)
                    SelBehavior.human_like_type(password_field, self.password)
                    SelBehavior.random_sleep(0.01, 0.5)

                    try:
                        self.cloudflare.handle_cloudflare_recaptcha()
                    except Exception as e:
                        self.logger.exception("Error handling Cloudflare reCAPTCHA: %s", e)

                    self.driver.find_element(
                        By.XPATH,
                        '//button[@type="submit" and @class="btn btn-primary"]',
                    ).click()

                    SelBehavior.random_sleep(3, 5)

                    if not self.driver.find_elements(
                        By.XPATH,
                        "//h1[@class='h4 text-secondary mb-4 login-box-msg']",
                    ):
                        self.logger.info("Login successful")
                        success = True
                    else:
                        self.logger.info("Login failed - Checking for error messages")
                        self.account_manager.update_runtime_state(
                            self.email,
                            "password_valid",
                            False,
                        )
                        self.check_login_errors()

            except NoSuchElementException as e:
                self.logger.error("Login form element not found: %s", e)
                raise
            except TimeoutException as e:
                self.logger.error("Timeout waiting for element: %s", e)
                raise
            except Exception as e:
                self.logger.error("Unexpected error during login: %s", e)
                raise
        else:
            success = True
        if not success:
            self.logger.info("Automated login failed. Please login yourself.")
            sys.exit("Automated login failed.")

    def cookies_login(self) -> bool:
        self.email, self.password = self.account_manager.random_pick(self.private_key)
        account = self.account_manager.read(self.email)
        if account is None:
            return False

        cookies_path = account.get("cookies")
        if cookies_path:
            cookies = load_cookies(cookies_path)
            self.driver.delete_all_cookies()
            for k, v in cookies.items():
                self.driver.add_cookie({"name": k, "value": v})
            self.driver.refresh()

        if not self.driver.find_element('//a[@href="/site/recovery-password"]'):
            self.logger.info("Account %s login successful with cookies", self.email)
            return True

        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self.account_manager.update_runtime_state(self.email, "cookies_valid", False)
        self.account_manager.update_account(self.email, "exceed_time", now)
        return False

    def check_login_errors(self) -> None:
        error_messages = self.driver.find_elements(By.CLASS_NAME, "errorMessage")
        if error_messages:
            for message in error_messages:
                self.logger.error("Login error: %s", message.text)
        else:
            self.logger.error("Login failed for unknown reasons")
            sys.exit(1)

    def handle_read_limit(self) -> None:
        if self.check_read_limit():
            # click logout
            logout_button = self.driver.find_element(
                By.XPATH,
                '//ul[@class="nav justify-content-end"]//a[contains(@href, "/user/logout")]',
            )
            logout_button.click()
            now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            self.account_manager.update_account(self.email, "exceed_quota", True)
            self.account_manager.update_account(self.email, "exceed_time", now)
            self.email, self.password = self.account_manager.random_pick(self.private_key)

    def check_read_limit(self) -> bool:
        return "https://www.v2ph.com/user/upgrade" in self.driver.current_url


class SelCloudflareHandler:
    """Handles Cloudflare protection detection and bypass attempts.

    Includes methods for dealing with various Cloudflare challenges.
    """

    def __init__(self, driver: WebDriver, logger: Logger):
        self.driver = driver
        self.logger = logger

    def handle_simple_block(self, attempt: int, retries: int) -> bool:
        """check and handle Cloudflare challenge."""
        blocked = False
        if self.is_simple_blocked():
            self.logger.info(
                "Detected Cloudflare challenge, attempting to solve... Attempt %d/%d",
                attempt + 1,
                retries,
            )
            self.handle_cloudflare_turnstile()
            blocked = True
        return blocked

    def handle_hard_block(self) -> bool:
        """Check whether blocked or not.

        This is a cloudflare WAF full page block.
        """
        blocked = False
        if self.is_hard_block():
            self.logger.warning("Hard block detected by Cloudflare - Unable to proceed")
            blocked = True
        return blocked

    def is_simple_blocked(self) -> bool:
        title_check = any(text in self.driver.title for text in ["請稍候...", "Just a moment..."])
        page_source_check = "Checking your" in self.driver.page_source
        return title_check or page_source_check

    def is_hard_block(self) -> bool:
        is_blocked = "Attention Required! | Cloudflare" in self.driver.title
        if is_blocked:
            self.logger.warning("Cloudflare hard block detected")
        return is_blocked

    def handle_cloudflare_turnstile(self) -> None:
        try:
            iframe = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//iframe[contains(@src, 'challenges.cloudflare.com')]",
                )),
            )
            self.driver.switch_to.frame(iframe)

            checkbox = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "cf-turnstile-response")),
            )
            SelBehavior.human_like_click(self.driver, checkbox)

            if "Select all squares with" in self.driver.page_source:
                self.solve_image_captcha()

            self.driver.switch_to.default_content()
            SelBehavior.random_sleep(10, 20)
        except (TimeoutException, NoSuchElementException):
            self.logger.error("Unable to solve Cloudflare challenge.")

    def handle_cloudflare_recaptcha(self) -> None:
        try:
            recaptcha_checkbox = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox']")),
            )
            SelBehavior.human_like_click(self.driver, recaptcha_checkbox)

            verify_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), '驗證您是人類')]")),
            )
            SelBehavior.human_like_click(self.driver, verify_button)

            SelBehavior.random_sleep(3, 5)
        except (TimeoutException, NoSuchElementException) as e:
            self.logger.warning(
                "reCAPTCHA checkbox or verify button not found or unable to interact: %s",
                e,
            )

    def solve_image_captcha(self) -> None:
        raise NotImplementedError


class SelBehavior(BaseBehavior):
    @staticmethod
    def human_like_mouse_movement(driver: Any, element: Any) -> None:
        action = ActionChains(driver)
        action.move_by_offset(random.randint(-100, 100), random.randint(-100, 100))
        action.move_to_element_with_offset(
            element,
            random.randint(-10, 10),
            random.randint(-10, 10),
        )
        action.pause(random.uniform(0.1, 0.3))
        action.move_to_element(element)
        action.perform()
        SelBehavior.random_sleep(*BaseBehavior.pause_time)

    @staticmethod
    def human_like_click(driver: Any, element: Any) -> None:
        SelBehavior.human_like_mouse_movement(driver, element)
        action = ActionChains(driver)
        action.click()
        action.perform()
        SelBehavior.random_sleep(*BaseBehavior.pause_time)

    @staticmethod
    def human_like_type(element: Any, text: str) -> None:
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.001, 0.2))
        SelBehavior.random_sleep(*BaseBehavior.pause_time)


class SelScroll(BaseScroll):
    def __init__(self, driver: WebDriver, base_config: "BaseConfig", logger: Logger):
        super().__init__(base_config, logger)
        self.driver = driver

    def scroll_to_bottom(self) -> None:
        max_attempts = 10
        attempts = 0
        last_position = -123459
        scroll_length = lambda: random.randint(
            self.base_config.download.min_scroll_length,
            self.base_config.download.max_scroll_length,
        )

        while attempts < max_attempts:
            SelBehavior.random_sleep(1, 2)
            scroll = scroll_length()
            self.logger.debug(
                "Current position: %d, scrolling down by %d pixels",
                last_position,
                scroll,
            )
            self.driver.execute_script(f"window.scrollBy({{top: {scroll}, behavior: 'smooth'}});")
            new_position = self.driver.execute_script("return window.pageYOffset;")
            if new_position == last_position:
                break
            last_position = new_position
            attempts += 1

    def old_scroll_to_bottom(self) -> None:
        self.logger.info("Start scrolling the page")
        scroll_attempts = 0
        max_attempts = 45

        scroll_pos_init = self.driver.execute_script("return window.pageYOffset;")
        step_scroll = random.randint(
            self.base_config.download.min_scroll_length,
            self.base_config.download.max_scroll_length,
        )

        while scroll_attempts < max_attempts:
            scroll_attempts += 1

            self.driver.execute_script(f"window.scrollBy(0, {step_scroll});")
            scroll_pos_end = self.driver.execute_script("return window.pageYOffset;")
            time.sleep(0.75)

            if scroll_pos_init >= scroll_pos_end:
                self.logger.debug("Reached the bottom of the page")
                break

            scroll_pos_init = scroll_pos_end

            step_scroll = random.randint(
                self.base_config.download.min_scroll_length,
                self.base_config.download.max_scroll_length,
            )

            self.wait_for_content_load()

            self.successive_scroll_count += 1
            if self.successive_scroll_count >= self.max_successive_scrolls:
                pause_time = random.uniform(3, 7)
                self.logger.debug(
                    "Scrolled %d times, pausing for %.2f seconds",
                    self.successive_scroll_count,
                    pause_time,
                )
                time.sleep(pause_time)
                self.successive_scroll_count = 0
                self.max_successive_scrolls = random.randint(3, 7)

        if scroll_attempts == max_attempts:
            self.logger.info(
                "Reached maximum attempts (%d), scrolling finished, may not have fully reached the bottom",
                max_attempts,
            )
        else:
            self.logger.info("Page scroll completed")

    def perform_scroll_action(self) -> None:
        action = random.choices(
            ["scroll_down", "scroll_up", "pause", "jump"],
            weights=[0.7, 0.1, 0.1, 0.1],
        )[0]

        current_position = self.get_scroll_position()

        if action == "scroll_down":
            scroll_length = random.randint(
                self.base_config.download.min_scroll_length,
                self.base_config.download.max_scroll_length,
            )
            target_position = current_position + scroll_length
            self.logger.debug("Trying to scroll down %d pixels", scroll_length)
            actual_position = self.safe_scroll(target_position)
            self.logger.debug("Actually scrolled to %d pixels", actual_position)
            time.sleep(random.uniform(*BaseBehavior.pause_time))
        elif action == "scroll_up":
            scroll_length = random.randint(
                self.base_config.download.min_scroll_length,
                self.base_config.download.max_scroll_length,
            )
            target_position = max(0, current_position - scroll_length)
            self.logger.debug("Trying to scroll up %d pixels", scroll_length)
            actual_position = self.safe_scroll(target_position)
            self.logger.debug("Actually scrolled to %d pixels", actual_position)
        elif action == "pause":
            pause_time = random.uniform(1, 3)
            self.logger.debug("Pausing for %.2f seconds", pause_time)
            time.sleep(pause_time)
        elif action == "jump":
            jump_position = current_position + random.randint(100, 500)
            self.logger.debug("Trying to jump to position %d", jump_position)
            actual_position = self.safe_scroll(jump_position)
            self.logger.debug("Actually jumped to %d", actual_position)

    def safe_scroll(self, target_position: float) -> float:
        current_position = self.get_scroll_position()
        step = random.uniform(
            self.base_config.download.min_scroll_step,
            self.base_config.download.max_scroll_step,
        )
        # step = 50 if target_position > current_position else -50
        # while abs(current_position - target_position) > abs(step):

        while abs(current_position - target_position) > step:
            self.driver.execute_script(f"window.scrollTo(0, {current_position + step});")
            time.sleep(random.uniform(0.01, 0.2))
            new_position = self.get_scroll_position()
            if new_position == current_position:
                self.logger.debug(
                    "Cannot continue scrolling, target: %d, current: %d",
                    target_position,
                    current_position,
                )
                break
            current_position = new_position
        self.driver.execute_script(f"window.scrollTo(0, {target_position});")
        return self.get_scroll_position()

    def get_scroll_position(self) -> float:
        return self.driver.execute_script("return window.pageYOffset")

    def get_page_height(self) -> float:
        return self.driver.execute_script("return document.body.scrollHeight")

    def wait_for_content_load(self) -> None:
        try:
            WebDriverWait(self.driver, 5).until(
                lambda d: d.execute_script("return document.readyState") == "complete",
            )
        except TimeoutException:
            self.logger.warning("Timeout waiting for new content to load")
