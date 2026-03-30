-- ========================================
-- SecondBrain 数据库 v2.0 新表结构
-- 创建时间：2026-03-30
-- 说明：规范化数据库设计，支持高级查询功能
-- ========================================

-- ========================================
-- 核心表
-- ========================================

-- 1. 文档主表 (规范化文档元数据)
CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    vault_name TEXT DEFAULT 'NanobotMemory',
    checksum TEXT,
    doc_type TEXT DEFAULT 'default',  -- faq/technical/blog/legal/meeting/default
    priority INTEGER DEFAULT 5,       -- 1-9
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    indexed_at TIMESTAMP
);

-- 2. 分块内容表
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,        -- doc_id#chunk_index
    doc_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    heading_level INTEGER,            -- 标题层级
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
);

-- 3. 向量存储表 (sqlite-vec 虚拟表)
-- 注意：需要在加载 sqlite_vec 扩展后创建
-- CREATE VIRTUAL TABLE IF NOT EXISTS vectors_vec USING vec0(
--     chunk_id TEXT PRIMARY KEY,
--     embedding float[512]
-- );

-- 4. 全文检索索引 (FTS5)
-- 注意：需要在创建 chunks 表后创建
-- CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
--     chunk_id,
--     content,
--     content='chunks',
--     content_rowid='rowid'
-- );

-- ========================================
-- 元数据表
-- ========================================

-- 5. 标签表 (规范化标签管理)
CREATE TABLE IF NOT EXISTS tags (
    tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_name TEXT UNIQUE NOT NULL,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. 文档 - 标签关联表
CREATE TABLE IF NOT EXISTS document_tags (
    doc_id TEXT NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (doc_id, tag_id),
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(tag_id) ON DELETE CASCADE
);

-- 7. Frontmatter 存储表 (JSON 格式)
CREATE TABLE IF NOT EXISTS frontmatter (
    doc_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,  -- JSON 格式存储完整 frontmatter
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
);

-- ========================================
-- 链接关系表
-- ========================================

-- 8. 链接表 (存储笔记间的链接关系)
CREATE TABLE IF NOT EXISTS links (
    link_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_doc_id TEXT NOT NULL,
    target_doc_id TEXT,
    target_file_path TEXT,
    link_text TEXT,
    link_type TEXT DEFAULT 'internal',  -- internal/external/image
    is_broken INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
);

-- ========================================
-- 索引
-- ========================================

-- 文档索引
CREATE INDEX IF NOT EXISTS idx_documents_file_path ON documents(file_path);
CREATE INDEX IF NOT EXISTS idx_documents_doc_type ON documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_documents_priority ON documents(priority);
CREATE INDEX IF NOT EXISTS idx_documents_vault ON documents(vault_name);
CREATE INDEX IF NOT EXISTS idx_documents_updated ON documents(updated_at);

-- 分块索引
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_heading ON chunks(heading_level);

-- 标签索引
CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(tag_name);
CREATE INDEX IF NOT EXISTS idx_document_tags_doc_id ON document_tags(doc_id);
CREATE INDEX IF NOT EXISTS idx_document_tags_tag_id ON document_tags(tag_id);

-- 链接索引
CREATE INDEX IF NOT EXISTS idx_links_source ON links(source_doc_id);
CREATE INDEX IF NOT EXISTS idx_links_target ON links(target_doc_id);
CREATE INDEX IF NOT EXISTS idx_links_broken ON links(is_broken);
CREATE INDEX IF NOT EXISTS idx_links_type ON links(link_type);

-- ========================================
-- 视图
-- ========================================

-- 9. 索引统计视图
CREATE VIEW IF NOT EXISTS v_index_stats AS
SELECT 
    (SELECT COUNT(*) FROM documents) as doc_count,
    (SELECT COUNT(*) FROM chunks) as chunk_count,
    (SELECT COUNT(*) FROM tags) as tag_count,
    (SELECT COUNT(*) FROM links) as link_count,
    (SELECT COUNT(*) FROM links WHERE is_broken = 1) as broken_link_count,
    (SELECT COUNT(DISTINCT file_path) FROM documents) as file_count,
    (SELECT COUNT(*) FROM frontmatter) as frontmatter_count;

-- 10. 标签使用统计视图
CREATE VIEW IF NOT EXISTS v_tag_stats AS
SELECT 
    t.tag_id,
    t.tag_name,
    t.usage_count,
    COUNT(dt.doc_id) as actual_count,
    (SELECT COUNT(*) FROM document_tags dt2 WHERE dt2.tag_id = t.tag_id) as link_count
FROM tags t
LEFT JOIN document_tags dt ON t.tag_id = dt.tag_id
GROUP BY t.tag_id
ORDER BY actual_count DESC;

-- 11. 文档类型分布视图
CREATE VIEW IF NOT EXISTS v_doc_type_stats AS
SELECT 
    doc_type,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / NULLIF((SELECT COUNT(*) FROM documents), 0), 2) as percentage
