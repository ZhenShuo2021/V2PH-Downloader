from __future__ import annotations

from typing import Literal, TypeAlias, TypeVar

# Manage return types of each scraper here
AlbumResult: TypeAlias = str  # url
ImageResult: TypeAlias = tuple[str, str]  # url and alt
PageResultType = TypeVar("PageResultType", bound=AlbumResult | ImageResult)
ScrapeType = Literal["album_list", "album_image"]
