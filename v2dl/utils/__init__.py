# v2dl/utils/__init__.py
from .common import count_files, enum_to_string
from .download import (
    AlbumTracker,
    BaseDownloadAPI,
    DownloadLogKeys,
    DownloadPathTool,
    DownloadStatus,
    ImageDownloadAPI,
)
from .factory import DownloadAPIFactory, ServiceType, TaskServiceFactory
from .multitask import (
    AsyncService,
    BaseTaskService,
    Task,
    ThreadingService,
)
from .parser import LinkParser
from .security import AccountManager, Encryptor, KeyManager, SecureFileHandler

# only import __all__ when using from automation import *
__all__ = [
    "AccountManager",
    "AlbumTracker",
    "AsyncService",
    "BaseDownloadAPI",
    "BaseTaskService",
    "DownloadAPIFactory",
    "DownloadLogKeys",
    "DownloadPathTool",
    "DownloadStatus",
    "Encryptor",
    "ImageDownloadAPI",
    "KeyManager",
    "LinkParser",
    "SecureFileHandler",
    "ServiceType",
    "Task",
    "TaskServiceFactory",
    "ThreadingService",
    "count_files",
    "enum_to_string",
]
