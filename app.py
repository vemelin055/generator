"""
Flask server for the Description Generator GUI
"""

from flask import Flask, render_template, request, jsonify, Response
import subprocess
import threading
import queue
import json
import os
import sys
from datetime import datetime
from credentials_util import ensure_google_credentials_file

app = Flask(__name__)

# Global variables for process management
process_queue = queue.Queue()
current_process = None
process_thread = None

def run_generation(sheet_id, sheet_name, column_name, start_row, end_row, prompt_text, force=False, dry_run=False):
    """Run the description generation script with given parameters"""
    cmd = [
        sys.executable, "generate_descriptions.py",
        "--sheet-id", sheet_id,
        "--worksheet", sheet_name,
        "--start-row", str(start_row),
        "--end-row", str(end_row),
        "--log-level", "INFO"
    ]
    
    if force:
        cmd.append("--force")
    if dry_run:
        cmd.append("--dry-run")
    
    # Create a temporary script to handle the custom column name
    temp_script = f"""
import sys
sys.path.insert(0, '.')
from generate_descriptions import DescriptionGenerator, parse_args

# Modify the column mapping
args = parse_args()
args.sheet_id = "{sheet_id}"
args.worksheet = "{sheet_name}"

# Create generator with custom args
generator = DescriptionGenerator(
    sheet_id=args.sheet_id,
    worksheet_name=args.worksheet,
    force=args.force,
    dry_run=args.dry_run,
    max_retries=args.max_retries,
    retry_delay=args.retry_delay,
    log_level=args.log_level
)

# Modify the description column resolution
try:
    count = generator.process(
        start_row={start_row},
        end_row={end_row} if {end_row} else None,
        limit=None,
        sleep=0.0
    )
    print(f"✅ Обработано строк: {{count}}")
except Exception as e:
    print(f"❌ Ошибка: {{e}}")
"""

    # Write temporary script and run it
    temp_file = "temp_generate.py"
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(temp_script)
    
    try:
        process = subprocess.Popen(
            [sys.executable, temp_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        for line in process.stdout:
            yield line
            
        process.wait()
        if process.returncode != 0:
            yield f"❌ Process exited with code {process.returncode}\n"
            
    except Exception as e:
        yield f"❌ Error running process: {str(e)}\n"
    finally:
        # Clean up temporary file
        try:
            os.remove(temp_file)
        except:
            pass

@app.route('/')
def index():
    return open('gui.html', 'r').read()

@app.route('/api/start', methods=['POST'])
def start_generation():
    global process_thread
    
    data = request.json
    sheet_url = data.get('sheet_url', '')
    sheet_name = data.get('sheet_name', '')
    column_name = data.get('column_name', 'Описание')
    start_row = data.get('start_row', 2)
    end_row = data.get('end_row', 100)
    prompt = data.get('prompt', '')
    force = data.get('force', False)
    dry_run = data.get('dry_run', False)
    
    # Extract sheet ID from URL if full URL is provided
    sheet_id = sheet_url
    if 'spreadsheets/d/' in sheet_url:
        sheet_id = sheet_url.split('/d/')[1].split('/')[0]
    
    # Validate inputs
    if start_row >= end_row:
        return jsonify({'error': 'Начальная строка должна быть меньше конечной'}), 400
    
    if not sheet_id or not sheet_name:
        return jsonify({'error': 'Необходимо указать ID таблицы и название листа'}), 400
    
    # Clear the queue
    while not process_queue.empty():
        process_queue.get_nowait()
    
    def generation_worker():
        try:
            for line in run_generation(sheet_id, sheet_name, column_name, start_row, end_row, prompt, force, dry_run):
                process_queue.put({
                    'timestamp': datetime.now().isoformat(),
                    'message': line.strip(),
                    'type': 'info'
                })
            process_queue.put({
                'timestamp': datetime.now().isoformat(),
                'message': '✅ Генерация завершена',
                'type': 'success'
            })
        except Exception as e:
            process_queue.put({
                'timestamp': datetime.now().isoformat(),
                'message': f'❌ Ошибка: {str(e)}',
                'type': 'error'
            })
    
    # Start the generation in a separate thread
    process_thread = threading.Thread(target=generation_worker)
    process_thread.daemon = True
    process_thread.start()
    
    return jsonify({'status': 'started', 'start_row': start_row, 'end_row': end_row})

@app.route('/api/stop', methods=['POST'])
def stop_generation():
    global process_thread
    
    # Stop the generation thread by setting a flag (simple approach)
    # In a real implementation, we'd need a more robust way to stop the process
    if process_thread and process_thread.is_alive():
        # We'll rely on the frontend to handle the stop by not processing further messages
        return jsonify({'status': 'stop_requested'})
    
    return jsonify({'status': 'no process running'})

@app.route('/api/status')
def status():
    return jsonify({
        'active': process_thread.is_alive() if process_thread else False
    })

@app.route('/api/preview', methods=['POST'])
def preview_sheet():
    try:
        data = request.json
        sheet_url = data.get('sheet_url', '')
        sheet_name = data.get('sheet_name', '')
        
        # Extract sheet ID from URL if full URL is provided
        sheet_id = sheet_url
        if 'spreadsheets/d/' in sheet_url:
            sheet_id = sheet_url.split('/d/')[1].split('/')[0]
        
        if not sheet_id:
            return jsonify({'error': 'Не указан ID таблицы'}), 400
        
        # Import gspread here to avoid dependency issues
        import gspread
        from google.oauth2.service_account import Credentials
        
        # Set up credentials
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        
        credentials_file = ensure_google_credentials_file()
        creds = Credentials.from_service_account_file(str(credentials_file), scopes=scopes)
        gc = gspread.authorize(creds)
        
        # Open the spreadsheet
        spreadsheet = gc.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Get all data
        data = worksheet.get_all_values()
        headers = data[0] if data else []
        rows = data[1:10] if len(data) > 1 else []  # First 9 rows for preview
        
        return jsonify({
            'headers': headers,
            'rows': rows,
            'total_rows': len(data) - 1 if len(data) > 1 else 0
        })
        
    except Exception as e:
        return jsonify({'error': f'Ошибка загрузки данных: {str(e)}'}), 500

@app.route('/api/logs')
def stream_logs():
    def generate():
        while True:
            try:
                log = process_queue.get(timeout=1)
                yield f"data: {json.dumps(log)}\n\n"
            except queue.Empty:
                yield "data: {\"keep_alive\": true}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    use_debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(
        debug=use_debug,
        port=port,
        host="0.0.0.0",
        use_reloader=use_debug,
    )
