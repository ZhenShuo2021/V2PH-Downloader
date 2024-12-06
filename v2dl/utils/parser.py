import re
from logging import Logger
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from lxml import html


class LinkParser:
    """Tool class for parsing and modifying URLs."""

    @staticmethod
    def parse_input_url(url: str) -> tuple[list[str], int]:
        """
        Extracts path segments and the starting page number from a URL.

        Args:
            url (str): Input URL.

        Returns:
            tuple[list[str], int]: Path segments and the starting page number.
        """
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.split("/")
        query_params = parse_qs(parsed_url.query)
        start_page: int = int(query_params.get("page", [1])[0])  # default page=1
        return path_parts, start_page

    @staticmethod
    def parse_html(html_content: str, logger: Logger) -> html.HtmlElement | None:
        """Parses HTML content into an HTML element.

        Args:
            html_content (str): HTML content as a string.
            logger (Logger): Logger for error handling.

        Returns:
            html.HtmlElement | None: Parsed HTML element or None if parsing fails.
        """
        if "Failed" in html_content:
            return None

        try:
            return html.fromstring(html_content)
        except Exception as e:
            logger.error("Error parsing HTML content: %s", e)
            return None

    @staticmethod
    def get_max_page(tree: html.HtmlElement) -> int:
        """
        Retrieves the maximum page number from a pagination element.

        Args:
            tree (html.HtmlElement): Parsed HTML tree.

        Returns:
            int: Maximum page number, default is 1 if none found.
        """
        page_links = tree.xpath(
            '//li[@class="page-item"]/a[@class="page-link" and string-length(text()) <= 2]/@href',
        )

        if not page_links:
            return 1

        page_numbers = []
        for link in page_links:
            match = re.search(r"page=(\d+)", link)
            if match:
                page_number = int(match.group(1))
            else:
                page_number = 1
            page_numbers.append(page_number)

        return max(page_numbers)

    @staticmethod
    def add_page_num(url: str, page: int) -> str:
        """
        Adds or updates the page number in a URL.

        Args:
            url (str): Original URL.
            page (int): Page number to add or update.

        Returns:
            str: Updated URL with the specified page number.
        """
        parsed_url = urlparse(url)  # 解析 URL
        query_params = parse_qs(parsed_url.query)  # 解析查詢參數
        query_params["page"] = [str(page)]  # 修改頁碼

        new_query = urlencode(query_params, doseq=True)  # 組合成字串
        new_url = parsed_url._replace(query=new_query)  # 替換頁碼

        # Example
        # url = "https://example.com/search?q=test&sort=asc", page = 3
        # parsed_url: ParseResult(scheme='https', netloc='example.com', path='/search', params='', query='q=test&sort=asc', fragment='')
        # query_params: {'q': ['test'], 'sort': ['asc'], 'page': ['3']}
        # new_query: 'q=test&sort=asc&page=3'
        # new_url: ParseResult(scheme='https', netloc='example.com', path='/search', params='', query='q=test&sort=asc&page=3', fragment='')
        # urlunparse: 'https://example.com/search?q=test&sort=asc&page=3'
        return urlunparse(new_url)

    @staticmethod
    def remove_page_num(url: str) -> str:
        """
        Removes the page parameter from a URL.

        Args:
            url (str): Original URL.

        Returns:
            str: URL without the page parameter.
        """
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)

        if "page" in query_params:
            del query_params["page"]

        new_query = urlencode(query_params, doseq=True)

        return urlunparse(parsed_url._replace(query=new_query))

    @staticmethod
    def remove_query_params(url: str) -> str:
        parsed_url = urlparse(url)
        return urlunparse(parsed_url._replace(query=""))

    @staticmethod
    def update_language(url: str, lang: str) -> str:
        parsed_url = urlparse(url)
        query = parse_qs(parsed_url.query)
        query["hl"] = [lang]
        updated_query = urlencode(query, doseq=True)
        return urlunparse(parsed_url._replace(query=updated_query))
