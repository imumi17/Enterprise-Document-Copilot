from openai import OpenAI

from app.config import settings

EMBEDDING_BATCH_SIZE = 128


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    client = OpenAI(api_key=settings.openai_api_key)
    embeddings: list[list[float]] = []

    for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[start : start + EMBEDDING_BATCH_SIZE]
        response = client.embeddings.create(
            model=settings.openai_embedding_model,
            input=batch,
        )
        embeddings.extend(item.embedding for item in response.data)

    return embeddings
