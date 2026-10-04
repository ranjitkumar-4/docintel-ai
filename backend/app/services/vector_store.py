import logging
import json
import os
import uuid
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import settings
from app.models.document import DocumentChunk
from app.services.embeddings import embedding_function, EmbeddingConfigurationError

logger = logging.getLogger(__name__)

COLLECTION_NAME = "docintel_documents"


class VectorStore:
    def __init__(self, persist_dir: Optional[str] = None, collection_name: str = COLLECTION_NAME):
        self.persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.configuration_error: Optional[str] = None
        self.distance_metric = "cosine"
        self.collection = self._open_collection()

    @property
    def collection_pointer_path(self) -> str:
        return os.path.join(settings.DATA_DIR, "active_vector_collection.json")

    def _configured_profile(self) -> Dict[str, Any]:
        return {
            **embedding_function.profile,
            "hnsw:space": "cosine",
        }

    @staticmethod
    def _profile_metadata(profile: Dict[str, Any]) -> Dict[str, Any]:
        return {
            key: value for key, value in profile.items()
            if key != "hnsw:space"
        }

    @staticmethod
    def _collection_distance_metric(collection) -> str:
        metadata = collection.metadata or {}
        metric = metadata.get("hnsw:space")
        if metric:
            return str(metric).lower()
        configuration = getattr(collection, "configuration", {}) or {}
        hnsw_configuration = configuration.get("hnsw", {})
        return str(hnsw_configuration.get("space", "l2")).lower()

    def _open_collection(self):
        try:
            profile = self._configured_profile()
            active_name = self.collection_name
            if self.collection_name == COLLECTION_NAME and os.path.exists(self.collection_pointer_path):
                with open(self.collection_pointer_path, "r", encoding="utf-8") as pointer:
                    active_name = json.load(pointer)["collection_name"]
            collection = self.client.get_or_create_collection(
                name=active_name,
                embedding_function=embedding_function,
                metadata=profile,
            )
            self.distance_metric = self._collection_distance_metric(collection)
            stored_profile = collection.metadata or {}
            actual_profile = {
                key: stored_profile.get(key)
                for key in (
                    "embedding_provider",
                    "embedding_model",
                    "embedding_dimension",
                    "embedding_version",
                )
            }
            expected_profile = {
                key: profile[key]
                for key in (
                    "embedding_provider",
                    "embedding_model",
                    "embedding_dimension",
                    "embedding_version",
                )
            }

            if not any(value is not None for value in actual_profile.values()):
                if collection.count() == 0:
                    collection.modify(metadata=self._profile_metadata(profile))
                elif (
                    profile["embedding_provider"] == "local"
                    and profile["embedding_model"] == "local-hash-v1"
                    and self._all_vectors_have_dimension(collection, profile["embedding_dimension"])
                ):
                    logger.warning(
                        "Adopting legacy local Chroma index after confirming its stored vector dimension."
                    )
                    collection.modify(metadata=self._profile_metadata(profile))
                else:
                    self.configuration_error = (
                        f"Existing Chroma collection '{active_name}' has no embedding profile metadata. "
                        "Its provider/model cannot be verified. Preserve the existing data and run "
                        "`PYTHONPATH=backend .venv/bin/python reindex_embeddings.py` to build and "
                        "activate a verified index."
                    )
            elif actual_profile != expected_profile:
                self.configuration_error = (
                    f"Embedding profile mismatch for Chroma collection '{active_name}'. "
                    f"Index uses {actual_profile['embedding_provider']}/"
                    f"{actual_profile['embedding_model']} "
                    f"({actual_profile['embedding_dimension']} dimensions); configuration uses "
                    f"{expected_profile['embedding_provider']}/{expected_profile['embedding_model']} "
                    f"({expected_profile['embedding_dimension']} dimensions). Queries and indexing "
                    "are disabled. Keep the existing data and run "
                    "`PYTHONPATH=backend .venv/bin/python reindex_embeddings.py` after configuring "
                    "the desired profile."
                )
            return collection
        except (EmbeddingConfigurationError, OSError, KeyError, json.JSONDecodeError) as exc:
            self.configuration_error = str(exc)
            logger.error("Unable to validate Chroma embedding configuration: %s", exc)
            try:
                collection = self.client.get_collection(
                    self.collection_name,
                    embedding_function=embedding_function,
                )
            except Exception:
                collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    embedding_function=embedding_function,
                    metadata={"hnsw:space": "cosine"},
                )
            self.distance_metric = self._collection_distance_metric(collection)
            return collection

    @staticmethod
    def _all_vectors_have_dimension(collection, dimension: int) -> bool:
        if collection.count() == 0:
            return True
        result = collection.get(include=["embeddings"], limit=1)
        vectors = result.get("embeddings")
        return bool(vectors is not None and len(vectors) == 1 and len(vectors[0]) == dimension)

    def ensure_compatible(self) -> None:
        embedding_function.validate_credentials()
        if self.configuration_error:
            raise EmbeddingConfigurationError(self.configuration_error)
        expected = self._configured_profile()
        stored = self.collection.metadata or {}
        for key in ("embedding_provider", "embedding_model", "embedding_dimension", "embedding_version"):
            if stored.get(key) != expected[key]:
                raise EmbeddingConfigurationError(
                    "The configured embedding provider/model/dimension no longer matches the active "
                    f"index ({stored.get('embedding_provider')}/{stored.get('embedding_model')}/"
                    f"{stored.get('embedding_dimension')} vs "
                    f"{expected['embedding_provider']}/{expected['embedding_model']}/"
                    f"{expected['embedding_dimension']}). Queries and indexing are disabled. Preserve "
                    "the existing data and run `PYTHONPATH=backend .venv/bin/python "
                    "reindex_embeddings.py` with the intended embedding configuration."
                )

    def activate_collection(self, collection_name: str) -> None:
        collection = self.client.get_collection(
            collection_name,
            embedding_function=embedding_function,
        )
        expected = self._configured_profile()
        stored = collection.metadata or {}
        for key in ("embedding_provider", "embedding_model", "embedding_dimension", "embedding_version"):
            if stored.get(key) != expected[key]:
                raise EmbeddingConfigurationError(
                    f"Staged collection does not match configured embedding profile ({key})."
                )
        os.makedirs(os.path.dirname(self.collection_pointer_path), exist_ok=True)
        temporary_pointer = f"{self.collection_pointer_path}.{uuid.uuid4().hex}.tmp"
        with open(temporary_pointer, "w", encoding="utf-8") as pointer:
            json.dump({"collection_name": collection_name}, pointer)
            pointer.flush()
            os.fsync(pointer.fileno())
        os.replace(temporary_pointer, self.collection_pointer_path)
        self.collection = collection
        self.collection_name = collection_name
        self.configuration_error = None

    def add_chunks(self, chunks: List[DocumentChunk]):
        self.ensure_compatible()
        if not chunks:
            return

        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = []
        for c in chunks:
            metadatas.append({
                "document_id": c.document_id,
                "filename": c.filename,
                "page_number": int(c.page_number),
                "chunk_id": c.chunk_id,
                "file_type": c.file_type,
            })

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"Successfully indexed {len(chunks)} chunks in ChromaDB")

    def query(
        self,
        query_text: str,
        n_results: int = 6,
        document_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        self.ensure_compatible()
        where_filter = None
        if document_ids and len(document_ids) > 0:
            if len(document_ids) == 1:
                where_filter = {"document_id": document_ids[0]}
            else:
                where_filter = {"document_id": {"$in": document_ids}}

        total_count = self.collection.count()
        if total_count == 0:
            return []

        if n_results <= 0:
            return []
        actual_n = min(n_results, total_count)
        
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=actual_n,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            logger.error(f"Error executing Chroma query: {e}")
            raise RuntimeError(f"Vector search failed: {e}") from e

        formatted: List[Dict[str, Any]] = []
        if not results or not results["documents"] or not results["documents"][0]:
            return []

        docs = results["documents"][0]
        metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
        distances = results["distances"][0] if results.get("distances") else [0.5] * len(docs)
        ids = results["ids"][0] if results.get("ids") else [""] * len(docs)

        for i, text in enumerate(docs):
            dist = distances[i] if i < len(distances) else 0.5
            if self.distance_metric == "cosine":
                similarity = 1.0 - dist
            elif self.distance_metric == "l2":
                # Chroma returns squared L2 distances; local vectors are unit-normalized.
                similarity = 1.0 - (dist / 2.0)
            elif self.distance_metric == "ip":
                similarity = 1.0 - dist
            else:
                raise RuntimeError(
                    f"Unsupported Chroma distance metric '{self.distance_metric}'. "
                    "Reindex the vector collection using cosine distance."
                )
            similarity = max(0.0, min(1.0, similarity))
            
            meta = metas[i] if i < len(metas) else {}
            formatted.append({
                "chunk_id": ids[i],
                "document_id": meta.get("document_id", ""),
                "filename": meta.get("filename", "Unknown"),
                "page_number": int(meta.get("page_number", 1)),
                "text": text,
                "file_type": meta.get("file_type", ""),
                "similarity_score": round(similarity, 4),
                "page_number_approximate": meta.get("file_type", "").lower() == "docx",
                "distance": dist
            })

        return formatted

    def get_document_chunks(self, document_id: str) -> List[DocumentChunk]:
        self.ensure_compatible()
        result = self.collection.get(
            where={"document_id": document_id},
            include=["documents", "metadatas"],
        )
        chunks = []
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
        ids = result.get("ids") or []
        for index, text in enumerate(documents):
            metadata = metadatas[index] or {}
            chunk_id = ids[index]
            chunks.append(DocumentChunk(
                chunk_id=chunk_id,
                document_id=metadata.get("document_id", document_id),
                filename=metadata.get("filename", "Unknown"),
                page_number=int(metadata.get("page_number", 1)),
                text=text,
                file_type=metadata.get("file_type", ""),
                metadata={
                    **metadata,
                    "chunk_id": chunk_id,
                },
            ))
        return chunks

    def delete_document_chunks(self, document_id: str):
        self.ensure_compatible()
        try:
            self.collection.delete(where={"document_id": document_id})
            logger.info(f"Deleted chunks for document {document_id} from ChromaDB")
        except Exception as e:
            logger.error(f"Error deleting chunks for document {document_id}: {e}")

    def get_chunk_count(self) -> int:
        self.ensure_compatible()
        return self.collection.count()

    def clear_all(self):
        self.ensure_compatible()
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            embedding_function=embedding_function,
            metadata=self._configured_profile(),
        )

vector_store = VectorStore()
