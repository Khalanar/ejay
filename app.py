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

def get_exercises_for_weekday(weekday_name, sheet_data, week=None):
    """Extract exercises for a specific weekday name (and optionally week) from sheet data."""
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
        if row[day_idx].strip().lower() == weekday_name.lower() and (week is None or str(row[week_idx]) == str(week)):
            exercises.append(row[exercise_idx].strip())
    return exercises

def get_weekday_name_from_start(start_date, offset_days):
    """Return the weekday name for a given offset from the start date."""
    target_date = start_date + timedelta(days=offset_days)
    return target_date.strftime('%A')

def get_exercise_row_by_offset(sheet_data, offset):
    """Return the exercise row at the given offset (excluding header)."""
    if not sheet_data or len(sheet_data) < 2:
        return []
    data_rows = sheet_data[1:]
    if 0 <= offset < len(data_rows):
        return data_rows[offset]
    return []

def get_unique_days_in_order(sheet_data):
    """Return a list of unique 'Day' values in the order they appear in the sheet (excluding header)."""
    if not sheet_data or len(sheet_data) < 2:
        return []
    day_idx = sheet_data[0].index("Day")
    seen = set()
    unique_days = []
    for row in sheet_data[1:]:
        if len(row) > day_idx:
            day = row[day_idx].strip()
            if day and day not in seen:
                unique_days.append(day)
                seen.add(day)
    return unique_days

def get_exercises_for_day_group(sheet_data, day_name, week=None):
    """Return all rows for the given day_name and week (if provided)."""
    if not sheet_data or len(sheet_data) < 2:
        return []
    headers = sheet_data[0]
    week_idx = headers.index("Week")
    day_idx = headers.index("Day")
    group = []
    for row in sheet_data[1:]:
        if len(row) <= max(week_idx, day_idx):
            continue
        if row[day_idx].strip() == day_name and (week is None or str(row[week_idx]) == str(week)):
            group.append(row)
    return group

def get_motivational_sentence():

    try:
        import openai
        settings = get_settings()
        api_key = settings.get('openai_api_key', '')
        print(f"[DEBUG] OpenAI API key: {api_key[:8]}...{api_key[-4:]}")
        if not api_key:
            print("[DEBUG] No OpenAI API key found in settings.")
            return "Give it your best today!", 0.0
        openai.api_key = api_key
        print("[DEBUG] Making OpenAI API call...")
        # Use a current, cheaper model
        model_name = "gpt-4.1-nano"  # Change here if you want a different model
        response = openai.ChatCompletion.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a motivational fitness coach."},
                {"role": "user", "content": "Give me a short, punchy, and thoughtful motivational sentence for my workout today. It should connect today's effort to the long-term benefits of gaining muscle, losing fat, and improving my life. Only return the sentence, nothing else."}
            ],
            max_tokens=40
        )
        print("[DEBUG] OpenAI API call successful.")
        # Calculate cost for GPT-4.1 nano
        usage = response['usage']
        input_tokens = usage['prompt_tokens']
        output_tokens = usage['completion_tokens']
        # Pricing for GPT-4.1 nano
        input_cost = input_tokens * 0.100 / 1_000_000  # $0.100 per 1M tokens
        output_cost = output_tokens * 0.400 / 1_000_000  # $0.400 per 1M tokens
        total_cost = input_cost + output_cost
        print(f"[DEBUG] Cost: ${total_cost:.6f} (Input: {input_tokens} tokens, Output: {output_tokens} tokens)")
        return response.choices[0].message['content'].strip(), total_cost
    except Exception as e:
        print(f"[ERROR] OpenAI API call failed: {e}")
        return "Give it your best today!", 0.0

@app.route('/today', methods=['GET'])
def get_today_exercises():
    try:
        settings = get_settings()
        start_date = datetime.strptime(settings.get('start_date', '2025-06-29'), "%Y-%m-%d").date()
        today = date.today()
        days_passed = (today - start_date).days
        days_passed = max(days_passed, 0)
        sheet_data = fetch_sheet_data()
        unique_days = get_unique_days_in_order(sheet_data)
        if not unique_days:
            motivation, cost = get_motivational_sentence()
            return jsonify({'exercises': [], 'day': str(today), 'week': get_current_week(), 'motivation': motivation, 'estimated_cost': cost})
        day_idx = days_passed % len(unique_days)
        day_name = unique_days[day_idx]
        current_week = get_current_week()
        exercises_rows = get_exercises_for_day_group(sheet_data, day_name, week=current_week)
        headers = sheet_data[0]
        exercise_idx = headers.index("Exercise")
        exercise_names = [row[exercise_idx] for row in exercises_rows if len(row) > exercise_idx]
        motivation, cost = get_motivational_sentence()
        return jsonify({
            'day': str(today),
            'exercises': exercise_names,
            'week': current_week,
            'motivation': motivation,
            'estimated_cost': cost
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Failed to fetch exercises'
        }), 500

@app.route('/tomorrow', methods=['GET'])
def get_tomorrow_exercises():
    try:
        settings = get_settings()
        start_date = datetime.strptime(settings.get('start_date', '2025-06-29'), "%Y-%m-%d").date()
        today = date.today()
        days_passed = (today - start_date).days
        days_passed = max(days_passed, 0)
        sheet_data = fetch_sheet_data()
        unique_days = get_unique_days_in_order(sheet_data)
        if not unique_days:
            motivation, cost = get_motivational_sentence()
            return jsonify({'exercises': [], 'day': str(today + timedelta(days=1)), 'week': get_current_week(), 'motivation': motivation, 'estimated_cost': cost})
        day_idx = (days_passed + 1) % len(unique_days)
        day_name = unique_days[day_idx]
        current_week = get_current_week()
        exercises_rows = get_exercises_for_day_group(sheet_data, day_name, week=current_week)
        headers = sheet_data[0]
        exercise_idx = headers.index("Exercise")
        exercise_names = [row[exercise_idx] for row in exercises_rows if len(row) > exercise_idx]
        motivation, cost = get_motivational_sentence()
        return jsonify({
            'day': str(today + timedelta(days=1)),
            'exercises': exercise_names,
            'week': current_week,
            'motivation': motivation,
            'estimated_cost': cost
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
        <label for="openai_api_key">OpenAI API Key:</label>
        <input type="text" id="openai_api_key" name="openai_api_key" value="{{ openai_api_key }}" style="width:400px;">
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
            openai_api_key = request.form.get('openai_api_key', settings.get('openai_api_key', ''))
            if auto_week:
                set_auto_week(True)
                set_start_date(start_date)
                settings['openai_api_key'] = openai_api_key
                save_settings(settings)
                message = f"Auto week calculation enabled. Start date set to {start_date}."
            else:
                week = int(request.form['week'])
                set_current_week(week)
                set_auto_week(False)
                set_start_date(start_date)
                settings['openai_api_key'] = openai_api_key
                save_settings(settings)
                message = f"Week updated to {week}. Start date set to {start_date}."
        except Exception:
            message = "Invalid input."
    settings = get_settings()
    return render_template_string(SETTINGS_PAGE, current_week=settings.get('current_week', 1), start_date=settings.get('start_date', '2025-06-29'), auto_week=settings.get('auto_week', False), openai_api_key=settings.get('openai_api_key', ''), message=message)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
