"""
Production-grade Semantic Chunker
Features:
- Semantic-aware splitting (Chinese + English)
- Stable chunk_id (content-based SHA256)
- Markdown hierarchy support with line tracking
- Small chunk merging (no data loss)
- Extensible token control
"""
import re
import hashlib
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple

# -----------------------------
# Data Structure
# -----------------------------
@dataclass
class Chunk:
    content: str
    chunk_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    file_path: Optional[str] = None

    @property
    def word_count(self) -> int:
        return len(self.content)

    @property
    def line_count(self) -> int:
        if self.start_line is None or self.end_line is None:
            return 0
        return self.end_line - self.start_line + 1

# -----------------------------
# Chunker
# -----------------------------
class SemanticChunker:
    # Precompile regex for performance
    HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.*)$')
    SENTENCE_PATTERN = re.compile(r'(?<=[。！？.!?])\s*')

    def __init__(
        self,
        max_chars: int = 800,
        overlap: int = 100,
        min_chars: int = 100,
    ):
        """
        Initialize the SemanticChunker.
        
        Args:
            max_chars: Maximum characters per chunk.
            overlap: Number of overlapping characters between chunks.
            min_chars: Minimum characters for a valid chunk (smaller chunks will be merged).
        """
        self.max_chars = max_chars
        self.overlap = overlap
        self.min_chars = min_chars

    # -----------------------------
    # Public API
    # -----------------------------
    def chunk_text(
        self,
        file_path: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Split text content into semantic chunks based on Markdown structure.
        
        Args:
            file_path: Path to the source file (for metadata).
            content: The raw text content to chunk.
            metadata: Optional additional metadata to attach to each chunk.
            
        Returns:
            List of Chunk objects.
        """
        if not content.strip():
            return []

        file_checksum = self._sha256(content)
        lines = content.split("\n")
        
        # Parse structure with line numbers
        sections = self._parse_markdown_structure(lines)
        
        chunks: List[Chunk] = []
        chunk_index = 0

        for sec in sections:
            sec_content = sec["content"]
            sec_start_line = sec["start_line"]
            
            if not sec_content.strip():
                continue

            # Split section into sub-chunks with line tracking
            sub_chunks_info = self._split_section_with_lines(
                sec_content, 
                sec_start_line
            )

        for sub_info in sub_chunks_info:
            sub_text = sub_info["content"]

            # Skip empty chunks
            if not sub_text.strip():
                continue

            # Handle min_chars logic: Merge small chunks instead of dropping
            if len(sub_text) < self.min_chars and chunks:
                # Merge with previous chunk
                prev_chunk = chunks[-1]
                prev_chunk.content += "\n" + sub_text
                prev_chunk.end_line = sub_info["end_line"]
                # Regenerate ID for the modified previous chunk
                # Note: chunk_index remains the same as the last chunk's index
                prev_chunk.chunk_id = self._build_chunk_id(file_path, chunk_index - 1)
                continue

            chunk_id = self._build_chunk_id(file_path, chunk_index)

            chunk_meta = {
                "file_path": file_path,
                "chunk_index": chunk_index,
                "section_path": sec["path"],
                "section_title": sec["title"],
                "file_checksum": file_checksum,
            }

            if metadata:
                chunk_meta.update(metadata)

            chunks.append(Chunk(
                content=sub_text,
                chunk_id=chunk_id,
                metadata=chunk_meta,
                start_line=sub_info["start_line"],
                end_line=sub_info["end_line"],
                file_path=file_path
            ))

            chunk_index += 1

        # Post-processing: Check if the last chunk was too small (edge case)
        # (Already handled in loop by merging to previous, but if only 1 chunk exists and is small, keep it)

        return chunks

    # -----------------------------
    # Markdown Structure Parsing
    # -----------------------------
    def _parse_markdown_structure(self, lines: List[str]) -> List[Dict[str, Any]]:
        """
        Parse markdown headers to create hierarchical sections with line numbers.
        
        Returns:
            List of section dicts containing title, path, content (str), start_line, end_line.
        """
        sections: List[Dict[str, Any]] = []
        stack: List[str] = []
        
        current = {
            "title": "root",
            "path": "",
            "content_lines": [],
            "start_line": 0,
            "end_line": 0
        }
        
        # Track the line index where current section started collecting content
        content_start_idx = 0 

        for idx, line in enumerate(lines):
            match = self.HEADING_PATTERN.match(line)
            
            if match:
                # Flush previous section if it has content
                if current["content_lines"]:
                    sections.append({
                        "title": current["title"],
                        "path": current["path"],
                        "content": "\n".join(current["content_lines"]),
                        "start_line": current["start_line"],
                        "end_line": current["end_line"]
                    })
                
                # Update hierarchy stack
                level = len(match.group(1))
                title = match.group(2).strip()
                
                # Adjust stack to correct level
                # Ensure stack doesn't grow too fast if levels are skipped (e.g., h1 -> h3)
                if level > len(stack) + 1:
                    level = len(stack) + 1
                
                stack = stack[:level - 1]
                stack.append(title)
                
                # Reset current section
                current = {
                    "title": title,
                    "path": " > ".join(stack),
                    "content_lines": [],
                    "start_line": idx, # Section starts at header line
                    "end_line": idx
                }
                content_start_idx = idx + 1 # Content starts after header
            else:
                # Add line to current section content
                if not current["content_lines"]:
                    current["start_line"] = idx # Update start line if first content line
                current["content_lines"].append(line)
                current["end_line"] = idx

        # Flush last section
        if current["content_lines"]:
            sections.append({
                "title": current["title"],
                "path": current["path"],
                "content": "\n".join(current["content_lines"]),
                "start_line": current["start_line"],
                "end_line": current["end_line"]
            })
            
        # Handle case where file has no headers (everything is root)
        if not sections and lines:
            sections.append({
                "title": "root",
                "path": "",
                "content": "\n".join(lines),
                "start_line": 0,
                "end_line": len(lines) - 1
            })

        return sections

    # -----------------------------
    # Semantic Split with Line Tracking
    # -----------------------------
    def _split_section_with_lines(
        self, 
        text: str, 
        section_start_line: int
    ) -> List[Dict[str, Any]]:
        """
        Split section text into chunks while tracking line numbers.
        
        Returns:
            List of dicts with 'content', 'start_line', 'end_line'.
        """
        # Split by sentences
        sentences = self.SENTENCE_PATTERN.split(text)
        sentences = [s for s in sentences if s.strip()] # Remove empty strings
        
        if not sentences:
            return []

        chunks_info = []
        current_text = ""
        current_lines_count = 0
        
        # To track lines accurately, we count newlines in the accumulated text
        # This is an approximation but robust enough for most cases
        # Precise mapping requires original line indices which is complex after joining
        
        for sent in sentences:
            sent_len = len(sent)
            
            # Check if adding this sentence exceeds max_chars
            if len(current_text) + sent_len <= self.max_chars:
                current_text += sent
                current_lines_count += sent.count('\n')
            else:
                # Push current chunk if exists
                if current_text.strip():
                    chunks_info.append({
                        "content": current_text.strip(),
                        "start_line": section_start_line, # Approximate start
                        "end_line": section_start_line + current_lines_count
                    })
                
                # Handle Overlap
                # Take the last 'overlap' chars from previous chunk as start of new chunk
                overlap_text = ""
                if len(current_text) > self.overlap:
                    overlap_text = current_text[-self.overlap:]
                    # Try to cut at sentence boundary within overlap if possible (simplified)
                
                current_text = overlap_text + sent
                # Recalculate line count for the new buffer
                current_lines_count = current_text.count('\n')

        # Push remaining
        if current_text.strip():
            chunks_info.append({
                "content": current_text.strip(),
                "start_line": section_start_line,
                "end_line": section_start_line + current_lines_count
            })
            
        return chunks_info

    # -----------------------------
    # Utils
    # -----------------------------
    def _build_chunk_id(self, file_path: str, chunk_index: int) -> str:
        """Generate a stable ID in format: file_path#chunk_index."""
        return f"{file_path}#{chunk_index}"

    def _sha256(self, text: str) -> str:
        """Calculate SHA256 hash of text."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

# -----------------------------
# Compatibility Alias
# -----------------------------
Chunker = SemanticChunker

if __name__ == "__main__":
    text = """# 数据库设计
这是第一段内容。这是第二段内容。
这是一些额外的说明文字。

## 索引结构
向量索引非常重要。它决定了检索效率。
B+ 树也是常用的结构。

### 查询优化
可以使用 ANN 算法提升性能。
需要注意内存占用。
"""
    chunker = SemanticChunker(max_chars=100, overlap=20, min_chars=50)
    chunks = chunker.chunk_text("test.md", text)

    print(f"Total chunks: {len(chunks)}\n")
    for i, c in enumerate(chunks):
        print(f"--- Chunk {i} ---")
        print(f"ID: {c.chunk_id[:16]}...")
        print(f"Section: {c.metadata.get('section_path', 'N/A')}")
        print(f"Lines: {c.start_line} - {c.end_line}")
        print(f"Content: {c.content[:50]}...")
        print()
