"""
元数据管理模块
提供标签管理、链接分析、反向链接查询等功能
"""

import sqlite3
import os
import re
from typing import List, Dict, Any, Optional, Set
from pathlib import Path

import sqlite_vec

from .models import NoteInfo, LinkInfo, TagInfo


class MetadataManager:
    """元数据管理器"""
    
    def __init__(self, db_path: str, vault_path: str = None):
        """
        初始化元数据管理器
        
        Args:
            db_path: 数据库路径
            vault_path: Vault 根路径（用于读取文件内容）
        """
        self.db_path = os.path.expanduser(db_path)
        self.vault_path = os.path.expanduser(vault_path) if vault_path else None
    
    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA encoding='UTF-8'")
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ==================== 标签管理 ====================
    
    def get_note_tags(self, doc_id: str) -> List[str]:
        """
        获取笔记的标签列表
        
        Args:
            doc_id: 文档 ID
        
        Returns:
            List[str]: 标签列表
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT t.tag_name FROM document_tags dt
            JOIN tags t ON dt.tag_id = t.tag_id
            WHERE dt.doc_id = ?
            ORDER BY t.tag_name
        """, (doc_id,))
        
        tags = [row["tag_name"] for row in cursor.fetchall()]
        conn.close()
        
        return tags
    
    def add_tag(self, doc_id: str, tag_name: str) -> bool:
        """
        添加标签到笔记
        
        Args:
            doc_id: 文档 ID
            tag_name: 标签名称
        
        Returns:
            bool: 是否成功
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # 确保标签存在
            cursor.execute("INSERT OR IGNORE INTO tags (tag_name) VALUES (?)", (tag_name,))
            
            # 获取 tag_id
            cursor.execute("SELECT tag_id FROM tags WHERE tag_name = ?", (tag_name,))
            tag_row = cursor.fetchone()
            
            if not tag_row:
                conn.close()
                return False
            
            tag_id = tag_row["tag_id"]
            
            # 添加关联
            cursor.execute("""
                INSERT OR IGNORE INTO document_tags (doc_id, tag_id)
                VALUES (?, ?)
            """, (doc_id, tag_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"添加标签失败：{e}")
            conn.close()
            return False
    
    def remove_tag(self, doc_id: str, tag_name: str) -> bool:
        """
        从笔记移除标签
        
        Args:
            doc_id: 文档 ID
            tag_name: 标签名称
        
        Returns:
            bool: 是否成功
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # 获取 tag_id
            cursor.execute("SELECT tag_id FROM tags WHERE tag_name = ?", (tag_name,))
            tag_row = cursor.fetchone()
            
            if not tag_row:
                conn.close()
                return False
            
            tag_id = tag_row["tag_id"]
            
            # 删除关联
            cursor.execute("""
                DELETE FROM document_tags
                WHERE doc_id = ? AND tag_id = ?
            """, (doc_id, tag_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"移除标签失败：{e}")
            conn.close()
            return False
    
    def search_by_tags(
        self,
        tags: List[str],
        mode: str = "any",
        top_k: int = 10
    ) -> List[NoteInfo]:
        """
        按标签搜索笔记
        
        Args:
            tags: 标签列表
            mode: 匹配模式 (any/all)
            top_k: 返回结果数
        
        Returns:
            List[NoteInfo]: 匹配的笔记信息
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        if mode == "all":
            # 必须包含所有标签
            placeholders = ",".join(["?" for _ in tags])
            query = f"""
                SELECT d.* FROM documents d
                JOIN document_tags dt ON d.doc_id = dt.doc_id
                JOIN tags t ON dt.tag_id = t.tag_id
                WHERE t.tag_name IN ({placeholders})
                GROUP BY d.doc_id
                HAVING COUNT(DISTINCT t.tag_name) = ?
                LIMIT ?
            """
            cursor.execute(query, tags + [len(tags), top_k])
        else:
            # 包含任意标签
            placeholders = ",".join(["?" for _ in tags])
            query = f"""
                SELECT DISTINCT d.* FROM documents d
                JOIN document_tags dt ON d.doc_id = dt.doc_id
                JOIN tags t ON dt.tag_id = t.tag_id
                WHERE t.tag_name IN ({placeholders})
                LIMIT ?
            """
            cursor.execute(query, tags + [top_k])
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_note_info(row) for row in rows]
    
    # ==================== 链接分析 ====================
    
    def extract_links_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        从文件中提取链接
        
        Args:
            file_path: 文件路径（相对路径）
        
        Returns:
            List[Dict]: 链接信息列表
        """
        # 拼接绝对路径
        if self.vault_path:
            full_path = os.path.join(self.vault_path, file_path)
        else:
            full_path = file_path
        
        if not os.path.exists(full_path):
            return []
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return []
        
        links = []
        
        # 匹配 Markdown 链接：[text](link) 或 [[link]]
        # 标准 Markdown 链接
        md_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        for match in re.finditer(md_pattern, content):
            link_text = match.group(1)
            link_target = match.group(2)
            
            # 跳过外部链接和图片
            if link_target.startswith('http') or link_target.endswith(('.png', '.jpg', '.gif')):
                continue
            
            links.append({
                "link_text": link_text,
                "target": link_target,
                "link_type": "internal"
            })
        
        # Obsidian 内部链接：[[link]]
        obsidian_pattern = r'\[\[([^\]]+)\]\]'
        for match in re.finditer(obsidian_pattern, content):
            link_target = match.group(1)
            
            # 分离锚点
            if '|' in link_target:
                target, display = link_target.split('|', 1)
                link_text = display
            else:
                target = link_target
                link_text = link_target
            
            links.append({
                "link_text": link_text,
                "target": target,
                "link_type": "internal"
            })
        
        return links
    
    def scan_all_links(self) -> int:
        """
        扫描所有文件并更新链接关系
        
        Returns:
            int: 扫描的文件数
        """
        if not self.vault_path:
            print("⚠️  vault_path 未设置，无法扫描文件")
            return 0
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 清空现有链接
        cursor.execute("DELETE FROM links")
        
        scanned_count = 0
        
        # 遍历所有文件
        for root, dirs, files in os.walk(self.vault_path):
            for file in files:
                if not file.endswith('.md'):
                    continue
                
                file_path = os.path.relpath(os.path.join(root, file), self.vault_path)
                
                # 获取 doc_id
                cursor.execute("SELECT doc_id FROM documents WHERE file_path = ?", (file_path,))
                row = cursor.fetchone()
                
                if not row:
                    continue
                
                doc_id = row["doc_id"]
                scanned_count += 1
                
                # 提取链接
                links = self.extract_links_from_file(file_path)
                
                for link in links:
                    target = link["target"]
                    
                    # 尝试解析目标文档
                    target_doc_id = self._resolve_link_target(target, file_path)
                    
                    # 插入链接记录
                    cursor.execute("""
                        INSERT INTO links 
                        (source_doc_id, target_doc_id, target_file_path, link_text, link_type, is_broken)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        doc_id,
                        target_doc_id,
                        target if not target_doc_id else None,
                        link["link_text"],
                        link["link_type"],
                        0 if target_doc_id else 1
                    ))
        
        conn.commit()
        
        # 获取链接数
        cursor.execute("SELECT COUNT(*) FROM links")
        link_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"✅ 扫描完成：{scanned_count} 个文件，发现 {link_count} 个链接")
        return scanned_count
    
    def _resolve_link_target(self, target: str, source_file_path: str) -> Optional[str]:
        """
        解析链接目标，返回 doc_id
        
        Args:
            target: 链接目标
            source_file_path: 源文件路径
        
        Returns:
            Optional[str]: doc_id 或 None
        """
        # 移除锚点
        if '#' in target:
            target = target.split('#')[0]
        
        # 处理相对路径
        if not target.startswith('/'):
            source_dir = os.path.dirname(source_file_path)
            target = os.path.normpath(os.path.join(source_dir, target))
        
        # 去掉 .md 扩展名
        if target.endswith('.md'):
            target = target[:-3]
        
        # 查找匹配的 doc_id
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 尝试精确匹配
        cursor.execute("SELECT doc_id FROM documents WHERE file_path = ?", (target + '.md',))
        row = cursor.fetchone()
        
        if row:
            conn.close()
            return row["doc_id"]
        
        # 尝试模糊匹配
        cursor.execute("SELECT doc_id FROM documents WHERE file_path LIKE ?", (f"%{target}%",))
        row = cursor.fetchone()
        
        conn.close()
        return row["doc_id"] if row else None
    
    def get_backlinks(self, doc_id: str) -> List[LinkInfo]:
        """
        获取笔记的反向链接
        
        Args:
            doc_id: 文档 ID
        
        Returns:
            List[LinkInfo]: 反向链接列表
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT l.*, d.file_path as source_file_path
            FROM links l
            LEFT JOIN documents d ON l.source_doc_id = d.doc_id
            WHERE l.target_doc_id = ?
        """, (doc_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_link_info(row) for row in rows]
    
    def get_links(self, doc_id: str) -> List[LinkInfo]:
        """
        获取笔记的出站链接
        
        Args:
            doc_id: 文档 ID
        
        Returns:
            List[LinkInfo]: 出站链接列表
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT l.*, d.file_path as target_file_path
            FROM links l
            LEFT JOIN documents d ON l.target_doc_id = d.doc_id
            WHERE l.source_doc_id = ?
        """, (doc_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_link_info(row) for row in rows]
    
    def find_broken_links(self) -> List[LinkInfo]:
        """
        查找所有断裂链接
        
        Returns:
            List[LinkInfo]: 断裂链接列表
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT l.*, d.file_path as source_file_path
            FROM links l
            LEFT JOIN documents d ON l.source_doc_id = d.doc_id
            WHERE l.is_broken = 1
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_link_info(row) for row in rows]
    
    def find_orphaned_notes(self) -> List[str]:
        """
        查找孤立笔记（无入链）
        
        Returns:
            List[str]: 孤立笔记的 doc_id 列表
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT doc_id FROM documents
            WHERE doc_id NOT IN (
                SELECT target_doc_id FROM links WHERE target_doc_id IS NOT NULL
            )
            AND doc_id NOT IN (
                SELECT source_doc_id FROM links
            )
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [row["doc_id"] for row in rows]
    
    # ==================== 辅助方法 ====================
    
    def _row_to_note_info(self, row) -> NoteInfo:
        """转换数据库行到 NoteInfo"""
        # 获取标签
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.tag_name FROM document_tags dt
            JOIN tags t ON dt.tag_id = t.tag_id
            WHERE dt.doc_id = ?
        """, (row["doc_id"],))
        tags = [r["tag_name"] for r in cursor.fetchall()]
        conn.close()
        
        return NoteInfo(
            doc_id=row["doc_id"],
            file_path=row["file_path"],
            vault_name=row["vault_name"],
            title=self._extract_title(row["file_path"]),
            tags=tags,
            priority=row["priority"],
            doc_type=row["doc_type"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            indexed_at=row["indexed_at"]
        )
    
    def _row_to_link_info(self, row) -> LinkInfo:
        """转换数据库行到 LinkInfo"""
        return LinkInfo(
            link_id=row["link_id"],
            source_doc_id=row["source_doc_id"],
            source_file_path=row["source_file_path"] or "",
            target_doc_id=row["target_doc_id"],
            target_file_path=row["target_file_path"],
            link_text=row["link_text"],
            link_type=row["link_type"] or "internal",
            is_broken=bool(row["is_broken"]),
            created_at=row["created_at"]
        )
    
    def _extract_title(self, file_path: str) -> str:
        """从文件路径提取标题"""
        if not file_path:
            return "Untitled"
        
        path = Path(file_path)
        title = path.stem
        title = title.replace("-", " ").replace("_", " ")
        
        return title.title()


# 测试
if __name__ == "__main__":
    import os
    
    db_path = os.path.expanduser("~/.local/share/secondbrain/semantic_index.db")
    vault_path = os.path.expanduser("~/NanobotMemory")
    
    manager = MetadataManager(db_path, vault_path)
    
    print("🔍 测试元数据管理模块...")
    
    # 测试 1: 扫描链接
    print("\n1. 扫描所有文件链接:")
    count = manager.scan_all_links()
    print(f"   扫描了 {count} 个文件")
    
    # 测试 2: 查找断裂链接
    print("\n2. 查找断裂链接:")
    broken = manager.find_broken_links()
    print(f"   发现 {len(broken)} 个断裂链接")
    for link in broken[:3]:
        print(f"   - {link.source_file_path} -> {link.target_file_path}")
    
    # 测试 3: 查找孤立笔记
    print("\n3. 查找孤立笔记:")
    orphaned = manager.find_orphaned_notes()
    print(f"   发现 {len(orphaned)} 个孤立笔记")
    print(f"   示例：{orphaned[:3]}")
    
    print("\n✅ 测试完成!")
