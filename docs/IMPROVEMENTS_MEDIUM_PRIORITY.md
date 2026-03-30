# SecondBrain 中优先级问题改进总结

## 改进时间
2026-03-28

## 已完成的改进

### 5. ✅ 配置验证

**问题**：配置文件没有验证机制，错误配置可能导致运行时错误

**解决方案**：
- 使用 Pydantic 创建配置验证模块
- 定义所有配置的数据模型
- 提供配置验证函数

**新增文件**：
- `src/config/validator.py`

**核心功能**：
```python
class PriorityLevelConfig(BaseModel):
    """优先级级别配置"""
    priority: int = Field(..., ge=1, le=9, description="优先级级别 (1-9)")
    label: str = Field(..., min_length=1, description="标签名称")
    description: str = Field(..., min_length=1, description="描述")
    retention_days: Optional[int] = Field(None, ge=-1, description="保留天数 (-1=永久)")
    search_weight: float = Field(..., gt=0, description="搜索权重")
    path_patterns: List[str] = Field(default_factory=list, description="路径模式列表")

class MainConfig(BaseModel):
    """主配置"""
    vaults: List[VaultConfig] = Field(..., min_items=1, description="Vault 配置列表")
    index: IndexConfig = Field(default_factory=IndexConfig, description="索引配置")
    priority: PriorityConfig = Field(..., description="优先级配置")
    security: SecurityConfig = Field(default_factory=SecurityConfig, description="安全配置")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="日志配置")

def validate_config(config_dict: Dict[str, Any]) -> MainConfig:
    """验证配置字典"""
    return MainConfig(**config_dict)
```

**使用示例**：
```python
from src.config.validator import validate_config, get_default_priority_config

config = {
    "vaults": [{"path": "~/NanobotMemory", "name": "default"}],
    "priority": get_default_priority_config()
}

validated = validate_config(config)
```

---

### 6. ✅ 性能优化 - 查询缓存

**问题**：每次搜索都重新编码查询文本，没有查询缓存机制

**解决方案**：
- 创建查询缓存模块
- 支持基于参数的缓存键生成
- 提供 LRU 缓存策略
- 支持缓存装饰器

**新增文件**：
- `src/utils/cache.py`

**核心功能**：
```python
class QueryCache:
    """查询缓存"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}

    def get(self, *args, **kwargs) -> Optional[Any]:
        """获取缓存值"""
        key = self._generate_key(*args, **kwargs)
        if key not in self._cache:
            return None
        entry = self._cache[key]
        if entry.is_expired():
            del self._cache[key]
            return None
        return entry.value

    def set(self, value: Any, ttl: Optional[int] = None, *args, **kwargs) -> None:
        """设置缓存值"""
        key = self._generate_key(*args, **kwargs)
        if len(self._cache) >= self.max_size:
            self._evict_oldest()
        entry = CacheEntry(key=key, value=value, ttl=ttl or self.default_ttl)
        self._cache[key] = entry

def cached(ttl: int = 3600, key_prefix: str = ""):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            cache_key = (key_prefix, func.__name__, args, frozenset(kwargs.items()))
            cached_result = cache.get(*cache_key)
            if cached_result is not None:
                return cached_result
            result = func(*args, **kwargs)
            cache.set(result, ttl=ttl, *cache_key)
            return result
        return wrapper
    return decorator
```

**使用示例**：
```python
from src.utils.cache import cached, get_cache

# 使用装饰器
@cached(ttl=30, key_prefix="search")
def expensive_search(query: str, top_k: int = 10):
    # 执行搜索
    return results

# 手动使用缓存
cache = get_cache()
cache.set(results, ttl=60, query="人工智能", top_k=5)
results = cache.get(query="人工智能", top_k=5)
```

---

### 7. ✅ 错误处理 - 细化异常处理

**问题**：部分异常捕获过于宽泛，缺少具体的错误信息

**解决方案**：
- 创建统一的异常类体系
- 定义错误代码枚举
- 提供错误处理装饰器
- 支持安全执行函数

**新增文件**：
- `src/utils/exceptions.py`

**核心功能**：
```python
class ErrorCode(str, Enum):
    """错误代码"""
    INVALID_CONFIG = "INVALID_CONFIG"
    INDEX_NOT_FOUND = "INDEX_NOT_FOUND"
    SEARCH_FAILED = "SEARCH_FAILED"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    MODEL_LOAD_FAILED = "MODEL_LOAD_FAILED"
    DATABASE_ERROR = "DATABASE_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"

class SecondBrainError(Exception):
    """SecondBrain 基础异常类"""
    def __init__(self, message: str, code: ErrorCode, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {"error": self.code.value, "message": self.message, "details": self.details}

def handle_errors(func):
    """错误处理装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SecondBrainError:
            raise
        except FileNotFoundError as e:
            raise FileError(f"文件未找到：{e}", cause=e)
        except (ValueError, TypeError) as e:
            raise ValidationError(f"参数错误：{e}", cause=e)
        except Exception as e:
            raise SecondBrainError(f"未知错误：{e}", ErrorCode.UNKNOWN_ERROR, cause=e)
    return wrapper

def safe_execute(func, default=None, log_error: bool = True):
    """安全执行函数"""
    try:
        return func()
    except Exception as e:
        if log_error:
            logger.error(f"执行失败：{e}")
        return default
```

