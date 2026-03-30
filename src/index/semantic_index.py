    def add_embeddings_batch(
        self,
        items: List[Tuple[str, List[float], Optional[Dict[str, Any]], Optional[str], int, int]]
    ) -> Tuple[int, int]:
        """
        批量添加向量嵌入

        Args:
            items: List of (doc_id, embedding, metadata, content, start_line, end_line)

        Returns:
            Tuple[int, int]: (成功数量，失败数量)
        """
        if not items:
            return 0, 0

        success_count = 0
        fail_count = 0

        try:
            with self._transaction() as conn:
                cur = conn.cursor()

                vec_rows = []
                meta_rows = []
                chunk_rows = []
                fts_rows = []

                for item in items:
                    # 兼容旧版本（3 个元素）和新版本（6 个元素）
                    if len(item) == 3:
                        doc_id, emb, meta = item
                        content, start_line, end_line = None, 0, 0
                    elif len(item) == 6:
                        doc_id, emb, meta, content, start_line, end_line = item
                    else:
                        logger.warning(f"Invalid item format: {item}")
                        fail_count += 1
                        continue

                    if len(emb) != self.dim:
                        logger.warning(f"Dim mismatch for {doc_id}: expected {self.dim}, got {len(emb)}")
                        fail_count += 1
                        continue

                    # 确保 meta 是字典或字符串
                    if isinstance(meta, str):
                        metadata_dict = json.loads(meta) if meta else {}
                    elif isinstance(meta, dict):
                        metadata_dict = meta
                    else:
                        metadata_dict = {}

                    doc_id_str = str(doc_id)

                    # 序列化 metadata 为 JSON 字符串
                    metadata_json = json.dumps(metadata_dict, ensure_ascii=False)

                    vec_rows.append((doc_id_str, sqlite_vec.serialize_float32(emb)))
                    meta_rows.append((doc_id_str, metadata_json))

                    # 如果有内容，准备 chunks 和 FTS 数据
                    if content is not None:
                        # 从 doc_id 中提取 chunk_index (格式：file_path#chunk_index)
                        chunk_index = 0
                        if '#' in doc_id_str:
                            try:
                                chunk_index = int(doc_id_str.rsplit('#', 1)[1])
                            except (ValueError, IndexError):
                                chunk_index = 0
                        
                        # 确保 start_line 和 end_line 是整数
                        sl = int(start_line) if start_line is not None else 0
                        el = int(end_line) if end_line is not None else 0
                        
                        chunk_rows.append((doc_id_str, chunk_index, content, sl, el))
                        fts_rows.append((doc_id_str, doc_id_str, chunk_index, content))

                # 批量插入 vectors
                if meta_rows:
                    logger.debug(f"Inserting {len(meta_rows)} rows into vectors table")
                    cur.executemany(
                        "INSERT OR REPLACE INTO vectors (doc_id, metadata) VALUES (?, ?)",
                        meta_rows
                    )

                # 批量插入 vectors_vec
                if vec_rows:
                    logger.debug(f"Inserting {len(vec_rows)} rows into vectors_vec table")
                    cur.executemany(
                        "INSERT OR REPLACE INTO vectors_vec (doc_id, embedding) VALUES (?, ?)",
                        vec_rows
                    )

                # 批量插入 chunks
                if chunk_rows:
                    logger.debug(f"Inserting {len(chunk_rows)} rows into chunks table")
                    cur.executemany("""
                    INSERT OR REPLACE INTO chunks (doc_id, chunk_index, content, start_line, end_line)
                    VALUES (?, ?, ?, ?, ?)
                    """, chunk_rows)

                # 批量插入 FTS
                if fts_rows:
                    logger.debug(f"Inserting {len(fts_rows)} rows into chunks_fts table")
                    cur.executemany("""
                    INSERT OR REPLACE INTO chunks_fts (rowid, doc_id, chunk_index, content)
                    VALUES (?, ?, ?, ?)
                    """, fts_rows)

                success_count = len(vec_rows)
                logger.info(f"Batch insert completed: {success_count} success, {fail_count} failed")
                return success_count, fail_count

        except Exception as e:
            logger.error(f"Batch insert failed at step: {e}")
            import traceback
            traceback.print_exc()
            return success_count, len(items) - success_count
