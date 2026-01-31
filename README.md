# 🎯 ClipCompass  
### Multi-Modal Video-Context Search Engine

ClipCompass is a **production-ready Multi-Modal RAG system** that ingests videos (Zoom recordings, YouTube content), synchronizes audio transcripts with visual frame embeddings, and enables **natural language search across both audio and visual contexts**.

> **Why this matters**  
> Text RAG is largely solved. Real-world enterprise data lives in **video**. ClipCompass demonstrates the ability to build **complex, unstructured, multi-modal pipelines** that operate at scale.

---

## 🚀 Project Vision

### The Problem
Organizations accumulate massive volumes of video data—meetings, trainings, demos—that are practically **unsearchable**.

### The Solution
ClipCompass understands **what was said** *and* **what was shown**, enabling queries like:
- *“Show me when the CEO discussed the budget”*
- *“Find slides with revenue charts”*
- *“When did the product demo happen?”*

---

## ✨ Features

### Core Capabilities
- **Multi-Modal Search** (audio + visual)
- **Timestamp Synchronization** between transcripts and frames
- **Natural Language Queries**
- **Click-to-Seek Smart Playback**
- **Auto-Tagging of Visual Scenes**

### Technical Highlights
- Whisper ASR with word-level timestamps
- CLIP-based image–text similarity
- Qdrant vector database
- Async background processing
- YouTube ingestion via `yt-dlp`

---

## 🧠 Tech Stack

### Backend
- **FastAPI** (async Python)
- **AI/ML**
  - OpenAI Whisper (ASR)
  - CLIP ViT-B/32 (visual embeddings)
  - ResNet50 (image tagging)
  - Sentence-Transformers (text embeddings)
- **Vector DB**: Qdrant
- **Video**: FFmpeg, yt-dlp
- **Async Tasks**: Celery + Redis

### Frontend
- **Next.js 14 (App Router)**
- **Tailwind CSS v4**
- Glassmorphism, responsive UI

---

## 🏗️ Architecture Overview

```mermaid
graph TB
    A[Video Input] --> B[Video Processor]
    B --> C[Audio Extractor]
    B --> D[Frame Extractor]
    C --> E[Whisper ASR]
    D --> F[ResNet50 Tagger]
    D --> G[CLIP Embedder]
    E --> H[Text Embedder]
    H --> I[Qdrant]
    G --> I
    J[User Query] --> K[Search Engine]
    K --> L[Query Embedder]
    L --> I
    I --> M[Hybrid Results]
