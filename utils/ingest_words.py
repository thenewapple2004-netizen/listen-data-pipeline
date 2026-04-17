import sys
import os
import json
from sqlmodel import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Add current directory to path so we can import modules
sys.path.append(os.getcwd())

from db.db import engine
from models.models import UrduWord

def ingest_words(words_list):
    """
    Ingests a list of Urdu words into the database.
    Skips duplicates using PostgreSQL's on_conflict_do_nothing.
    """
    if not words_list:
        print("No words provided for ingestion.")
        return

    # Clean words
    clean_words = [w.strip() for w in words_list if w.strip()]
    
    if not clean_words:
        print("No valid words found after cleaning.")
        return

    print(f"Attempting to ingest {len(clean_words)} words...")

    try:
        with Session(engine) as session:
            # Prepare values for bulk insert
            values = [{"word": w} for w in clean_words]
            
            # Using PostgreSQL-specific 'on_conflict_do_nothing' for the 'word' unique constraint
            stmt = pg_insert(UrduWord).values(values).on_conflict_do_nothing(index_elements=["word"])
            
            result = session.exec(stmt)
            session.commit()
            
            print("Successfully completed ingestion process.")
            
    except Exception as e:
        print(f"Error during ingestion: {e}")
        session.rollback()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python utils/ingest_words.py <word1> <word2> ...")
        print("Or provide a path to a JSON file: python utils/ingest_words.py --file words.json")
        sys.exit(1)

    if sys.argv[1] == "--file":
        if len(sys.argv) < 3:
            print("Please provide a file path.")
            sys.exit(1)
        
        filepath = sys.argv[2]
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Handle both list of words and dict mapping (where values are Urdu words)
                if isinstance(data, list):
                    words = data
                elif isinstance(data, dict):
                    words = list(data.values())
                else:
                    print("Unsupported JSON format. Expected list or dictionary.")
                    sys.exit(1)
                ingest_words(words)
        except Exception as e:
            print(f"Error reading file {filepath}: {e}")
            sys.exit(1)
    else:
        # Treat remaining arguments as words
        ingest_words(sys.argv[1:])
