from typing import List
from app.core.config import EMBEDDING_MODEL_NAME, USE_OPENAI, OPENAI_API_KEY

_openai_available = False
try:
    if USE_OPENAI:
        from openai import OpenAI  # type: ignore
        _openai_available = True
except Exception:
    _openai_available = False

from sentence_transformers import SentenceTransformer

class EmbeddingClient:
    def __init__(self):
        self.use_openai = USE_OPENAI and _openai_available and bool(OPENAI_API_KEY)
        if self.use_openai:
            self.client = OpenAI(api_key=OPENAI_API_KEY)
            self.dim = 1536
            self.model_name = "text-embedding-3-small"
        else:
            self.model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            self.dim = self.model.get_sentence_embedding_dimension()
            self.model_name = EMBEDDING_MODEL_NAME

    def embed(self, texts: List[str]) -> List[List[float]]:
        if self.use_openai:
            resp = self.client.embeddings.create(input=texts, model=self.model_name)
            return [d.embedding for d in resp.data]
        else:
            embs = self.model.encode(texts, normalize_embeddings=True).tolist()
            return embs

    def embed_one(self, text: str) -> List[float]:
        return self.embed([text])[0]

    def get_dimension(self) -> int:
        return self.dim

    def name(self) -> str:
        return self.model_name
