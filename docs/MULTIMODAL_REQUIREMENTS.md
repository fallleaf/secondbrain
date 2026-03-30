# SecondBrain 多模态支持功能需求

## 概述

多模态支持旨在扩展 SecondBrain 的检索能力，支持图片、音频、视频等多种媒体类型的索引和检索，实现真正的多模态知识管理。

## 功能需求

### 1. 图片搜索

#### 1.1 图片索引
- **功能描述**：支持对图片文件进行索引和向量化
- **支持格式**：JPG, PNG, GIF, WebP, BMP
- **技术方案**：使用 CLIP (Contrastive Language-Image Pre-training) 模型
- **向量维度**：512 维（与文本向量一致）

**核心功能**：
- ✅ 图片文件扫描和识别
- ✅ 图片特征提取和向量化
- ✅ 图片元数据提取（EXIF、尺寸、格式等）
- ✅ 图片缩略图生成
- ✅ 图片 OCR 文字提取（可选）

**API 接口**：
```python
# 添加图片到索引
def add_image(image_path: str, metadata: Dict[str, Any]) -> None:
    """添加图片到索引"""
    pass

# 图片相似度搜索
def search_image(query_image: str, top_k: int = 10) -> List[SearchResult]:
    """使用图片进行相似度搜索"""
    pass

# 文本搜索图片
def search_image_by_text(query: str, top_k: int = 10) -> List[SearchResult]:
    """使用文本搜索图片"""
    pass
```

#### 1.2 图片检索
- **功能描述**：支持图片到图片、文本到图片的检索
- **检索模式**：
  - 图片相似度搜索
  - 文本描述搜索图片
  - 混合检索（图片 + 文本）

**检索场景**：
- 查找相似图片
- 根据描述查找图片
- 图片分类和标注
- 重复图片检测

---

### 2. 音频转录

#### 2.1 音频索引
- **功能描述**：支持对音频文件进行转录和索引
- **支持格式**：MP3, WAV, M4A, FLAC, OGG
- **技术方案**：使用 Whisper 模型进行语音识别
- **支持语言**：中文、英文、多语言

**核心功能**：
- ✅ 音频文件扫描和识别
- ✅ 语音转文字（ASR）
- ✅ 音频元数据提取（时长、采样率、格式等）
- ✅ 音频分段和标记
- ✅ 说话人识别（可选）

**API 接口**：
```python
# 添加音频到索引
def add_audio(audio_path: str, metadata: Dict[str, Any]) -> None:
    """添加音频到索引"""
    pass

# 音频转录
def transcribe_audio(audio_path: str, language: str = "auto") -> str:
    """转录音频为文字"""
    pass

# 搜索音频
def search_audio(query: str, top_k: int = 10) -> List[SearchResult]:
    """搜索音频内容"""
    pass
```

#### 2.2 音频检索
- **功能描述**：支持基于转录文本的音频检索
- **检索模式**：
  - 文本搜索音频
  - 音频片段搜索
  - 时间范围搜索

**检索场景**：
- 查找会议录音
- 搜索讲座内容
- 查找语音备忘录
- 音频内容分类

---

### 3. 视频内容提取

#### 3.1 视频索引
- **功能描述**：支持对视频文件进行内容提取和索引
- **支持格式**：MP4, AVI, MKV, MOV, WebM
- **技术方案**：
  - 提取关键帧（使用 CLIP 编码）
  - 提取音频（使用 Whisper 转录）
  - 提取字幕（如果有）

**核心功能**：
- ✅ 视频文件扫描和识别
- ✅ 关键帧提取和向量化
- ✅ 音频提取和转录
- ✅ 字幕提取（如果有）
- ✅ 视频元数据提取（时长、分辨率、格式等）
- ✅ 视频缩略图生成

