"""
异常处理模块

提供统一的异常类和错误处理机制
"""

from typing import Optional, Dict, Any
from enum import Enum


class ErrorCode(str, Enum):
    """错误代码"""
    # 配置错误
    INVALID_CONFIG = "INVALID_CONFIG"
    CONFIG_FILE_NOT_FOUND = "CONFIG_FILE_NOT_FOUND"
    CONFIG_PARSE_ERROR = "CONFIG_PARSE_ERROR"

    # 索引错误
    INDEX_NOT_FOUND = "INDEX_NOT_FOUND"
    INDEX_CORRUPTED = "INDEX_CORRUPTED"
    INDEX_BUILD_FAILED = "INDEX_BUILD_FAILED"

    # 搜索错误
    SEARCH_FAILED = "SEARCH_FAILED"
    QUERY_TOO_LONG = "QUERY_TOO_LONG"
    NO_RESULTS = "NO_RESULTS"

    # 文件错误
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_READ_ERROR = "FILE_READ_ERROR"
    FILE_WRITE_ERROR = "FILE_WRITE_ERROR"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_FILE_PATH = "INVALID_FILE_PATH"

    # 模型错误
    MODEL_LOAD_FAILED = "MODEL_LOAD_FAILED"
    MODEL_NOT_AVAILABLE = "MODEL_NOT_AVAILABLE"
    EMBEDDING_FAILED = "EMBEDDING_FAILED"

    # 数据库错误
    DATABASE_ERROR = "DATABASE_ERROR"
    DATABASE_LOCKED = "DATABASE_LOCKED"
    DATABASE_CONNECTION_FAILED = "DATABASE_CONNECTION_FAILED"

    # 验证错误
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_PARAMETER = "INVALID_PARAMETER"

    # 权限错误
    PERMISSION_DENIED = "PERMISSION_DENIED"
    ACCESS_DENIED = "ACCESS_DENIED"

    # 通用错误
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class SecondBrainError(Exception):
    """SecondBrain 基础异常类"""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        初始化异常

        Args:
            message: 错误消息
            code: 错误代码
            details: 错误详情
            cause: 原始异常
        """
        self.message = message
        self.code = code
        self.details = details or {}
        self.cause = cause

        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典

        Returns:
            Dict[str, Any]: 异常信息字典
        """
        return {
            "error": str(self.code),
            "message": self.message,
            "details": self.details
        }

    def __str__(self) -> str:
        """字符串表示"""
        if self.details:
            return f"[{self.code}] {self.message} - {self.details}"
        return f"[{self.code}] {self.message}"


class ConfigError(SecondBrainError):
    """配置错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, ErrorCode.INVALID_CONFIG, details, cause)


class IndexError(SecondBrainError):
    """索引错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, ErrorCode.INDEX_NOT_FOUND, details, cause)


class SearchError(SecondBrainError):
    """搜索错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, ErrorCode.SEARCH_FAILED, details, cause)


class FileError(SecondBrainError):
    """文件错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, ErrorCode.FILE_NOT_FOUND, details, cause)


class ModelError(SecondBrainError):
    """模型错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, ErrorCode.MODEL_LOAD_FAILED, details, cause)


class DatabaseError(SecondBrainError):
    """数据库错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, ErrorCode.DATABASE_ERROR, details, cause)


class ValidationError(SecondBrainError):
    """验证错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, ErrorCode.VALIDATION_ERROR, details, cause)


def handle_errors(func):
    """
    错误处理装饰器

    捕获异常并转换为 SecondBrainError

    Args:
        func: 要装饰的函数

    Returns:
        装饰后的函数
    """
    from functools import wraps
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.logger import get_logger

    logger = get_logger(__name__)

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SecondBrainError:
            # 已经是 SecondBrainError，直接抛出
            raise
        except FileNotFoundError as e:
            logger.error(f"文件未找到：{e}")
            raise FileError(f"文件未找到：{e}", cause=e)
        except PermissionError as e:
            logger.error(f"权限错误：{e}")
            raise FileError(f"权限被拒绝：{e}", cause=e)
        except (ValueError, TypeError) as e:
            logger.error(f"参数错误：{e}")
            raise ValidationError(f"参数错误：{e}", cause=e)
        except Exception as e:
            logger.error(f"未知错误：{e}")
            raise SecondBrainError(f"未知错误：{e}", ErrorCode.UNKNOWN_ERROR, cause=e)

    return wrapper


def safe_execute(func, default=None, log_error: bool = True):
    """
    安全执行函数

    捕获所有异常并返回默认值

    Args:
        func: 要执行的函数
        default: 默认返回值
        log_error: 是否记录错误

    Returns:
        函数执行结果或默认值
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.logger import get_logger

    logger = get_logger(__name__)

    try:
        return func()
    except Exception as e:
        if log_error:
            logger.error(f"执行失败：{e}")
        return default


if __name__ == "__main__":
    # 测试异常处理
    try:
        raise ConfigError("配置文件格式错误", details={"file": "config.yaml"})
    except SecondBrainError as e:
        print(f"捕获异常：{e}")
        print(f"异常字典：{e.to_dict()}")

    # 测试装饰器
    @handle_errors
    def test_function(value: int):
        if value < 0:
            raise ValueError("值不能为负数")
        return value * 2

    try:
        result = test_function(-1)
    except ValidationError as e:
        print(f"验证错误：{e}")

    # 测试安全执行
    result = safe_execute(lambda: 10 / 0, default=0)
    print(f"安全执行结果：{result}")

    print("✅ 异常处理测试完成")
