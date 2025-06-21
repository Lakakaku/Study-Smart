import json
from flask import Flask, render_template, request, redirect, url_for, flash, render_template_string, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import requests
import fitz  # PyMuPDF
import pytesseract
import urllib.parse
from pdf2image import convert_from_path
import os
import json.decoder
from spaced_repetition import update_rating
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['SECRET_KEY'] = 'din-hemliga-nyckel'  # byt till något säkert
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

SUBJECTS_FILE = 'subjects.json'
QUIZZES_FILE = 'quizzes.json'
DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'data')
RATINGS_FILE = os.path.join(DATA_FOLDER, 'ratings.json')
FLASHCARDS_DATA_FILE = 'flashcards_data.json'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Du måste vara inloggad för att komma åt den här sidan.'
login_manager.login_message_category = 'info'

# Användare loader för flask-login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(60), nullable=False)
    flashcards = db.relationship('Flashcard', backref='owner', lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"User('{self.username}')"

class Flashcard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    ease_factor = db.Column(db.Float, default=2.5)
    interval = db.Column(db.Integer, default=1)  # dagar till nästa repetition
    repetitions = db.Column(db.Integer, default=0)
    next_review = db.Column(db.Date, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    topic = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Flashcard('{self.question[:50]}...')"

# Skapa tabeller om de inte finns
with app.app_context():
    db.create_all()

# -------------------- Utility Functions --------------------
def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return default

def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Användarspecifika funktioner
def get_user_subjects_file():
    """Returnerar användarspecifik subjects-fil"""
    return f'subjects_{current_user.id}.json'

def get_user_quizzes_file():
    """Returnerar användarspecifik quizzes-fil"""
    return f'quizzes_{current_user.id}.json'

def get_user_ratings_file():
    """Returnerar användarspecifik ratings-fil"""
    return os.path.join(DATA_FOLDER, f'ratings_{current_user.id}.json')

# -------------------- Subjects (användarspecifika) --------------------
def load_subjects():
    if current_user.is_authenticated:
        return load_json(get_user_subjects_file(), [])
    return []

def save_subjects(subjects):
    if current_user.is_authenticated:
        save_json(subjects, get_user_subjects_file())

# -------------------- Quizzes (användarspecifika) --------------------
def load_quizzes():
    if current_user.is_authenticated:
        return load_json(get_user_quizzes_file(), {})
    return {}

def save_quizzes(quizzes):
    if current_user.is_authenticated:
        save_json(quizzes, get_user_quizzes_file())

# -------------------- Ratings (användarspecifika) --------------------
def load_ratings():
    if current_user.is_authenticated:
        return load_json(get_user_ratings_file(), {})
    return {}

def save_ratings(ratings):
    if current_user.is_authenticated:
        save_json(ratings, get_user_ratings_file())

def save_flashcard_data(data):
    save_ratings(data)

def update_flashcard_schedule(data, subject, topic, question, rating, time_taken):
    flashcard = data.setdefault(subject, {}).setdefault(topic, {}).setdefault(question, {
        "ease_factor": 2.5, "repetitions": 0, "interval": 0,
        "next_review": datetime.now().strftime("%Y-%m-%d")
    })

    ef = flashcard["ease_factor"]
    reps = flashcard["repetitions"]
    prev_interval = flashcard["interval"]
    q = int(rating)

    # 1) Ease-factor
    ef = max(1.3, ef + (0.1 - (4 - q) * (0.08 + (4 - q) * 0.02)))

    # 2) Reps & interval
    if q < 3:
        reps, interval = 0, 1
    else:
        reps += 1
        if reps == 1:
            interval = int(round(ef)) if q == 4 else 1
        elif reps == 2:
            interval = 6
        else:
            interval = int(round(prev_interval * ef))

    # 3) Bonus för super-snabbt perfekt svar
    if q == 4 and time_taken is not None and time_taken < 5:
        interval = max(interval, int(round((prev_interval or 1) * ef * 1.2)))

    next_rev = (datetime.now() + timedelta(days=interval)).strftime("%Y-%m-%d")

    flashcard.update({
        "rating": q,
        "time": time_taken,
        "ease_factor": round(ef, 2),
        "repetitions": reps,
        "interval": interval,
        "next_review": next_rev,
        "timestamp": datetime.now().isoformat()
    })
    return data

# -------------------- Auth Routes --------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Omdirigera inloggade användare
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        # Validering
        if len(username) < 3:
            flash('Användarnamn måste vara minst 3 tecken långt.', 'danger')
            return redirect(url_for('register'))
        
        if len(password) < 6:
            flash('Lösenord måste vara minst 6 tecken långt.', 'danger')
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Användarnamn finns redan.', 'danger')
            return redirect(url_for('register'))

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, password_hash=hashed_pw)
        db.session.add(user)
        db.session.commit()
        flash('Kontot skapades! Nu kan du logga in.', 'success')
        return redirect(url_for('login'))

    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Registrera - Flashcards</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 400px; margin: 50px auto; padding: 20px; }
                input { width: 100%; padding: 10px; margin: 5px 0; box-sizing: border-box; }
                button { background: #007bff; color: white; padding: 10px; border: none; width: 100%; cursor: pointer; }
                button:hover { background: #0056b3; }
                .flash-messages { margin: 10px 0; }
                .alert { padding: 10px; margin: 5px 0; border-radius: 4px; }
                .alert-danger { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
                .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            </style>
        </head>
        <body>
            <h2>Registrera nytt konto</h2>
            
            <div class="flash-messages">
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ category }}">{{ message }}</div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}
            </div>
            
            <form method="POST">
                <label>Användarnamn:</label>
                <input name="username" required minlength="3">
                <label>Lösenord:</label>
                <input type="password" name="password" required minlength="6">
                <button type="submit">Registrera</button>
            </form>
            <p><a href="{{ url_for('login') }}">Redan registrerad? Logga in här.</a></p>
        </body>
        </html>
    ''')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Omdirigera inloggade användare
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f'Välkommen {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Fel användarnamn eller lösenord.', 'danger')

    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Logga in - Flashcards</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 400px; margin: 50px auto; padding: 20px; }
                input { width: 100%; padding: 10px; margin: 5px 0; box-sizing: border-box; }
                button { background: #28a745; color: white; padding: 10px; border: none; width: 100%; cursor: pointer; }
                button:hover { background: #1e7e34; }
                .flash-messages { margin: 10px 0; }
                .alert { padding: 10px; margin: 5px 0; border-radius: 4px; }
                .alert-danger { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
                .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
                .alert-info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
            </style>
        </head>
        <body>
            <h2>Logga in</h2>
            
            <div class="flash-messages">
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ category }}">{{ message }}</div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}
            </div>
            
            <form method="POST">
                <label>Användarnamn:</label>
                <input name="username" required>
                <label>Lösenord:</label>
                <input type="password" name="password" required>
                <button type="submit">Logga in</button>
            </form>
            <p><a href="{{ url_for('register') }}">Skapa nytt konto</a></p>
        </body>
        </html>
    ''')