**API 接口**：
```python
# 添加视频到索引
def add_video(video_path: str, metadata: Dict[str, Any]) -> None:
    """添加视频到索引"""
    pass

# 提取视频关键帧
def extract_keyframes(video_path: str, max_frames: int = 10) -> List[str]:
    """提取视频关键帧"""
    pass

# 提取视频音频
def extract_audio(video_path: str) -> str:
    """提取视频音频"""
    pass

# 搜索视频
def search_video(query: str, top_k: int = 10) -> List[SearchResult]:
    """搜索视频内容"""
    pass
```

#### 3.2 视频检索
- **功能描述**：支持基于关键帧和转录文本的视频检索
- **检索模式**：
  - 文本搜索视频
  - 图片搜索视频
  - 时间范围搜索

**检索场景**：
- 查找教学视频
- 搜索会议录像
- 查找演示视频
- 视频内容分类

---

### 4. 多模态融合检索

#### 4.1 融合策略
- **功能描述**：支持多种模态的融合检索
- **融合方式**：
  - 早期融合（向量级融合）
  - 晚期融合（结果级融合）
  - 混合融合（结合早期和晚期）

**融合算法**：
- RRF (Reciprocal Rank Fusion)
- 加权平均
- 学习排序（可选）

#### 4.2 跨模态检索
- **功能描述**：支持跨模态的检索
- **跨模态场景**：
  - 文本搜索图片
  - 图片搜索文本
  - 文本搜索音频
  - 音频搜索文本
  - 文本搜索视频
  - 视频搜索文本

**API 接口**：
```python
# 跨模态搜索
def cross_modal_search(
    query: Union[str, bytes],
    query_type: str,  # "text", "image", "audio"
    target_type: str,  # "text", "image", "audio", "video"
    top_k: int = 10
) -> List[SearchResult]:
    """跨模态搜索"""
    pass
```

---

## 技术要求

### 1. 模型要求

#### 1.1 图片编码模型
- **模型选择**：CLIP (OpenAI)
- **模型版本**：ViT-B/32 或 ViT-L/14
- **向量维度**：512 或 768
- **推理速度**：< 100ms/张

**备选模型**：
- OpenCLIP
- Chinese-CLIP（支持中文）

#### 1.2 音频转录模型
- **模型选择**：Whisper (OpenAI)
- **模型版本**：base 或 small
- **支持语言**：多语言
- **转录速度**：实时或接近实时

**备选模型**：
- WhisperX（支持说话人识别）
- FunASR（中文优化）

#### 1.3 视频处理
- **关键帧提取**：FFmpeg
- **音频提取**：FFmpeg
- **字幕提取**：FFmpeg

### 2. 性能要求

#### 2.1 索引性能
- **图片索引**：< 500ms/张
- **音频转录**：< 实时速度
- **视频处理**：< 10s/分钟视频

#### 2.2 检索性能
- **图片检索**：< 100ms
- **音频检索**：< 200ms
- **视频检索**：< 300ms
- **跨模态检索**：< 500ms

#### 2.3 存储要求
- **图片向量**：512 维 × 4 字节 = 2KB/张
- **音频文本**：取决于音频长度
- **视频数据**：取决于视频长度

### 3. 兼容性要求

#### 3.1 文件格式
- **图片**：JPG, PNG, GIF, WebP, BMP
- **音频**：MP3, WAV, M4A, FLAC, OGG
- **视频**：MP4, AVI, MKV, MOV, WebM

#### 3.2 平台支持
- **操作系统**：Linux, macOS, Windows
- **Python 版本**：3.8+
- **GPU 支持**：可选（CUDA, MPS）

---

## 实现方案

### 1. 架构设计