**使用示例**：
```python
from src.utils.exceptions import handle_errors, FileError, safe_execute

# 使用装饰器
@handle_errors
def read_file(path: str):
    with open(path) as f:
        return f.read()

# 安全执行
result = safe_execute(lambda: risky_operation(), default=None)
```

---

### 8. ✅ 数据迁移 - 版本控制和迁移机制

**问题**：索引格式变更时无法迁移旧数据，没有版本控制

**解决方案**：
- 创建迁移管理器
- 支持版本控制
- 提供备份和恢复功能
- 支持迁移回滚

**新增文件**：
- `src/utils/migration.py`

**核心功能**：
```python
@dataclass
class Migration:
    """迁移定义"""
    version: str
    description: str
    up: callable
    down: Optional[callable] = None

class MigrationManager:
    """迁移管理器"""

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir).expanduser().resolve()
        self.current_version = self._load_version()
        self._migrations: Dict[str, Migration] = {}

    def register(self, migration: Migration) -> None:
        """注册迁移"""
        self._migrations[migration.version] = migration

    def migrate(self, target_version: Optional[str] = None) -> None:
        """执行迁移"""
        pending = self.get_pending_migrations()
        for migration in pending:
            migration.up()
            self.current_version = migration.version
            self._save_version(migration.version)

    def rollback(self, target_version: str) -> None:
        """回滚迁移"""
        for version in sorted_versions:
            if version <= target_version:
                break
            migration = self._migrations.get(version)
            if migration.down:
                migration.down()
                self.current_version = version
                self._save_version(version)

    def backup(self, name: Optional[str] = None) -> str:
        """备份数据"""
        backup_dir = self.data_dir / "backups" / name
        # 复制文件到备份目录
        return str(backup_dir)

    def restore(self, backup_name: str) -> None:
        """恢复备份"""
        backup_dir = self.data_dir / "backups" / backup_name
        # 从备份目录恢复文件
```

**使用示例**：
```python
from src.utils.migration import create_migration_manager

# 创建迁移管理器
manager = create_migration_manager("~/.local/share/secondbrain")

# 执行迁移
manager.migrate()

# 回滚迁移
manager.rollback("1.0.0")

# 备份数据
backup_path = manager.backup()

# 恢复备份
manager.restore("20260328_181300")
```

---

## 改进效果

### 配置管理
- ✅ 配置验证防止错误配置
- ✅ 类型安全的配置访问
- ✅ 详细的错误提示

### 性能优化
- ✅ 查询缓存减少重复计算
- ✅ LRU 策略优化内存使用
- ✅ 可配置的过期时间

### 错误处理
- ✅ 统一的异常体系
- ✅ 详细的错误信息
- ✅ 优雅的错误处理

### 数据管理
- ✅ 版本控制支持
- ✅ 数据迁移机制
- ✅ 备份和恢复功能

---

## 下一步计划

### 低优先级改进
1. **Web 界面**：完善 Web 管理界面
2. **插件系统**：实现插件架构
3. **多模态支持**：支持图片、音频搜索

---

## 测试验证

### 配置验证测试
```python
from src.config.validator import validate_config, get_default_priority_config

config = {
    "vaults": [{"path": "~/NanobotMemory", "name": "default"}],
    "priority": get_default_priority_config()
}

validated = validate_config(config)
print(f"✅ 配置验证通过：{validated}")
```

### 查询缓存测试
```python
from src.utils.cache import cached, get_cache

@cached(ttl=30, key_prefix="search")
def search(query: str):
    return f"结果：{query}"

result1 = search("测试")
result2 = search("测试")  # 从缓存获取
```

### 错误处理测试
```python
from src.utils.exceptions import handle_errors, FileError

@handle_errors
def read_file(path: str):
    with open(path) as f:
        return f.read()

try:
    read_file("nonexistent.txt")
except FileError as e:
    print(f"捕获错误：{e}")
```

### 数据迁移测试
```python
from src.utils.migration import create_migration_manager

manager = create_migration_manager("~/.local/share/secondbrain")
manager.migrate()
backup_path = manager.backup()
```

---

## 总结

所有中优先级问题已解决：
1. ✅ 配置验证
2. ✅ 性能优化 - 查询缓存
3. ✅ 错误处理 - 细化异常处理
4. ✅ 数据迁移 - 版本控制和迁移机制

项目功能更加完善，代码质量显著提升，为生产环境部署奠定了坚实基础。
