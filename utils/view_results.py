import sys
import os
from sqlmodel import Session, select

# Add current directory to path
sys.path.append(os.getcwd())

from db.db import engine
from models.models import UrduSentence

def view_sentences():
    print("Fetching sentences from the database...\n")
    
    with Session(engine) as session:
        # Fetch all sentences
        # If you want to filter specifically by the words you added:
        # statement = select(UrduSentence).where(UrduSentence.starting_word.in_(your_list))
        
        statement = select(UrduSentence).order_by(UrduSentence.id.desc()).limit(100)
        results = session.exec(statement).all()
        
        if not results:
            print("No sentences found in the database.")
            return

        print(f"{'ID':<5} | {'Starting Word':<20} | {'Sentence'}")
        print("-" * 80)
        for row in results:
            print(f"{row.id:<5} | {row.starting_word:<20} | {row.sentence}")

if __name__ == "__main__":
    view_sentences()
