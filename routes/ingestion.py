import json
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql import func
from openai import AsyncOpenAI

from db.db import get_session
from models.models import (
    UrduWord,
    UrduSentence,
    WordBatchRequest,
    SentenceBatchRequest,
)

import os
from dotenv import load_dotenv

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

# Explicitly load environment variables so that newly added keys are picked up
load_dotenv()

# Initialize Async OpenAI Client
# We explicitly pass the key so it throws a clearer error if the .env variable is misspelled
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is missing from the .env file.")
client = AsyncOpenAI(api_key=api_key)

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

    cleaned = [w.strip() for w in payload.list_of_words if w.strip()]

    if not cleaned:
        raise HTTPException(status_code=422, detail="No valid words found after cleaning.")

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

        starting_word = cleaned_sentence.split()[0]
        rows.append({
            "sentence": cleaned_sentence,
            "starting_word": starting_word,
        })

    if not rows:
        raise HTTPException(status_code=422, detail="No valid sentences found after cleaning.")

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

# ──────────────────────────────────────────────
#  POST /ingest/auto-words
# ──────────────────────────────────────────────

@router.post("/auto-words", summary="Auto-generate and ingest Urdu words using LLM")
async def auto_ingest_words(topic: str = "daily life", count: int = 20, session: Session = Depends(get_session)):
    """
    Generates unique Urdu words using gpt-4o-mini based on a topic and inserts them.
    Duplicate words natively handled by Database ON CONFLICT constraints.
    """
    prompt = f"""
    Generate {count} unique and varied Urdu words related to: '{topic}'.
    Return ONLY a JSON object with a single key 'list_of_words' containing an array of strings representing the literal Urdu words.
    Example: {{"list_of_words": ["پانی", "کتاب", "درخت"]}}
    """

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        words = data.get("list_of_words", [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate or parse LLM response: {str(e)}")

    if not words:
        return {"status": "error", "message": "LLM returned no words."}

    cleaned = [w.strip() for w in words if w.strip()]
    if not cleaned:
        return {"status": "error", "message": "No valid words found."}

    stmt = (
        pg_insert(UrduWord)
        .values([{"word": w} for w in cleaned])
        .on_conflict_do_nothing(index_elements=["word"])
    )
    session.exec(stmt)
    session.commit()

    return {
        "status": "ok",
        "message": f"Successfully auto-generated and attempted insertion of {len(cleaned)} words into database. Duplicates were ignored.",
        "generated_words": cleaned
    }

# ──────────────────────────────────────────────
#  POST /ingest/auto-sentences
# ──────────────────────────────────────────────

@router.post("/auto-sentences", summary="Auto-generate and ingest Urdu sentences using LLM")
async def auto_ingest_sentences(count: int = 15, session: Session = Depends(get_session)):
    """
    Fetches random words from the db and uses gpt-4o-mini to auto-generate sentences 
    starting with those exact words to guarantee diverse and helpful data ingestion.
    """
    # Fetch random words to start sentences from
    words_in_db = session.exec(select(UrduWord.word).order_by(func.random()).limit(count)).all()

    if not words_in_db:
        prompt = f"""
        Generate {count} unique Urdu sentences.
        Return ONLY a JSON object with a single key 'list_of_sentences' containing an array of strings.
        Example: {{"list_of_sentences": ["میں روزانہ سکول جاتا ہوں۔", "وہ کتاب پڑھتی ہے۔"]}}
        """
    else:
        words_string = ", ".join(words_in_db)
        prompt = f"""
        Generate {len(words_in_db)} unique Urdu sentences. 
        Each sentence MUST start with ONE of the following precise words: {words_string}.
        Use each word exactly once as the very first word in the sentence.
        Return ONLY a JSON object with a single key 'list_of_sentences' containing an array of strings.
        Example: {{"list_of_sentences": ["میں روزانہ سکول جاتا ہوں۔", "وہ کتاب پڑھتی ہے۔"]}}
        """

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        sentences = data.get("list_of_sentences", [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate or parse LLM response: {str(e)}")

    if not sentences:
        return {"status": "error", "message": "LLM returned no sentences."}

    rows = []
    for sentence in sentences:
        cleaned_sentence = sentence.strip()
        if not cleaned_sentence:
            continue
        starting_word = cleaned_sentence.split()[0]
        rows.append({
            "sentence": cleaned_sentence,
            "starting_word": starting_word,
        })

    if not rows:
        return {"status": "error", "message": "No valid sentences found."}

    stmt = (
        pg_insert(UrduSentence)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["sentence"])
    )
    session.exec(stmt)
    session.commit()

    return {
        "status": "ok",
        "message": f"Successfully auto-generated and attempted insertion of {len(rows)} sentences into database. Duplicates were ignored.",
        "generated_sentences": sentences
    }
