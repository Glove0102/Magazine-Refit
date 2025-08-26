
from flask import Flask, render_template, request, jsonify, session
import subprocess
import os
from replit.object_storage import Client
import hashlib
import uuid

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-this')

def verify_admin_password(password):
    """Verify admin password against stored hash"""
    stored_hash = os.getenv('ADMIN_PASSWORD_HASH')
    if not stored_hash:
        print("DEBUG: No ADMIN_PASSWORD_HASH found in environment")
        return False

    password_hash = hashlib.sha256(password.encode()).hexdigest()
    result = password_hash == stored_hash
    print(f"DEBUG: Password verification result: {result}")
    return result

def is_authenticated():
    """Check if current session is authenticated"""
    return session.get('authenticated', False)

@app.route('/')
def dashboard():
    # Get available folders from Object Storage
    storage_client = Client()
    try:
        all_objects = storage_client.list()
        folders = set()
        pdf_files = []

        for obj in all_objects:
            if obj.name.endswith('.pdf'):
                if '/' in obj.name:
                    folder = obj.name.split('/')[0]
                    folders.add(folder)
                else:
                    pdf_files.append(obj.name)
    except:
        folders = set()
        pdf_files = []

    return render_template('dashboard.html', 
                         folders=sorted(folders), 
                         pdf_files=sorted(pdf_files))

@app.route('/check_auth')
def check_auth():
    """Check authentication status"""
    return jsonify({'authenticated': is_authenticated()})

@app.route('/admin_auth', methods=['POST'])
def admin_auth():
    """Handle admin authentication"""
    try:
        data = request.get_json()
        password = data.get('password')
        
        if not password:
            return jsonify({'success': False, 'error': 'No password provided'}), 400
            
        if verify_admin_password(password):
            session['authenticated'] = True
            session['auth_token'] = str(uuid.uuid4())
            return jsonify({'success': True, 'token': session['auth_token']})
        else:
            return jsonify({'success': False, 'error': 'Invalid admin password'}), 403
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/translate', methods=['POST'])
def translate_pdf():
    try:
        if not is_authenticated():
            return jsonify({'error': 'Authentication required'}), 403

        data = request.get_json()
        pdf_file = data.get('pdf_file')
        
        if not pdf_file:
            return jsonify({'error': 'No PDF file specified'}), 400

        print(f"DEBUG: Starting translation for: {pdf_file}")

        # Update the main.py configuration
        with open('main.py', 'r') as f:
            content = f.read()

        # Replace the input_pdf value
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('input_pdf = '):
                lines[i] = f'input_pdf = "{pdf_file}"'
                break

        with open('main.py', 'w') as f:
            f.write('\n'.join(lines))

        # Run the translation
        result = subprocess.run(['python', 'main.py'], 
                              capture_output=True, text=True, timeout=600)

        return jsonify({
            'success': True,
            'output': result.stdout,
            'error': result.stderr if result.stderr else None
        })

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Translation timed out (10 min limit)'}), 408
    except Exception as e:
        print(f"Translation error: {str(e)}")
        return jsonify({'error': f'Translation failed: {str(e)}'}), 500

@app.route('/merge', methods=['POST'])
def merge_folder():
    try:
        if not is_authenticated():
            return jsonify({'error': 'Authentication required'}), 403

        data = request.get_json()
        folder_name = data.get('folder_name')
        
        if not folder_name:
            return jsonify({'error': 'No folder specified'}), 400

        print(f"DEBUG: Starting merge for folder: {folder_name}")

        # Run the merge script
        result = subprocess.run(['python', 'merge_pdfs.py', folder_name], 
                              capture_output=True, text=True, timeout=120)

        return jsonify({
            'success': True,
            'output': result.stdout,
            'error': result.stderr if result.stderr else None
        })

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Merge timed out (2 min limit)'}), 408
    except Exception as e:
        print(f"Merge error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/logout')
def logout():
    """Clear authentication session"""
    session.clear()
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
