# Listen Data Pipeline

Listen Data Pipeline is an automated data ingestion service for an Urdu dictionary database. It features dynamic generation of Urdu words and sentences using an LLM (GPT-4o-mini) and supports background execution through an integrated cron-style scheduler.

## Features
- **FastAPI Endpoints**: Submit batch ingestion of words and sentences.
- **Automated Generation**: Connects to OpenAI for generating contextual Urdu content.
- **Scheduled Ingestion**: Periodically executes background jobs using APScheduler based on your configuration.
- **Robust Database**: Uses PostgreSQL via SQLModel to ingest all data into the `urdu_dict` schema.

## Prerequisites
- Python 3.9+
- PostgreSQL server instance
- OpenAI API Key

## Setup & Installation

**1. Clone the project**
Navigate to the root directory `c:\projects\listen-data-pipeline`.

**2. Create and activate virtual environment**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

**3. Install Dependencies**
```powershell
pip install -r requirements.txt
```

**4. Environment Variables**
Configure your database connection and API keys. We use `.env` to store sensitive data.
Create a `.env` file at the root directory of the project:
```env
DATABASE_URL=postgresql://postgres:{password}@localhost:5432/urdu_dict
OPENAI_API_KEY=sk-proj-YOUR_API_KEY
```
*Make sure you create the `urdu_dict` database in PostgreSQL.*

**5. Adjust Configuration**
You can customize exactly how much data is ingested and when inside the `config.yml` file:
```yaml
auto_ingest:
  cron_schedule: "*/15 * * * *"  # e.g., Every 15 minutes
  words_count: 100
  sentences_count: 100
  topics: 
    - "daily life"
    - "emotions"
    # ...
```

## Running the Application

To run the application locally, use Uvicorn via the terminal:

```powershell
uvicorn main:app --reload
```

## API Documentation

Once the app is running, access the interactive auto-generated documentation for the ingestion endpoints:
- Swagger UI (Docs): [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Project Structure
- `main.py` - FastAPI entry point and application lifecycle logic.
- `config.yml` - Contains settings for scheduled data generation (counts, topics, frequency).
- `models/` - SQLModel database entities.
- `db/` - Database connection schema creations.
- `routes/` - Route handlers for ingestion.
- `services/` - Background cron jobs and LLM integrations.
