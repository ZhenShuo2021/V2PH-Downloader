import shutil

import pytest

from v2dl.scraper.downloader import DirectoryCache, DownloadPathTool


@pytest.fixture
def test_dir(tmp_path):
    file1 = tmp_path / "testfile.txt"
    file1.touch()
    file2 = tmp_path / "testfile.log"
    file2.touch()
    file3 = tmp_path / "testfile2.any"
    file3.touch()

    yield tmp_path

    shutil.rmtree(tmp_path)


@pytest.fixture
def dir_cache():
    return DirectoryCache(3)


@pytest.mark.parametrize(
    "filename, force_download, expected",
    [
        ("testfile.txt", False, True),  # 文件存在
        ("nonexistent.txt", False, False),  # 文件不存在
        ("testfile.txt", True, False),  # 强制下载
    ],
)
def test_is_file_exists(test_dir, mock_logger, filename, force_download, expected):
    cache = DirectoryCache()
    file_path = test_dir / filename

    result = DownloadPathTool.is_file_exists(
        file_path=file_path, force_download=force_download, cache=cache, logger=mock_logger
    )

    assert result == expected

    # 验证 logger 是否被正确调用
    if expected and not force_download and filename == "testfile.txt":
        mock_logger.info.assert_called_once_with(
            "File already exists (ignoring extension): '%s'", file_path
        )
    else:
        mock_logger.info.assert_not_called()


def test_file_not_exists_force_download(test_dir, mock_logger, dir_cache):
    file_path = test_dir / "newfile.any"
    result = DownloadPathTool.is_file_exists(file_path, True, dir_cache, mock_logger)

    assert result is False


def test_file_not_exists_no_force_download(test_dir, mock_logger, dir_cache):
    file_path = test_dir / "newfile.any"
    result = DownloadPathTool.is_file_exists(file_path, False, dir_cache, mock_logger)

    assert result is False


# ============ test cache ============
@pytest.fixture
def setup_cache_dirs(tmp_path):
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir3 = tmp_path / "dir3"
    dir4 = tmp_path / "dir4"

    dir1.mkdir()
    dir2.mkdir()
    dir3.mkdir()
    dir4.mkdir()

    (dir1 / "file1.txt").write_text("test")
    (dir1 / "file2.txt").write_text("test")
    (dir2 / "file3.txt").write_text("test")

    return dir1, dir2, dir3, dir4


def test_get_files_cache_hit(dir_cache, setup_cache_dirs):
    dir1, _, _, _ = setup_cache_dirs
    # 第一次呼叫，填充快取
    first_result = dir_cache.get_files(dir1)
    # 第二次呼叫，應該命中快取
    second_result = dir_cache.get_files(dir1)

    expected = {str(dir1 / "file1.txt"), str(dir1 / "file2.txt")}
    assert first_result == expected
    assert second_result == expected
    assert dir_cache._cache[dir1] == expected
    assert list(dir_cache._cache.keys())[-1] == dir1  # 確認移到末尾


def test_get_files_cache_miss(dir_cache, setup_cache_dirs):
    dir1, dir2, _, _ = setup_cache_dirs
    # 第一次呼叫 dir1，未命中
    result1 = dir_cache.get_files(dir1)
    # 第一次呼叫 dir2，未命中
    result2 = dir_cache.get_files(dir2)

    expected1 = {str(dir1 / "file1.txt"), str(dir1 / "file2.txt")}
    expected2 = {str(dir2 / "file3.txt")}

    assert result1 == expected1
    assert result2 == expected2
    assert dir1 in dir_cache._cache
    assert dir2 in dir_cache._cache
    assert len(dir_cache._cache) == 2


def test_cache_eviction(dir_cache, setup_cache_dirs):
    dir1, dir2, dir3, dir4 = setup_cache_dirs
    # 填充快取到最大容量 (3)
    dir_cache.get_files(dir1)
    dir_cache.get_files(dir2)
    dir_cache.get_files(dir3)
    # 快取應包含 dir1, dir2, dir3
    assert len(dir_cache._cache) == 3
    assert dir1 in dir_cache._cache
    assert dir2 in dir_cache._cache
    assert dir3 in dir_cache._cache

    # 加入新目錄，應該逐出最舊的 (dir1)
    dir_cache.get_files(dir4)
    assert len(dir_cache._cache) == 3
    assert dir1 not in dir_cache._cache
    assert dir2 in dir_cache._cache
    assert dir3 in dir_cache._cache
    assert dir4 in dir_cache._cache


def test_get_image_ext():
    assert DownloadPathTool.get_image_ext("photo.jpg") == "jpg"
    assert DownloadPathTool.get_image_ext("picture.jpeg") == "jpg"
    assert DownloadPathTool.get_image_ext("image.png") == "png"
    assert DownloadPathTool.get_image_ext("file.PNG") == "png"
    assert DownloadPathTool.get_image_ext("banner.GIF") == "gif"

    # test edge case
    assert DownloadPathTool.get_image_ext("image.png?param=value") == "png"  # With query params
    assert DownloadPathTool.get_image_ext("photo.jpg#fragment") == "jpg"  # With fragment

    # test not support
    assert DownloadPathTool.get_image_ext("file.txt") == "jpg"
    assert DownloadPathTool.get_image_ext("doc.docx") == "jpg"
    assert DownloadPathTool.get_image_ext("example") == "jpg"
    assert DownloadPathTool.get_image_ext("") == "jpg"
