# Exercise Server

A lightweight Python Flask server that fetches exercise data from Google Sheets and exposes it via REST API endpoints.

## Features

- Fetches exercise data from Google Sheets
- Exposes exercises for the current day of the week
- `/today` endpoint for current day's exercises
- Health check endpoint

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Google Sheets API Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API
4. Create credentials (OAuth 2.0 Client ID)
5. Download the credentials file and save it as `credentials.json` in the project root

### 3. Google Sheets Structure

Your Google Sheet should be structured with one row per exercise:
- Column A: Day of the week (Monday, Tuesday, etc.)
- Column B: Exercise name

Example:
```
Day     | Exercise
Monday  | Push-ups
Monday  | Squats
Monday  | Planks
Tuesday | Pull-ups
Tuesday | Lunges
Tuesday | Burpees
Wednesday| Running
Wednesday| Yoga
```

### 4. Run the Server

```bash
python app.py
```

The server will start on `http://localhost:3000`

## API Endpoints

### GET /today
Get exercises for today's day of the week.

**Example:**
```bash
curl "http://localhost:3000/today"
```

**Response:**
```json
{
  "day": "Monday",
  "exercises": ["Push-ups", "Squats", "Planks"],
  "timestamp": "2024-01-15T10:30:00"
}
```

### GET /health
Health check endpoint.

**Example:**
```bash
curl "http://localhost:3000/health"
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00"
}
```

## Configuration

You can modify the following variables in `app.py`:

- `SPREADSHEET_ID`: Your Google Sheet ID (already set to your provided URL)
- `RANGE_NAME`: The range to read from the sheet (default: 'Sheet1!A:Z')

## Notes

- The server will prompt for Google authentication on first run
- Authentication tokens are saved in `token.pickle` for subsequent runs
- Make sure your Google Sheet is accessible to the authenticated account