```
SecondBrain 多模态架构

┌─────────────────────────────────────────┐
│           Web 界面 / API                 │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         多模态检索引擎                    │
│  ┌──────────┬──────────┬──────────┐    │
│  │ 文本检索 │ 图片检索 │ 音频检索 │    │
│  └──────────┴──────────┴──────────┘    │
│  ┌──────────┬──────────┬──────────┐    │
│  │ 视频检索 │ 跨模态   │ 融合检索 │    │
│  └──────────┴──────────┴──────────┘    │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         多模态索引层                      │
│  ┌──────────┬──────────┬──────────┐    │
│  │ 文本索引 │ 图片索引 │ 音频索引 │    │
│  └──────────┴──────────┴──────────┘    │
│  ┌──────────┬──────────┬──────────┐    │
│  │ 视频索引 │ 元数据   │ 向量库   │    │
│  └──────────┴──────────┴──────────┘    │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         多模态处理层                      │
│  ┌──────────┬──────────┬──────────┐    │
│  │ CLIP     │ Whisper  │ FFmpeg   │    │
│  └──────────┴──────────┴──────────┘    │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         存储层                            │
│  ┌──────────┬──────────┬──────────┐    │
│  │ 文件系统 │ 向量数据库 │ 元数据库 │    │
│  └──────────┴──────────┴──────────┘    │
└─────────────────────────────────────────┘
```

### 2. 模块设计

#### 2.1 图片处理模块
```python
class ImageProcessor:
    """图片处理模块"""

    def __init__(self, model_name: str = "ViT-B/32"):
        self.model = load_clip_model(model_name)

    def encode_image(self, image_path: str) -> np.ndarray:
        """编码图片为向量"""
        pass

    def extract_metadata(self, image_path: str) -> Dict[str, Any]:
        """提取图片元数据"""
        pass

    def generate_thumbnail(self, image_path: str, size: Tuple[int, int]) -> str:
        """生成缩略图"""
        pass
```

#### 2.2 音频处理模块
```python
class AudioProcessor:
    """音频处理模块"""

    def __init__(self, model_name: str = "base"):
        self.model = load_whisper_model(model_name)

    def transcribe(self, audio_path: str, language: str = "auto") -> str:
        """转录音频为文字"""
        pass

    def extract_metadata(self, audio_path: str) -> Dict[str, Any]:
        """提取音频元数据"""
        pass

    def segment_audio(self, audio_path: str, segment_length: int) -> List[str]:
        """分段音频"""
        pass
```

#### 2.3 视频处理模块
```python
class VideoProcessor:
    """视频处理模块"""

    def __init__(self):
        self.image_processor = ImageProcessor()
        self.audio_processor = AudioProcessor()

    def extract_keyframes(self, video_path: str, max_frames: int = 10) -> List[str]:
        """提取关键帧"""
        pass

    def extract_audio(self, video_path: str) -> str:
        """提取音频"""
        pass

    def extract_subtitles(self, video_path: str) -> str:
        """提取字幕"""
        pass

    def process_video(self, video_path: str) -> Dict[str, Any]:
        """处理视频"""
        pass
```

#### 2.4 多模态索引模块
```python
class MultiModalIndex:
    """多模态索引"""

    def __init__(self):
        self.text_index = SemanticIndex()
        self.image_index = ImageIndex()
        self.audio_index = AudioIndex()
        self.video_index = VideoIndex()

    def add_image(self, image_path: str, metadata: Dict[str, Any]) -> None:
        """添加图片到索引"""
        pass

    def add_audio(self, audio_path: str, metadata: Dict[str, Any]) -> None:
        """添加音频到索引"""
        pass

    def add_video(self, video_path: str, metadata: Dict[str, Any]) -> None:
        """添加视频到索引"""
        pass

    def search(self, query: Union[str, bytes], query_type: str, target_type: str, top_k: int = 10) -> List[SearchResult]:
        """多模态搜索"""
        pass
```

### 3. 数据库设计

#### 3.1 图片索引表
```sql
CREATE TABLE images (
    id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    embedding BLOB(2048),  -- 512 维 × 4 字节
    metadata TEXT,
    thumbnail_path TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE VIRTUAL TABLE images_vec USING vec0(
    embedding float[512]
);
```

#### 3.2 音频索引表
```sql
CREATE TABLE audio (
    id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    transcript TEXT,
    duration REAL,
    metadata TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE VIRTUAL TABLE audio_fts USING fts5(
    transcript,
    metadata
);
```

