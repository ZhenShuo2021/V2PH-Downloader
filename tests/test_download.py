import shutil
import logging
from unittest.mock import Mock

import pytest

from v2dl.utils.download import DirectoryCache, DownloadPathTool


# ============ test is_file_exists ============
@pytest.fixture
def mock_logger():
    return Mock(spec=logging.Logger)


@pytest.fixture
def test_dir(tmp_path):
    file1 = tmp_path / "testfile.txt"
    file1.touch()
    file2 = tmp_path / "testfile.log"
    file2.touch()

    yield tmp_path

    shutil.rmtree(tmp_path)


@pytest.fixture
def dir_cache():
    return DirectoryCache()


def test_file_exists_ignore_suffix(test_dir, mock_logger, dir_cache):
    file_path = test_dir / "testfile.any"
    result = DownloadPathTool.is_file_exists(file_path, False, dir_cache, mock_logger)

    assert result is True


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
def directory_cache():
    return DirectoryCache(max_cache_size=3)


@pytest.fixture
def tmp_directory(tmp_path):
    file1 = tmp_path / "file1.txt"
    file1.touch()
    file2 = tmp_path / "file2.log"
    file2.touch()
    return tmp_path


def test_get_stems_cache_hit(directory_cache, tmp_directory):
    # test cache hit
    stems = directory_cache.get_stems(tmp_directory)
    assert stems == {"file1", "file2"}


def test_get_stems_cache_miss(directory_cache, tmp_directory):
    new_file = tmp_directory / "nonexistent.any"
    stems = directory_cache.get_stems(new_file)
    assert stems == set()


def test_add_stem(directory_cache, tmp_directory):
    directory_cache.get_stems(tmp_directory)
    directory_cache.add_stem(tmp_directory, "newfile")
    assert "newfile" in directory_cache._cache[tmp_directory]


def test_cache_eviction(directory_cache, tmp_directory):
    dir1 = tmp_directory / "dir1"
    dir2 = tmp_directory / "dir2"
    dir3 = tmp_directory / "dir3"
    dir4 = tmp_directory / "dir4"
    dir1.mkdir()
    dir2.mkdir()
    dir3.mkdir()
    dir4.mkdir()

    directory_cache.get_stems(dir1)
    directory_cache.get_stems(dir2)
    directory_cache.get_stems(dir3)

    directory_cache.get_stems(dir4)
    assert dir1 not in directory_cache._cache
    assert dir2 in directory_cache._cache
    assert dir3 in directory_cache._cache
    assert dir4 in directory_cache._cache
