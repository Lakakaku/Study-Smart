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
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from sqlalchemy import JSON, Text

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['SECRET_KEY'] = 'din-hemliga-nyckel'  # byt till något säkert
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'data')

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Du måste vara inloggad för att komma åt den här sidan.'
login_manager.login_message_category = 'info'

# -------------------- Database Models --------------------

# -------------------- Database Models --------------------

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(60), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    subjects = db.relationship('Subject', backref='owner', lazy=True, cascade='all, delete-orphan')
    quizzes = db.relationship('Quiz', backref='owner', lazy=True, cascade='all, delete-orphan')
    flashcards = db.relationship('Flashcard', backref='owner', lazy=True, cascade='all, delete-orphan')
    events = db.relationship('Event', backref='owner', lazy=True, cascade='all, delete-orphan')
    krav_documents = db.relationship('KravDocument', backref='owner', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"User('{self.username}')"

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships - Korrigerade foreign keys
    quizzes = db.relationship('Quiz', backref='subject_ref', lazy=True, cascade='all, delete-orphan',
                             foreign_keys='Quiz.subject_id')
    flashcards = db.relationship('Flashcard', backref='subject_ref', lazy=True, cascade='all, delete-orphan',
                                foreign_keys='Flashcard.subject_id')
    krav_documents = db.relationship('KravDocument', backref='subject_ref', lazy=True, cascade='all, delete-orphan',
                                    foreign_keys='KravDocument.subject_id')

    def __repr__(self):
        return f"Subject('{self.name}')"

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    quiz_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    subject_name = db.Column(db.String(100), nullable=False)  # Behåll för bakåtkompatibilitet
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=True)  # Ny foreign key
    use_documents = db.Column(db.Boolean, default=False)
    files = db.Column(JSON)  # Lista av filsökvägar
    questions = db.Column(JSON)  # Lista av frågor och svar
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Quiz('{self.title}')"

class Flashcard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    subject = db.Column(db.String(100), nullable=False)  # Behåll för bakåtkompatibilitet
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=True)  # Ny foreign key
    topic = db.Column(db.String(100), nullable=False)
    
    # Spaced repetition fields
    ease_factor = db.Column(db.Float, default=2.5)
    interval = db.Column(db.Integer, default=0)
    repetitions = db.Column(db.Integer, default=0)
    next_review = db.Column(db.Date, nullable=True)
    rating = db.Column(db.Integer, nullable=True)
    time_taken = db.Column(db.Float, nullable=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"Flashcard('{self.question[:50]}...')"

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD format
    subject = db.Column(db.String(100), nullable=False)
    test_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date,
            'subject': self.subject,
            'testType': self.test_type,
            'title': self.title,
            'created': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"Event('{self.title}', '{self.date}')"

class KravDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_name = db.Column(db.String(100), nullable=False)  # Behåll för bakåtkompatibilitet
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=True)  # Ny foreign key
    doc_type = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"KravDocument('{self.subject_name}', '{self.doc_type}')"



# Lägg till denna funktion efter database models men före user_loader
def init_database():
    """Initiera databas och hantera migrationer"""
    with app.app_context():
        # Skapa tabeller om de inte finns
        db.create_all()
        
        # Lista över alla kolumner som behövs för varje tabell
        required_columns = {
            'quiz': [
                ('subject_name', 'VARCHAR(100)'),
                ('subject_id', 'INTEGER'),
                ('use_documents', 'BOOLEAN'),
                ('files', 'JSON'),
                ('questions', 'JSON')
            ],
            'flashcard': [
                ('subject', 'VARCHAR(100)'),
                ('subject_id', 'INTEGER'),
                ('ease_factor', 'FLOAT'),
                ('interval', 'INTEGER'),
                ('repetitions', 'INTEGER'),
                ('next_review', 'DATE'),
                ('rating', 'INTEGER'),
                ('time_taken', 'FLOAT'),
                ('updated_at', 'DATETIME')
            ],
            'krav_document': [
                ('subject_name', 'VARCHAR(100)'),
                ('subject_id', 'INTEGER')
            ]
        }
        
        # Kontrollera och lägg till saknade kolumner
        for table_name, columns in required_columns.items():
            for column_name, column_type in columns:
                try:
                    # Testa om kolumnen finns genom att köra en SELECT
                    db.session.execute(db.text(f"SELECT {column_name} FROM {table_name} LIMIT 1"))
                except Exception:
                    # Kolumnen finns inte, lägg till den
                    try:
                        # Hantera olika datatyper
                        if column_type == 'BOOLEAN':
                            default_value = ' DEFAULT 0'
                        elif column_type == 'FLOAT':
                            default_value = ' DEFAULT 2.5' if column_name == 'ease_factor' else ' DEFAULT 0.0'
                        elif column_type == 'INTEGER':
                            default_value = ' DEFAULT 0'
                        elif column_type == 'DATETIME':
                            default_value = " DEFAULT CURRENT_TIMESTAMP"
                        else:
                            default_value = ''
                        
                        alter_query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}{default_value}"
                        db.session.execute(db.text(alter_query))
                        print(f"Added column {column_name} to {table_name}")
                    except Exception as e:
                        print(f"Error adding column {column_name} to {table_name}: {e}")
        
        try:
            db.session.commit()
            print("Database schema updated successfully")
        except Exception as e:
            print(f"Error committing database changes: {e}")
            db.session.rollback()


