from contextlib import asynccontextmanager
from fastapi import FastAPI

# Import the database logic (assuming you moved it to a 'db' folder based on your import!)
from db.db import create_db_and_tables 

# The lifespan manager runs before the server starts taking requests
@asynccontextmanager
async def lifespan(app: FastAPI):
    # This triggers the connection test from your database file
    print("Initializing application...")
    create_db_and_tables()
    yield
    print("Application shutting down...")

# Initialize the FastAPI app with the lifespan
app = FastAPI(lifespan=lifespan, title="FastAPI SQLModel Server")

# --- Routes ---

@app.get("/")
def root():
    """A simple health check route."""
    return {"status": "ok", "message": "Server is running and the database connection was tested!"}

# I have temporarily removed the /users/ routes. 
# You can paste them back in once you create your models.py file!