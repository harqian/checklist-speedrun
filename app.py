import os
import json
import glob
from datetime import datetime, timedelta
from pathlib import Path

import dotenv
from flask import Flask, render_template, jsonify, request, send_from_directory
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables early
dotenv.load_dotenv()

app = Flask(__name__)
# Flask 2.3+ handles JSON sorting via this config
app.json.sort_keys = False

# Configuration
BASE_DIR = Path(__file__).parent
CHECKLISTS_DIR = BASE_DIR / 'checklists'
CHECKLISTS_DIR.mkdir(exist_ok=True)

SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
SHEET_NAME = os.getenv('SHEET_NAME', 'Sheet1')
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')

# Checklist name to column mapping
CHECKLIST_COLUMN_NAME_MAP = {
    'morning': 'Day',
    'night': 'Night'
}

CHECKLIST_COLUMN_NUMBER_MAP = {
    'Day': 2,
    'Night': 4
}

def get_sheets_service():
    """Create and return Google Sheets API service"""
    if not SERVICE_ACCOUNT_FILE or not Path(SERVICE_ACCOUNT_FILE).exists():
        app.logger.error(f"Service account file not found: {SERVICE_ACCOUNT_FILE}")
        return None

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=credentials, cache_discovery=False)
        return service
    except Exception as e:
        app.logger.error(f"Error creating sheets service: {e}")
        return None

@app.route('/')
def index():
    """Serve the main todo app page"""
    return render_template('index.html')

@app.route('/keyboard_shortcuts.json')
def get_shortcuts():
    """Serve keyboard shortcuts configuration"""
    return send_from_directory(BASE_DIR, 'keyboard_shortcuts.json')

@app.route('/api/checklists')
def list_checklists():
    """List all available checklist JSON files"""
    try:
        json_files = list(CHECKLISTS_DIR.glob('*.json'))
        checklists = [
            {
                'name': f.stem,
                'filename': f.name
            }
            for f in sorted(json_files)
        ]
        return jsonify({'checklists': checklists})
    except Exception as e:
        app.logger.error(f"Error listing checklists: {e}")
        return jsonify({'error': str(e)}), 500

def get_safe_path(name):
    """Ensure the checklist name doesn't lead to path traversal"""
    if not name:
        return None
    # Add .json extension and resolve the full path
    try:
        safe_path = (CHECKLISTS_DIR / f"{name}.json").resolve()
        # Check if the resolved path is still inside CHECKLISTS_DIR
        if CHECKLISTS_DIR.resolve() in safe_path.parents:
            return safe_path
    except (ValueError, RuntimeError):
        return None
    return None

@app.route('/api/checklist/<checklist_name>')
def get_checklist(checklist_name):
    """Get a specific checklist by name"""
    try:
        file_path = get_safe_path(checklist_name)
        
        if not file_path or not file_path.exists():
            return jsonify({'error': 'Checklist not found'}), 404

        with open(file_path, 'r', encoding='utf-8') as f:
            checklist_data = json.load(f)

        return jsonify({'checklist': checklist_data})
    except Exception as e:
        app.logger.error(f"Error getting checklist {checklist_name}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/checklist/<checklist_name>', methods=['PUT'])
def save_checklist(checklist_name):
    """Save/update a checklist"""
    try:
        data = request.json
        if not data or 'checklist' not in data:
            return jsonify({'error': 'No checklist data provided'}), 400

        file_path = get_safe_path(checklist_name)
        if not file_path:
            return jsonify({'error': 'Invalid checklist name'}), 400

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data['checklist'], f, ensure_ascii=False, indent=2)

        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error saving checklist {checklist_name}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/log-time', methods=['POST'])
def log_time():
    """Log completion time to Google Sheets"""
    try:
        data = request.json
        checklist_name = data.get('checklist_name')
        time_seconds = data.get('time_seconds')
        is_rushed = data.get('is_rushed', False)

        if not checklist_name or time_seconds is None:
            return jsonify({'error': 'Missing checklist_name or time_seconds'}), 400

        if not SPREADSHEET_ID:
            return jsonify({'error': 'SPREADSHEET_ID not configured'}), 500

        # Determine which column to update based on checklist name
        column_name = CHECKLIST_COLUMN_NAME_MAP.get(checklist_name.lower(), 'Day')

        service = get_sheets_service()
        if not service:
            return jsonify({'error': 'Could not connect to Google Sheets'}), 500

        # Get today's date in format M/D/YYYY
        now = datetime.now()
        # If it's early morning (before 6 AM), log as the previous day
        target_date = now - timedelta(days=1) if now.hour < 6 else now
        today = target_date.strftime('%-m/%-d/%Y')

        # Find today's date in column A
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{SHEET_NAME}'!A:A"
        ).execute()

        values = result.get('values', [])
        row_number = next((i + 1 for i, row in enumerate(values) if row and row[0] == today), None)

        if row_number is None:
            return jsonify({'error': f'Could not find date {today} in spreadsheet'}), 404

        column_index = CHECKLIST_COLUMN_NUMBER_MAP.get(column_name, 2) - 1  # Zero-based index
        if is_rushed:
            column_index += 1
            
        column_letter = chr(ord('A') + column_index)

        # Format time string
        td = timedelta(seconds=int(time_seconds))
        parts = []
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0: parts.append(f"{hours}h")
        if minutes > 0: parts.append(f"{minutes}m")
        if seconds > 0 or not parts: parts.append(f"{seconds}s")
        time_str = " ".join(parts)

        # Update the cell
        range_to_update = f"'{SHEET_NAME}'!{column_letter}{row_number}"
        body = {'values': [[time_str]]}

        result = service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_to_update,
            valueInputOption='RAW',
            body=body
        ).execute()

        display_name = column_name + (" (rushed)" if is_rushed else "")
        return jsonify({
            'success': True,
            'message': f'Logged {time_str} to {display_name} column',
            'updated_cells': result.get('updatedCells', 0)
        })

    except HttpError as error:
        app.logger.error(f"Google Sheets API error: {error}")
        return jsonify({'error': f'Google Sheets API error: {error.reason}'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error in log_time: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Use environment variables for host/port if available, but default to 5001 as per original
    port = int(os.getenv('PORT', 5001))
    app.run(debug=True, port=port)

