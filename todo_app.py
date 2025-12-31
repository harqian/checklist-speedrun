from flask import Flask, render_template, jsonify, request, send_from_directory
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import json
import glob
import dotenv

app = Flask(__name__)
app.json.sort_keys = False

# Configuration
dotenv.load_dotenv()
CHECKLISTS_DIR = os.path.join(os.path.dirname(__file__), 'checklists')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')  # Update if needed
SHEET_NAME = os.getenv('SHEET_NAME')  # Update if needed
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
# Checklist name to column mapping
CHECKLIST_COLUMN_NAME_MAP = {
    'morning': 'Day',
    'morning (rushed)': 'Day (rushed)',
    'night': 'Night'
}

CHECKLIST_COLUMN_NUMBER_MAP = {
    'Day': 2,
    'Day (rushed)': 3,
    'Night': 4
}

def get_sheets_service():
    """Create and return Google Sheets API service"""
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=credentials)
        return service
    except Exception as e:
        print(f"❌ Error creating sheets service: {e}")
        return None

@app.route('/')
def index():
    """Serve the main todo app page"""
    return render_template('todo_app.html')

@app.route('/keyboard_shortcuts.json')
def get_shortcuts():
    """Serve keyboard shortcuts configuration"""
    shortcuts_path = os.path.join(os.path.dirname(__file__), 'keyboard_shortcuts.json')
    return send_from_directory(os.path.dirname(shortcuts_path), 'keyboard_shortcuts.json')

@app.route('/api/checklists')
def list_checklists():
    """List all available checklist JSON files"""
    try:
        json_files = glob.glob(os.path.join(CHECKLISTS_DIR, '*.json'))
        checklists = []
        for file_path in json_files:
            filename = os.path.basename(file_path)
            checklist_name = os.path.splitext(filename)[0]
            checklists.append({
                'name': checklist_name,
                'filename': filename
            })
        return jsonify({'checklists': checklists})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/checklist/<checklist_name>')
def get_checklist(checklist_name):
    """Get a specific checklist by name"""
    try:
        file_path = os.path.join(CHECKLISTS_DIR, f'{checklist_name}.json')
        # Prevent path traversal attacks
        if not os.path.realpath(file_path).startswith(os.path.realpath(CHECKLISTS_DIR)):
            return jsonify({'error': 'Invalid checklist name'}), 400
        if not os.path.exists(file_path):
            return jsonify({'error': 'Checklist not found'}), 404

        with open(file_path, 'r', encoding='utf-8') as f:
            checklist_data = json.load(f)

        response = app.response_class(
            response=json.dumps({'checklist': checklist_data}, ensure_ascii=False, sort_keys=False),
            status=200,
            mimetype='application/json'
        )
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/log-time', methods=['POST'])
def log_time():
    """Log completion time to Google Sheets"""
    try:
        data = request.json
        checklist_name = data.get('checklist_name')
        time_seconds = data.get('time_seconds')

        if not checklist_name or time_seconds is None:
            return jsonify({'error': 'Missing checklist_name or time_seconds'}), 400

        # Determine which column to update based on checklist name
        column_name = CHECKLIST_COLUMN_NAME_MAP.get(checklist_name.lower(), 'Day')

        service = get_sheets_service()
        if not service:
            return jsonify({'error': 'Could not connect to Google Sheets'}), 500

        # Get today's date in format M/D/YYYY
        now = datetime.now()
        if now.hour < 6:
            target_date = now - timedelta(days=1)
        else:
            target_date = now

        # Format without leading zeros (M/D/YYYY)
        month = str(target_date.month)
        day = str(target_date.day)
        year = str(target_date.year)
        today = f"{month}/{day}/{year}"

        # Find today's date in column A
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!A:A'
        ).execute()

        values = result.get('values', [])
        row_number = None
        for i, row in enumerate(values):
            if row and row[0] == today:
                row_number = i + 1
                break

        if row_number is None:
            return jsonify({'error': f'Could not find date {today} in spreadsheet'}), 404

        column_index = CHECKLIST_COLUMN_NUMBER_MAP.get(column_name, 2) - 1  # Zero-based index
        column_letter = chr(ord('A') + column_index)

        # Format time as hours, minutes, and seconds
        hours = int(time_seconds // 3600)
        minutes = int((time_seconds % 3600) // 60)
        seconds = int(time_seconds % 60)

        if hours > 0:
            time_str = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            time_str = f"{minutes}m {seconds}s"
        else:
            time_str = f"{seconds}s"

        # Update the cell
        range_to_update = f'{SHEET_NAME}!{column_letter}{row_number}'
        body = {'values': [[time_str]]}

        result = service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_to_update,
            valueInputOption='RAW',
            body=body
        ).execute()

        return jsonify({
            'success': True,
            'message': f'Logged {time_str} to {column_name} column',
            'updated_cells': result.get('updatedCells', 0)
        })

    except HttpError as error:
        return jsonify({'error': f'Google Sheets API error: {error}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)