# Användare loader för flask-login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Skapa tabeller om de inte finns
init_database()


# -------------------- Helper Functions --------------------

def get_user_subjects():
    """Hämta alla ämnen för nuvarande användare"""
    if not current_user.is_authenticated:
        return []
    subjects = Subject.query.filter_by(user_id=current_user.id).all()
    return [subject.name for subject in subjects]

def add_user_subject(subject_name):
    """Lägg till nytt ämne för nuvarande användare"""
    if not current_user.is_authenticated:
        return False
    
    # Kontrollera om ämnet redan finns
    existing = Subject.query.filter_by(user_id=current_user.id, name=subject_name).first()
    if existing:
        return False
    
    subject = Subject(name=subject_name, user_id=current_user.id)
    db.session.add(subject)
    db.session.commit()
    return True

def get_user_quizzes(subject_name=None):
    """Hämta quiz för nuvarande användare, eventuellt filtrerat på ämne"""
    if not current_user.is_authenticated:
        return {}
    
    query = Quiz.query.filter_by(user_id=current_user.id)
    if subject_name:
        query = query.filter_by(subject_name=subject_name)
    
    quizzes = query.all()
    
    if subject_name:
        # Returnera lista för specifikt ämne
        return [quiz_to_dict(quiz) for quiz in quizzes]
    else:
        # Returnera grupperat per ämne
        result = {}
        for quiz in quizzes:
            if quiz.subject_name not in result:
                result[quiz.subject_name] = []
            result[quiz.subject_name].append(quiz_to_dict(quiz))
        return result

def quiz_to_dict(quiz):
    """Konvertera Quiz-objekt till dictionary"""
    return {
        'title': quiz.title,
        'type': quiz.quiz_type,
        'description': quiz.description,
        'files': quiz.files or [],
        'use_documents': quiz.use_documents,
        'questions': quiz.questions or []
    }

def add_user_quiz(subject_name, quiz_data):
    """Lägg till nytt quiz för nuvarande användare"""
    if not current_user.is_authenticated:
        return False
    
    # Hitta Subject-objektet
    subject_obj = Subject.query.filter_by(user_id=current_user.id, name=subject_name).first()
    
    quiz = Quiz(
        title=quiz_data['title'],
        quiz_type=quiz_data['type'],
        description=quiz_data.get('description', ''),
        subject_name=subject_name,  # Behåll för bakåtkompatibilitet
        subject_id=subject_obj.id if subject_obj else None,  # Ny foreign key
        use_documents=quiz_data.get('use_documents', False),
        files=quiz_data.get('files', []),
        questions=quiz_data.get('questions', []),
        user_id=current_user.id
    )
    db.session.add(quiz)
    db.session.commit()
    return True


def get_user_krav_documents(subject_name=None):
    """Hämta krav-dokument för nuvarande användare"""
    if not current_user.is_authenticated:
        return {}
    
    query = KravDocument.query.filter_by(user_id=current_user.id)
    if subject_name:
        query = query.filter_by(subject_name=subject_name)
    
    documents = query.all()
    
    if subject_name:
        # Returnera dictionary för specifikt ämne
        result = {}
        for doc in documents:
            result[doc.doc_type] = {'innehåll': doc.content}
        return result
    else:
        # Returnera grupperat per ämne
        result = {}
        for doc in documents:
            if doc.subject_name not in result:
                result[doc.subject_name] = {}
            result[doc.subject_name][doc.doc_type] = {'innehåll': doc.content}
        return result

