from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from db.db import get_session
from models.models import (
    UrduWord,
    UrduSentence,
    WordBatchRequest,
    SentenceBatchRequest,
)

router = APIRouter(prefix="/ingest", tags=["Ingestion"])


# ──────────────────────────────────────────────
#  POST /ingest/words
# ──────────────────────────────────────────────

@router.post("/words", summary="Batch ingest Urdu words")
def ingest_words(payload: WordBatchRequest, session: Session = Depends(get_session)):
    """
    Accepts a list of Urdu words and bulk-inserts them into the urdu_words table.
    Duplicate words are silently ignored (ON CONFLICT DO NOTHING).
    """
    if not payload.list_of_words:
        raise HTTPException(status_code=422, detail="list_of_words cannot be empty.")

    # Strip whitespace and remove blank strings
    cleaned = [w.strip() for w in payload.list_of_words if w.strip()]

    if not cleaned:
        raise HTTPException(status_code=422, detail="No valid words found after cleaning.")

    # Build the upsert statement — ignores duplicates gracefully
    stmt = (
        pg_insert(UrduWord)
        .values([{"word": w} for w in cleaned])
        .on_conflict_do_nothing(index_elements=["word"])
    )

    session.exec(stmt)
    session.commit()

    return {
        "status": "ok",
        "message": f"Processed {len(cleaned)} words. Duplicates were ignored.",
    }


# ──────────────────────────────────────────────
#  POST /ingest/sentences
# ──────────────────────────────────────────────

@router.post("/sentences", summary="Batch ingest Urdu sentences")
def ingest_sentences(payload: SentenceBatchRequest, session: Session = Depends(get_session)):
    """
    Accepts a list of Urdu sentences and bulk-inserts them into the urdu_sentences table.
    The starting_word is extracted automatically from the first word of each sentence.
    Duplicate sentences are silently ignored (ON CONFLICT DO NOTHING).
    """
    if not payload.list_of_sentences:
        raise HTTPException(status_code=422, detail="list_of_sentences cannot be empty.")

    rows = []
    for sentence in payload.list_of_sentences:
        cleaned_sentence = sentence.strip()
        if not cleaned_sentence:
            continue  # skip blank strings

        # Extract the first word (split on whitespace)
        starting_word = cleaned_sentence.split()[0]

        rows.append({
            "sentence": cleaned_sentence,
            "starting_word": starting_word,
        })

    if not rows:
        raise HTTPException(status_code=422, detail="No valid sentences found after cleaning.")

    # Build the upsert statement — ignores duplicates gracefully
    stmt = (
        pg_insert(UrduSentence)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["sentence"])
    )

    session.exec(stmt)
    session.commit()

    return {
        "status": "ok",
        "message": f"Processed {len(rows)} sentences. Duplicates were ignored.",
    }
