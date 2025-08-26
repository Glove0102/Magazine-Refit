
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import subprocess
import os
from replit.object_storage import Client
import hashlib
import secrets

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))

def get_user_info(request):
    """Extract user info from Repl Auth headers"""
    return {
        'id': request.headers.get('X-Replit-User-Id'),
        'name': request.headers.get('X-Replit-User-Name'),
        'profile_image': request.headers.get('X-Replit-User-Profile-Image'),
        'bio': request.headers.get('X-Replit-User-Bio'),
        'url': request.headers.get('X-Replit-User-Url')
    }

def is_authenticated(request):
    """Check if user is authenticated via Repl Auth"""
    return request.headers.get('X-Replit-User-Id') is not None

def verify_admin_password(password):
    """Verify admin password against stored hash"""
    stored_hash = os.getenv('ADMIN_PASSWORD_HASH')
    if not stored_hash:
        return False
    
    # Hash the provided password
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return password_hash == stored_hash

def is_admin_authenticated(request):
    """Check if user has admin privileges"""
    return session.get('admin_authenticated', False)

@app.route('/')
def dashboard():
    if not is_authenticated(request):
        return redirect('/login')
    
    user = get_user_info(request)
    admin_auth = is_admin_authenticated(request)
    
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
                         user=user, 
                         folders=sorted(folders), 
                         pdf_files=sorted(pdf_files),
                         admin_authenticated=admin_auth)

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/admin_auth', methods=['POST'])
def admin_auth():
    if not is_authenticated(request):
        return jsonify({'error': 'Not authenticated'}), 401
    
    password = request.json.get('password')
    if not password:
        return jsonify({'error': 'Password required'}), 400
    
    if verify_admin_password(password):
        session['admin_authenticated'] = True
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Invalid admin password'}), 401

@app.route('/translate', methods=['POST'])
def translate_pdf():
    if not is_authenticated(request):
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not is_admin_authenticated(request):
        return jsonify({'error': 'Admin authentication required'}), 403
    
    pdf_file = request.form.get('pdf_file')
    if not pdf_file:
        return jsonify({'error': 'No PDF file specified'}), 400
    
    # Run the translation script
    try:
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
                              capture_output=True, text=True, timeout=300)
        
        return jsonify({
            'success': True,
            'output': result.stdout,
            'error': result.stderr if result.stderr else None
        })
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Translation timed out (5 min limit)'}), 408
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/merge', methods=['POST'])
def merge_folder():
    if not is_authenticated(request):
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not is_admin_authenticated(request):
        return jsonify({'error': 'Admin authentication required'}), 403
    
    try:
        data = request.get_json()
        if not data:
            folder_name = request.form.get('folder_name')
        else:
            folder_name = data.get('folder_name')
            
        if not folder_name:
            return jsonify({'error': 'No folder specified'}), 400
        
        # Update the merge_pdfs.py configuration
        with open('merge_pdfs.py', 'r') as f:
            content = f.read()
        
        # Replace the target_folder value
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('target_folder = '):
                lines[i] = f'target_folder = "{folder_name}"'
                break
        
        with open('merge_pdfs.py', 'w') as f:
            f.write('\n'.join(lines))
        
        # Run the merge script
        result = subprocess.run(['python', 'merge_pdfs.py'], 
                              capture_output=True, text=True, timeout=120)
        
        response_data = {
            'success': True,
            'output': result.stdout,
            'error': result.stderr if result.stderr else None
        }
        
        return jsonify(response_data)
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Merge timed out (2 min limit)'}), 408
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