def save_krav_document(subject_name, doc_type, content):
    """Spara eller uppdatera krav-dokument"""
    if not current_user.is_authenticated:
        return False
    
    # Hitta Subject-objektet
    subject_obj = Subject.query.filter_by(user_id=current_user.id, name=subject_name).first()
    
    # Leta efter befintligt dokument
    existing = KravDocument.query.filter_by(
        user_id=current_user.id,
        subject_name=subject_name,
        doc_type=doc_type
    ).first()
    
    if existing:
        existing.content = content
        existing.subject_id = subject_obj.id if subject_obj else None  # Uppdatera foreign key
    else:
        doc = KravDocument(
            subject_name=subject_name,
            subject_id=subject_obj.id if subject_obj else None,  # Ny foreign key
            doc_type=doc_type,
            content=content,
            user_id=current_user.id
        )
        db.session.add(doc)
    
    db.session.commit()
    return True

def delete_krav_document(subject_name, doc_type):
    """Ta bort krav-dokument"""
    if not current_user.is_authenticated:
        return False
    
    doc = KravDocument.query.filter_by(
        user_id=current_user.id,
        subject_name=subject_name,
        doc_type=doc_type
    ).first()
    
    if doc:
        db.session.delete(doc)
        db.session.commit()
        return True
    return False

# -------------------- Spaced Repetition Functions --------------------

def get_flashcard_data(subject, topic, question):
    """Hämta flashcard-data för en specifik fråga"""
    if not current_user.is_authenticated:
        return None
    
    return Flashcard.query.filter_by(
        user_id=current_user.id,
        subject=subject,
        topic=topic,
        question=question
    ).first()

def update_flashcard_rating(subject, topic, question, rating, time_taken):
    """Uppdatera flashcard-rating med spaced repetition algoritm"""
    if not current_user.is_authenticated:
        return False
    
    # Hitta Subject-objektet
    subject_obj = Subject.query.filter_by(user_id=current_user.id, name=subject).first()
    
    # Hitta eller skapa flashcard
    flashcard = Flashcard.query.filter_by(
        user_id=current_user.id,
        subject=subject,
        topic=topic,
        question=question
    ).first()
    
    if not flashcard:
        # Skapa ny flashcard
        flashcard = Flashcard(
            question=question,
            answer="",  # Vi har inte svaret här, men det behövs för modellen
            subject=subject,
            subject_id=subject_obj.id if subject_obj else None,  # Ny foreign key
            topic=topic,
            user_id=current_user.id
        )
        db.session.add(flashcard)
    else:
        # Uppdatera foreign key om den saknas
        if not flashcard.subject_id and subject_obj:
            flashcard.subject_id = subject_obj.id
    
    # Använd spaced repetition algoritm
    ef = flashcard.ease_factor
    reps = flashcard.repetitions
    prev_interval = flashcard.interval
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

    next_rev = datetime.now().date() + timedelta(days=interval)

    # Uppdatera flashcard
    flashcard.ease_factor = round(ef, 2)
    flashcard.repetitions = reps
    flashcard.interval = interval
    flashcard.next_review = next_rev
    flashcard.rating = q
    flashcard.time_taken = time_taken
    flashcard.updated_at = datetime.utcnow()
    
    db.session.commit()
    return True

def get_due_flashcards():
    """Hämta alla förfallna flashcards för nuvarande användare"""
    if not current_user.is_authenticated:
        return []
    
    today = datetime.now().date()
    flashcards = Flashcard.query.filter(
        Flashcard.user_id == current_user.id,
        Flashcard.next_review <= today
    ).all()
    
    return flashcards

def get_flashcard_statistics():
    """Hämta statistik över flashcards för nuvarande användare"""
    if not current_user.is_authenticated:
        return {}
    
    today = datetime.now().date()
    
    total = Flashcard.query.filter_by(user_id=current_user.id).count()
    due = Flashcard.query.filter(
        Flashcard.user_id == current_user.id,
        Flashcard.next_review <= today
    ).count()
    
    return {
        'total_flashcards': total,
        'due_today': due,
        'reviewed_today': 0  # Skulle behöva spåra detta separat
    }