@app.route('/dashboard')
@login_required
def dashboard():
    subjects = load_subjects()
    user_stats = {
        'total_subjects': len(subjects),
        'total_quizzes': sum(len(quizzes) for quizzes in load_quizzes().values()),
        'member_since': current_user.created_at.strftime('%Y-%m-%d')
    }
    
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Dashboard - Flashcards</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                .header { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                .stats { display: flex; gap: 20px; margin: 20px 0; }
                .stat-card { background: #e9ecef; padding: 15px; border-radius: 8px; text-align: center; flex: 1; }
                .nav-links { margin: 20px 0; }
                .nav-links a { display: inline-block; background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; margin: 5px; }
                .nav-links a:hover { background: #0056b3; }
                .logout { background: #dc3545; }
                .logout:hover { background: #c82333; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Dashboard</h1>
                <p>Välkommen, <strong>{{ current_user.username }}</strong>!</p>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <h3>{{ user_stats.total_subjects }}</h3>
                    <p>Ämnen</p>
                </div>
                <div class="stat-card">
                    <h3>{{ user_stats.total_quizzes }}</h3>
                    <p>Quiz</p>
                </div>
                <div class="stat-card">
                    <h3>{{ user_stats.member_since }}</h3>
                    <p>Medlem sedan</p>
                </div>
            </div>
            
            <div class="nav-links">
                <a href="{{ url_for('home') }}">Mina Ämnen</a>
                <a href="{{ url_for('create_quiz') }}">Skapa Quiz</a>
                <a href="{{ url_for('flashcards_by_date') }}">Repetitioner</a>
                <a href="{{ url_for('logout') }}" class="logout">Logga ut</a>
            </div>
        </body>
        </html>
    ''', current_user=current_user, user_stats=user_stats)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Du är utloggad.', 'info')
    return redirect(url_for('login'))

# -------------------- Main Routes (nu med @login_required) --------------------

@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
    subjects = load_subjects()
    if request.method == 'POST':
        sub = request.form['subject'].strip()
        if sub and sub not in subjects:
            subjects.append(sub)
            save_subjects(subjects)
        return redirect(url_for('home'))
    return render_template('index.html', subjects=subjects)

@app.route('/delete_krav_document', methods=['POST'])
@login_required
def delete_krav_document():
    data = request.get_json()
    subject = data.get('subject')
    doc_type = data.get('doc_type')

    krav_path = f'data/krav_{current_user.id}.json'

    if os.path.exists(krav_path):
        with open(krav_path, 'r', encoding='utf-8') as f:
            krav_data = json.load(f)
    else:
        return {'status': 'error', 'message': 'Krav-data finns inte'}, 400

    if subject in krav_data and doc_type in krav_data[subject]:
        del krav_data[subject][doc_type]
        if not krav_data[subject]:
            del krav_data[subject]
        
        with open(krav_path, 'w', encoding='utf-8') as f:
            json.dump(krav_data, f, ensure_ascii=False, indent=2)
        return {'status': 'success'}
    else:
        return {'status': 'error', 'message': 'Dokument hittades inte'}, 404

@app.route('/subject/<subject_name>')
@login_required
def subject(subject_name):
    quizzes = load_quizzes().get(subject_name, [])
    
    # Läs användarspecifik krav.json
    krav_path = f'data/krav_{current_user.id}.json'
    if os.path.exists(krav_path):
        with open(krav_path, 'r', encoding='utf-8') as f:
            krav_data = json.load(f)
    else:
        krav_data = {}

    documents = krav_data.get(subject_name, {})
    return render_template('subject.html', subject_name=subject_name, quizzes=quizzes, documents=documents)

@app.route('/delete_subject', methods=['POST'])
@login_required
def delete_subject():
    subject_to_delete = request.form.get('subject')
    subjects = load_subjects()
    if subject_to_delete in subjects:
        subjects.remove(subject_to_delete)
        save_subjects(subjects)
    return redirect(url_for('home'))

@app.route('/subject/<subject_name>/quiz/<int:quiz_index>')
@login_required
def start_quiz(subject_name, quiz_index):
    quizzes = load_quizzes().get(subject_name, [])
    if 0 <= quiz_index < len(quizzes):
        quiz = quizzes[quiz_index]
        return render_template('start_quiz.html', subject_name=subject_name, quiz=quiz)
    return "Quiz not found", 404

@app.route('/upload_krav_pdf', methods=['POST'])
@login_required
def upload_krav_pdf():
    subject = request.form['subject']
    doc_type = request.form['type']
    file = request.files.get('file')
    if not file:
        return jsonify(status='error', message='Ingen fil'), 400

    # Användarspecifik mapp för krav-dokument
    folder = os.path.join('static', 'uploads', 'krav', str(current_user.id), subject)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{doc_type}.pdf")
    file.save(path)

    # Extrahera text från PDF
    pdf_path = path
    text = ''
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    # fallback OCR om tomt
    if not text.strip():
        images = convert_from_path(pdf_path)
        for img in images:
            text += pytesseract.image_to_string(img)

    # Uppdatera användarspecifik krav.json
    krav_path = f'data/krav_{current_user.id}.json'
    krav_data = load_json(krav_path, {})
    krav_data.setdefault(subject, {})[doc_type] = {'innehåll': text}
    save_json(krav_data, krav_path)

    return jsonify(status='success')

@app.route('/create-quiz', methods=['GET', 'POST'])
@login_required
def create_quiz():
    subjects = load_subjects()

    if request.method == 'POST':
        # Form inputs
        uploaded_files = request.files.getlist('data1')
        user_title = request.form.get('quiz_title', '').strip()
        subject = request.form.get('subject')
        quiz_type = request.form.get('quiz-drop')
        description = request.form.get('quiz-description', '').strip()
        use_docs = bool(request.form.get('use_documents'))

        # Map quiz_type to number of questions
        type_map = {
            'ten': 10,
            'twenty-five': 25,
            'fifty': 50,
            'extended-response': None,
            'exam': None
        }
        desired_count = type_map.get(quiz_type)

        # Build title
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        quiz_title = user_title or f"{subject} - {quiz_type.replace('-', ' ').title()} - {now}"

        # Handle file uploads and extract content
        saved_files = []
        file_contents = []
        # Användarspecifik upload-mapp
        upload_folder = os.path.join('uploads', str(current_user.id), subject)
        os.makedirs(upload_folder, exist_ok=True)

        for file in uploaded_files:
            if not file or not file.filename:
                continue
            filename = secure_filename(file.filename)
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            saved_files.append(filepath)

            ext = os.path.splitext(filename)[1].lower()
            try:
                if ext == '.pdf':
                    text = ''
                    with fitz.open(filepath) as doc:
                        for page in doc:
                            text += page.get_text()
                    if not text.strip():
                        images = convert_from_path(filepath)
                        for image in images:
                            text += pytesseract.image_to_string(image)
                    file_contents.append(text)
                elif ext in ['.txt', '.doc', '.docx']:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        file_contents.append(f.read())
            except Exception as e:
                print(f"[ERROR] Failed to process '{filename}': {e}")

        combined_text = "\n\n".join(file_contents) if file_contents else ''

        # Append krav documents (användarspecifika)
        if use_docs:
            krav_path = f'data/krav_{current_user.id}.json'
            if os.path.exists(krav_path):
                with open(krav_path, 'r', encoding='utf-8') as f:
                    krav_data = json.load(f)
                subj_docs = krav_data.get(subject, {})
                krav_texts = []
                for d_type, d_info in subj_docs.items():
                    text = d_info.get('innehåll', '').strip()
                    if text:
                        krav_texts.append(f"{d_type.capitalize()}: {text}")
                if krav_texts:
                    combined_text += "\n\n" + "\n\n".join(krav_texts)

        # Build AI prompt
        prompt = f"You're an AI quiz generator – create"
        if desired_count:
            prompt += f" a {desired_count}-question"
        else:
            prompt += " an appropriate"
        prompt += f" {quiz_type.replace('-', ' ')} quiz. Use the following materials to craft questions testing understanding:\n\n"
        prompt += f"Description: {description}\n\n"
        if combined_text:
            prompt += f"Material:\n{combined_text}\n\n"
        prompt += "Format as Q: [Question]\nA: [Answer]"

        # Call AI
        try:
            response = requests.post(
                "https://ai.hackclub.com/chat/completions",
                json={"messages": [{"role": "user", "content": prompt}]},
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            raw = response.json().get("choices", [])[0].get("message", {}).get("content", "")
        except Exception as e:
            raw = ""

        # Parse AI output
        questions = []
        q = None
        for line in raw.splitlines():
            if line.lower().startswith('q:'):
                q = line[2:].strip()
            elif line.lower().startswith('a:') and q:
                a = line[2:].strip()
                questions.append({'question': q, 'answer': a})
                q = None

        if not questions:
            questions = [{'question': '[Error]', 'answer': 'Could not generate questions.'}]

        # Truncate to desired count
        if desired_count and len(questions) > desired_count:
            questions = questions[:desired_count]

        # Save quiz (användarspecifikt)
        quizzes = load_quizzes()
        quizzes.setdefault(subject, []).append({
            'title': quiz_title,
            'type': quiz_type,
            'description': description,
            'files': saved_files,
            'use_documents': use_docs,
            'questions': questions
        })
        save_quizzes(quizzes)

        return redirect(url_for('subject', subject_name=subject))

    # GET - läs användarspecifika events
    events_file = f'events_{current_user.id}.json'
    events = load_json(events_file, [])
    return render_template('create-quiz.html', subjects=subjects, events=events)

@app.route('/subject/<subject_name>/delete_quiz/<int:quiz_index>', methods=['POST'])
@login_required
def delete_quiz(subject_name, quiz_index):
    quizzes = load_quizzes()
    if subject_name in quizzes and 0 <= quiz_index < len(quizzes[subject_name]):
        deleted_quiz = quizzes[subject_name].pop(quiz_index)
        save_quizzes(quizzes)
        flash(f"Deleted quiz: {deleted_quiz.get('title', 'Unknown')}", "success")
    else:
        flash("Quiz or subject not found.", "error")
    return redirect(url_for('subject', subject_name=subject_name))

@app.route('/subject/<subject_name>/flashcards/<int:quiz_index>')
@login_required
def flashcards(subject_name, quiz_index):
    quizzes = load_quizzes().get(subject_name, [])
    if 0 <= quiz_index < len(quizzes):
        quiz = quizzes[quiz_index]
        flashcards = [
            f"{q['question']}|{q['answer']}"
            for q in quiz.get('questions', [])
            if 'question' in q and 'answer' in q and not q['question'].startswith("[Error]")
        ]
        quiz_title = quiz.get('title', 'Untitled Quiz')
        return render_template('flashcards.html', subject_name=subject_name, questions=flashcards, quiz_title=quiz_title)
    return "Flashcards not found", 404




@app.route('/submit_ratings', methods=['POST'])
@login_required
def submit_rating():
    """
    Förbättrad version som korrekt hanterar både originala quiz och daily quiz repetitioner
    med korrekt användarspecifik ratings-hantering
    """
    try:
        payload = request.get_json()
        
        subject = payload.get('subject')
        quiz_title = payload.get('quiz_title') 
        responses = payload.get('responses', [])

        if not (subject and quiz_title and responses):
            return jsonify({'error': 'Missing required data (subject, quiz_title, responses)'}), 400

        # Extrahera rätt subject och topic från quiz_title om det är en daily quiz
        actual_subject = subject
        actual_topic = quiz_title
        
        # Hantera olika format av daily quiz titlar
        if " — " in subject:
            # Format: "subject — topic"
            parts = subject.split(" — ")
            if len(parts) == 2:
                actual_subject = parts[0].strip()
                actual_topic = parts[1].strip()
        elif quiz_title.startswith("Repetition") and " — " in quiz_title:
            # Format: "Repetition YYYY-MM-DD — subject / topic"
            parts = quiz_title.split(" — ")
            if len(parts) == 2:
                subject_topic = parts[1]
                if " / " in subject_topic:
                    subj_parts = subject_topic.split(" / ")
                    if len(subj_parts) == 2:
                        actual_subject = subj_parts[0].strip()
                        actual_topic = subj_parts[1].strip()

        # Import från spaced_repetition.py
        from spaced_repetition import update_rating
        
        updated_count = 0
        failed_count = 0
        
        print(f"[DEBUG] Processing {len(responses)} responses for {actual_subject}/{actual_topic}")
        
        # Uppdatera varje fråga med den nya funktionen
        for resp in responses:
            question = resp.get('question', '').strip()
            rating = resp.get('rating')
            time_taken = resp.get('time')
            
            if not question:
                print(f"[WARNING] Skipping empty question")
                failed_count += 1
                continue
                
            if rating is None:
                print(f"[WARNING] Skipping question without rating: {question[:30]}...")
                failed_count += 1
                continue
            
            try:
                rating_int = int(rating)
                if not (1 <= rating_int <= 4):
                    print(f"[WARNING] Invalid rating {rating_int} for question: {question[:30]}...")
                    failed_count += 1
                    continue
                
                # Konvertera time_taken om det finns
                time_float = None
                if time_taken is not None:
                    try:
                        time_float = float(time_taken)
                    except (ValueError, TypeError):
                        print(f"[WARNING] Invalid time_taken '{time_taken}' for question: {question[:30]}...")
                        time_float = None
                
                # Anropa update_rating funktionen med rätt subject/topic
                success = update_rating(actual_subject, actual_topic, question, rating_int, time_float)
                
                if success:
                    updated_count += 1
                    print(f"[SUCCESS] Updated question: {question[:30]}... (Rating: {rating_int})")
                else:
                    failed_count += 1
                    print(f"[ERROR] Failed to update question: {question[:30]}...")
                        
            except ValueError as e:
                print(f"[ERROR] Could not process rating '{rating}' for question '{question[:30]}...': {e}")
                failed_count += 1
            except Exception as e:
                print(f"[ERROR] Failed to update question '{question[:30]}...': {e}")
                import traceback
                traceback.print_exc()
                failed_count += 1

        # Returnera detaljerat svar
        return jsonify({
            'status': 'success' if updated_count > 0 else 'partial_success' if failed_count < len(responses) else 'error',
            'message': f'Updated {updated_count}/{len(responses)} questions successfully',
            'updated_count': updated_count,
            'failed_count': failed_count,
            'total_responses': len(responses),
            'resolved_subject': actual_subject,
            'resolved_topic': actual_topic
        })
        
    except Exception as e:
        print(f"[ERROR] Submit ratings failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Failed to update ratings: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/api/statistics')
@login_required
def get_statistics_api():
    """API endpoint för att få statistik"""
    try:
        from spaced_repetition import get_statistics
        stats = get_statistics()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': 'Failed to get statistics'}), 500

@app.route('/api/due_questions')
@login_required
def get_due_questions_api():
    """API endpoint för att få alla förfallna frågor"""
    try:
        from spaced_repetition import get_due_questions
        due_questions = get_due_questions()
        return jsonify({
            'count': len(due_questions),
            'questions': due_questions
        })
    except Exception as e:
        return jsonify({'error': 'Failed to get due questions'}), 500


@app.route('/reset_question', methods=['POST'])
@login_required
def reset_question_route():
    if not app.debug:
        return jsonify({'error': 'Only available in debug mode'}), 403
    
    try:
        data = request.get_json()
        subject = data.get('subject')
        quiz_title = data.get('quiz_title') 
        question = data.get('question')
        
        if not all([subject, quiz_title, question]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        from spaced_repetition import reset_question
        reset_question(subject, quiz_title, question)
        
        return jsonify({'status': 'success', 'message': 'Question reset'})
        
    except Exception as e:
        return jsonify({'error': 'Failed to reset question'}), 500

@app.route('/api/events', methods=['GET'])
@login_required
def get_events():
    try:
        events_file = f'events_{current_user.id}.json'
        if os.path.exists(events_file):
            with open(events_file, 'r', encoding='utf-8') as f:
                events = json.load(f)
        else:
            events = []
        return jsonify(events)
    except Exception as e:
        return jsonify([]), 500


@app.route('/api/events', methods=['POST'])
@login_required
def save_event():
    try:
        event_data = request.get_json()
        required_fields = ['date', 'subject', 'testType', 'title']
        for field in required_fields:
            if field not in event_data or not event_data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        events_file = f'events_{current_user.id}.json'
        events = []
        if os.path.exists(events_file):
            with open(events_file, 'r', encoding='utf-8') as f:
                events = json.load(f)

        if 'created' not in event_data:
            event_data['created'] = datetime.now().isoformat()

        events.append(event_data)

        with open(events_file, 'w', encoding='utf-8') as f:
            json.dump(events, f, indent=2, ensure_ascii=False)

        return jsonify({'success': True, 'message': 'Event saved successfully'})

    except Exception as e:
        return jsonify({'error': 'Failed to save event'}), 500


@app.route('/api/events/<int:event_id>', methods=['DELETE'])
@login_required
def delete_event(event_id):
    try:
        events_file = f'events_{current_user.id}.json'
        events = []
        if os.path.exists(events_file):
            with open(events_file, 'r', encoding='utf-8') as f:
                events = json.load(f)

        events = [event for event in events if event.get('id') != event_id]

        with open(events_file, 'w', encoding='utf-8') as f:
            json.dump(events, f, indent=2, ensure_ascii=False)

        return jsonify({'success': True, 'message': 'Event deleted successfully'})

    except Exception as e:
        return jsonify({'error': 'Failed to delete event'}), 500


@app.route("/get_events_for_date")
@login_required
def get_events_for_date():
    date = request.args.get("date")
    if not date:
        return jsonify([])

    try:
        events_file = f'events_{current_user.id}.json'
        if os.path.exists(events_file):
            with open(events_file, 'r', encoding='utf-8') as f:
                events = json.load(f)
        else:
            events = []

        filtered_events = [event for event in events if event.get("date") == date]
        return jsonify(filtered_events)
    except Exception as e:
        return jsonify([]), 500


def group_flashcards_by_review_date(data):
    result = {}
    for subject, topics in data.items():
        for topic, questions in topics.items():
            for question_text, qdata in questions.items():
                next_review = qdata.get('next_review')
                if not next_review:
                    continue
                if next_review not in result:
                    result[next_review] = []
                entry = {
                    "subject": subject,
                    "topic": topic,
                    "question": question_text,
                }
                entry.update(qdata)
                result[next_review].append(entry)
    return result


@app.route('/flashcards_by_date')
@login_required
def flashcards_by_date():
    """
    Returnerar både nya frågor och due-frågor grupperade per next_review-datum.
    Nya frågor (utan metadata) får next_review = idag.
    
    Förbättrad version som korrekt hanterar användarspecifika ratings.
    """
    try:
        # 1) Läs in metadata och alla sparade quizzar (användarspecifikt)
        ratings = load_ratings()       # från spaced_repetition.py
        all_quizzes = load_quizzes()   # från main app (användarspecifik)
        today = datetime.now().date()
        today_str = today.isoformat()

        schedule = {}

        # 2) För varje subject → varje quiz → varje fråga
        for subject, quiz_list in all_quizzes.items():
            for quiz in quiz_list:
                topic = quiz['title']
                questions = quiz.get('questions', [])
                
                # Filtrera bort frågor som börjar med [Error]
                valid_questions = [q for q in questions 
                                 if q.get('question') and 
                                    not q['question'].startswith("[Error]") and
                                    q.get('answer')]
                
                for item in valid_questions:
                    question = item.get('question', '').strip()
                    if not question:
                        continue

                    # 3) Kontrollera om frågan finns i ratings-data
                    question_meta = (ratings
                                   .get(subject, {})
                                   .get(topic, {})
                                   .get(question))

                    if question_meta and 'next_review' in question_meta:
                        # Existerande fråga med metadata
                        try:
                            next_review_str = question_meta['next_review']
                            next_review_date = datetime.strptime(next_review_str, '%Y-%m-%d').date()
                            
                            # Lägg till i schemat
                            key = next_review_date.isoformat()
                            if key not in schedule:
                                schedule[key] = []
                            
                            schedule[key].append({
                                'subject': subject,
                                'topic': topic,
                                'question': question,
                                'is_new': False,
                                'interval': question_meta.get('interval', 0),
                                'repetitions': question_meta.get('repetitions', 0),
                                'ease_factor': question_meta.get('ease_factor', 2.5)
                            })
                            
                        except (ValueError, TypeError) as e:
                            print(f"[WARNING] Invalid date format for question '{question[:30]}...': {e}")
                            # Fallback till idag om datumet är korrupt
                            if today_str not in schedule:
                                schedule[today_str] = []
                            schedule[today_str].append({
                                'subject': subject,
                                'topic': topic,
                                'question': question,
                                'is_new': True,
                                'interval': 0,
                                'repetitions': 0,
                                'ease_factor': 2.5
                            })
                    else:
                        # Ny fråga utan metadata → schemalägg för idag
                        if today_str not in schedule:
                            schedule[today_str] = []
                        
                        schedule[today_str].append({
                            'subject': subject,
                            'topic': topic,
                            'question': question,
                            'is_new': True,
                            'interval': 0,
                            'repetitions': 0,
                            'ease_factor': 2.5
                        })

        # 4) Sortera schema-nycklarna kronologiskt
        sorted_schedule = {}
        for date_key in sorted(schedule.keys()):
            sorted_schedule[date_key] = schedule[date_key]

        print(f"[DEBUG] Flashcards schedule generated for user {current_user.id}: {len(sorted_schedule)} dates")
        
        return jsonify(sorted_schedule)

    except Exception as e:
        print(f"[ERROR] Failed to generate flashcards schedule: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({}), 500


@app.route('/daily_quiz/<date>/<subject>/<path:topic>')
@login_required
def daily_quiz(date, subject, topic):
    """
    Förbättrad version som korrekt hanterar både nya och befintliga frågor
    baserat på användarspecifik ratings-data
    """
    subject = urllib.parse.unquote(subject)
    topic = urllib.parse.unquote(topic)
    
    try:
        # Hämta alla frågor från den ursprungliga quizen
        all_quizzes = load_quizzes().get(subject, [])
        quiz = next((z for z in all_quizzes if z['title'] == topic), None)
        
        if not quiz:
            return f"Quiz '{topic}' not found for subject '{subject}'", 404

        # Hämta spaced repetition data (användarspecifik)
        ratings_data = load_ratings()  # från spaced_repetition.py
        questions_meta = ratings_data.get(subject, {}).get(topic, {})
        
        cards = []
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
        target_date_str = target_date.isoformat()
        
        # Gå igenom alla frågor i quizet
        for item in quiz['questions']:
            question = item.get('question', '').strip()
            answer = item.get('answer', '').strip()
            
            # Skippa error-frågor och tomma frågor
            if (question.startswith("[Error]") or 
                not question or 
                not answer):
                continue
            
            should_include = False
            
            if question in questions_meta:
                # Frågan har metadata - kontrollera om den ska repeteras detta datum
                next_review = questions_meta[question].get('next_review')
                
                if next_review:
                    # Inkludera om schemalagd för target_date eller tidigare (försenade)
                    if next_review <= target_date_str:
                        should_include = True
                else:
                    # Metadata finns men inget next_review - behandla som ny
                    if target_date_str == datetime.now().strftime("%Y-%m-%d"):
                        should_include = True
            else:
                # Ny fråga som aldrig testats - inkludera bara för dagens datum
                if target_date_str == datetime.now().strftime("%Y-%m-%d"):
                    should_include = True
            
            if should_include:
                cards.append(f"{question}|{answer}")

        # Kontrollera om det finns kort att visa
        if not cards:
            message = f"No cards scheduled for {subject} / {topic} on {date}"
            if target_date > datetime.now().date():
                message += " (future date - cards only show on or after their review date)"
            
            return render_template('flashcards.html',
                                 subject_name=subject,
                                 quiz_title=f"No repetitions for {date}",
                                 questions=[],
                                 message=message)

        print(f"[DEBUG] Daily quiz for {date}: {len(cards)} cards for {subject}/{topic}")

        # Använd original topic som quiz_title för korrekt spårning
        return render_template('flashcards.html',
                             subject_name=subject,      # Skicka bara subject
                             quiz_title=topic,          # Skicka original topic som quiz_title
                             questions=cards,
                             is_daily_quiz=True,        # Markera att det är en daily quiz
                             quiz_date=date)            # Skicka med datumet för display
                             
    except Exception as e:
        print(f"[ERROR] Daily quiz error: {e}")
        import traceback
        traceback.print_exc()
        return f"Error loading quiz: {e}", 500




def update_flashcard(old, rating, time_taken):
    ef = old.get('ease_factor', 2.5)
    reps = old.get('repetitions', 0)
    interval = old.get('interval', 0)

    q = int(rating)

    # Update ease factor (min 1.3)
    ef = max(1.3, ef + (0.1 - (4 - q) * (0.08 + (4 - q) * 0.02)))

    if q < 3:
        reps = 0
        interval = 1
    else:
        reps += 1
        if reps == 1:
            interval = 1
        elif reps == 2:
            interval = 6
        else:
            interval = int(round(interval * ef))

    # Bonus för snabbt perfekt svar
    if q == 4 and time_taken is not None and time_taken < 5:
        interval = max(interval, int(round(interval * ef * 1.2)))

    next_review = (datetime.now() + timedelta(days=interval)).strftime("%Y-%m-%d")

    return {
        'rating': q,
        'time': time_taken,
        'ease_factor': round(ef, 2),
        'repetitions': reps,
        'interval': interval,
        'next_review': next_review,
        'timestamp': datetime.now().isoformat()
    }


if __name__ == '__main__':
    app.run(debug=True)