#### 3.3 视频索引表
```sql
CREATE TABLE videos (
    id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    duration REAL,
    keyframes TEXT,  -- JSON 数组
    transcript TEXT,
    metadata TEXT,
    thumbnail_path TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE VIRTUAL TABLE videos_vec USING vec0(
    embedding float[512]
);
```

---

## 开发计划

### 阶段一：图片搜索（4 周）
- Week 1-2：图片处理模块开发
- Week 3：图片索引和检索
- Week 4：测试和优化

### 阶段二：音频转录（3 周）
- Week 1-2：音频处理模块开发
- Week 3：音频索引和检索

### 阶段三：视频处理（3 周）
- Week 1-2：视频处理模块开发
- Week 3：视频索引和检索

### 阶段四：多模态融合（2 周）
- Week 1：融合算法实现
- Week 2：跨模态检索

### 阶段五：集成和优化（2 周）
- Week 1：Web 界面集成
- Week 2：性能优化和测试

**总计**：14 周

---

## 依赖项

### Python 包
```txt
# 图片处理
torch>=2.0.0
torchvision>=0.15.0
clip>=1.0
Pillow>=10.0.0

# 音频处理
openai-whisper>=20230314
pydub>=0.25.0

# 视频处理
ffmpeg-python>=0.2.0
opencv-python>=4.8.0

# 其他
numpy>=1.24.0
```

### 系统依赖
```bash
# FFmpeg
sudo apt install ffmpeg

# GPU 支持（可选）
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

---

## 测试计划

### 单元测试
- 图片处理模块测试
- 音频处理模块测试
- 视频处理模块测试
- 多模态索引测试

### 集成测试
- 图片索引和检索测试
- 音频索引和检索测试
- 视频索引和检索测试
- 跨模态检索测试

### 性能测试
- 索引性能测试
- 检索性能测试
- 并发测试
- 内存使用测试

---

## 风险和挑战

### 1. 性能风险
- **风险**：大文件处理可能较慢
- **缓解**：异步处理、进度显示、缓存机制

### 2. 存储风险
- **风险**：多模态数据占用大量存储
- **缓解**：压缩存储、定期清理、分层存储

### 3. 准确性风险
- **风险**：模型识别准确率可能不够高
- **缓解**：模型微调、多模型融合、人工校验

### 4. 兼容性风险
- **风险**：不同格式文件处理可能有问题
- **缓解**：格式转换、错误处理、降级方案

---

## 成功指标

### 功能指标
- ✅ 支持图片、音频、视频索引
- ✅ 支持跨模态检索
- ✅ 检索准确率 > 80%
- ✅ 检索响应时间 < 500ms

### 性能指标
- ✅ 图片索引速度 < 500ms/张
- ✅ 音频转录速度 < 实时
- ✅ 视频处理速度 < 10s/分钟

### 用户体验指标
- ✅ Web 界面支持多模态上传
- ✅ 支持拖拽上传
- ✅ 实时进度显示
- ✅ 友好的错误提示

---

## 总结

多模态支持将显著扩展 SecondBrain 的检索能力，支持图片、音频、视频等多种媒体类型的索引和检索。通过使用 CLIP、Whisper 等先进模型，实现高质量的跨模态检索，为用户提供更强大的知识管理能力。

### 核心价值
- 🖼️ 图片搜索：查找相似图片、根据描述查找图片
- 🎵 音频转录：会议录音、讲座内容自动转录
- 🎬 视频处理：关键帧提取、内容索引
- 🔍 跨模态检索：文本搜索图片、图片搜索文本

### 技术亮点
- 🚀 先进模型：CLIP、Whisper
- ⚡ 高性能：GPU 加速、异步处理
- 🎯 高准确率：多模型融合
- 💡 易用性：Web 界面、拖拽上传

多模态支持将使 SecondBrain 成为真正的多模态知识管理系统！
