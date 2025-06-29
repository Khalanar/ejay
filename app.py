from flask import Flask, jsonify, request, render_template_string, redirect, url_for
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import pickle
from datetime import datetime, timedelta, date
import json
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Google Sheets API configuration
SERVICE_ACCOUNT_FILE = 'service_account.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SPREADSHEET_ID = '1xB33OtYu_PQJjQLgGvg_TCcQCFlwhiUcXSUVj1w9_lw'
RANGE_NAME = 'Sheet1!A:Z'  # Adjust based on your sheet structure

SETTINGS_FILE = 'settings.json'

def get_google_sheets_service():
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('sheets', 'v4', credentials=creds)

def fetch_sheet_data():
    """Fetch data from Google Sheets."""
    try:
        service = get_google_sheets_service()
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME
        ).execute()
        values = result.get('values', [])
        print("Fetched sheet data:", values)
        return values
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def get_settings():
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {"current_week": 1, "start_date": "2025-06-29", "auto_week": False}

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f)

def calculate_week(start_date_str):
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        today = date.today()
        days_passed = (today - start_date).days
        if days_passed < 0:
            return 1
        return (days_passed // 7) + 1
    except Exception:
        return 1

def get_current_week():
    settings = get_settings()
    if settings.get("auto_week", False):
        return calculate_week(settings.get("start_date", "2025-06-29"))
    return settings.get("current_week", 1)

def set_current_week(week):
    settings = get_settings()
    settings["current_week"] = week
    save_settings(settings)

def set_start_date(start_date):
    settings = get_settings()
    settings["start_date"] = start_date
    save_settings(settings)

def set_auto_week(auto_week):
    settings = get_settings()
    settings["auto_week"] = auto_week
    save_settings(settings)

def get_exercises_for_day(day, sheet_data, week=None):
    """Extract exercises for a specific day (and optionally week) from sheet data."""
    if not sheet_data or len(sheet_data) < 2:
        return []

    headers = sheet_data[0]
    week_idx = headers.index("Week")
    day_idx = headers.index("Day")
    exercise_idx = headers.index("Exercise")

    exercises = []
    for row in sheet_data[1:]:
        if len(row) <= max(week_idx, day_idx, exercise_idx):
            continue
        if row[day_idx].strip().lower() == day.lower() and (week is None or str(row[week_idx]) == str(week)):
            exercises.append(row[exercise_idx].strip())
    return exercises

@app.route('/today', methods=['GET'])
def get_today_exercises():
    try:
        today = datetime.now().strftime('%A')
        current_week = get_current_week()
        sheet_data = fetch_sheet_data()
        exercises = get_exercises_for_day(today, sheet_data, week=current_week)
        return jsonify({
            'day': today,
            'week': current_week,
            'exercises': exercises,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Failed to fetch exercises'
        }), 500

@app.route('/tomorrow', methods=['GET'])
def get_tomorrow_exercises():
    try:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%A')
        current_week = get_current_week()
        sheet_data = fetch_sheet_data()
        exercises = get_exercises_for_day(tomorrow, sheet_data, week=current_week)
        return jsonify({
            'day': tomorrow,
            'week': current_week,
            'exercises': exercises,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Failed to fetch exercises'
        }), 500

SETTINGS_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Set Current Week</title>
</head>
<body>
    <h1>Settings</h1>
    <form method="post">
        <label for="week">Week Number:</label>
        <input type="number" id="week" name="week" min="1" value="{{ current_week }}" required {% if auto_week %}disabled{% endif %}>
        <br><br>
        <label for="start_date">Start Date (YYYY-MM-DD):</label>
        <input type="date" id="start_date" name="start_date" value="{{ start_date }}">
        <br><br>
        <label for="auto_week">Calculate week automatically:</label>
        <input type="checkbox" id="auto_week" name="auto_week" value="true" {% if auto_week %}checked{% endif %}>
        <br><br>
        <button type="submit">Save</button>
    </form>
    {% if message %}<p>{{ message }}</p>{% endif %}
</body>
</html>
'''

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    message = ''
    settings = get_settings()
    if request.method == 'POST':
        try:
            auto_week = request.form.get('auto_week') == 'true'
            start_date = request.form.get('start_date', settings.get('start_date', '2025-06-29'))
            if auto_week:
                set_auto_week(True)
                set_start_date(start_date)
                message = f"Auto week calculation enabled. Start date set to {start_date}."
            else:
                week = int(request.form['week'])
                set_current_week(week)
                set_auto_week(False)
                set_start_date(start_date)
                message = f"Week updated to {week}. Start date set to {start_date}."
        except Exception:
            message = "Invalid input."
    settings = get_settings()
    return render_template_string(SETTINGS_PAGE, current_week=settings.get('current_week', 1), start_date=settings.get('start_date', '2025-06-29'), auto_week=settings.get('auto_week', False), message=message)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
