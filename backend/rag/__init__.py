"""
RAG (Retrieval-Augmented Generation) module.
Provides ChromaDB integration for knowledge retrieval.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional

import chromadb
from chromadb.config import Settings

_client: Optional[chromadb.ClientAPI] = None
_collection: Optional[chromadb.Collection] = None
_fallback_docs: List[Dict] = []
_chroma_unavailable = False

KNOWLEDGE_SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge_seed"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def get_chroma_client() -> Optional[chromadb.ClientAPI]:
    """Get or create the ChromaDB client singleton."""
    global _client, _chroma_unavailable
    if _chroma_unavailable:
        return None
    if os.getenv("CYBERTRAINER_USE_CHROMA", "0").lower() not in ("1", "true", "yes"):
        _chroma_unavailable = True
        print("  Knowledge base: using lexical fallback (set CYBERTRAINER_USE_CHROMA=1 for ChromaDB)")
        return None
    if _client is None:
        persist_dir = Path(os.getenv("CHROMA_PERSIST_DIR", "data/chroma_db"))
        if not persist_dir.is_absolute():
            persist_dir = PROJECT_ROOT / persist_dir
        persist_dir.mkdir(parents=True, exist_ok=True)

        try:
            _client = chromadb.PersistentClient(
                path=str(persist_dir),
                settings=Settings(anonymized_telemetry=False),
            )
        except Exception as exc:
            _chroma_unavailable = True
            print(f"  Knowledge base: ChromaDB unavailable, using lexical fallback ({exc})")
            return None
    return _client


def get_collection() -> Optional[chromadb.Collection]:
    """Get or create the fitness knowledge collection."""
    global _collection
    if _collection is None:
        client = get_chroma_client()
        if client is None:
            return None
        collection_name = os.getenv("CHROMA_COLLECTION", "fitness_knowledge")
        _collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks by paragraphs, then by character count."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: List[str] = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = current_chunk[-overlap:] + "\n\n" + para
        else:
            current_chunk = current_chunk + "\n\n" + para if current_chunk else para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def _read_seed_chunks() -> tuple[List[str], List[Dict], List[str], str]:
    """Read seed markdown files and return chunk data for either backend."""
    import hashlib

    hasher = hashlib.sha256()
    md_files = sorted(KNOWLEDGE_SEED_DIR.rglob("*.md"))
    for md_file in md_files:
        hasher.update(md_file.read_bytes())
    content_hash = hasher.hexdigest()

    documents: List[str] = []
    metadatas: List[Dict] = []
    ids: List[str] = []

    chunk_idx = 0
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        relative_path = str(md_file.relative_to(KNOWLEDGE_SEED_DIR))
        category = md_file.parent.name

        for i, chunk in enumerate(_chunk_text(content)):
            documents.append(chunk)
            metadatas.append({
                "source": relative_path,
                "category": category,
                "chunk_index": i,
                "_index_hash": content_hash,
            })
            ids.append(f"seed_{chunk_idx}")
            chunk_idx += 1

    return documents, metadatas, ids, content_hash


def _index_fallback(documents: List[str], metadatas: List[Dict]) -> int:
    """Store seed chunks in process memory for lexical fallback search."""
    global _fallback_docs
    _fallback_docs = [
        {"content": doc, **metadata}
        for doc, metadata in zip(documents, metadatas)
    ]
    return len(_fallback_docs)


def index_knowledge_seed() -> int:
    """
    Read all markdown files from the knowledge seed directory,
    chunk them, and add them to ChromaDB or the lexical fallback.

    Returns the number of chunks indexed.
    """
    documents, metadatas, ids, content_hash = _read_seed_chunks()
    collection = get_collection()

    if collection is None:
        return _index_fallback(documents, metadatas)

    # Check if already indexed with same hash
    try:
        existing_meta = collection.get(where={"_index_hash": content_hash}, limit=1)
        if existing_meta["ids"]:
            return collection.count()
    except Exception:
        pass

    if documents:
        # Clear existing seed documents before re-indexing
        try:
            existing = collection.get(where={"source": {"$ne": ""}})
            if existing["ids"]:
                collection.delete(ids=existing["ids"])
        except Exception:
            pass

        try:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )
        except Exception as exc:
            print(f"  Knowledge base: ChromaDB indexing failed, using lexical fallback ({exc})")
            return _index_fallback(documents, metadatas)

    return len(documents)


def search_knowledge(query: str, top_k: int = 3) -> List[Dict]:
    """
    Search the knowledge base for relevant documents.

    Returns a list of dicts with 'content', 'source', and 'score' keys.
    """
    collection = get_collection()

    if collection is None:
        return _search_fallback(query, top_k)

    try:
        if collection.count() == 0:
            return _search_fallback(query, top_k)

        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, collection.count()),
        )
    except Exception as exc:
        print(f"  Knowledge base: ChromaDB search failed, using lexical fallback ({exc})")
        return _search_fallback(query, top_k)

    docs = []
    if results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            distance = results["distances"][0][i] if results["distances"] else 0.0
            docs.append({
                "content": doc,
                "source": metadata.get("source", "unknown"),
                "category": metadata.get("category", "unknown"),
                "score": 1.0 - distance,
            })

    return docs


def _search_fallback(query: str, top_k: int = 3) -> List[Dict]:
    """Simple lexical search used when ChromaDB is unavailable."""
    if not _fallback_docs:
        documents, metadatas, _, _ = _read_seed_chunks()
        _index_fallback(documents, metadatas)

    terms = [term for term in re.findall(r"\w+", query.lower()) if len(term) > 1]
    scored = []
    for doc in _fallback_docs:
        content = doc["content"]
        haystack = f"{content} {doc.get('source', '')} {doc.get('category', '')}".lower()
        score = sum(haystack.count(term) for term in terms)
        if score > 0:
            scored.append((score, doc))

    if not scored:
        scored = [(1, doc) for doc in _fallback_docs[:top_k]]

    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "content": doc["content"],
            "source": doc.get("source", "unknown"),
            "category": doc.get("category", "unknown"),
            "score": float(score),
        }
        for score, doc in scored[:top_k]
    ]
