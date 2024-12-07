import shutil

import pytest

from v2dl.utils.download import DirectoryCache, DownloadPathTool

# ============ test is_file_exists ============


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
def test_get_stems_cache_hit(dir_cache, test_dir):
    # test cache hit
    stems = dir_cache.get_stems(test_dir)
    assert stems == {"testfile", "testfile2"}


def test_get_stems_cache_miss(dir_cache, test_dir):
    new_file = test_dir / "nonexistent.any"
    stems = dir_cache.get_stems(new_file)
    assert stems == set()


def test_add_stem(dir_cache, test_dir):
    dir_cache.get_stems(test_dir)
    dir_cache.add_stem(test_dir, "newfile")
    assert "newfile" in dir_cache._cache[test_dir]


def test_cache_eviction(dir_cache, test_dir):
    dir1 = test_dir / "dir1"
    dir2 = test_dir / "dir2"
    dir3 = test_dir / "dir3"
    dir4 = test_dir / "dir4"
    dir1.mkdir()
    dir2.mkdir()
    dir3.mkdir()
    dir4.mkdir()

    dir_cache.get_stems(dir1)
    dir_cache.get_stems(dir2)
    dir_cache.get_stems(dir3)

    dir_cache.get_stems(dir4)
    assert dir1 not in dir_cache._cache
    assert dir2 in dir_cache._cache
    assert dir3 in dir_cache._cache
    assert dir4 in dir_cache._cache
