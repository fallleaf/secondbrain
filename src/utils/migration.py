"""
数据迁移模块

提供索引和配置的版本控制和迁移功能
"""

import json
import shutil
from typing import Optional, Dict, List
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class Migration:
    """迁移定义"""
    version: str
    description: str
    up: callable
    down: Optional[callable] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class MigrationManager:
    """迁移管理器"""

    def __init__(self, data_dir: str):
        """
        初始化迁移管理器

        Args:
            data_dir: 数据目录
        """
        self.data_dir = Path(data_dir).expanduser().resolve()
        self.migrations_dir = self.data_dir / "migrations"
        self.version_file = self.data_dir / "version.json"

        # 创建目录
        self.migrations_dir.mkdir(parents=True, exist_ok=True)

        # 加载当前版本
        self.current_version = self._load_version()

        # 注册的迁移
        self._migrations: Dict[str, Migration] = {}

    def _load_version(self) -> str:
        """
        加载当前版本

        Returns:
            str: 当前版本
        """
        if not self.version_file.exists():
            return "0.0.0"

        with open(self.version_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("version", "0.0.0")

    def _save_version(self, version: str) -> None:
        """
        保存当前版本

        Args:
            version: 版本号
        """
        with open(self.version_file, 'w', encoding='utf-8') as f:
            json.dump({
                "version": version,
                "updated_at": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)

    def register(self, migration: Migration) -> None:
        """
        注册迁移

        Args:
            migration: 迁移定义
        """
        self._migrations[migration.version] = migration

    def get_pending_migrations(self) -> List[Migration]:
        """
        获取待执行的迁移

        Returns:
            List[Migration]: 待执行的迁移列表
        """
        # 按版本号排序
        sorted_versions = sorted(self._migrations.keys())

        pending = []
        for version in sorted_versions:
            if version > self.current_version:
                pending.append(self._migrations[version])

        return pending

    def migrate(self, target_version: Optional[str] = None) -> None:
        """
        执行迁移

        Args:
            target_version: 目标版本，None 表示迁移到最新版本
        """
        pending = self.get_pending_migrations()

        if not pending:
            print("✅ 没有待执行的迁移")
            return

        print(f"🔄 开始迁移，当前版本：{self.current_version}")

        for migration in pending:
            if target_version and migration.version > target_version:
                break

            print(f"  执行迁移 {migration.version}: {migration.description}")

            try:
                # 执行迁移
                migration.up()

                # 更新版本
                self.current_version = migration.version
                self._save_version(migration.version)

                print(f"  ✅ 迁移 {migration.version} 完成")
            except Exception as e:
                print(f"  ❌ 迁移 {migration.version} 失败：{e}")
                raise

        print(f"✅ 迁移完成，当前版本：{self.current_version}")

    def rollback(self, target_version: str) -> None:
        """
        回滚迁移

        Args:
            target_version: 目标版本
        """
        # 按版本号降序排序
        sorted_versions = sorted(self._migrations.keys(), reverse=True)

        print(f"🔄 开始回滚，当前版本：{self.current_version}")

        for version in sorted_versions:
            if version <= target_version:
                break

            migration = self._migrations.get(version)
            if not migration or not migration.down:
                continue

            print(f"  回滚迁移 {version}: {migration.description}")

            try:
                # 执行回滚
                migration.down()

                # 更新版本
                self.current_version = version
                self._save_version(version)

                print(f"  ✅ 回滚迁移 {version} 完成")
            except Exception as e:
                print(f"  ❌ 回滚迁移 {version} 失败：{e}")
                raise

        print(f"✅ 回滚完成，当前版本：{self.current_version}")

    def backup(self, name: Optional[str] = None) -> str:
        """
        备份数据

        Args:
            name: 备份名称，None 表示使用时间戳

        Returns:
            str: 备份路径
        """
        if name is None:
            name = datetime.now().strftime("%Y%m%d_%H%M%S")

        backup_dir = self.data_dir / "backups" / name
        backup_dir.mkdir(parents=True, exist_ok=True)

        # 备份索引文件
        index_files = list(self.data_dir.glob("*.db"))
        for index_file in index_files:
            shutil.copy2(index_file, backup_dir / index_file.name)

        # 备份配置文件
        config_files = list(self.data_dir.glob("*.json"))
        for config_file in config_files:
            shutil.copy2(config_file, backup_dir / config_file.name)

        print(f"✅ 备份完成：{backup_dir}")
        return str(backup_dir)

    def restore(self, backup_name: str) -> None:
        """
        恢复备份

        Args:
            backup_name: 备份名称
        """
        backup_dir = self.data_dir / "backups" / backup_name

        if not backup_dir.exists():
            raise FileNotFoundError(f"备份不存在：{backup_name}")

        print(f"🔄 开始恢复备份：{backup_name}")

        # 恢复索引文件
        index_files = list(backup_dir.glob("*.db"))
        for index_file in index_files:
            shutil.copy2(index_file, self.data_dir / index_file.name)

        # 恢复配置文件
        config_files = list(backup_dir.glob("*.json"))
        for config_file in config_files:
            shutil.copy2(config_file, self.data_dir / config_file.name)

        print("✅ 恢复完成")


def create_migration_manager(data_dir: str) -> MigrationManager:
    """
    创建迁移管理器并注册默认迁移

    Args:
        data_dir: 数据目录

    Returns:
        MigrationManager: 迁移管理器
    """
    manager = MigrationManager(data_dir)

    # 注册迁移
    manager.register(Migration(
        version="1.0.0",
        description="初始版本",
        up=lambda: print("初始化索引结构")
    ))

    manager.register(Migration(
        version="1.1.0",
        description="添加向量索引支持",
        up=lambda: print("创建向量索引表"),
        down=lambda: print("删除向量索引表")
    ))

    manager.register(Migration(
        version="1.2.0",
        description="添加优先级系统",
        up=lambda: print("创建优先级配置"),
        down=lambda: print("删除优先级配置")
    ))

    return manager


if __name__ == "__main__":
    # 测试迁移管理器
    import tempfile

    # 创建临时目录
    temp_dir = tempfile.mkdtemp()

    try:
        # 创建迁移管理器
        manager = create_migration_manager(temp_dir)

        print(f"当前版本：{manager.current_version}")
        print(f"待执行迁移：{len(manager.get_pending_migrations())}")

        # 执行迁移
        manager.migrate()

        print(f"迁移后版本：{manager.current_version}")

        # 备份
        backup_path = manager.backup()
        print(f"备份路径：{backup_path}")

        # 回滚
        manager.rollback("1.0.0")
        print(f"回滚后版本：{manager.current_version}")

        print("✅ 迁移管理器测试完成")

    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
