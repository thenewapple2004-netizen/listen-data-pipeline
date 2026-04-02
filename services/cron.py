import os
import random
import json
import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql import func
from openai import AsyncOpenAI

from db.db import engine
from models.models import UrduWord, UrduSentence

def get_openai_client():
    # Helper to fetch the client cleanly in case the .env was hot-reloaded
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[CRON] WARNING: OPENAI_API_KEY is not set.")
    return AsyncOpenAI(api_key=api_key)

def load_config():
    try:
        with open("config.yml", "r") as f:
            return yaml.safe_load(f).get("auto_ingest", {})
    except Exception as e:
        print(f"[CRON] Error loading config.yml: {e}")
        return {}

async def run_auto_ingestion():
    config = load_config()
    if not config:
        print("[CRON] Skipped ingestion due to missing config.")
        return
        
    words_count = config.get("words_count", 20)
    sentences_count = config.get("sentences_count", 15)
    topics = config.get("topics", ["general"])
    selected_topic = random.choice(topics)
    
    print(f"\n[CRON] Starting ingestion job. Topic: '{selected_topic}', Words: {words_count}, Sentences: {sentences_count}")
    client = get_openai_client()
    
    # === 1. Auto Ingest Words ===
    try:
        word_prompt = f"""
        Generate {words_count} unique and varied Urdu words related to: '{selected_topic}'.
        Return ONLY a JSON object with a single key 'list_of_words' containing an array of strings representing the literal Urdu words.
        """
        resp_w = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": word_prompt}],
            response_format={"type": "json_object"},
        )
        words_data = json.loads(resp_w.choices[0].message.content)
        words = [w.strip() for w in words_data.get("list_of_words", []) if w.strip()]
        
        if words:
            with Session(engine) as session:
                stmt = pg_insert(UrduWord).values([{"word": w} for w in words]).on_conflict_do_nothing(index_elements=["word"])
                session.exec(stmt)
                session.commit()
            print(f"[CRON] Successfully ingested up to {len(words)} words.")
    except Exception as e:
        print(f"[CRON] Error ingesting words: {e}")

    # === 2. Auto Ingest Sentences ===
    try:
        with Session(engine) as session:
            words_in_db = session.exec(select(UrduWord.word).order_by(func.random()).limit(sentences_count)).all()
            
        if words_in_db:
            words_string = ", ".join(words_in_db)
            sent_prompt = f"""
            Generate {len(words_in_db)} unique Urdu sentences. 
            Each sentence MUST start with ONE of the following precise words: {words_string}.
            Use each word exactly once as the very first word in the sentence.
            Return ONLY a JSON object with a single key 'list_of_sentences' containing an array of strings.
            """
            
            resp_s = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": sent_prompt}],
                response_format={"type": "json_object"},
            )
            sent_data = json.loads(resp_s.choices[0].message.content)
            sentences = sent_data.get("list_of_sentences", [])
            
            rows = []
            for sentence in sentences:
                clean_s = sentence.strip()
                if clean_s:
                    rows.append({
                        "sentence": clean_s,
                        "starting_word": clean_s.split()[0],
                    })
                    
            if rows:
                with Session(engine) as session:
                    stmt = pg_insert(UrduSentence).values(rows).on_conflict_do_nothing(index_elements=["sentence"])
                    session.exec(stmt)
                    session.commit()
                print(f"[CRON] Successfully ingested up to {len(rows)} sentences.\n")
    except Exception as e:
        print(f"[CRON] Error ingesting sentences: {e}")


def start_scheduler():
    config = load_config()
    cron_str = config.get("cron_schedule", "0 * * * *")
    
    # We use AsyncIOScheduler since this runs alongside FastAPI's event loop
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_auto_ingestion, CronTrigger.from_crontab(cron_str))
    scheduler.start()
    
    print(f"[CRON] Scheduler started with cron schedule: '{cron_str}'")
    return scheduler
