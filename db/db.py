import os
from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session, text

# Load environment variables from the .env file
load_dotenv()

# Fetch the DATABASE_URL. If it's missing, this will prevent the app from starting silently.
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set in the .env file.")

# Create the engine
# echo=True will print the SQL queries to the console (great for debugging)
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    # 1. Test the connection first
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            print("\n✅ Successfully connected to the PostgreSQL database!\n")
    except Exception as e:
        print(f"\n❌ Failed to connect to the database: {e}\n")
        raise e  # Stop execution if the database isn't reachable

    # 2. Create the tables in the database based on your models
    SQLModel.metadata.create_all(engine)

def get_session():
    # This provides a database session for our FastAPI endpoints
    with Session(engine) as session:
        yield session