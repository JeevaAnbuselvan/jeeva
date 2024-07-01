import os
import tarfile
import re
import tempfile
from flask import Flask, request, redirect, url_for, render_template, flash
from werkzeug.utils import secure_filename

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'tar', 'tar.gz'}
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'supersecretkey'


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def analyze_logs(directory):
    patterns = {
        'failure': re.compile(r'failure', re.IGNORECASE),
        'error': re.compile(r'error', re.IGNORECASE),
        'warning': re.compile(r'warning', re.IGNORECASE),
        'crash': re.compile(r'core_', re.IGNORECASE),
    }
    log_matches = []
    skip_files = ["bgpd-tech.txt.gz", "l2mribd-tech.txt", "nsm-tech.txt", "onmd-tech.txt", "hslrasmgr-tech.txt", "ndd-tech.txt", "vrrpd-tech.txt"]
    for root, dirs, files in os.walk(directory):
        files[:] = [f for f in files if f not in skip_files]
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines):
                        for log_level, pattern in patterns.items():
                            if pattern.search(line):
                                log_matches.append({
                                    'file': file,
                                    'line_number': i + 1,
                                    'log_level': log_level,
                                    'message': line.strip()
                                })
            except Exception as e:
                log_matches.append({
                    'file': file,
                    'line_number': -1,
                    'log_level': 'error',
                    'message': f"Could not read file {file_path}: {e}"
                })

    return log_matches

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        with tempfile.TemporaryDirectory() as temp_dir:
            with tarfile.open(file_path, "r:*") as tar:
                tar.extractall(path=temp_dir)
            log_matches = analyze_logs(temp_dir)

        os.remove(file_path)
        return render_template('results.html', log_matches=log_matches)

    flash('Invalid file format')
    return redirect(request.url)


if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
