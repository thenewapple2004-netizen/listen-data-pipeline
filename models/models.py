from typing import Optional
from sqlmodel import Field, SQLModel


# ──────────────────────────────────────────────
#  DATABASE TABLE MODELS
# ──────────────────────────────────────────────

class UrduWord(SQLModel, table=True):
    """Stores individual Urdu words. Indexed for prefix searches by the inference app."""
    __tablename__ = "urdu_words"

    id: Optional[int] = Field(default=None, primary_key=True)
    word: str = Field(unique=True, index=True, nullable=False)


class UrduSentence(SQLModel, table=True):
    """Stores full Urdu sentences. starting_word is indexed separately
    for ultra-fast lookup from the inference app once a word is predicted."""
    __tablename__ = "urdu_sentences"

    id: Optional[int] = Field(default=None, primary_key=True)
    sentence: str = Field(unique=True, nullable=False)
    starting_word: str = Field(index=True, nullable=False)


# ──────────────────────────────────────────────
#  REQUEST SCHEMAS (Pydantic)
# ──────────────────────────────────────────────

class WordBatchRequest(SQLModel):
    """Request body for bulk word ingestion."""
    list_of_words: list[str]


class SentenceBatchRequest(SQLModel):
    """Request body for bulk sentence ingestion."""
    list_of_sentences: list[str]