FROM documents
GROUP BY doc_type
ORDER BY count DESC;

-- 12. 优先级分布视图
CREATE VIEW IF NOT EXISTS v_priority_stats AS
SELECT 
    priority,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / NULLIF((SELECT COUNT(*) FROM documents), 0), 2) as percentage
FROM documents
GROUP BY priority
ORDER BY priority DESC;

-- 13. 文档详细信息视图 (包含标签和链接统计)
CREATE VIEW IF NOT EXISTS v_document_details AS
SELECT 
    d.doc_id,
    d.file_path,
    d.vault_name,
    d.doc_type,
    d.priority,
    d.created_at,
    d.updated_at,
    d.indexed_at,
    (SELECT COUNT(*) FROM document_tags dt WHERE dt.doc_id = d.doc_id) as tag_count,
    (SELECT COUNT(*) FROM links WHERE source_doc_id = d.doc_id) as out_link_count,
    (SELECT COUNT(*) FROM links WHERE target_doc_id = d.doc_id) as in_link_count,
    (SELECT GROUP_CONCAT(t.tag_name, ', ') FROM document_tags dt 
     JOIN tags t ON dt.tag_id = t.tag_id WHERE dt.doc_id = d.doc_id) as tags
FROM documents d;

-- ========================================
-- 触发器 (自动更新统计)
-- ========================================

-- 更新文档更新时间触发器
CREATE TRIGGER IF NOT EXISTS trg_documents_update_timestamp 
AFTER UPDATE ON documents
BEGIN
    UPDATE documents SET updated_at = CURRENT_TIMESTAMP WHERE doc_id = NEW.doc_id;
END;

-- 更新标签使用次数触发器 (插入)
CREATE TRIGGER IF NOT EXISTS trg_document_tags_insert 
AFTER INSERT ON document_tags
BEGIN
    UPDATE tags SET usage_count = usage_count + 1 WHERE tag_id = NEW.tag_id;
END;

-- 更新标签使用次数触发器 (删除)
CREATE TRIGGER IF NOT EXISTS trg_document_tags_delete 
AFTER DELETE ON document_tags
BEGIN
    UPDATE tags SET usage_count = usage_count - 1 WHERE tag_id = OLD.tag_id;
END;

-- ========================================
-- 说明
-- ========================================

-- 使用示例:
-- 1. 创建表结构:
--    sqlite3 semantic_index.db < create_new_schema.sql
--
-- 2. 迁移数据:
--    使用 migrate_to_v2.py 脚本
--
-- 3. 查询统计:
--    SELECT * FROM v_index_stats;
--    SELECT * FROM v_tag_stats;
--    SELECT * FROM v_doc_type_stats;
--
-- 4. 查询文档详情:
--    SELECT * FROM v_document_details WHERE doc_id = 'xxx';
--
-- 5. 查找断裂链接:
--    SELECT * FROM links WHERE is_broken = 1;
--
-- 6. 查找孤立笔记:
--    SELECT d.* FROM documents d
--    WHERE d.doc_id NOT IN (SELECT target_doc_id FROM links WHERE target_doc_id IS NOT NULL);