# -------------------- Auth Routes --------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Omdirigera inloggade användare
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
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
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f'Välkommen {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
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
    subjects = get_user_subjects()
    all_quizzes = get_user_quizzes()
    total_quizzes = sum(len(quizzes) for quizzes in all_quizzes.values())
    
    user_stats = {
        'total_subjects': len(subjects),
        'total_quizzes': total_quizzes,
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
                .home-link { background: #28a745; }
                .home-link:hover { background: #1e7e34; }
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
                <a href="{{ url_for('home') }}" class="home-link">Tillbaka till Startsida</a>
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
    """Logga ut användaren"""
    logout_user()
    flash('Du har loggats ut.', 'info')
    return redirect(url_for('login'))

# -------------------- Main Routes --------------------

@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
    subjects = get_user_subjects()
    if request.method == 'POST':
        sub = request.form['subject'].strip()
        if sub and sub not in subjects:
            add_user_subject(sub)
        return redirect(url_for('home'))
    return render_template('index.html', subjects=subjects)

@app.route('/delete_krav_document', methods=['POST'])
@login_required
def delete_krav_document_route():
    data = request.get_json()
    subject = data.get('subject')
    doc_type = data.get('doc_type')

    if delete_krav_document(subject, doc_type):
        return {'status': 'success'}
    else:
        return {'status': 'error', 'message': 'Dokument hittades inte'}, 404

@app.route('/subject/<subject_name>')
@login_required
def subject(subject_name):
    quizzes = get_user_quizzes(subject_name)
    documents = get_user_krav_documents(subject_name)
    return render_template('subject.html', subject_name=subject_name, quizzes=quizzes, documents=documents)

@app.route('/delete_subject', methods=['POST'])
@login_required
def delete_subject():
    subject_to_delete = request.form.get('subject')
    if subject_to_delete:
        # Ta bort ämnet från databasen
        subject_obj = Subject.query.filter_by(user_id=current_user.id, name=subject_to_delete).first()
        if subject_obj:
            db.session.delete(subject_obj)
            db.session.commit()
    return redirect(url_for('home'))

@app.route('/subject/<subject_name>/quiz/<int:quiz_index>')
@login_required
def start_quiz(subject_name, quiz_index):
    quizzes = get_user_quizzes(subject_name)
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

    # Spara till databas
    save_krav_document(subject, doc_type, text)

    return jsonify(status='success')

@app.route('/create-quiz', methods=['GET', 'POST'])
@login_required
def create_quiz():
    subjects = get_user_subjects()

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
        desired_count = type_map
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
        upload_folder = os.path.join('static', 'uploads', str(current_user.id), subject)
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

        # Append krav documents
        if use_docs:
            krav_docs = get_user_krav_documents(subject)
            krav_texts = []
            for d_type, d_info in krav_docs.items():
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

        # Save quiz
        quiz_data = {
            'title': quiz_title,
            'type': quiz_type,
            'description': description,
            'files': saved_files,
            'use_documents': use_docs,
            'questions': questions
        }
        
        add_user_quiz(subject, quiz_data)
        return redirect(url_for('subject', subject_name=subject))

    # GET - läs events
    events = Event.query.filter_by(user_id=current_user.id).all()
    events_data = [event.to_dict() for event in events]
    return render_template('create-quiz.html', subjects=subjects, events=events_data)

@app.route('/subject/<subject_name>/delete_quiz/<int:quiz_index>', methods=['POST'])
@login_required
def delete_quiz(subject_name, quiz_index):
    quizzes = get_user_quizzes(subject_name)
    if 0 <= quiz_index < len(quizzes):
        # Hitta quiz i databasen
        quiz_to_delete = Quiz.query.filter_by(
            user_id=current_user.id,
            subject_name=subject_name
        ).offset(quiz_index).first()
        
        if quiz_to_delete:
            db.session.delete(quiz_to_delete)
            db.session.commit()
            flash(f"Deleted quiz: {quiz_to_delete.title}", "success")
        else:
            flash("Quiz not found.", "error")
    else:
        flash("Invalid quiz index.", "error")
    return redirect(url_for('subject', subject_name=subject_name))

@app.route('/subject/<subject_name>/flashcards/<int:quiz_index>')
@login_required
def flashcards(subject_name, quiz_index):
    quizzes = get_user_quizzes(subject_name)
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
        
        updated_count = 0
        failed_count = 0
        
        print(f"[DEBUG] Processing {len(responses)} responses for {actual_subject}/{actual_topic}")
        
        # Uppdatera varje fråga med spaced repetition
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
                
                # Anropa update_flashcard_rating funktionen
                success = update_flashcard_rating(actual_subject, actual_topic, question, rating_int, time_float)
                
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
        stats = get_flashcard_statistics()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': 'Failed to get statistics'}), 500

@app.route('/api/due_questions')
@login_required
def get_due_questions_api():
    """API endpoint för att få alla förfallna frågor"""
    try:
        due_questions = get_due_flashcards()
        questions_data = []
        for flashcard in due_questions:
            questions_data.append({
                'subject': flashcard.subject,
                'topic': flashcard.topic,
                'question': flashcard.question,
                'next_review': flashcard.next_review.isoformat() if flashcard.next_review else None
            })
        return jsonify({
            'count': len(questions_data),
            'questions': questions_data
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
        
        # Hitta och återställ flashcard
        flashcard = get_flashcard_data(subject, quiz_title, question)
        if flashcard:
            flashcard.ease_factor = 2.5
            flashcard.interval = 0
            flashcard.repetitions = 0
            flashcard.next_review = datetime.now().date()
            flashcard.rating = None
            flashcard.time_taken = None
            db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Question reset'})
        
    except Exception as e:
        return jsonify({'error': 'Failed to reset question'}), 500

@app.route('/api/events', methods=['GET'])
@login_required
def get_events():
    try:
        events = Event.query.filter_by(user_id=current_user.id).all()
        events_data = [event.to_dict() for event in events]
        return jsonify(events_data)
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

        event = Event(
            date=event_data['date'],
            subject=event_data['subject'],
            test_type=event_data['testType'],
            title=event_data['title'],
            user_id=current_user.id
        )
        
        db.session.add(event)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Event saved successfully'})

    except Exception as e:
        print(f"[ERROR] Failed to save event: {e}")
        return jsonify({'error': 'Failed to save event'}), 500

@app.route('/api/events/<int:event_id>', methods=['DELETE'])
@login_required
def delete_event(event_id):
    try:
        event = Event.query.filter_by(id=event_id, user_id=current_user.id).first()
        if event:
            db.session.delete(event)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Event deleted successfully'})
        else:
            return jsonify({'error': 'Event not found'}), 404

    except Exception as e:
        print(f"[ERROR] Failed to delete event: {e}")
        return jsonify({'error': 'Failed to delete event'}), 500

@app.route("/get_events_for_date")
@login_required
def get_events_for_date():
    date = request.args.get("date")
    if not date:
        return jsonify([])

    try:
        events = Event.query.filter_by(user_id=current_user.id, date=date).all()
        events_data = [event.to_dict() for event in events]
        return jsonify(events_data)
    except Exception as e:
        return jsonify([]), 500

@app.route('/flashcards_by_date')
@login_required
def flashcards_by_date():
    """
    Returnerar både nya frågor och due-frågor grupperade per next_review-datum.
    Nya frågor (utan metadata) får next_review = idag.
    """
    try:
        all_quizzes = get_user_quizzes()
        today = datetime.now().date()
        today_str = today.isoformat()

        schedule = {}

        # För varje subject → varje quiz → varje fråga
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

                    # Kontrollera om frågan finns i flashcard-data
                    flashcard = get_flashcard_data(subject, topic, question)

                    if flashcard and flashcard.next_review:
                        # Existerande fråga med metadata
                        next_review_date = flashcard.next_review
                        key = next_review_date.isoformat()
                        
                        if key not in schedule:
                            schedule[key] = []
                        
                        schedule[key].append({
                            'subject': subject,
                            'topic': topic,
                            'question': question,
                            'is_new': False,
                            'interval': flashcard.interval,
                            'repetitions': flashcard.repetitions,
                            'ease_factor': flashcard.ease_factor
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

        # Sortera schema-nycklarna kronologiskt
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
    baserat på användarspecifik flashcard-data
    """
    subject = urllib.parse.unquote(subject)
    topic = urllib.parse.unquote(topic)
    
    try:
        # Hämta alla frågor från den ursprungliga quizen
        all_quizzes = get_user_quizzes().get(subject, [])
        quiz = next((z for z in all_quizzes if z['title'] == topic), None)
        
        if not quiz:
            return f"Quiz '{topic}' not found for subject '{subject}'", 404

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
            
            # Kontrollera flashcard-data
            flashcard = get_flashcard_data(subject, topic, question)
            
            if flashcard and flashcard.next_review:
                # Frågan har metadata - kontrollera om den ska repeteras detta datum
                if flashcard.next_review <= target_date:
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

if __name__ == '__main__':
    app.run(debug=True)
