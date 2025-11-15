# EDGAR Data Parse App

This is a web application that integrates with the SEC's EDGAR Database, enabling users to search and research companies by accessing financial filings, facts, and other relevant data. It uses AI to generate summaries for better analysis.

## Technology Stack

- **Backend**: Django (Python web framework for handling API integrations, data processing, and server-side logic)
- **Frontend**: React with TypeScript (for building interactive user interfaces)
- **Database**: PostgreSQL (recommended for production; SQLite for development)
- **Other**: AI integration for summaries (e.g., OpenAI API)

## Setup

1. Clone the repo: `git clone https://github.com/yourusername/edgar-data-parse.git`
2. **Backend Setup (Django API)**:
   - Navigate to the backend: `cd src`
   - Copy env: `cp .env.example .env` and fill values
   - Create venv (optional) and install: `pip install -r ../requirements.txt`
   - Migrate DB: `python manage.py migrate`
   - Create admin user: `python manage.py createsuperuser`
3. **Frontend Setup**:
   - Navigate to the frontend directory: `cd frontend`
   - Install dependencies: `npm install`
4. Set environment variables (e.g., in .env file):
   - USER_AGENT_EMAIL=your@email.com
   - OPENAI_API_KEY=your_key
   - DATABASE_URL (for PostgreSQL)

## Running the Application

- Start the backend server (from `src/`): `python manage.py runserver`
- Start the frontend development server: `cd frontend && npm start`
- Access the app at `http://localhost:3000` (or configured port)

## Features

- Company search by ticker, name, or CIK
- View and download filings (10-K, 10-Q, etc.)
- AI-generated summaries of financial data
- User accounts for saving searches and preferences

### New API (initial)
- Companies: `GET /api/companies/`
- Filings: `GET /api/filings/`
- Facts: `GET /api/facts/`
- Sections: `GET /api/sections/`
- Tables: `GET /api/tables/`

Ingest an HTM filing into the warehouse models:

```bash
cd src
python manage.py ingest_htm --url https://www.sec.gov/Archives/edgar/data/1425627/000147793223002085/sobr_10k.htm --ticker SOBR
```

## Usage

To process an SEC HTM filing:

```bash
python src/main.py --action process_htm --url https://www.sec.gov/Archives/edgar/data/1425627/000147793223002085/sobr_10k.htm
```

This will download the filing, parse sections and tables, and save the parsed data to a JSON file in the data/ directory.

## Project Structure

- `src/`: Backend code (Django apps, models, views, etc.)
- `frontend/`: Frontend code (React components, TypeScript files)
- `notebooks/`: Exploratory notebooks
- `data/`: Sample data and outputs
- `docs/`: Additional documentation
