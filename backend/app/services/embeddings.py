import hashlib
import logging
from typing import List
import numpy as np
import httpx
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
from app.config import settings

logger = logging.getLogger(__name__)

class EmbeddingConfigurationError(RuntimeError):
    """Raised when configured embeddings cannot safely use the current vector index."""


class SemanticDenseEmbeddingFunction(EmbeddingFunction):
    """
    Robust multi-mode embedding function for ChromaDB.
    - Default/Fallback: Fast, deterministic 384-dimensional dense semantic hashing vectorizer.
    - OpenAI: text-embedding-3-small if OPENAI_API_KEY is configured and provider is openai.
    - Gemini: text-embedding-004 if GEMINI_API_KEY is configured and provider is gemini.
    """
    PROVIDER_MODELS = {
        "local": {"local-hash-v1": 384},
        "openai": {"text-embedding-3-small": 1536},
        "gemini": {"text-embedding-004": 768},
    }

    def __init__(self) -> None:
        pass

    @staticmethod
    def name() -> str:
        return "docintel-semantic-dense-v1"

    def get_config(self) -> dict[str, str | int]:
        return dict(self.profile)

    @staticmethod
    def build_from_config(config: dict[str, str | int]) -> "SemanticDenseEmbeddingFunction":
        function = SemanticDenseEmbeddingFunction()
        if config != function.profile:
            raise EmbeddingConfigurationError(
                "Persisted Chroma embedding configuration does not match the backend settings."
            )
        return function

    @property
    def profile(self) -> dict[str, str | int]:
        provider = settings.EMBEDDING_PROVIDER.lower()
        model = settings.EMBEDDING_MODEL
        if provider == "local" and model == "all-MiniLM-L6-v2":
            # Previous releases exposed this label but always used the local hash vectorizer.
            model = "local-hash-v1"
        try:
            dimension = self.PROVIDER_MODELS[provider][model]
        except KeyError as exc:
            supported = ", ".join(
                f"{name}: {', '.join(models)}"
                for name, models in self.PROVIDER_MODELS.items()
            )
            raise EmbeddingConfigurationError(
                f"Unsupported embedding provider/model '{provider}/{model}'. "
                f"Supported profiles: {supported}."
            ) from exc
        return {
            "embedding_provider": provider,
            "embedding_model": model,
            "embedding_dimension": dimension,
            "embedding_version": "1",
        }

    def validate_credentials(self) -> None:
        profile = self.profile
        if profile["embedding_provider"] == "openai" and not settings.OPENAI_API_KEY:
            raise EmbeddingConfigurationError(
                "OpenAI embeddings require OPENAI_API_KEY. Configure the key and "
                "reindex documents with the selected embedding profile."
            )
        if profile["embedding_provider"] == "gemini" and not settings.GEMINI_API_KEY:
            raise EmbeddingConfigurationError(
                "Gemini embeddings require GEMINI_API_KEY. Configure the key and "
                "reindex documents with the selected embedding profile."
            )

    def __call__(self, input: Documents) -> Embeddings:
        profile = self.profile
        provider = profile["embedding_provider"]
        if provider == "openai":
            self.validate_credentials()
            try:
                vectors = self._embed_openai(input)
            except EmbeddingConfigurationError:
                raise
            except Exception as exc:
                raise EmbeddingConfigurationError(
                    f"OpenAI embedding request failed ({type(exc).__name__}). "
                    "Check the backend API key, provider availability, and network connection."
                ) from exc
        elif provider == "gemini":
            self.validate_credentials()
            try:
                vectors = self._embed_gemini(input)
            except EmbeddingConfigurationError:
                raise
            except Exception as exc:
                raise EmbeddingConfigurationError(
                    f"Gemini embedding request failed ({type(exc).__name__}). "
                    "Check the backend API key, provider availability, and network connection."
                ) from exc
        else:
            vectors = self._embed_local(input, int(profile["embedding_dimension"]))

        if any(len(vector) != profile["embedding_dimension"] for vector in vectors):
            raise EmbeddingConfigurationError(
                f"Embedding provider returned an unexpected vector dimension; expected "
                f"{profile['embedding_dimension']} for {provider}/{profile['embedding_model']}."
            )
        return vectors

    def _embed_local(self, texts: List[str], dimension: int) -> Embeddings:
        results = []
        for text in texts:
            vec = np.zeros(dimension, dtype=np.float32)
            clean_text = text.lower().replace('\n', ' ')
            words = clean_text.split()
            
            for w in words:
                # Word hash projection
                h = int(hashlib.sha256(w.encode('utf-8')).hexdigest(), 16) % dimension
                vec[h] += 1.2
                # Subword n-grams (3-gram to 5-gram) for morphological and keyword capture
                for k in range(3, min(len(w) + 1, 6)):
                    for i in range(len(w) - k + 1):
                        sub = w[i:i+k]
                        h_sub = int(hashlib.md5(sub.encode('utf-8')).hexdigest(), 16) % dimension
                        vec[h_sub] += 0.4

            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            results.append(vec.tolist())
        return results

    def _embed_openai(self, texts: List[str]) -> Embeddings:
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "input": texts,
            "model": "text-embedding-3-small"
        }
        with httpx.Client(timeout=20.0) as client:
            resp = client.post("https://api.openai.com/v1/embeddings", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]

    def _embed_gemini(self, texts: List[str]) -> Embeddings:
        headers = {"Content-Type": "application/json"}
        results = []
        with httpx.Client(timeout=20.0) as client:
            for text in texts:
                url = "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent"
                payload = {
                    "model": "models/text-embedding-004",
                    "content": {"parts": [{"text": text[:2000]}]}
                }
                response_headers = {
                    **headers,
                    "x-goog-api-key": settings.GEMINI_API_KEY,
                }
                resp = client.post(url, json=payload, headers=response_headers)
                resp.raise_for_status()
                data = resp.json()
                results.append(data["embedding"]["values"])
        return results

embedding_function = SemanticDenseEmbeddingFunction()
