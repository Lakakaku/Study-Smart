import json
from flask import Flask, render_template, request, redirect, url_for, flash, render_template_string, jsonify, send_file, abort
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import requests
import fitz  # PyMuPDF
import pytesseract
import threading
from pydub import AudioSegment  # IMPORTERA AudioSegment

from threading import Thread



import base64
from moviepy import VideoFileClip
import speech_recognition as sr
import io
import wave



import urllib.parse
from pdf2image import convert_from_path
import os
import json.decoder
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from sqlalchemy import JSON, Text
from extensions import db
import string
import secrets
import uuid
import mimetypes
basedir = os.path.abspath(os.path.dirname(__file__))


app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['SECRET_KEY'] = 'din-hemliga-nyckel'  # byt till något säkert
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'site.db')

DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'data')

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Du måste vara inloggad för att komma åt den här sidan.'
login_manager.login_message_category = 'info'

# -------------------- Database Models --------------------

# -------------------- Database Models --------------------


import secrets
import string


# Lägg till dessa routes i din Flask app
class Lesson(db.Model):
    __tablename__ = 'lessons'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(100))
    duration = db.Column(db.Integer)
    lesson_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    view_count = db.Column(db.Integer, default=0)
    transcription = db.Column(db.Text)  # NY: För transkriberat innehåll
    transcription_status = db.Column(db.String(50), default='pending')  # NY: pending, processing, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    


    # Relationships
    subject = db.relationship('Subject', backref='lessons')
    creator = db.relationship('User', backref='created_lessons')
    
    def __repr__(self):
        return f"Lesson('{self.title}', date='{self.lesson_date}', subject_id={self.subject_id})"
    
    def get_file_extension(self):
        """Hämta filens extension"""
        return self.filename.split('.')[-1].lower() if '.' in self.filename else ''
    
    def get_display_size(self):
        """Formatera filstorlek för visning"""
        if not self.file_size:
            return "Okänd storlek"
        
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def get_duration_display(self):
        """Formatera duration för visning"""
        if not self.duration:
            return "Okänd längd"
        
        minutes = self.duration // 60
        seconds = self.duration % 60
        
        if minutes >= 60:
            hours = minutes // 60
            minutes = minutes % 60
            return f"{hours}h {minutes}m {seconds}s"
        else:
            return f"{minutes}m {seconds}s"
    
    def is_accessible_by_user(self, user_id):
        """Kontrollera om en användare kan komma åt lektionen"""
        # Skaparen kan alltid komma åt
        if self.user_id == user_id:
            return True
        
        # Kontrollera om användaren har tillgång till ämnet
        user = User.query.get(user_id)
        if user and user.is_member_of_subject(self.subject_id):
            return True
        
        return False
    
    # Resten av modellen som innan...
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'subject_id': self.subject_id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'filename': self.filename,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'duration': self.duration,
            'lesson_date': self.lesson_date.isoformat() if self.lesson_date else None,
            'is_active': self.is_active,
            'view_count': self.view_count,
            'transcription': self.transcription,
            'transcription_status': self.transcription_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'extension': self.get_file_extension(),
            'display_size': self.get_display_size(),
            'duration_display': self.get_duration_display()
        }


# Lägg till denna model i din models.py
class SharedFile(db.Model):
    __tablename__ = 'shared_files'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Uppladdaren
    filename = db.Column(db.String(255), nullable=False)  # Ursprungligt filnamn
    file_path = db.Column(db.String(500), nullable=False)  # Sökväg på servern
    file_size = db.Column(db.Integer)  # Storlek i bytes
    file_type = db.Column(db.String(100))  # MIME-typ
    description = db.Column(db.Text)  # Valfri beskrivning
    is_active = db.Column(db.Boolean, default=True)  # För att "ta bort" filer
    download_count = db.Column(db.Integer, default=0)  # Statistik
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - ta bort backref eftersom de redan hanteras från Subject och User modellerna
    # subject = db.relationship('Subject') - hanteras från Subject-sidan
    # uploader = db.relationship('User') - hanteras från User-sidan
    
    def __repr__(self):
        # Hämta subject för att undvika lazy loading issues
        subject_obj = Subject.query.get(self.subject_id)
        return f"SharedFile('{self.filename}', subject='{subject_obj.name if subject_obj else 'Unknown'}')"
    
    def get_file_extension(self):
        """Hämta filens extension"""
        return self.filename.split('.')[-1].lower() if '.' in self.filename else ''
    
    def get_display_size(self):
        """Formatera filstorlek för visning"""
        if not self.file_size:
            return "Okänd storlek"
        
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def is_downloadable_by_user(self, user_id):
        """Kontrollera om en användare kan ladda ner filen"""
        # Ägaren kan alltid ladda ner
        if self.user_id == user_id:
            return True
        
        # Kontrollera om användaren har tillgång till ämnet
        user = User.query.get(user_id)
        if user and user.is_member_of_subject(self.subject_id):
            return True
        
        return False
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'subject_id': self.subject_id,
            'user_id': self.user_id,
            'filename': self.filename,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'description': self.description,
            'is_active': self.is_active,
            'download_count': self.download_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'extension': self.get_file_extension(),
            'display_size': self.get_display_size()
        }


# Uppdatera Subject model
# Uppdatera Subject model
class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Kolumner som kommer att läggas till via migration
    share_code = db.Column(db.String(8), unique=True, nullable=True)
    is_shared = db.Column(db.Boolean, default=False)
    
    # Relationships
    quizzes = db.relationship('Quiz', backref='subject_ref', lazy=True, cascade='all, delete-orphan',
                             foreign_keys='Quiz.subject_id')
    flashcards = db.relationship('Flashcard', backref='subject_ref', lazy=True, cascade='all, delete-orphan',
                                foreign_keys='Flashcard.subject_id')
    members = db.relationship('SubjectMember', backref='subject', lazy=True, cascade='all, delete-orphan')
    
    # Lägg till relationship för krav_documents och shared_files
    krav_documents = db.relationship('KravDocument', backref='subject', lazy=True, cascade='all, delete-orphan')
    shared_files = db.relationship('SharedFile', backref='subject', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"Subject('{self.name}', code='{self.share_code}')"

    def generate_share_code(self):
        """Generera en unik 8-karaktärs kod"""
        import secrets
        import string
        
        while True:
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            existing = Subject.query.filter_by(share_code=code).first()
            if not existing:
                return code

    @classmethod
    def create_with_code(cls, name, user_id, is_shared=False):
        """Skapa ett nytt subject med automatisk share_code"""
        subject = cls(
            name=name,
            user_id=user_id,
            is_shared=is_shared
        )
        subject.share_code = subject.generate_share_code()
        return subject


# Ny model för att hålla reda på vilka användare som är medlemmar i vilket subject
class SubjectMember(db.Model):
    __tablename__ = 'subject_members'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    role = db.Column(db.String(20), default='member')  # 'admin' eller 'member'
    
    # Unique constraint för att förhindra duplicerade medlemskap
    __table_args__ = (db.UniqueConstraint('subject_id', 'user_id', name='unique_subject_member'),)
    
    def __repr__(self):
        return f"SubjectMember(subject_id={self.subject_id}, user_id={self.user_id}, role='{self.role}')"
# Uppdatera User model för att inkludera subject memberships



# Uppdatera User model för att inkludera subject memberships
# Uppdatera User model för att inkludera subject memberships
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
    
    # Ny relationship för subject memberships
    subject_memberships = db.relationship('SubjectMember', backref='user', lazy=True, cascade='all, delete-orphan')
    
    # Relationship för krav documents och shared files
    krav_documents = db.relationship('KravDocument', backref='user', lazy=True, cascade='all, delete-orphan')
    shared_files = db.relationship('SharedFile', backref='uploader', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"User('{self.username}')"
    
    def get_all_subjects(self):
        """Hämta alla subjects som användaren har tillgång till (äger eller är medlem i)"""
        owned_subjects = self.subjects
        
        # Hämta subjects där användaren är medlem
        member_subjects = db.session.query(Subject).join(SubjectMember).filter(
            SubjectMember.user_id == self.id,
            Subject.user_id != self.id  # Exkludera subjects som användaren redan äger
        ).all()
        
        return owned_subjects + member_subjects
    
    def is_member_of_subject(self, subject_id):
        """Kontrollera om användaren är medlem eller ägare av ett subject"""
        # Kontrollera om användaren äger subject
        if Subject.query.filter_by(id=subject_id, user_id=self.id).first():
            return True
        
        # Kontrollera om användaren är medlem
        return SubjectMember.query.filter_by(subject_id=subject_id, user_id=self.id).first() is not None
    
    def get_role_in_subject(self, subject_id):
        """Hämta användarens roll i ett subject"""
        # Kontrollera om användaren äger subject
        if Subject.query.filter_by(id=subject_id, user_id=self.id).first():
            return 'owner'
        
        # Kontrollera medlemskap
        membership = SubjectMember.query.filter_by(subject_id=subject_id, user_id=self.id).first()
        return membership.role if membership else None
    
    def get_owned_subjects(self):
        """Hämta ämnen som användaren äger"""
        return Subject.query.filter_by(user_id=self.id).all()
    
    def get_shared_subjects(self):
        """Hämta ämnen som användaren är medlem i (men inte äger)"""
        return db.session.query(Subject).join(SubjectMember).filter(
            SubjectMember.user_id == self.id
        ).all()

def check_quiz_schema():
    """Kontrollera och uppdatera quiz-tabellens schema"""
    try:
        # Kontrollera om is_personal kolumnen finns
        db.session.execute(db.text("SELECT is_personal FROM quiz LIMIT 1"))
        print("Quiz table already has is_personal column")
    except Exception:
        # Kolumnen finns inte, lägg till den
        try:
            print("Adding is_personal column to quiz table...")
            db.session.execute(db.text("ALTER TABLE quiz ADD COLUMN is_personal BOOLEAN DEFAULT 1"))
            db.session.commit()
            print("✓ Added is_personal column to quiz table")
        except Exception as e:
            print(f"Error adding is_personal column: {e}")
            db.session.rollback()
    
    # Uppdatera befintliga quizzes som saknar is_personal värde
    try:
        quizzes_to_update = Quiz.query.filter_by(is_personal=None).all()
        for quiz in quizzes_to_update:
            # Sätt is_personal baserat på skaparens roll
            if quiz.subject_id:
                user_role = User.query.get(quiz.user_id).get_role_in_subject(quiz.subject_id)
                quiz.is_personal = user_role not in ['owner', 'admin']
            else:
                quiz.is_personal = True  # Default till personal
        
        if quizzes_to_update:
            db.session.commit()
            print(f"✓ Updated {len(quizzes_to_update)} quizzes with is_personal values")
            
    except Exception as e:
        print(f"Error updating existing quizzes: {e}")
        db.session.rollback()



# Update your init_database function to include the new table
def init_database():
    """Initiera databas och hantera migrationer"""
    with app.app_context():
        # Skapa tabeller om de inte finns
        db.create_all()
        
        # Lista över alla kolumner som behövs för varje tabell
        required_columns = {
            'subject': [
                ('share_code', 'VARCHAR(8)'),
                ('is_shared', 'BOOLEAN')
            ],
            'quiz': [
                ('subject_name', 'VARCHAR(100)'),
                ('subject_id', 'INTEGER'),
                ('use_documents', 'BOOLEAN'),
                ('files', 'JSON'),
                ('questions', 'JSON'),
                ('is_personal', 'BOOLEAN')
            ],
            'lessons': [
                ('subject_id', 'INTEGER'),
                ('user_id', 'INTEGER'),
                ('title', 'VARCHAR(200)'),
                ('description', 'TEXT'),
                ('filename', 'VARCHAR(255)'),
                ('file_path', 'VARCHAR(500)'),
                ('file_size', 'INTEGER'),
                ('file_type', 'VARCHAR(100)'),
                ('duration', 'INTEGER'),
                ('lesson_date', 'DATE'),
                ('is_active', 'BOOLEAN'),
                ('view_count', 'INTEGER'),
                ('created_at', 'DATETIME'),
                ('updated_at', 'DATETIME')
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
            'shared_files': [
                ('subject_id', 'INTEGER'),
                ('user_id', 'INTEGER'), 
                ('filename', 'VARCHAR(255)'),
                ('file_path', 'VARCHAR(500)'),
                ('file_size', 'INTEGER'),
                ('file_type', 'VARCHAR(100)'),
                ('description', 'TEXT'),
                ('is_active', 'BOOLEAN'),
                ('download_count', 'INTEGER'),
                ('created_at', 'DATETIME'),
                ('updated_at', 'DATETIME')
            ],
            'krav_documents': [
                ('subject_id', 'INTEGER'),
                ('user_id', 'INTEGER'),
                ('doc_type', 'VARCHAR(50)'),
                ('filename', 'VARCHAR(255)'),
                ('file_path', 'VARCHAR(500)'),
                ('file_size', 'INTEGER'),
                ('created_at', 'DATETIME'),
                ('updated_at', 'DATETIME')
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
                            if column_name == 'is_personal':
                                default_value = ' DEFAULT 1'  # Personliga som standard
                            else:
                                default_value = ' DEFAULT 0'
                        elif column_type == 'FLOAT':
                            default_value = ' DEFAULT 2.5' if column_name == 'ease_factor' else ' DEFAULT 0.0'
                        elif column_type == 'INTEGER':
                            default_value = ' DEFAULT 0'
                        elif column_type == 'DATETIME':
                            default_value = " DEFAULT CURRENT_TIMESTAMP"
                        elif column_type == 'VARCHAR(8)' and column_name == 'share_code':
                            default_value = ''  # Kommer fyllas i av generate_share_code()
                        else:
                            default_value = ''
                        
                        alter_query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}{default_value}"
                        db.session.execute(db.text(alter_query))
                        print(f"Added column {column_name} to {table_name}")
                    except Exception as e:
                        print(f"Error adding column {column_name} to {table_name}: {e}")
        
        # Migrera befintliga quiz-poster
        try:
            quizzes_to_update = Quiz.query.filter_by(is_personal=None).all()
            for quiz in quizzes_to_update:
                if quiz.subject_id:
                    subject_obj = Subject.query.get(quiz.subject_id)
                    if subject_obj and quiz.user_id == subject_obj.user_id:
                        quiz.is_personal = False  # Ägaren skapar shared quiz
                    else:
                        quiz.is_personal = True   # Medlemmar skapar personliga quiz
                else:
                    quiz.is_personal = True
            print(f"Updated is_personal for {len(quizzes_to_update)} quizzes")
        except Exception as e:
            print(f"Error updating is_personal: {e}")
        
        try:
            db.session.commit()
            print("Database schema updated successfully")
        except Exception as e:
            print(f"Error committing database changes: {e}")
            db.session.rollback()

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    quiz_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    subject_name = db.Column(db.String(100), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    use_documents = db.Column(db.Boolean, default=False)
    files = db.Column(db.JSON)
    questions = db.Column(db.JSON)
    is_personal = db.Column(db.Boolean, default=True)  # Lägg till denna om den inte finns
    
    def to_dict(self):
        """Konvertera Quiz-objekt till dictionary för JSON-serialisering"""
        return {
            'id': self.id,
            'title': self.title,
            'quiz_type': self.quiz_type,
            'description': self.description,
            'subject_name': self.subject_name,
            'subject_id': self.subject_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'use_documents': self.use_documents,
            'files': self.files,
            'questions': self.questions,
            'is_personal': self.is_personal
        }
    
    def __repr__(self):
        return f"Quiz('{self.title}', '{self.quiz_type}')"



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
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=True)  # Lägg till subject_id
    test_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Skaparen
    is_shared = db.Column(db.Boolean, default=False)  # Om eventet är delat med medlemmar
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date,
            'subject': self.subject,
            'subject_id': self.subject_id,
            'testType': self.test_type,
            'title': self.title,
            'description': self.description,
            'created': self.created_at.isoformat() if self.created_at else None,
            'is_shared': self.is_shared
        }

    def __repr__(self):
        return f"Event('{self.title}', '{self.date}')"




class FlashcardResponse(db.Model):
    __tablename__ = 'flashcard_responses'
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100), nullable=False)
    quiz_title = db.Column(db.String(100), nullable=False)
    question = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    time_taken = db.Column(db.Integer, nullable=False)  # i sekunder
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
class KravDocument(db.Model):
    """Model för krav-dokument som kunskapskrav, begreppslistor etc."""
    __tablename__ = 'krav_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doc_type = db.Column(db.String(50), nullable=False)  # 'begrippslista', 'kunskapskrav', 'kunskapsmal'
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - ta bort backref eftersom de redan finns i Subject och User modellerna
    # subject = db.relationship('Subject') - relationshipen hanteras från Subject-sidan
    # user = db.relationship('User') - relationshipen hanteras från User-sidan
    
    def to_dict(self):
        # Hämta subject-objektet för att få namnet
        subject_obj = Subject.query.get(self.subject_id)
        return {
            'id': self.id,
            'subject_id': self.subject_id,
            'doc_type': self.doc_type,
            'filename': self.filename,
            'file_url': f'/static/uploads/krav/{self.user_id}/{subject_obj.name if subject_obj else "unknown"}/{self.doc_type}.pdf',
            'file_size': self.file_size,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f"KravDocument('{self.doc_type}', '{self.filename}')"



def create_tables():
    """Skapa alla databastabeller"""
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")

def update_database():
    """Uppdatera databasen med nya tabeller"""
    try:
        # Skapa Lesson-tabellen om den inte finns
        db.engine.execute("""
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                filename VARCHAR(255) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                file_size INTEGER,
                file_type VARCHAR(100),
                duration INTEGER,
                lesson_date DATE NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                view_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subject (id),
                FOREIGN KEY (user_id) REFERENCES user (id)
            )
        """)
        
        # Skapa index
        db.engine.execute("CREATE INDEX IF NOT EXISTS idx_lessons_subject_id ON lessons(subject_id)")
        db.engine.execute("CREATE INDEX IF NOT EXISTS idx_lessons_user_id ON lessons(user_id)")
        db.engine.execute("CREATE INDEX IF NOT EXISTS idx_lessons_lesson_date ON lessons(lesson_date)")
        db.engine.execute("CREATE INDEX IF NOT EXISTS idx_lessons_active ON lessons(is_active)")
        
        db.session.commit()
        print("Database updated successfully!")
        
    except Exception as e:
        print(f"Error updating database: {e}")
        db.session.rollback()




def create_shared_files_table():
    """Create the shared_files table if it doesn't exist"""
    try:
        # Check if table exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        
        if 'shared_files' not in inspector.get_table_names():
            # Create the table
            db.create_all()
            print("✅ shared_files table created successfully!")
        else:
            print("ℹ️  shared_files table already exists")
        
        # Verify the table structure
        columns = [column['name'] for column in inspector.get_columns('shared_files')]
        required_columns = [
            'id', 'subject_id', 'user_id', 'filename', 'file_path', 
            'file_size', 'file_type', 'description', 'is_active', 
            'download_count', 'created_at', 'updated_at'
        ]
        
        missing_columns = [col for col in required_columns if col not in columns]
        if missing_columns:
            print(f"⚠️  Missing columns in shared_files table: {missing_columns}")
            print("You may need to run a proper migration to add these columns.")
        else:
            print("✅ All required columns exist in shared_files table")
            
    except Exception as e:
        print(f"❌ Error creating shared_files table: {str(e)}")

def ensure_upload_directories():
    """Ensure upload directories exist"""
    import os
    
    # Create base upload directory
    upload_base = os.path.join(app.root_path, 'static', 'uploads')
    shared_files_dir = os.path.join(upload_base, 'shared_files')
    
    os.makedirs(shared_files_dir, exist_ok=True)
    print(f"✅ Upload directories created: {shared_files_dir}")




def migrate_database():
    """Migrera databas för att lägga till saknade kolumner"""
    with app.app_context():
        try:
            # Försök att läsa från share_code kolumnen
            db.session.execute(db.text("SELECT share_code FROM subject LIMIT 1"))
            print("Database already has share_code column")
        except Exception:
            # Kolumnen finns inte, lägg till den
            try:
                print("Adding share_code column to subject table...")
                db.session.execute(db.text("ALTER TABLE subject ADD COLUMN share_code VARCHAR(8)"))
                db.session.commit()
                print("✓ Added share_code column")
            except Exception as e:
                print(f"Error adding share_code column: {e}")
                db.session.rollback()
        
        try:
            # Försök att läsa från is_shared kolumnen
            db.session.execute(db.text("SELECT is_shared FROM subject LIMIT 1"))
            print("Database already has is_shared column")
        except Exception:
            # Kolumnen finns inte, lägg till den
            try:
                print("Adding is_shared column to subject table...")
                db.session.execute(db.text("ALTER TABLE subject ADD COLUMN is_shared BOOLEAN DEFAULT 0"))
                db.session.commit()
                print("✓ Added is_shared column")
            except Exception as e:
                print(f"Error adding is_shared column: {e}")
                db.session.rollback()
        
        # Generera share_codes för befintliga subjects som saknar dem
        try:
            subjects_without_codes = Subject.query.filter(
                db.or_(Subject.share_code == None, Subject.share_code == '')
            ).all()
            
            for subject in subjects_without_codes:
                # Använd en enklare metod för att generera share_code
                import secrets
                import string
                
                # Generera unik kod
                while True:
                    code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
                    existing = Subject.query.filter_by(share_code=code).first()
                    if not existing:
                        subject.share_code = code
                        break
                
                # Sätt default värde för is_shared om det saknas
                if subject.is_shared is None:
                    subject.is_shared = False
                
                print(f"Generated share code {subject.share_code} for subject: {subject.name}")
            
            if subjects_without_codes:
                db.session.commit()
                print(f"✓ Updated {len(subjects_without_codes)} subjects with share codes")
                
        except Exception as e:
            print(f"Error updating subjects with share codes: {e}")
            db.session.rollback()








# Användare loader för flask-login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Skapa tabeller om de inte finns
init_database()



@app.route('/upload_krav_pdf', methods=['POST'])
@login_required
def upload_krav_pdf():
    """Upload a krav document PDF"""
    try:
        # Get form data
        subject_name = request.form.get('subject')
        doc_type = request.form.get('type')
        file = request.files.get('file')
        
        if not all([subject_name, doc_type, file]):
            return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
        
        # Validate document type
        allowed_types = ['begrippslista', 'kunskapskrav', 'kunskapsmal']
        if doc_type not in allowed_types:
            return jsonify({'status': 'error', 'message': 'Invalid document type'}), 400
        
        # Get subject and check permissions
        subject_obj = Subject.query.filter_by(name=subject_name).first()
        if not subject_obj:
            return jsonify({'status': 'error', 'message': 'Subject not found'}), 404
        
        user_role = current_user.get_role_in_subject(subject_obj.id)
        if user_role not in ['owner', 'admin']:
            return jsonify({'status': 'error', 'message': 'Insufficient permissions'}), 403
        
        # Validate file
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'status': 'error', 'message': 'Only PDF files are allowed'}), 400
        
        # Check file size (50MB limit)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > 50 * 1024 * 1024:  # 50MB
            return jsonify({'status': 'error', 'message': 'File too large. Maximum size is 50MB'}), 400
        
        # Create directory structure
        upload_dir = os.path.join(app.static_folder, 'uploads', 'krav', str(current_user.id), subject_name)
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file with standardized name
        filename = f"{doc_type}.pdf"
        file_path = os.path.join(upload_dir, filename)
        
        # Save the file
        file.save(file_path)
        
        # Remove existing document of same type if exists
        existing_doc = KravDocument.query.filter_by(
            subject_id=subject_obj.id, 
            doc_type=doc_type
        ).first()
        
        if existing_doc:
            # Remove old file
            try:
                if os.path.exists(existing_doc.file_path):
                    os.remove(existing_doc.file_path)
            except Exception as e:
                print(f"Error removing old file: {e}")
            
            # Update existing record
            existing_doc.filename = file.filename
            existing_doc.file_path = file_path
            existing_doc.file_size = file_size
            existing_doc.updated_at = datetime.utcnow()
            document_id = existing_doc.id
        else:
            # Create new record
            new_doc = KravDocument(
                subject_id=subject_obj.id,
                user_id=current_user.id,
                doc_type=doc_type,
                filename=file.filename,
                file_path=file_path,
                file_size=file_size
            )
            db.session.add(new_doc)
            db.session.flush()  # Get the ID
            document_id = new_doc.id
        
        db.session.commit()
        
        # Return success response
        return jsonify({
            'status': 'success',
            'message': 'Document uploaded successfully',
            'document_id': document_id,
            'filename': file.filename,
            'file_url': f'/static/uploads/krav/{current_user.id}/{subject_name}/{filename}',
            'created_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error uploading krav document: {e}")
        return jsonify({'status': 'error', 'message': 'Upload failed'}), 500


@app.route('/remove_krav_pdf', methods=['POST'])
@login_required
def remove_krav_pdf():
    """Remove a krav document"""
    try:
        data = request.get_json()
        subject_name = data.get('subject')
        doc_type = data.get('type')
        document_id = data.get('document_id')
        
        if not all([subject_name, doc_type]):
            return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
        
        # Get subject and check permissions
        subject_obj = Subject.query.filter_by(name=subject_name).first()
        if not subject_obj:
            return jsonify({'status': 'error', 'message': 'Subject not found'}), 404
        
        user_role = current_user.get_role_in_subject(subject_obj.id)
        if user_role not in ['owner', 'admin']:
            return jsonify({'status': 'error', 'message': 'Insufficient permissions'}), 403
        
        # Find and remove document
        if document_id:
            doc = KravDocument.query.filter_by(
                id=document_id,
                subject_id=subject_obj.id,
                doc_type=doc_type
            ).first()
        else:
            doc = KravDocument.query.filter_by(
                subject_id=subject_obj.id,
                doc_type=doc_type
            ).first()
        
        if not doc:
            return jsonify({'status': 'error', 'message': 'Document not found'}), 404
        
        # Remove file from filesystem
        try:
            if os.path.exists(doc.file_path):
                os.remove(doc.file_path)
        except Exception as e:
            print(f"Error removing file: {e}")
        
        # Remove from database
        db.session.delete(doc)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Document removed successfully'})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error removing krav document: {e}")
        return jsonify({'status': 'error', 'message': 'Removal failed'}), 500


@app.route('/api/krav_documents/<subject_name>')
@login_required
def get_krav_documents(subject_name):
    """Get all krav documents for a subject"""
    try:
        # Get subject and check permissions
        subject_obj = Subject.query.filter_by(name=subject_name).first()
        if not subject_obj:
            return jsonify({'status': 'error', 'message': 'Subject not found'}), 404
        
        if not current_user.is_member_of_subject(subject_obj.id):
            return jsonify({'status': 'error', 'message': 'Access denied'}), 403
        
        # Get all krav documents for this subject
        documents = KravDocument.query.filter_by(subject_id=subject_obj.id).all()
        
        # Convert to dictionaries
        docs_data = [doc.to_dict() for doc in documents]
        
        return jsonify({
            'status': 'success',
            'documents': docs_data
        })
        
    except Exception as e:
        print(f"Error getting krav documents: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to load documents'}), 500











def extract_audio_from_video(video_path, audio_output_path):
    """Extrahera ljud från videofil"""
    try:
        video = VideoFileClip(video_path)
        audio = video.audio
        audio.write_audiofile(audio_output_path, logger=None, verbose=False)
        video.close()
        audio.close()
        return True
    except Exception as e:
        print(f"Error extracting audio: {str(e)}")
        return False

def compress_audio_if_needed(audio_path, max_size_mb=25):
    """Komprimera ljud om det är för stort - mer realistisk storlek"""
    try:
        # Kontrollera filstorlek
        file_size = os.path.getsize(audio_path)
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if file_size <= max_size_bytes:
            return audio_path  # Ingen komprimering behövs
        
        print(f"Audio file is {file_size / (1024*1024):.1f}MB, compressing to max {max_size_mb}MB...")
        
        # Skapa temporär fil för komprimerad version
        temp_compressed = audio_path.rsplit('.', 1)[0] + '_compressed.wav'
        
        # Ladda audio med pydub
        audio = AudioSegment.from_file(audio_path)
        
        # Beräkna målbitrate för att uppnå önskad filstorlek
        duration_seconds = len(audio) / 1000
        target_bitrate_kbps = int((max_size_bytes * 8) / (duration_seconds * 1000) * 0.8)  # 80% av max för säkerhet
        
        # Sätt minimum och maximum bitrate
        target_bitrate_kbps = max(64, min(128, target_bitrate_kbps))
        
        print(f"Compressing to {target_bitrate_kbps}kbps...")
        
        # Exportera med lägre kvalitet för mindre filstorlek
        audio.export(
            temp_compressed,
            format="wav",
            parameters=[
                "-ac", "1",      # Mono
                "-ar", "16000"   # Lägre samplerate
            ]
        )
        
        # Kontrollera att den komprimerade filen blev mindre
        compressed_size = os.path.getsize(temp_compressed)
        if compressed_size < max_size_bytes:
            print(f"Compression successful: {compressed_size / (1024*1024):.1f}MB")
            return temp_compressed
        else:
            print(f"File still too large after compression: {compressed_size / (1024*1024):.1f}MB")
            return temp_compressed  # Returnera ändå, kanske fungerar
            
    except Exception as e:
        print(f"Error compressing audio: {str(e)}")
        return audio_path  # Returnera original om komprimering misslyckas



def transcribe_with_speech_recognition(audio_file_path):
    """Transkribera ljud med lokala speech recognition (backup)"""
    temp_files_to_cleanup = []
    
    try:
        print(f"Starting transcription with SpeechRecognition for: {audio_file_path}")
        
        # Konvertera till WAV-format om det behövs
        working_audio_path = audio_file_path
        if not audio_file_path.lower().endswith('.wav'):
            temp_wav_path = audio_file_path.rsplit('.', 1)[0] + '_temp_sr.wav'
            try:
                audio = AudioSegment.from_file(audio_file_path)
                # Konvertera till format som speech_recognition förväntar sig
                audio = audio.set_frame_rate(16000).set_channels(1)
                audio.export(temp_wav_path, format="wav")
                working_audio_path = temp_wav_path
                temp_files_to_cleanup.append(temp_wav_path)
                print(f"Converted audio to WAV format: {temp_wav_path}")
            except Exception as e:
                print(f"Could not convert audio format: {e}")
                return None
        
        # Komprimera om filen är för stor
        compressed_path = compress_audio_if_needed(working_audio_path, max_size_mb=25)
        if compressed_path != working_audio_path:
            temp_files_to_cleanup.append(compressed_path)
            working_audio_path = compressed_path
        
        # Använd speech_recognition
        recognizer = sr.Recognizer()
        
        with sr.AudioFile(working_audio_path) as source:
            print("Reading audio data...")
            audio_data = recognizer.record(source)
        
        print("Starting transcription with Google Speech Recognition...")
        
        try:
            # Försök med Google Speech Recognition (gratis)
            transcription = recognizer.recognize_google(audio_data, language='sv-SE')
            print("Transcription completed successfully with Google SR")
            return transcription
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand audio")
            return "Ljudet kunde inte transkriberas - talet var oklart eller tystnad."
        except sr.RequestError as e:
            print(f"Google Speech Recognition service error: {e}")
            return f"Transkribering misslyckades: {str(e)}"
    
    except Exception as e:
        print(f"Error in transcription: {str(e)}")
        return f"Fel vid transkribering: {str(e)}"
        
    finally:
        # Rensa temporära filer
        for temp_file in temp_files_to_cleanup:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    print(f"Cleaned up temporary file: {temp_file}")
            except Exception as e:
                print(f"Could not remove temp file {temp_file}: {e}")


def transcribe_with_whisper_api(audio_file_path):
    """Transkribera med OpenAI Whisper API (om API-nyckel finns)"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("No OpenAI API key found, skipping Whisper API")
        return None
    
    temp_files_to_cleanup = []
    
    try:
        print(f"Starting transcription with OpenAI Whisper API: {audio_file_path}")
        
        # Komprimera filen om den är för stor (Whisper API har 25MB limit)
        working_audio_path = compress_audio_if_needed(audio_file_path, max_size_mb=25)
        if working_audio_path != audio_file_path:
            temp_files_to_cleanup.append(working_audio_path)
        
        with open(working_audio_path, 'rb') as audio_file:
            response = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={
                    "Authorization": f"Bearer {api_key}"
                },
                files={
                    "file": audio_file
                },
                data={
                    "model": "whisper-1",
                    "language": "sv"
                },
                timeout=120
            )
        
        if response.status_code == 200:
            result = response.json()
            transcription = result.get('text', '')
            print("Whisper API transcription completed successfully")
            return transcription
        else:
            print(f"Whisper API error {response.status_code}: {response.text}")
            return None
    
    except Exception as e:
        print(f"Error with Whisper API: {str(e)}")
        return None
    
    finally:
        # Rensa temporära filer
        for temp_file in temp_files_to_cleanup:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                print(f"Could not remove temp file {temp_file}: {e}")


def transcribe_with_huggingface(audio_file_path):
    """Transkribera ljud med Hugging Face Inference API (GRATIS)"""

    hf_token = os.getenv("HF_API_TOKEN")
    if not hf_token:
        print("Ingen HF_API_TOKEN uppsatt, kan inte använda Hugging Face API")
        return None    
    temp_files_to_cleanup = []
    
    try:
        print(f"Starting transcription with Hugging Face API: {audio_file_path}")
        
        # Konvertera till WAV om det behövs och komprimera
        working_audio_path = audio_file_path
        if not audio_file_path.lower().endswith('.wav'):
            temp_wav_path = audio_file_path.rsplit('.', 1)[0] + '_temp_hf.wav'
            try:
                audio = AudioSegment.from_file(audio_file_path)
                # Konvertera till format som fungerar bra för API:et
                audio = audio.set_frame_rate(16000).set_channels(1)
                audio.export(temp_wav_path, format="wav")
                working_audio_path = temp_wav_path
                temp_files_to_cleanup.append(temp_wav_path)
                print(f"Converted audio to WAV format: {temp_wav_path}")
            except Exception as e:
                print(f"Could not convert audio format: {e}")
                return None
        
        # Komprimera filen för API (max 10MB för säkerhet)
        compressed_path = compress_audio_if_needed(working_audio_path, max_size_mb=10)
        if compressed_path != working_audio_path:
            temp_files_to_cleanup.append(compressed_path)
            working_audio_path = compressed_path
        
        # Läs ljudfilen
        with open(working_audio_path, 'rb') as f:
            audio_data = f.read()
        
        # Kontrollera filstorlek (Hugging Face har ca 10MB limit)
        if len(audio_data) > 10 * 1024 * 1024:
            print(f"Audio file still too large: {len(audio_data) / (1024*1024):.1f}MB")
            return "Ljudfilen är för stor för transkribering. Försök med en kortare fil."
        
        print(f"Sending {len(audio_data) / (1024*1024):.1f}MB audio file for transcription...")
        
        # Använd Hugging Face Inference API med Whisper-modell
        # Detta är GRATIS utan API-nyckel!
        API_URL = "https://api-inference.huggingface.co/models/openai/whisper-large-v3"
        
        headers = {
            "Authorization": f"Bearer {hf_token}",
            "Content-Type": "audio/wav"
        }
        
        try:
            response = requests.post(
                API_URL,
                headers=headers,
                data=audio_data,
                timeout=120
            )
            
            print(f"Hugging Face API response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"API Response: {result}")
                
                # Hugging Face returnerar olika format beroende på modell
                if isinstance(result, dict):
                    if 'text' in result:
                        transcription = result['text']
                    elif 'generated_text' in result:
                        transcription = result['generated_text']
                    else:
                        print(f"Unexpected response format: {result}")
                        transcription = str(result)
                elif isinstance(result, str):
                    transcription = result
                else:
                    print(f"Unexpected response type: {type(result)}")
                    transcription = str(result)
                
                if transcription and transcription.strip():
                    print("Hugging Face transcription completed successfully")
                    return transcription.strip()
                else:
                    return "Transkriberingen gav inget resultat."
                    
            elif response.status_code == 503:
                # Modellen laddar, försök igen efter en kort paus
                print("Model is loading, retrying in 10 seconds...")
                import time
                time.sleep(10)
                
                # Andra försök
                response = requests.post(
                    API_URL,
                    headers=headers,
                    data=audio_data,
                    timeout=180
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, dict) and 'text' in result:
                        return result['text'].strip()
                    elif isinstance(result, str):
                        return result.strip()
                
                return f"API-fel efter omförsök: {response.status_code}"
                
            else:
                print(f"Hugging Face API error: {response.status_code} - {response.text}")
                return f"Transkribering misslyckades: API-fel {response.status_code}"
            
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return f"Nätverksfel vid transkribering: {str(e)}"
            
    except Exception as e:
        print(f"Error transcribing with Hugging Face: {str(e)}")
        return f"Fel vid transkribering: {str(e)}"
        
    finally:
        # Rensa temporära filer
        for temp_file in temp_files_to_cleanup:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    print(f"Cleaned up temporary file: {temp_file}")
            except Exception as e:
                print(f"Could not remove temp file {temp_file}: {e}")



def transcribe_with_hackclub_ai(audio_file_path):
    """Transkribera ljud med Hackclub AI API"""
    temp_files_to_cleanup = []
    
    try:
        # Konvertera till WAV-format om det behövs
        working_audio_path = audio_file_path
        if not audio_file_path.lower().endswith(('.wav', '.mp3')):
            temp_wav_path = audio_file_path.rsplit('.', 1)[0] + '_temp.wav'
            try:
                audio = AudioSegment.from_file(audio_file_path)
                audio.export(temp_wav_path, format="wav")
                working_audio_path = temp_wav_path
                temp_files_to_cleanup.append(temp_wav_path)
            except Exception as e:
                print(f"Could not convert audio format: {e}")
                pass
        
        # Komprimera mer aggressivt för stora filer
        compressed_path = compress_audio_if_needed(working_audio_path, max_size_mb=3)  # Minska till 3MB
        if compressed_path != working_audio_path:
            temp_files_to_cleanup.append(compressed_path)
            working_audio_path = compressed_path
        
        # Läs ljudfilen
        with open(working_audio_path, 'rb') as audio_file:
            audio_data = audio_file.read()
        
        # Kontrollera filstorlek (max 3MB för base64)
        if len(audio_data) > 3 * 1024 * 1024:
            print(f"Audio file still too large after compression: {len(audio_data) / (1024*1024):.1f}MB")
            return None
        
        print(f"Sending {len(audio_data) / (1024*1024):.1f}MB audio file for transcription...")
        
        # Skapa enklare prompt utan base64 - bara be om transkribering
        prompt = "Transkribera denna ljudfil till svensk text. Formatera med korrekt interpunktion och styckeindelning."
        
        # Använd requests.Session för bättre SSL-hantering
        session = requests.Session()
        session.verify = True  # Verifiera SSL
        
        try:
            response = session.post(
                "https://ai.hackclub.com/chat/completions",
                json={
                    "messages": [
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ]
                },
                headers={"Content-Type": "application/json"},
                timeout=300,  # Kortare timeout
                stream=False
            )
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    transcription = result['choices'][0]['message']['content']
                    print("Transcription completed successfully")
                    return transcription.strip()
                else:
                    print("No transcription content in response")
                    return None
            else:
                print(f"API returned status {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.SSLError as ssl_error:
            print(f"SSL Error: {ssl_error}")
            # Försök utan SSL-verifiering som sista utväg
            try:
                print("Retrying without SSL verification...")
                session.verify = False
                response = session.post(
                    "https://ai.hackclub.com/chat/completions",
                    json={
                        "messages": [
                            {
                                "role": "user", 
                                "content": "Transkribera denna text till svenska: 'Detta är ett test av transkribering.'"
                            }
                        ]
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=60
                )
                
                if response.status_code == 200:
                    print("API connection works, but audio transcription may not be supported")
                    return "Transkribering är inte tillgänglig för denna fil. API:et svarar men stöder inte ljudfiler."
                
            except Exception as retry_error:
                print(f"Retry failed: {retry_error}")
                
            return None
            
        except Exception as e:
            print(f"[ERROR] AI API call failed: {e}")
            return None
        
    except Exception as e:
        print(f"Error transcribing with Hackclub AI: {str(e)}")
        return None
        
    finally:
        # Rensa temporära filer
        for temp_file in temp_files_to_cleanup:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    print(f"Cleaned up temporary file: {temp_file}")
            except Exception as e:
                print(f"Could not remove temp file {temp_file}: {e}")

def start_transcription_async(lesson_id):
    """Starta transkribering i bakgrundstråd"""
    thread = Thread(target=process_transcription, args=(lesson_id,))
    thread.daemon = True
    thread.start()
    print(f"Started transcription thread for lesson {lesson_id}")

# Lägg till denna route för att manuellt starta transkribering
@app.route('/api/lesson/<int:lesson_id>/retranscribe', methods=['POST'])
@login_required
def retranscribe_lesson(lesson_id):
    try:
        lesson = Lesson.query.get_or_404(lesson_id)
        
        # Kontrollera att användaren har rättigheter
        subject = Subject.query.get(lesson.subject_id)
        if not subject or subject.creator_id != current_user.id:
            return jsonify({'status': 'error', 'message': 'Ingen behörighet'})
        
        # Starta transkribering
        start_transcription_async(lesson_id)
        
        return jsonify({'status': 'success', 'message': 'Transkribering startad'})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

def process_transcription(lesson_id):
    """Behandla transkribering för en lektion (körs i bakgrund) - UPPDATERAD"""
    try:
        with app.app_context():  # Viktigt för att använda databas i bakgrundstråd
            lesson = Lesson.query.get(lesson_id)
            if not lesson:
                print(f"Lesson {lesson_id} not found")
                return False
            
            # Uppdatera status
            lesson.transcription_status = 'processing'
            db.session.commit()
            
            print(f"Starting transcription for lesson {lesson_id}: {lesson.title}")
            
            # Kontrollera att filen existerar
            if not os.path.exists(lesson.file_path):
                print(f"File not found: {lesson.file_path}")
                lesson.transcription_status = 'failed'
                lesson.transcription = 'Fel: Filen hittades inte'
                db.session.commit()
                return False
            
            # Skapa temporär ljudfil
            temp_audio_path = None
            original_file_path = lesson.file_path
            
            # Om det är en videofil, extrahera ljud först
            if lesson.file_type and lesson.file_type.startswith('video/'):
                temp_audio_path = original_file_path.rsplit('.', 1)[0] + '_temp_audio.wav'
                print(f"Extracting audio from video to {temp_audio_path}")
                if not extract_audio_from_video(original_file_path, temp_audio_path):
                    lesson.transcription_status = 'failed'
                    lesson.transcription = 'Fel: Kunde inte extrahera ljud från video'
                    db.session.commit()
                    return False
                audio_path = temp_audio_path
            else:
                audio_path = original_file_path
            
            print(f"Transcribing audio file: {audio_path}")
            print(f"File size: {os.path.getsize(audio_path) / (1024*1024):.1f}MB")
            
            # Försök flera transkriberings-metoder i prioritetsordning
            transcription = None
            
            # 1. Först försök med OpenAI Whisper API (om tillgänglig)
            transcription = transcribe_with_whisper_api(audio_path)
            
            # 2. Fallback till Hugging Face (GRATIS OCH BRA!)
            if not transcription:
                print("Whisper API not available, trying Hugging Face...")
                transcription = transcribe_with_huggingface(audio_path)
            
            # 3. Sista utväg: lokal speech recognition
            if not transcription or transcription.startswith("Fel") or transcription.startswith("Transkribering"):
                print("Hugging Face failed, trying local speech recognition...")
                local_result = transcribe_with_speech_recognition(audio_path)
                if local_result and not local_result.startswith("Fel"):
                    transcription = local_result
            
            # Rensa temporär fil
            if temp_audio_path and os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
            
            # Spara resultatet
            if transcription and transcription.strip() and not transcription.startswith("Fel"):
                lesson.transcription = transcription.strip()
                lesson.transcription_status = 'completed'
                print(f"Transcription completed for lesson {lesson_id}")
                print(f"Transcription preview: {transcription[:100]}...")
            else:
                lesson.transcription_status = 'failed'
                lesson.transcription = transcription or 'Transkribering misslyckades. Kontrollera att ljudet innehåller tal och försök igen.'
                print(f"Transcription failed for lesson {lesson_id}")
            
            db.session.commit()
            return transcription is not None and transcription.strip()
        
    except Exception as e:
        print(f"Error processing transcription for lesson {lesson_id}: {str(e)}")
        # Uppdatera status till failed
        try:
            with app.app_context():
                lesson = Lesson.query.get(lesson_id)
                if lesson:
                    lesson.transcription_status = 'failed'
                    lesson.transcription = f'Fel vid transkribering: {str(e)}'
                    db.session.commit()
        except Exception as commit_error:
            print(f"Error updating lesson status: {commit_error}")
        return False




# Konfiguration för lektioner
ALLOWED_LESSON_EXTENSIONS = {
    'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv',  # Video
    'mp3', 'wav', 'aac', 'ogg', 'flac', 'm4a'         # Audio
}

def allowed_lesson_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_LESSON_EXTENSIONS

@app.route('/upload_lesson', methods=['POST'])
@login_required
def upload_lesson():
    """Ladda upp en ny lektion"""
    try:
        print("Upload lesson route called")
        
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        
        # Hämta formulärdata
        subject_id = request.form.get('subject_id')
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        lesson_date = request.form.get('lesson_date')
        
        print(f"Form data: subject_id={subject_id}, title={title}, lesson_date={lesson_date}")
        
        # Validera data
        if not subject_id:
            return jsonify({'status': 'error', 'message': 'Subject ID required'}), 400
        
        if not title:
            return jsonify({'status': 'error', 'message': 'Lesson title required'}), 400
        
        if not lesson_date:
            return jsonify({'status': 'error', 'message': 'Lesson date required'}), 400
        
        try:
            subject_id = int(subject_id)
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid subject ID'}), 400
        
        # Kontrollera att användaren äger ämnet
        subject = Subject.query.get_or_404(subject_id)
        if subject.user_id != current_user.id:
            return jsonify({'status': 'error', 'message': 'Access denied'}), 403
        
        # Kontrollera filtyp
        if not allowed_lesson_file(file.filename):
            return jsonify({
                'status': 'error', 
                'message': 'Invalid file type. Only video and audio files are allowed.'
            }), 400
        
        # Kontrollera filstorlek (100MB limit för uppladdning)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset till början
        
        if file_size > 100 * 1024 * 1024:  # 100MB
            return jsonify({
                'status': 'error', 
                'message': 'File too large. Maximum size is 100MB.'
            }), 400
        
        # Konvertera datum
        try:
            lesson_date_obj = datetime.strptime(lesson_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid date format'}), 400
        
        # Säker filnamn
        filename = secure_filename(file.filename)
        
        # Skapa mappstruktur
        subject_name_safe = secure_filename(subject.name)
        lesson_dir = os.path.join(
            app.config['UPLOAD_FOLDER'], 
            'lessons', 
            str(current_user.id), 
            subject_name_safe
        )
        os.makedirs(lesson_dir, exist_ok=True)
        
        # Unik filnamn för att undvika konflikter
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        unique_filename = f"{timestamp}_{name}{ext}"
        file_path = os.path.join(lesson_dir, unique_filename)
        
        print(f"Saving file to: {file_path}")
        
        # Spara fil
        file.save(file_path)
        
        # Hämta filinfo
        actual_file_size = os.path.getsize(file_path)
        file_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
        
        print(f"File saved: size={actual_file_size}, type={file_type}")
        
        # Skapa Lesson-post
        lesson = Lesson(
            subject_id=subject_id,
            user_id=current_user.id,
            title=title,
            description=description if description else None,
            filename=filename,
            file_path=file_path,
            file_size=actual_file_size,
            file_type=file_type,
            lesson_date=lesson_date_obj,
            transcription_status='pending'
        )
        
        db.session.add(lesson)
        db.session.commit()
        
        print(f"Lesson created with ID: {lesson.id}")
        
        # Starta transkribering i bakgrund
        start_transcription_async(lesson.id)
        
        return jsonify({
            'status': 'success',
            'message': 'Lesson uploaded successfully. Transcription is being processed.',
            'lesson': lesson.to_dict()
        })
        
    except Exception as e:
        print(f"Error in upload_lesson: {str(e)}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/lesson/<int:lesson_id>/transcription')
@login_required
def get_lesson_transcription(lesson_id):
    """Hämta transkription för en lektion"""
    try:
        lesson = Lesson.query.get_or_404(lesson_id)
        
        # Kontrollera tillgång
        if not lesson.is_accessible_by_user(current_user.id):
            return jsonify({'status': 'error', 'message': 'Access denied'}), 403
        
        return jsonify({
            'status': 'success',
            'transcription': lesson.transcription,
            'transcription_status': lesson.transcription_status
        })
        
    except Exception as e:
        print(f"Error getting transcription: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/lesson/<int:lesson_id>/retranscribe', methods=['POST'])
@login_required
def retry_transcription(lesson_id):
    """Försök transkribera igen"""
    try:
        lesson = Lesson.query.get_or_404(lesson_id)
        
        # Endast ägaren kan starta om transkribering
        if lesson.user_id != current_user.id:
            return jsonify({'status': 'error', 'message': 'Access denied'}), 403
        
        # Starta transkribering i bakgrund
        from threading import Thread
        transcription_thread = Thread(target=process_transcription, args=(lesson.id,))
        transcription_thread.daemon = True
        transcription_thread.start()
        
        return jsonify({
            'status': 'success',
            'message': 'Transcription restarted'
        })
        
    except Exception as e:
        print(f"Error restarting transcription: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/lessons/<int:subject_id>')
@login_required
def get_lessons(subject_id):
    """Hämta alla lektioner för ett ämne"""
    try:
        print(f"Getting lessons for subject {subject_id}")  # Debug
        
        # Kontrollera att användaren har tillgång till ämnet
        if not current_user.is_member_of_subject(subject_id):
            return jsonify({'status': 'error', 'message': 'Access denied'}), 403
        
        # Hämta alla aktiva lektioner, sorterade efter lesson_date
        lessons = Lesson.query.filter_by(
            subject_id=subject_id,
            is_active=True
        ).order_by(Lesson.lesson_date.asc()).all()
        
        print(f"Found {len(lessons)} lessons")  # Debug
        
        lessons_data = []
        for lesson in lessons:
            lesson_dict = lesson.to_dict()
            # Lägg till om användaren kan redigera
            lesson_dict['can_edit'] = lesson.user_id == current_user.id
            lessons_data.append(lesson_dict)
        
        return jsonify({
            'status': 'success',
            'lessons': lessons_data,
            'total_lessons': len(lessons_data)
        })
        
    except Exception as e:
        print(f"Error in get_lessons: {str(e)}")  # Debug
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/stream_lesson/<int:lesson_id>')
@login_required
def stream_lesson(lesson_id):
    """Strömma en lektion (video/audio)"""
    try:
        lesson = Lesson.query.get_or_404(lesson_id)
        
        # Kontrollera tillgång
        if not lesson.is_accessible_by_user(current_user.id):
            return jsonify({'status': 'error', 'message': 'Access denied'}), 403
        
        # Öka view count
        lesson.view_count += 1
        db.session.commit()
        
        # Returnera filen för streaming
        return send_file(lesson.file_path, as_attachment=False)
        
    except Exception as e:
        print(f"Error in stream_lesson: {str(e)}")  # Debug
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/download_lesson/<int:lesson_id>')
@login_required
def download_lesson(lesson_id):
    """Ladda ner en lektion"""
    try:
        lesson = Lesson.query.get_or_404(lesson_id)
        
        # Kontrollera tillgång
        if not lesson.is_accessible_by_user(current_user.id):
            return jsonify({'status': 'error', 'message': 'Access denied'}), 403
        
        # Öka view count
        lesson.view_count += 1
        db.session.commit()
        
        # Returnera filen för nedladdning
        return send_file(lesson.file_path, as_attachment=True, 
                        download_name=lesson.filename)
        
    except Exception as e:
        print(f"Error in download_lesson: {str(e)}")  # Debug
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/delete_lesson', methods=['POST'])
@login_required
def delete_lesson():
    """Ta bort en lektion"""
    try:
        data = request.get_json()
        lesson_id = data.get('lesson_id')
        
        if not lesson_id:
            return jsonify({'status': 'error', 'message': 'Lesson ID required'}), 400
        
        lesson = Lesson.query.get_or_404(lesson_id)
        
        # Kontrollera att användaren äger lektionen
        if lesson.user_id != current_user.id:
            return jsonify({'status': 'error', 'message': 'Access denied'}), 403
        
        # Markera som inaktiv istället för att ta bort
        lesson.is_active = False
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Lesson deleted successfully'
        })
        
    except Exception as e:
        print(f"Error in delete_lesson: {str(e)}")  # Debug
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/lessons/<int:subject_id>/stats')
@login_required
def get_lesson_stats(subject_id):
    """Hämta statistik för lektioner (endast för ägare)"""
    try:
        subject = Subject.query.get_or_404(subject_id)
        
        # Kontrollera att användaren äger ämnet
        if subject.user_id != current_user.id:
            return jsonify({'status': 'error', 'message': 'Access denied'}), 403
        
        # Hämta statistik
        lessons = Lesson.query.filter_by(subject_id=subject_id, is_active=True).all()
        total_lessons = len(lessons)
        total_views = sum(lesson.view_count for lesson in lessons)
        total_duration = sum(lesson.duration for lesson in lessons if lesson.duration)
        
        return jsonify({
            'status': 'success',
            'total_lessons': total_lessons,
            'total_views': total_views,
            'total_duration': total_duration,
            'total_duration_display': f"{total_duration // 3600}h {(total_duration % 3600) // 60}m" if total_duration else "N/A"
        })
        
    except Exception as e:
        print(f"Error in get_lesson_stats: {str(e)}")  # Debug
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Kontrollera att UPLOAD_FOLDER är konfigurerad
if not hasattr(app.config, 'UPLOAD_FOLDER'):
    app.config['UPLOAD_FOLDER'] = 'uploads'

# Skapa upload-mappen om den inte finns
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)



















@app.route('/join_subject', methods=['POST'])
@login_required
def join_subject():
    """Gå med i ett subject via share code"""
    try:
        data = request.get_json()
        share_code = data.get('share_code', '').strip().upper()
        
        if not share_code:
            return jsonify({'status': 'error', 'message': 'Share code is required'}), 400
        
        # Hitta subject med denna kod
        subject = Subject.query.filter_by(share_code=share_code).first()
        
        if not subject:
            return jsonify({'status': 'error', 'message': 'Invalid share code'}), 404
        
        if not subject.is_shared:
            return jsonify({'status': 'error', 'message': 'This subject is not shared'}), 403
        
        # Kontrollera om användaren redan är medlem eller ägare
        if subject.user_id == current_user.id:
            return jsonify({'status': 'error', 'message': 'You are the owner of this subject'}), 400
        
        existing_membership = SubjectMember.query.filter_by(
            subject_id=subject.id,
            user_id=current_user.id
        ).first()
        
        if existing_membership:
            return jsonify({'status': 'error', 'message': 'You are already a member of this subject'}), 400
        
        # Lägg till användaren som medlem
        membership = SubjectMember(
            subject_id=subject.id,
            user_id=current_user.id,
            role='member'
        )
        
        db.session.add(membership)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully joined "{subject.name}"',
            'subject_name': subject.name
        })
        
    except Exception as e:
        print(f"[ERROR] Failed to join subject: {e}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Failed to join subject'}), 500 


@app.route('/api/subject/<int:subject_id>/share_code')
@login_required
def get_share_code(subject_id):
    """Hämta share code för ett ämne (endast för ägaren)"""
    try:
        subject = Subject.query.filter_by(id=subject_id, user_id=current_user.id).first()
        
        if not subject:
            return jsonify({'status': 'error', 'message': 'Subject not found or no access'}), 404
        
        return jsonify({
            'status': 'success',
            'share_code': subject.share_code,
            'is_shared': subject.is_shared
        })
        
    except Exception as e:
        print(f"[ERROR] Failed to get share code: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to get share code'}), 500

@app.route('/api/subject/<int:subject_id>/regenerate_code', methods=['POST'])
@login_required
def regenerate_share_code(subject_id):
    """Regenerera share code för ett ämne"""
    try:
        subject = Subject.query.filter_by(id=subject_id, user_id=current_user.id).first()
        
        if not subject:
            return jsonify({'status': 'error', 'message': 'Subject not found or no access'}), 404
        
        # Generera ny kod
        subject.share_code = subject.generate_share_code()
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'share_code': subject.share_code,
            'message': 'Share code regenerated successfully'
        })
        
    except Exception as e:
        print(f"[ERROR] Failed to regenerate share code: {e}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Failed to regenerate share code'}), 500





@app.route('/api/my_subjects')
@login_required
def get_my_subjects():
    """Hämta alla ämnen som användaren har tillgång till"""
    try:
        owned_subjects = current_user.get_owned_subjects()
        shared_subjects = current_user.get_shared_subjects()
        
        owned_data = []
        for subject in owned_subjects:
            owned_data.append({
                'id': subject.id,
                'name': subject.name,
                'share_code': subject.share_code,
                'is_shared': subject.is_shared,
                'role': 'owner',
                'created_at': subject.created_at.isoformat()
            })
        
        shared_data = []
        for subject in shared_subjects:
            membership = SubjectMember.query.filter_by(
                subject_id=subject.id,
                user_id=current_user.id
            ).first()
            
            shared_data.append({
                'id': subject.id,
                'name': subject.name,
                'role': membership.role if membership else 'member',
                'joined_at': membership.joined_at.isoformat() if membership else None,
                'owner': subject.owner.username
            })
        
        return jsonify({
            'status': 'success',
            'owned_subjects': owned_data,
            'shared_subjects': shared_data
        })
        
    except Exception as e:
        print(f"[ERROR] Failed to get subjects: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to get subjects'}), 500


@app.route('/api/subject/<int:subject_id>/share', methods=['POST'])
@login_required
def toggle_subject_sharing(subject_id):
    """Aktivera/inaktivera delning av ett subject"""
    try:
        subject = Subject.query.filter_by(id=subject_id, user_id=current_user.id).first()
        
        if not subject:
            return jsonify({'status': 'error', 'message': 'Subject not found'}), 404
        
        # Toggle sharing status
        subject.is_shared = not subject.is_shared
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'is_shared': subject.is_shared,
            'share_code': subject.share_code if subject.is_shared else None,
            'message': f'Subject sharing {"enabled" if subject.is_shared else "disabled"}'
        })
        
    except Exception as e:
        print(f"[ERROR] Failed to toggle subject sharing: {e}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Failed to update sharing'}), 500

@app.route('/api/subject/<int:subject_id>/members')
@login_required
def get_subject_members(subject_id):
    """Hämta medlemmar för ett subject"""
    try:
        subject = Subject.query.filter_by(id=subject_id, user_id=current_user.id).first()
        
        if not subject:
            return jsonify({'status': 'error', 'message': 'Subject not found'}), 404
        
        members = db.session.query(SubjectMember, User).join(User).filter(
            SubjectMember.subject_id == subject_id
        ).all()
        
        members_data = []
        for membership, user in members:
            members_data.append({
                'id': user.id,
                'username': user.username,
                'role': membership.role,
                'joined_at': membership.joined_at.isoformat()
            })
        
        # Lägg till ägaren
        owner_data = {
            'id': subject.user_id,
            'username': subject.owner.username,
            'role': 'owner',
            'joined_at': subject.created_at.isoformat()
        }
        
        return jsonify({
            'status': 'success',
            'owner': owner_data,
            'members': members_data,
            'total_members': len(members_data) + 1  # +1 för ägaren
        })
        
    except Exception as e:
        print(f"[ERROR] Failed to get subject members: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to get members'}), 500

@app.route('/api/subject/<int:subject_id>/member/<int:user_id>', methods=['DELETE'])
@login_required
def remove_subject_member(subject_id, user_id):
    """Ta bort en medlem från ett subject"""
    try:
        subject = Subject.query.filter_by(id=subject_id, user_id=current_user.id).first()
        
        if not subject:
            return jsonify({'status': 'error', 'message': 'Subject not found'}), 404
        
        membership = SubjectMember.query.filter_by(
            subject_id=subject_id,
            user_id=user_id
        ).first()
        
        if not membership:
            return jsonify({'status': 'error', 'message': 'Member not found'}), 404
        
        removed_user = User.query.get(user_id)
        username = removed_user.username if removed_user else 'Unknown'
        
        db.session.delete(membership)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Removed {username} from subject'
        })
        
    except Exception as e:
        print(f"[ERROR] Failed to remove subject member: {e}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Failed to remove member'}), 500

@app.route('/leave_subject/<int:subject_id>', methods=['POST'])
@login_required
def leave_subject(subject_id):
    """Lämna ett subject som medlem"""
    try:
        membership = SubjectMember.query.filter_by(
            subject_id=subject_id,
            user_id=current_user.id
        ).first()
        
        if not membership:
            return jsonify({'status': 'error', 'message': 'You are not a member of this subject'}), 404
        
        subject = Subject.query.get(subject_id)
        subject_name = subject.name if subject else 'Unknown'
        
        db.session.delete(membership)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Left subject "{subject_name}"'
        })
        
    except Exception as e:
        print(f"[ERROR] Failed to leave subject: {e}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Failed to leave subject'}), 500


# Uppdatera din befintliga index route med denna kod

@app.route('/')
@login_required
def index():
    """Huvudsida som visar alla ämnen användaren har tillgång till"""
    try:
        # Hämta alla ämnen som användaren har tillgång till (äger eller är medlem i)
        all_subjects = current_user.get_all_subjects()
        
        # Separera ägda och delade ämnen
        owned_subjects = [s for s in all_subjects if s.user_id == current_user.id]
        shared_subjects = [s for s in all_subjects if s.user_id != current_user.id]
        
        # Lägg till extra information för varje ämne
        for subject in all_subjects:
            # Räkna quiz för detta ämne
            quiz_count = Quiz.query.filter_by(subject_id=subject.id).count()
            subject.quiz_count = quiz_count
            
            # Räkna flashcards för detta ämne
            flashcard_count = Flashcard.query.filter_by(subject_id=subject.id).count()
            subject.flashcard_count = flashcard_count
            
            # Räkna due flashcards för användaren
            today = datetime.now().date()
            due_count = Flashcard.query.filter(
                Flashcard.subject_id == subject.id,
                Flashcard.user_id == current_user.id,
                db.or_(
                    Flashcard.next_review <= today,
                    Flashcard.next_review == None
                )
            ).count()
            subject.due_flashcards = due_count
            
            # Lägg till användarens roll
            subject.user_role = current_user.get_role_in_subject(subject.id)
        
        # Hämta totala statistik för användaren
        total_due = Flashcard.query.filter(
            Flashcard.user_id == current_user.id,
            db.or_(
                Flashcard.next_review <= datetime.now().date(),
                Flashcard.next_review == None
            )
        ).count()
        
        return render_template('index.html', 
                             owned_subjects=owned_subjects,
                             shared_subjects=shared_subjects,
                             total_due_flashcards=total_due)
        
    except Exception as e:
        print(f"[ERROR] Failed to load index: {e}")
        flash('Error loading subjects', 'error')
        return render_template('index.html', owned_subjects=[], shared_subjects=[], total_due_flashcards=0)


@app.route('/add_subject', methods=['POST'])
@login_required
def add_subject():
    """Skapa ett nytt ämne"""
    try:
        data = request.get_json()
        subject_name = data.get('name', '').strip()
        is_shared = data.get('is_shared', False)
        
        if not subject_name:
            return jsonify({'status': 'error', 'message': 'Subject name is required'}), 400
        
        # Kontrollera om ämnet redan finns för användaren
        existing = Subject.query.filter_by(name=subject_name, user_id=current_user.id).first()
        if existing:
            return jsonify({'status': 'error', 'message': 'Subject already exists'}), 400
        
        # Skapa nytt ämne med automatisk share_code
        subject = Subject.create_with_code(
            name=subject_name,
            user_id=current_user.id,
            is_shared=is_shared
        )
        
        db.session.add(subject)
        db.session.commit()
        
        # Lägg till räknare för quiz och flashcards (börjar med 0)
        subject.quiz_count = 0
        subject.flashcard_count = 0
        subject.due_flashcards = 0
        subject.user_role = 'owner'  # Skaparen är alltid owner
        
        return jsonify({
            'status': 'success',
            'message': f'Subject "{subject_name}" created successfully',
            'subject': {
                'id': subject.id,
                'name': subject.name,
                'share_code': subject.share_code,
                'is_shared': subject.is_shared,
                'quiz_count': 0,
                'flashcard_count': 0,
                'due_flashcards': 0,
                'user_role': 'owner'
            }
        })
        
    except Exception as e:
        print(f"[ERROR] Failed to add subject: {e}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Failed to create subject'}), 500
# Uppdatera dina befintliga quiz routes med denna kod för att hantera shared subjects


@app.route('/upload_shared_file', methods=['POST'])
@login_required
def upload_shared_file():
    """Upload a shared file to a subject (only owners can upload)"""
    try:
        # Get form data
        subject_name = request.form.get('subject')
        description = request.form.get('description', '')
        
        if not subject_name:
            return jsonify({'status': 'error', 'message': 'Subject name is required'})
        
        # Find subject
        subject_obj = Subject.query.filter_by(name=subject_name).first()
        if not subject_obj:
            return jsonify({'status': 'error', 'message': 'Subject not found'})
        
        # Check if user is owner (only owners can upload shared files)
        user_role = current_user.get_role_in_subject(subject_obj.id)
        if user_role != 'owner':
            return jsonify({'status': 'error', 'message': 'Only subject owners can upload shared files'})
        
        # Get uploaded file
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file uploaded'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'})
        
        # Validate file size (50MB limit)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > 50 * 1024 * 1024:  # 50MB
            return jsonify({'status': 'error', 'message': 'File too large (max 50MB)'})
        
        # Validate file type
        allowed_extensions = {
            'pdf', 'doc', 'docx', 'txt', 'rtf',
            'jpg', 'jpeg', 'png', 'gif', 'bmp',
            'mp4', 'avi', 'mov', 'wmv', 'flv',
            'mp3', 'wav', 'ogg', 'flac',
            'zip', 'rar', '7z', 'tar', 'gz'
        }
        
        file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if file_extension not in allowed_extensions:
            return jsonify({'status': 'error', 'message': 'File type not allowed'})
        
        # Create upload directory
        upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'shared_files', str(current_user.id))
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        original_filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        # Save file
        file.save(file_path)
        
        # Create database record
        shared_file = SharedFile(
            subject_id=subject_obj.id,
            user_id=current_user.id,
            filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file.content_type,
            description=description
        )
        
        db.session.add(shared_file)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'File uploaded successfully',
            'filename': original_filename,
            'file_id': shared_file.id
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error uploading file: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to upload file'})


@app.route('/api/shared_files/<subject_name>')
@login_required
def get_shared_files(subject_name):
    """Get all shared files for a subject"""
    try:
        # Find subject
        subject_obj = Subject.query.filter_by(name=subject_name).first()
        if not subject_obj:
            return jsonify({'status': 'error', 'message': 'Subject not found'})
        
        # Check if user has access
        if not current_user.is_member_of_subject(subject_obj.id):
            return jsonify({'status': 'error', 'message': 'Access denied'})
        
        user_role = current_user.get_role_in_subject(subject_obj.id)
        
        # Get all active shared files
        shared_files = SharedFile.query.filter_by(
            subject_id=subject_obj.id,
            is_active=True
        ).order_by(SharedFile.created_at.desc()).all()
        
        files_data = []
        for file in shared_files:
            files_data.append({
                'id': file.id,
                'filename': file.filename,
                'file_size': file.get_display_size(),
                'file_type': file.file_type,
                'description': file.description,
                'extension': file.get_file_extension(),
                'download_count': file.download_count,
                'created_at': file.created_at.strftime('%Y-%m-%d %H:%M'),
                'uploader': file.uploader.username,
                'can_delete': (user_role == 'owner' or file.user_id == current_user.id)
            })
        
        return jsonify({
            'status': 'success',
            'files': files_data,
            'total_files': len(files_data)
        })
        
    except Exception as e:
        print(f"Error getting shared files: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to load files'})


@app.route('/download_shared_file/<int:file_id>')
@login_required
def download_shared_file(file_id):
    """Download a shared file"""
    try:
        # Find file
        shared_file = SharedFile.query.get_or_404(file_id)
        
        # Check if user can download
        if not shared_file.is_downloadable_by_user(current_user.id):
            abort(403)
        
        # Check if file exists
        if not os.path.exists(shared_file.file_path):
            abort(404)
        
        # Increment download count
        shared_file.download_count += 1
        db.session.commit()
        
        # Send file
        return send_file(
            shared_file.file_path,
            as_attachment=True,
            download_name=shared_file.filename
        )
        
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        abort(500)


@app.route('/delete_shared_file', methods=['POST'])
@login_required
def delete_shared_file():
    """Delete a shared file"""
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        
        if not file_id:
            return jsonify({'status': 'error', 'message': 'File ID is required'})
        
        # Find file
        shared_file = SharedFile.query.get(file_id)
        if not shared_file:
            return jsonify({'status': 'error', 'message': 'File not found'})
        
        # Check permissions (only owner of subject or uploader can delete)
        user_role = current_user.get_role_in_subject(shared_file.subject_id)
        if user_role != 'owner' and shared_file.user_id != current_user.id:
            return jsonify({'status': 'error', 'message': 'Permission denied'})
        
        # Mark as inactive instead of deleting
        shared_file.is_active = False
        db.session.commit()
        
        # Optional: Delete physical file
        try:
            if os.path.exists(shared_file.file_path):
                os.remove(shared_file.file_path)
        except:
            pass  # Don't fail if file removal fails
        
        return jsonify({
            'status': 'success',
            'message': 'File deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting file: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to delete file'})


@app.route('/api/shared_files/<int:subject_id>/stats')
@login_required
def get_file_stats(subject_id):
    """Get file statistics for a subject (only for owners)"""
    try:
        # Find subject
        subject_obj = Subject.query.get_or_404(subject_id)
        
        # Check if user is owner
        user_role = current_user.get_role_in_subject(subject_obj.id)
        if user_role != 'owner':
            return jsonify({'status': 'error', 'message': 'Access denied'})
        
        # Get statistics
        shared_files = SharedFile.query.filter_by(
            subject_id=subject_obj.id,
            is_active=True
        ).all()
        
        total_files = len(shared_files)
        total_downloads = sum(file.download_count for file in shared_files)
        
        return jsonify({
            'status': 'success',
            'total_files': total_files,
            'total_downloads': total_downloads
        })
        
    except Exception as e:
        print(f"Error getting file stats: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to load stats'})


@app.route('/subject/<subject_name>')
@login_required
def subject(subject_name):
    """Subject page - visa olika quizzes baserat på användarens roll"""
    subject_obj = Subject.query.filter_by(name=subject_name).first()
    if not subject_obj:
        flash('Subject not found', 'error')
        return redirect(url_for('index'))
    
    # Kontrollera att användaren har tillgång till detta subject
    if not current_user.is_member_of_subject(subject_obj.id):
        flash('You do not have access to this subject', 'error')
        return redirect(url_for('index'))
    
    user_role = current_user.get_role_in_subject(subject_obj.id)
    
    # Hämta quizzes baserat på användarens roll
    if user_role in ['owner', 'admin']:
        # Owners och admins ser alla shared quizzes + sina egna personliga
        shared_quizzes = Quiz.query.filter_by(subject_id=subject_obj.id, is_personal=False).all()
        personal_quizzes = Quiz.query.filter_by(
            subject_id=subject_obj.id, 
            user_id=current_user.id, 
            is_personal=True
        ).all()
        all_quizzes = shared_quizzes + personal_quizzes
    else:
        # Medlemmar ser bara shared quizzes + sina egna personliga
        shared_quizzes = Quiz.query.filter_by(subject_id=subject_obj.id, is_personal=False).all()
        personal_quizzes = Quiz.query.filter_by(
            subject_id=subject_obj.id, 
            user_id=current_user.id, 
            is_personal=True
        ).all()
        all_quizzes = shared_quizzes + personal_quizzes
    
    # Hämta krav dokument OCH konvertera till dictionaries
    krav_docs_objects = KravDocument.query.filter_by(subject_id=subject_obj.id).all()
    krav_docs = [doc.to_dict() for doc in krav_docs_objects]  # Konvertera till dict
    
    # Konvertera quiz-objekt till dictionaries för JSON-serialisering
    quizzes_dict = [quiz.to_dict() for quiz in all_quizzes]
    shared_quizzes_dict = [quiz.to_dict() for quiz in shared_quizzes]
    personal_quizzes_dict = [quiz.to_dict() for quiz in personal_quizzes]
    
    # Skapa context för template
    context = {
        'subject_name': subject_name,
        'subject': subject_obj,
        'quizzes': quizzes_dict,  # Använd dict-versionen för JSON
        'shared_quizzes': shared_quizzes_dict,
        'personal_quizzes': personal_quizzes_dict,
        'krav_docs': krav_docs,  # Nu är detta en lista med dictionaries
        'user_role': user_role,
        'can_create_shared': user_role in ['owner', 'admin'],
        'can_create_personal': True  # Alla kan skapa personliga quizzes
    }
    
    return render_template('subject.html', **context)



def extract_text_from_pdf(file_path):
    """Extrahera text från PDF med fallback till OCR"""
    try:
        text = ''
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()
        
        # Om ingen text hittades, använd OCR
        if not text.strip():
            images = convert_from_path(file_path)
            for image in images:
                text += pytesseract.image_to_string(image)
        
        return text.strip()
    except Exception as e:
        print(f"[ERROR] Failed to extract text from {file_path}: {e}")
        return ""

@app.route('/create-quiz', methods=['GET', 'POST'])
@login_required
def create_quiz():
    """Skapa quiz - nu med stöd för shared subjects och personliga quiz"""
    # Hämta alla subjects som användaren har tillgång till
    all_subjects = current_user.get_all_subjects()
    subject_names = [s.name for s in all_subjects]

    if request.method == 'POST':
        subject_name = request.form.get('subject')
        
        # Kontrollera att användaren har tillgång till detta subject
        subject_obj = Subject.query.filter_by(name=subject_name).first()
        if not subject_obj or not current_user.is_member_of_subject(subject_obj.id):
            flash('You do not have access to this subject', 'error')
            return redirect(url_for('create_quiz'))
        
        # Kontrollera användarens roll för att avgöra om quiz ska vara personlig
        user_role = current_user.get_role_in_subject(subject_obj.id)
        is_personal = user_role not in ['admin', 'owner']  # Medlemmar skapar personliga quiz
        
        # Hämta form data
        uploaded_files = request.files.getlist('data1')
        user_title = request.form.get('quiz_title', '').strip()
        quiz_type = request.form.get('quiz-drop')
        description = request.form.get('quiz-description', '').strip()
        use_docs = bool(request.form.get('use_documents'))
        create_flashcards = bool(request.form.get('create_flashcards', True))

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
        quiz_title = user_title or f"{subject_name} - {quiz_type.replace('-', ' ').title()} - {now}"

        # Handle file uploads and extract content
        saved_files = []
        file_contents = []
        upload_folder = os.path.join('static', 'uploads', str(current_user.id), subject_name)
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
                    text = extract_text_from_pdf(filepath)
                    file_contents.append(text)
                elif ext in ['.txt', '.doc', '.docx']:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        file_contents.append(f.read())
            except Exception as e:
                print(f"[ERROR] Failed to process '{filename}': {e}")

        combined_text = "\n\n".join(file_contents) if file_contents else ''

        # **NYA DELEN: Lägg till krav-dokument om use_documents är aktiverat**
        krav_content = ""
        if use_docs:
            # Hämta alla krav-dokument för detta subject
            krav_documents = KravDocument.query.filter_by(subject_id=subject_obj.id).all()
            
            krav_texts = {}
            for doc in krav_documents:
                if os.path.exists(doc.file_path):
                    try:
                        text_content = extract_text_from_pdf(doc.file_path)
                        if text_content:
                            krav_texts[doc.doc_type] = text_content
                            print(f"[INFO] Loaded {doc.doc_type}: {len(text_content)} characters")
                    except Exception as e:
                        print(f"[ERROR] Failed to process krav document {doc.filename}: {e}")
            
            # Bygg krav-content strängen
            if krav_texts:
                krav_parts = []
                
                if 'kunskapsmal' in krav_texts:
                    krav_parts.append(f"=== KUNSKAPSMÅL ===\n{krav_texts['kunskapsmal']}")
                
                if 'kunskapskrav' in krav_texts:
                    krav_parts.append(f"=== KUNSKAPSKRAV ===\n{krav_texts['kunskapskrav']}")
                
                if 'begrippslista' in krav_texts:
                    krav_parts.append(f"=== BEGRIPPSLISTA ===\n{krav_texts['begrippslista']}")
                
                krav_content = "\n\n".join(krav_parts)
                print(f"[INFO] Combined krav content: {len(krav_content)} characters")

        # Build AI prompt med krav-dokument
        prompt_parts = []
        
        # Grundläggande instruktion
        if desired_count:
            prompt_parts.append(f"You're an AI quiz generator – create a {desired_count}-question {quiz_type.replace('-', ' ')} quiz.")
        else:
            prompt_parts.append(f"You're an AI quiz generator – create an appropriate {quiz_type.replace('-', ' ')} quiz.")
        
        # Lägg till beskrivning om den finns
        if description:
            prompt_parts.append(f"Quiz description: {description}")
        
        # Lägg till krav-dokument först (viktigast för att forma quizzen)
        if krav_content:
            prompt_parts.append("=== CURRICULUM REQUIREMENTS ===")
            prompt_parts.append("Use these curriculum documents as the PRIMARY foundation for your quiz questions:")
            prompt_parts.append(krav_content)
            prompt_parts.append("Questions MUST align with the knowledge goals (kunskapsmål), assessment criteria (kunskapskrav), and include relevant terminology from the concept list (begrippslista).")
        
        # Lägg till uppladdade material som sekundärt
        if combined_text:
            prompt_parts.append("=== ADDITIONAL STUDY MATERIALS ===")
            prompt_parts.append("Use these materials as supporting content:")
            prompt_parts.append(combined_text)
        
        # Slutlig formatering
        if krav_content and combined_text:
            prompt_parts.append("Create questions that integrate both the curriculum requirements and the study materials. Prioritize alignment with the curriculum goals while using the study materials for context and examples.")
        elif krav_content:
            prompt_parts.append("Focus questions on testing the specific knowledge goals and assessment criteria outlined in the curriculum documents.")
        elif combined_text:
            prompt_parts.append("Use the study materials to craft questions testing understanding.")
        
        prompt_parts.append("\nFormat as Q: [Question]\nA: [Answer]")
        
        prompt = "\n\n".join(prompt_parts)

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
            print(f"[ERROR] AI API call failed: {e}")
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
            questions = [{'question': '[Error]', 'answer': 'Could not generate questions. Please try again.'}]

        # Truncate to desired count
        if desired_count and len(questions) > desired_count:
            questions = questions[:desired_count]

        # Spara quiz med is_personal flagga
        new_quiz = Quiz(
            title=quiz_title,
            quiz_type=quiz_type,
            description=description,
            files=saved_files,
            use_documents=use_docs,
            questions=questions,
            subject_name=subject_name,
            subject_id=subject_obj.id,
            user_id=current_user.id,
            is_personal=is_personal
        )
        
        db.session.add(new_quiz)
        db.session.commit()
        
        # Skapa flashcards - för personliga quiz endast för skaparen
        if create_flashcards:
            if is_personal:
                # Endast för skaparen
                create_flashcards_for_user(new_quiz, current_user.id)
            else:
                # För alla medlemmar i subject
                create_flashcards_for_all_members(new_quiz, subject_obj)
        
        quiz_type_text = "personal quiz" if is_personal else "shared quiz"
        success_msg = f'{quiz_type_text.capitalize()} "{quiz_title}" created successfully'
        
        # Lägg till information om krav-dokument om de användes
        if use_docs and krav_content:
            krav_count = len([doc for doc in KravDocument.query.filter_by(subject_id=subject_obj.id).all()])
            success_msg += f" (using {krav_count} curriculum document{'s' if krav_count != 1 else ''})"
        
        flash(success_msg, 'success')
        return redirect(url_for('subject', subject_name=subject_name))

    # GET - visa create quiz form
    events = Event.query.filter_by(user_id=current_user.id).all()
    events_data = [event.to_dict() for event in events]
    return render_template('create-quiz.html', subjects=subject_names, events=events_data)

def serialize_for_template(obj):
    """Hjälpfunktion för att serialisera objekt för templates"""
    if hasattr(obj, 'to_dict'):
        return obj.to_dict()
    elif isinstance(obj, list):
        return [serialize_for_template(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    return obj

# Registrera som en Jinja2 filter
@app.template_filter('serialize')
def serialize_filter(obj):
    return serialize_for_template(obj)


def add_is_personal_column():
    """Migrera befintliga Quiz-poster för att sätta is_personal korrekt"""
    with app.app_context():
        try:
            # Lägg till kolumn om den inte finns
            db.session.execute(db.text("ALTER TABLE quiz ADD COLUMN is_personal BOOLEAN DEFAULT 1"))
            
            # Uppdatera befintliga quiz baserat på användarens roll
            quizzes = Quiz.query.all()
            for quiz in quizzes:
                if quiz.subject_id:
                    subject_obj = Subject.query.get(quiz.subject_id)
                    if subject_obj:
                        # Om quiz-skaparen är ägaren av subject, sätt som shared (false)
                        if quiz.user_id == subject_obj.user_id:
                            quiz.is_personal = False
                        else:
                            quiz.is_personal = True
                    else:
                        quiz.is_personal = True
                else:
                    quiz.is_personal = True
            
            db.session.commit()
            print("Successfully migrated is_personal column")
            
        except Exception as e:
            print(f"Error migrating is_personal column: {e}")
            db.session.rollback()



def create_flashcards_for_all_members(quiz, subject_obj):
    """Skapa flashcards för alla medlemmar i ett subject (endast för shared quizzes)"""
    if not quiz.questions:
        return
        
    # Hämta alla medlemmar (inklusive ägaren)
    members = db.session.query(SubjectMember.user_id).filter_by(subject_id=subject_obj.id).all()
    member_ids = [member.user_id for member in members]
    
    # Lägg till ägaren om den inte redan finns
    if subject_obj.user_id not in member_ids:
        member_ids.append(subject_obj.user_id)
    
    # Skapa flashcards för varje medlem
    for user_id in member_ids:
        create_flashcards_for_user(quiz, user_id)







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

def get_user_quizzes(subject_name=None, include_personal=True):
    """Hämta quizzes för nuvarande användare baserat på deras tillgång"""
    if not current_user.is_authenticated:
        return []
    
    if subject_name:
        # För ett specifikt ämne
        subject_obj = Subject.query.filter_by(name=subject_name).first()
        if not subject_obj or not current_user.is_member_of_subject(subject_obj.id):
            return []
        
        user_role = current_user.get_role_in_subject(subject_obj.id)
        
        # Hämta shared quizzes (alla medlemmar kan se dessa)
        shared_quizzes = Quiz.query.filter_by(subject_id=subject_obj.id, is_personal=False).all()
        
        if include_personal:
            # Lägg till användarens egna personliga quizzes
            personal_quizzes = Quiz.query.filter_by(
                subject_id=subject_obj.id,
                user_id=current_user.id,
                is_personal=True
            ).all()
            return shared_quizzes + personal_quizzes
        else:
            return shared_quizzes
    else:
        # Hämta alla ämnen användaren har tillgång till
        accessible_subjects = current_user.get_all_subjects()
        subject_ids = [subject.id for subject in accessible_subjects]
        
        # Hämta shared quizzes från alla ämnen
        shared_quizzes = Quiz.query.filter(
            Quiz.subject_id.in_(subject_ids),
            Quiz.is_personal == False
        ).all()
        
        if include_personal:
            # Lägg till användarens egna personliga quizzes
            personal_quizzes = Quiz.query.filter(
                Quiz.subject_id.in_(subject_ids),
                Quiz.user_id == current_user.id,
                Quiz.is_personal == True
            ).all()
            return shared_quizzes + personal_quizzes
        else:
            return shared_quizzes






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

# Uppdatera din befintliga add_user_quiz funktion i paste-2.txt


# 5. Uppdatera add_user_quiz funktionen
def add_user_quiz(subject_name, quiz_data):
    """Lägg till nytt quiz för nuvarande användare och skapa flashcards"""
    if not current_user.is_authenticated:
        return False
    
    # Hitta Subject-objektet
    subject_obj = Subject.query.filter_by(name=subject_name).first()
    if not subject_obj:
        return False
    
    # Kontrollera om användaren har tillgång till detta ämne
    if not current_user.is_member_of_subject(subject_obj.id):
        return False
    
    # Avgör om quiz ska vara personlig baserat på användarens roll
    user_role = current_user.get_role_in_subject(subject_obj.id)
    
    # Kontrollera om användaren försöker skapa ett shared quiz utan behörighet
    requested_personal = quiz_data.get('is_personal', True)
    if not requested_personal and user_role not in ['owner', 'admin']:
        # Tvinga till personlig quiz för medlemmar
        is_personal = True
    else:
        is_personal = requested_personal
    
    quiz = Quiz(
        title=quiz_data['title'],
        quiz_type=quiz_data['type'],
        description=quiz_data.get('description', ''),
        subject_name=subject_name,
        subject_id=subject_obj.id,
        use_documents=quiz_data.get('use_documents', False),
        files=quiz_data.get('files', []),
        questions=quiz_data.get('questions', []),
        user_id=current_user.id,
        is_personal=is_personal
    )
    
    try:
        db.session.add(quiz)
        db.session.commit()
        
        # Skapa flashcards baserat på quiz-typ
        if quiz_data.get('questions'):
            if is_personal:
                # Endast för skaparen
                create_flashcards_for_user(quiz, current_user.id)
            else:
                # För alla medlemmar i subject
                create_flashcards_for_all_members(quiz, subject_obj)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to add quiz: {e}")
        db.session.rollback()
        return False







def get_user_flashcards(subject_name=None):
    """Hämta flashcards för nuvarande användare"""
    if not current_user.is_authenticated:
        return []
    
    if subject_name:
        # För ett specifikt ämne
        subject_obj = Subject.query.filter_by(name=subject_name).first()
        if not subject_obj or not current_user.is_member_of_subject(subject_obj.id):
            return []
        
        # Hämta användarens egna flashcards för detta ämne
        flashcards = Flashcard.query.filter_by(
            subject_id=subject_obj.id,
            user_id=current_user.id
        ).all()
        return flashcards
    else:
        # Hämta alla ämnen användaren har tillgång till
        accessible_subjects = current_user.get_all_subjects()
        subject_ids = [subject.id for subject in accessible_subjects]
        
        # Hämta användarens flashcards för alla dessa ämnen
        flashcards = Flashcard.query.filter(
            Flashcard.subject_id.in_(subject_ids),
            Flashcard.user_id == current_user.id
        ).all()
        return flashcards










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

def update_flashcard_rating(flashcard, rating, time_taken):
    """Update flashcard using SuperMemo-2 spaced repetition algorithm"""
    try:
        # Get current values
        ease_factor = flashcard.ease_factor or 2.5
        repetitions = flashcard.repetitions or 0
        prev_interval = flashcard.interval or 0
        
        # Convert rating to quality score (q)
        q = int(rating)
        
        # SuperMemo-2 algorithm
        # 1. Update ease factor
        ease_factor = max(1.3, ease_factor + (0.1 - (4 - q) * (0.08 + (4 - q) * 0.02)))
        
        # 2. Calculate new interval and repetitions
        if q < 3:  # Difficult answer - start over
            repetitions = 0
            interval = 1
        else:  # Good answer
            repetitions += 1
            if repetitions == 1:
                interval = int(round(ease_factor)) if q == 4 else 1
            elif repetitions == 2:
                interval = 6
            else:
                interval = int(round(prev_interval * ease_factor))
        
        # 3. Bonus for super fast perfect answer
        if q == 4 and time_taken < 5:
            interval = max(interval, int(round((prev_interval or 1) * ease_factor * 1.2)))
        
        # 4. Calculate next review date
        next_review_date = datetime.now().date() + timedelta(days=interval)
        
        # 5. Update flashcard
        flashcard.ease_factor = round(ease_factor, 2)
        flashcard.repetitions = repetitions
        flashcard.interval = interval
        flashcard.next_review = next_review_date
        flashcard.rating = q
        flashcard.time_taken = time_taken
        flashcard.updated_at = datetime.utcnow()
        
        print(f"Updated flashcard: {flashcard.question[:50]}... -> Rating: {q}, Next review: {next_review_date}, Interval: {interval} days")
        
    except Exception as e:
        print(f"Error updating flashcard rating: {e}")
        raise

@app.route('/api/flashcards/due')
@login_required
def get_due_flashcards():
    """Get flashcards due for review"""
    try:
        target_date = request.args.get('date')
        if target_date:
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        else:
            target_date = datetime.now().date()
        
        due_flashcards = Flashcard.query.filter(
            Flashcard.user_id == current_user.id,
            db.or_(
                Flashcard.next_review == None,
                Flashcard.next_review <= target_date
            )
        ).all()
        
        flashcards_data = []
        for flashcard in due_flashcards:
            flashcards_data.append({
                'id': flashcard.id,
                'question': flashcard.question,
                'answer': flashcard.answer,
                'subject': flashcard.subject,
                'topic': flashcard.topic,
                'next_review': flashcard.next_review.isoformat() if flashcard.next_review else None,
                'interval': flashcard.interval,
                'repetitions': flashcard.repetitions,
                'ease_factor': flashcard.ease_factor
            })
        
        return jsonify({
            'success': True,
            'flashcards': flashcards_data,
            'count': len(flashcards_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/flashcards_due')
@login_required
def flashcards_due():
    """Show flashcards due for review today"""
    try:
        from flashcard_db_utils import get_due_flashcards, get_flashcard_statistics
        
        # Get flashcards due today
        due_cards = get_due_flashcards()
        
        # Get statistics
        stats = get_flashcard_statistics()
        
        return render_template('flashcards_due.html', 
                             flashcards=due_cards,
                             stats=stats)
        
    except Exception as e:
        print(f"[ERROR] Failed to get due flashcards: {e}")
        flash('Error loading flashcards', 'error')
        return redirect(url_for('dashboard'))





@app.route('/flashcard_statistics')
@login_required
def flashcard_statistics():
    """Show comprehensive flashcard statistics"""
    try:
        from flashcard_db_utils import get_flashcard_statistics, get_review_schedule
        
        stats = get_flashcard_statistics()
        schedule = get_review_schedule(days_ahead=14)
        
        return jsonify({
            'stats': stats,
            'schedule': schedule
        })
        
    except Exception as e:
        print(f"[ERROR] Failed to get flashcard statistics: {e}")
        return jsonify({'error': 'Failed to load statistics'}), 500


@app.route('/api/flashcards/statistics')
@login_required
def get_flashcard_statistics():
    """Get flashcard statistics for the current user"""
    try:
        today = datetime.now().date()
        
        # Total cards
        total_cards = Flashcard.query.filter_by(user_id=current_user.id).count()
        
        # Cards due today
        cards_due_today = Flashcard.query.filter(
            Flashcard.user_id == current_user.id,
            Flashcard.next_review == today
        ).count()
        
        # Overdue cards
        cards_overdue = Flashcard.query.filter(
            Flashcard.user_id == current_user.id,
            Flashcard.next_review < today
        ).count()
        
        # New cards (never reviewed)
        new_cards = Flashcard.query.filter(
            Flashcard.user_id == current_user.id,
            Flashcard.next_review == None
        ).count()
        
        # Cards for upcoming days
        cards_upcoming = total_cards - cards_due_today - cards_overdue - new_cards
        
        return jsonify({
            'success': True,
            'statistics': {
                'total_cards': total_cards,
                'cards_due_today': cards_due_today,
                'cards_overdue': cards_overdue,
                'new_cards': new_cards,
                'cards_upcoming': cards_upcoming
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/flashcards/review')
@login_required
def review_flashcards():
    """Review page for due flashcards"""
    try:
        today = datetime.now().date()
        
        # Get flashcards due for review
        due_flashcards = Flashcard.query.filter(
            Flashcard.user_id == current_user.id,
            db.or_(
                Flashcard.next_review == None,
                Flashcard.next_review <= today
            )
        ).order_by(Flashcard.next_review.asc().nullsfirst()).all()
        
        if not due_flashcards:
            flash('No flashcards are due for review!', 'info')
            return redirect(url_for('index'))
        
        # Prepare questions for the flashcard interface
        questions = []
        for flashcard in due_flashcards:
            questions.append(f"{flashcard.question}|{flashcard.answer}")
        
        # Use the existing flashcard template
        return render_template('flashcards.html',
                             subject_name="Review",
                             quiz_title="Due Cards",
                             questions=questions)
        
    except Exception as e:
        flash(f'Error loading flashcards: {str(e)}', 'error')
        return redirect(url_for('index'))





# Fix the API endpoint URL (you had an extra slash in the route)
@app.route('/api/flashcards/reset/<int:flashcard_id>', methods=['POST'])
@login_required
def reset_flashcard(flashcard_id):
    """Reset a flashcard to default values"""
    try:
        flashcard = Flashcard.query.filter_by(
            id=flashcard_id,
            user_id=current_user.id
        ).first()
        
        if not flashcard:
            return jsonify({'error': 'Flashcard not found'}), 404
        
        # Reset to default values
        flashcard.ease_factor = 2.5
        flashcard.repetitions = 0
        flashcard.interval = 0
        flashcard.next_review = None
        flashcard.rating = None
        flashcard.time_taken = None
        flashcard.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Flashcard reset successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500




def get_due_flashcards():
    """Hämta alla förfallna flashcards för nuvarande användare"""
    if not current_user.is_authenticated:
        return []
    
    today = date.today()  # Fixed: använd date.today() istället för datetime.now().date()
    flashcards = Flashcard.query.filter(
        Flashcard.user_id == current_user.id,
        Flashcard.next_review <= today
    ).all()
    
    return flashcards

def get_flashcard_statistics():
    """Hämta statistik över flashcards för nuvarande användare"""
    if not current_user.is_authenticated:
        return {}
    
    today = date.today()  # Fixed: använd date.today() istället för datetime.now().date()
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
    # Hämta från SQL istället för JSON
    subjects = Subject.query.filter_by(user_id=current_user.id).all()
    total_quizzes = Quiz.query.filter_by(user_id=current_user.id).count()
    
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

@app.route('/logout', methods=['POST'])
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
    # Hämta ämnen från SQL
    subjects = Subject.query.filter_by(user_id=current_user.id).all()
    subject_names = [s.name for s in subjects]
    
    if request.method == 'POST':
        sub = request.form['subject'].strip()
        if sub and sub not in subject_names:
            # Lägg till nytt ämne i SQL
            new_subject = Subject(name=sub, user_id=current_user.id)
            db.session.add(new_subject)
            db.session.commit()
        return redirect(url_for('home'))
    return render_template('index.html', subjects=subject_names)











# Lägg till denna funktion i din Flask-app

from datetime import datetime, timedelta
import re

def cleanup_expired_quizzes():
    """
    Ta bort quiz vars tillhörande provdatum har passerat
    """
    try:
        today = datetime.now().date()
        
        # Hämta alla quiz för alla användare
        all_quizzes = Quiz.query.all()
        deleted_count = 0
        
        for quiz in all_quizzes:
            # Kontrollera om det finns ett associerat event med samma titel/ämne
            associated_events = Event.query.filter_by(
                user_id=quiz.user_id,
                subject=quiz.subject_name
            ).all()
            
            # Kolla om quizets titel matchar något event
            quiz_expired = False
            for event in associated_events:
                # Konvertera event datum till date objekt
                event_date = datetime.strptime(event.date, '%Y-%m-%d').date()
                
                # Om eventet har passerat, markera quiz som förfallen
                if event_date < today:
                    # Kontrollera om quiz-titeln innehåller event-titeln eller vice versa
                    if (event.title.lower() in quiz.title.lower() or 
                        quiz.title.lower() in event.title.lower() or
                        event.test_type.lower() in quiz.title.lower()):
                        quiz_expired = True
                        break
            
            # Alternativt: extrahera datum från quiz-titel om inget event hittas
            if not quiz_expired and not associated_events:
                # Försök extrahera datum från quiz-titel (format: YYYY-MM-DD)
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', quiz.title)
                if date_match:
                    quiz_date = datetime.strptime(date_match.group(1), '%Y-%m-%d').date()
                    if quiz_date < today:
                        quiz_expired = True
            
            # Ta bort quiz om det har gått ut
            if quiz_expired:
                print(f"[CLEANUP] Deleting expired quiz: {quiz.title}")
                
                # Ta bort associerade filer
                files = quiz.files
                if isinstance(files, str):
                    try:
                        files = json.loads(files)
                    except:
                        files = []
                
                if files:
                    for file_path in files:
                        try:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                        except Exception as e:
                            print(f"Warning: Could not delete file {file_path}: {e}")
                
                db.session.delete(quiz)
                deleted_count += 1
        
        db.session.commit()
        print(f"[CLEANUP] Deleted {deleted_count} expired quizzes")
        return deleted_count
        
    except Exception as e:
        print(f"[ERROR] Failed to cleanup expired quizzes: {e}")
        db.session.rollback()
        return 0

def cleanup_on_startup():
    """Kör rensning när appen startar"""
    with app.app_context():
        cleanup_expired_quizzes()



# API endpoint för manuell rensning (endast för admin/debug)
@app.route('/api/cleanup_expired_quizzes', methods=['POST'])
@login_required
def cleanup_expired_quizzes_api():
    """API endpoint för att manuellt rensa förfallna quiz"""
    if not app.debug:
        return jsonify({'error': 'Only available in debug mode'}), 403
    
    try:
        deleted_count = cleanup_expired_quizzes()
        return jsonify({
            'status': 'success',
            'deleted_count': deleted_count,
            'message': f'Deleted {deleted_count} expired quizzes'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def cleanup_expired_quizzes_for_user_subject(user_id, subject_name):
    """
    Rensa förfallna quiz för specifik användare och ämne
    """
    try:
        today = datetime.now().date()
        
        # Hämta quiz för denna användare och ämne
        quizzes = Quiz.query.filter_by(
            user_id=user_id,
            subject_name=subject_name
        ).all()
        
        # Hämta events för denna användare och ämne
        events = Event.query.filter_by(
            user_id=user_id,
            subject=subject_name
        ).all()
        
        deleted_count = 0
        
        for quiz in quizzes:
            quiz_expired = False
            
            # Kontrollera mot events
            for event in events:
                event_date = datetime.strptime(event.date, '%Y-%m-%d').date()
                
                if event_date < today:
                    # Kontrollera om quiz är relaterat till detta event
                    if (event.title.lower() in quiz.title.lower() or 
                        quiz.title.lower() in event.title.lower() or
                        event.test_type.lower() in quiz.title.lower()):
                        quiz_expired = True
                        break
            
            # Alternativt: kontrollera datum i quiz-titel
            if not quiz_expired:
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', quiz.title)
                if date_match:
                    quiz_date = datetime.strptime(date_match.group(1), '%Y-%m-%d').date()
                    if quiz_date < today:
                        quiz_expired = True
            
            # Ta bort quiz om det har gått ut
            if quiz_expired:
                print(f"[CLEANUP] Deleting expired quiz for {subject_name}: {quiz.title}")
                
                # Ta bort associerade filer
                files = quiz.files
                if isinstance(files, str):
                    try:
                        files = json.loads(files)
                    except:
                        files = []
                
                if files:
                    for file_path in files:
                        try:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                        except Exception as e:
                            print(f"Warning: Could not delete file {file_path}: {e}")
                
                db.session.delete(quiz)
                deleted_count += 1
        
        if deleted_count > 0:
            db.session.commit()
            print(f"[CLEANUP] Deleted {deleted_count} expired quizzes for {subject_name}")
        
        return deleted_count
        
    except Exception as e:
        print(f"[ERROR] Failed to cleanup expired quizzes for {subject_name}: {e}")
        db.session.rollback()
        return 0

# Schemalagd rensning (valfritt - kör dagligen)
def schedule_daily_cleanup():
    """
    Schemalagd daglig rensning av förfallna quiz
    Kan köras med APScheduler eller liknande
    """
    import threading
    import time
    
    def daily_cleanup():
        while True:
            try:
                # Vänta 24 timmar
                time.sleep(24 * 60 * 60)  # 24 timmar i sekunder
                
                with app.app_context():
                    cleanup_expired_quizzes()
                    
            except Exception as e:
                print(f"[ERROR] Daily cleanup failed: {e}")
    
    # Starta cleanup-tråd
    cleanup_thread = threading.Thread(target=daily_cleanup, daemon=True)
    cleanup_thread.start()

@app.route('/delete_subject', methods=['POST'])
@login_required
def delete_subject():
    subject_to_delete = request.form.get('subject')
    if subject_to_delete:
        # Hämta subject-objektet
        subject_obj = Subject.query.filter_by(user_id=current_user.id, name=subject_to_delete).first()
        if subject_obj:
            try:
                # Ta bort alla relaterade krav_documents först
                KravDocument.query.filter_by(subject_id=subject_obj.id).delete()
                
                # Ta bort alla relaterade shared_files
                SharedFile.query.filter_by(subject_id=subject_obj.id).delete()
                
                # Ta bort subject-medlemskap
                SubjectMember.query.filter_by(subject_id=subject_obj.id).delete()
                
                # Nu kan vi säkert ta bort subject (quizzes och flashcards tas bort automatiskt via cascade)
                db.session.delete(subject_obj)
                db.session.commit()
                
                # Ta även bort fysiska filer om de finns
                import os
                krav_dir = f"static/uploads/krav/{current_user.id}/{subject_to_delete}"
                if os.path.exists(krav_dir):
                    import shutil
                    shutil.rmtree(krav_dir)
                
                flash(f'Ämnet "{subject_to_delete}" har tagits bort.', 'success')
                
            except Exception as e:
                db.session.rollback()
                flash(f'Ett fel uppstod vid borttagning av ämnet: {str(e)}', 'error')
                print(f"Error deleting subject: {e}")
    
    return redirect(url_for('home'))

@app.route('/quiz/<subject_name>/<path:quiz_title>')
@login_required
def quiz_route(subject_name, quiz_title):
    """Route to start a flashcard quiz - nu med stöd för shared subjects"""
    try:
        # Decode URL parameters
        subject_name = urllib.parse.unquote(subject_name)
        quiz_title = urllib.parse.unquote(quiz_title)
        
        print(f"[DEBUG] Looking for quiz: subject='{subject_name}', title='{quiz_title}'")
        
        # Hitta subject först
        subject_obj = Subject.query.filter_by(name=subject_name).first()
        if not subject_obj:
            flash('Subject not found', 'error')
            return redirect(url_for('index'))
        
        # Kontrollera om användaren har tillgång till detta subject
        if not current_user.is_member_of_subject(subject_obj.id):
            flash('You do not have access to this subject', 'error')
            return redirect(url_for('index'))
        
        # Hitta quiz baserat på subject_id och title (inte user_id)
        quiz = Quiz.query.filter_by(
            subject_id=subject_obj.id,
            title=quiz_title
        ).first()
        
        if not quiz:
            print(f"[DEBUG] Quiz not found. Available quizzes:")
            all_quizzes = Quiz.query.filter_by(subject_id=subject_obj.id).all()
            for q in all_quizzes:
                print(f"  - Subject: '{q.subject_name}', Title: '{q.title}'")
            
            flash(f'Quiz "{quiz_title}" not found', 'error')
            return redirect(url_for('subject', subject_name=subject_name))
        
        # Get questions from the quiz
        questions = quiz.questions or []
        if isinstance(questions, str):
            try:
                questions = json.loads(questions)
            except:
                questions = []
        
        print(f"[DEBUG] Found {len(questions)} questions in quiz")
        
        # Filter out error questions and format for flashcard template
        valid_questions = []
        for q in questions:
            if (q.get('question') and 
                q.get('answer') and 
                not q['question'].startswith("[Error]")):
                # Format as "question|answer" for the flashcard template
                valid_questions.append(f"{q['question']}|{q['answer']}")
        
        print(f"[DEBUG] {len(valid_questions)} valid questions after filtering")
        
        if not valid_questions:
            flash('No valid questions found in this quiz', 'error')
            return redirect(url_for('subject', subject_name=subject_name))
        
        # Skapa flashcards för den aktuella användaren om de inte finns
        created_count = create_flashcards_for_user(quiz, valid_questions, current_user.id)
        if created_count > 0:
            flash(f'Created {created_count} new flashcards', 'success')
        
        return render_template('flashcards.html',
                             subject_name=subject_name,
                             quiz_title=quiz_title,
                             questions=valid_questions,
                             is_spaced_repetition=True)
        
    except Exception as e:
        print(f"[ERROR] Quiz route failed: {e}")
        import traceback
        traceback.print_exc()
        flash('Error loading quiz', 'error')
        return redirect(url_for('home'))


# 4. Lägg till hjälpfunktion för att skapa flashcards för en enskild användare
# Uppdaterad create_flashcards_for_user funktion
def create_flashcards_for_user(quiz, user_id, subject_obj=None):
    """Skapa flashcards för en specifik användare"""
    try:
        # Hämta questions direkt från quiz-objektet
        questions = quiz.questions
        if not questions:
            print(f"[INFO] No questions found in quiz {quiz.title}")
            return 0

        created_count = 0
        for q_data in questions:
            # Hantera både dict-format och sträng-format
            if isinstance(q_data, dict):
                question_text = q_data.get('question', '')
                answer_text = q_data.get('answer', '')
            else:
                # Om det är en sträng i "question|answer" format
                if '|' in str(q_data):
                    question_text, answer_text = str(q_data).split('|', 1)
                    question_text = question_text.strip()
                    answer_text = answer_text.strip()
                else:
                    continue
            
            if not question_text or not answer_text:
                continue
                
            # Kontrollera om flashcard redan finns för denna användare
            existing = Flashcard.query.filter(
                Flashcard.user_id == user_id,
                Flashcard.question == question_text,
                Flashcard.subject_id == quiz.subject_id
            ).first()
            
            if not existing:
                flashcard = Flashcard(
                    question=question_text,
                    answer=answer_text,
                    subject=quiz.subject_name,
                    subject_id=quiz.subject_id,
                    topic=quiz.title,
                    user_id=user_id,
                    ease_factor=2.5,
                    interval=0,
                    repetitions=0,
                    next_review=None
                )
                db.session.add(flashcard)
                created_count += 1
                
        db.session.commit()
        print(f"[INFO] Created {created_count} flashcards for user {user_id}")
        return created_count
        
    except Exception as e:
        print(f"[ERROR] Failed to create flashcards for user: {e}")
        db.session.rollback()
        return 0


# Uppdaterad add_user_quiz funktion
def add_user_quiz(subject_name, quiz_data):
    """Lägg till nytt quiz för nuvarande användare och skapa flashcards"""
    if not current_user.is_authenticated:
        return False
        
    # Hitta Subject-objektet
    subject_obj = Subject.query.filter_by(name=subject_name).first()
    if not subject_obj:
        return False
        
    # Kontrollera om användaren har tillgång till detta ämne
    if not current_user.is_member_of_subject(subject_obj.id):
        return False
        
    # Avgör om quiz ska vara personlig baserat på användarens roll
    user_role = current_user.get_role_in_subject(subject_obj.id)
    
    # Kontrollera om användaren försöker skapa ett shared quiz utan behörighet
    requested_personal = quiz_data.get('is_personal', True)
    if not requested_personal and user_role not in ['owner', 'admin']:
        # Tvinga till personlig quiz för medlemmar
        is_personal = True
    else:
        is_personal = requested_personal
        
    quiz = Quiz(
        title=quiz_data['title'],
        quiz_type=quiz_data['type'],
        description=quiz_data.get('description', ''),
        subject_name=subject_name,
        subject_id=subject_obj.id,
        use_documents=quiz_data.get('use_documents', False),
        files=quiz_data.get('files', []),
        questions=quiz_data.get('questions', []),
        user_id=current_user.id,
        is_personal=is_personal
    )
    
    try:
        db.session.add(quiz)
        db.session.commit()
        
        # Skapa flashcards baserat på quiz-typ
        if quiz_data.get('questions'):
            if is_personal:
                # Endast för skaparen
                create_flashcards_for_user(quiz, current_user.id)
            else:
                # För alla medlemmar i subject
                create_flashcards_for_all_members(quiz, subject_obj)
                
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to add quiz: {e}")
        db.session.rollback()
        return False

@app.route('/flashcards/<subject_name>/<path:quiz_title>')
@login_required  
def flashcards_route(subject_name, quiz_title):
    """Alternative route for flashcards - redirects to main quiz route"""
    return redirect(url_for('quiz_route', subject_name=subject_name, quiz_title=quiz_title))


# Add this import at the top of your file if not already present
import urllib.parse

# Also add this route to handle the specific URL pattern from your subject.html template
@app.route('/subject/<subject_name>/quiz/<int:quiz_index>')
@login_required
def start_quiz(subject_name, quiz_index):
    """Start quiz från subject page - nu med stöd för shared subjects"""
    try:
        # Hitta subject först
        subject_obj = Subject.query.filter_by(name=subject_name).first()
        if not subject_obj:
            flash('Subject not found', 'error')
            return redirect(url_for('index'))
        
        # Kontrollera om användaren har tillgång till detta subject
        if not current_user.is_member_of_subject(subject_obj.id):
            flash('You do not have access to this subject', 'error')
            return redirect(url_for('index'))
        
        # Hämta quiz baserat på subject_id och index (inte user_id)
        quiz = (Quiz.query
                .filter_by(subject_id=subject_obj.id)
                .order_by(Quiz.created_at.desc())
                .offset(quiz_index)
                .first())

        if not quiz:
            flash('Quiz not found', 'error')
            return redirect(url_for('subject', subject_name=subject_name))

        # quiz.questions är lagrat som list objekt (inte JSON-sträng)
        raw_questions = quiz.questions or []
        if isinstance(raw_questions, str):
            try:
                raw_questions = json.loads(raw_questions)
            except ValueError:
                raw_questions = []

        # Bygg en lista ["Fråga|Svar", ...]
        questions = []
        for q in raw_questions:
            question_text = q.get('question', '').strip()
            answer_text = q.get('answer', '').strip()
            if question_text:
                questions.append(f"{question_text}|{answer_text}")

        if not questions:
            flash('No valid questions in this quiz', 'error')
            return redirect(url_for('subject', subject_name=subject_name))

        # Skapa flashcards för den aktuella användaren
        created_count = create_flashcards_for_user(quiz, questions, current_user.id)
        if created_count > 0:
            flash(f'Created {created_count} new flashcards', 'success')

        # Rendera flashcards.html med rätt parametrar
        return render_template('flashcards.html',
                               subject_name=subject_name,
                               quiz_title=quiz.title,
                               questions=questions,
                               is_spaced_repetition=True)
        
    except Exception as e:
        print(f"[ERROR] Start quiz failed: {e}")
        flash('Error loading quiz', 'error')
        return redirect(url_for('subject', subject_name=subject_name))




@app.route('/subject/<subject_name>/quiz/<int:quiz_index>/flashcards')
@login_required
def start_flashcard_quiz(subject_name, quiz_index):
    """Start flashcard quiz from subject page - nu med stöd för shared subjects"""
    try:
        # Hitta subject först
        subject_obj = Subject.query.filter_by(name=subject_name).first()
        if not subject_obj:
            flash('Subject not found', 'error')
            return redirect(url_for('index'))
        
        # Kontrollera om användaren har tillgång till detta subject
        if not current_user.is_member_of_subject(subject_obj.id):
            flash('You do not have access to this subject', 'error')
            return redirect(url_for('index'))
        
        # Get the quiz by index från subject_id
        quiz = (Quiz.query
                .filter_by(subject_id=subject_obj.id)
                .order_by(Quiz.created_at.desc())
                .offset(quiz_index)
                .first())
        
        if not quiz:
            flash('Quiz not found', 'error')
            return redirect(url_for('subject', subject_name=subject_name))
        
        # Redirect to the main quiz route using the quiz title
        return redirect(url_for('quiz_route', 
                               subject_name=subject_name, 
                               quiz_title=quiz.title))
        
    except Exception as e:
        print(f"[ERROR] Start flashcard quiz failed: {e}")
        flash('Error loading quiz', 'error')
        return redirect(url_for('subject', subject_name=subject_name))




def create_flashcards_from_quiz(subject_name_or_quiz, quiz_title_or_questions, questions=None):
    """Skapa flashcards från quiz-frågor - stöder båda anropsmetoderna"""
    if not current_user.is_authenticated:
        return False
    
    # Kontrollera vilken anropsmetod som används
    if questions is None:
        # Anropas som create_flashcards_from_quiz(quiz, questions)
        quiz = subject_name_or_quiz
        questions = quiz_title_or_questions
        return create_flashcards_for_user(quiz, questions, current_user.id)
    else:
        # Anropas som create_flashcards_from_quiz(subject_name, quiz_title, questions)
        subject_name = subject_name_or_quiz
        quiz_title = quiz_title_or_questions
        
        # Hitta subject
        subject_obj = Subject.query.filter_by(name=subject_name).first()
        if not subject_obj:
            return 0
        
        # Hitta quiz
        quiz = Quiz.query.filter_by(subject_id=subject_obj.id, title=quiz_title).first()
        if not quiz:
            return 0
        
        return create_flashcards_for_user(quiz, questions, current_user.id)


@app.route('/api/due_flashcards_today')
@login_required
def get_due_flashcards_today():
    """API endpoint för att få flashcards som ska repeteras idag"""
    try:
        today = datetime.now().date()
        
        # Hämta alla flashcards som ska repeteras idag eller tidigare
        due_flashcards = Flashcard.query.filter(
            Flashcard.user_id == current_user.id,
            db.or_(
                Flashcard.next_review <= today,
                Flashcard.next_review == None  # Nya kort
            )
        ).all()
        
        # Gruppera efter ämne och topic
        grouped = {}
        for flashcard in due_flashcards:
            key = f"{flashcard.subject}#{flashcard.topic}"
            if key not in grouped:
                grouped[key] = {
                    'subject': flashcard.subject,
                    'topic': flashcard.topic,
                    'count': 0,
                    'flashcards': []
                }
            grouped[key]['count'] += 1
            grouped[key]['flashcards'].append({
                'id': flashcard.id,
                'question': flashcard.question,
                'next_review': flashcard.next_review.isoformat() if flashcard.next_review else None,
                'status': 'new' if flashcard.next_review is None else ('overdue' if flashcard.next_review < today else 'due')
            })
        
        return jsonify({
            'total_count': len(due_flashcards),
            'groups': list(grouped.values())
        })
        
    except Exception as e:
        print(f"[ERROR] Failed to get due flashcards: {e}")
        return jsonify({'error': 'Failed to get due flashcards'}), 500



@app.route('/subject/<subject_name>/delete_quiz/<int:quiz_index>', methods=['POST'])
@login_required
def delete_quiz(subject_name, quiz_index):
    try:
        # Hämta subject
        subject_obj = Subject.query.filter_by(name=subject_name).first()
        if not subject_obj:
            flash("Subject not found.", "error")
            return redirect(url_for('index'))

        # Kolla att användaren är medlem eller ägare
        if not current_user.is_member_of_subject(subject_obj.id) and current_user.id != subject_obj.creator_id:
            flash('Du har inte tillgång till detta ämne', 'error')
            return redirect(url_for('index'))

        # Hämta quiz via subject och offset
        quiz_to_delete = Quiz.query.filter_by(subject_id=subject_obj.id).offset(quiz_index).first()

        if not quiz_to_delete:
            flash("Quiz not found.", "error")
            return redirect(url_for('subject', subject_name=subject_name))

        # Säkerhetskontroll: Är användaren skapare?
        if quiz_to_delete.user_id != current_user.id:
            flash("Du kan bara ta bort dina egna quiz.", "error")
            return redirect(url_for('subject', subject_name=subject_name))

        # Ta bort associerade flashcards INNAN vi tar bort quiz
        delete_flashcards_for_quiz(quiz_to_delete)

        # Ta bort associerade filer om de finns
        files = quiz_to_delete.files
        if isinstance(files, str):
            try:
                files = json.loads(files)
            except:
                files = []
        
        if files:
            for file_path in files:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f"Warning: Could not delete file {file_path}: {e}")

        # OK – ta bort quiz
        quiz_title = quiz_to_delete.title
        db.session.delete(quiz_to_delete)
        db.session.commit()
        flash(f"Quiz '{quiz_title}' borttaget.", "success")

    except Exception as e:
        print(f"[ERROR] Failed to delete quiz: {e}")
        flash("Ett fel uppstod vid borttagning.", "error")
        db.session.rollback()

    return redirect(url_for('subject', subject_name=subject_name))




@app.route('/subject/<subject_name>/flashcards')
@login_required
def subject_flashcards(subject_name):
    """Show all flashcards for a specific subject with their review status"""
    try:
        from flashcard_db_utils import get_flashcards_by_subject
        
        flashcards = get_flashcards_by_subject(subject_name)
        today = datetime.now().date()
        
        # Categorize flashcards
        due_today = []
        overdue = []
        upcoming = []
        new_cards = []
        
        for card in flashcards:
            if card.next_review is None:
                new_cards.append(card)
            elif card.next_review <= today:
                if card.next_review == today:
                    due_today.append(card)
                else:
                    overdue.append(card)
            else:
                upcoming.append(card)
        
        return render_template('subject_flashcards.html',
                             subject_name=subject_name,
                             due_today=due_today,
                             overdue=overdue,
                             upcoming=upcoming,
                             new_cards=new_cards)
        
    except Exception as e:
        print(f"[ERROR] Failed to get subject flashcards: {e}")
        flash('Error loading flashcards', 'error')
        return redirect(url_for('subject', subject_name=subject_name))



@app.route('/submit_ratings', methods=['POST'])
@login_required
def submit_ratings():
    """Handle quiz completion and update flashcard ratings with spaced repetition"""
    try:
        data = request.get_json()
        subject = data.get('subject')
        quiz_title = data.get('quiz_title')  
        responses = data.get('responses', [])
        is_spaced_repetition = data.get('is_spaced_repetition', False)
        
        updated_count = 0
        
        for response in responses:
            question_text = response.get('question')
            rating = int(response.get('rating', 3))
            time_taken = response.get('time_taken', 0)
            
            # Hitta flashcard baserat på fråga och ämne
            flashcard = Flashcard.query.filter(
                Flashcard.user_id == current_user.id,
                Flashcard.question == question_text,
                Flashcard.subject == subject
            ).first()
            
            if flashcard:
                # Uppdatera med spaced repetition algoritm
                if is_spaced_repetition:
                    update_flashcard_with_spaced_repetition(flashcard, rating, time_taken)
                else:
                    # För vanliga quiz, skapa spaced repetition schema
                    update_flashcard_with_spaced_repetition(flashcard, rating, time_taken)
                updated_count += 1
            else:
                print(f"[WARNING] Flashcard not found for question: {question_text[:50]}...")
        
        if updated_count > 0:
            db.session.commit()
            
        return jsonify({
            'status': 'success',
            'updated_count': updated_count,
            'resolved_subject': subject,
            'resolved_topic': quiz_title.split(' - ')[0] if ' - ' in quiz_title else quiz_title,
            'is_spaced_repetition': is_spaced_repetition
        })
        
    except Exception as e:
        print(f"[ERROR] Failed to submit ratings: {e}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500




def update_flashcard_with_spaced_repetition(flashcard, rating, time_taken):
    """
    Uppdatera flashcard med spaced repetition algoritm (SM-2)
    Rating: 1-5 (1=mycket svår, 5=mycket lätt)
    """
    from datetime import datetime, timedelta
    
    # Spara rating och tid
    flashcard.rating = rating
    flashcard.time_taken = time_taken
    flashcard.updated_at = datetime.utcnow()
    
    # SM-2 algoritm
    if rating < 3:
        # Fel svar - återställ repetitioner
        flashcard.repetitions = 0
        flashcard.interval = 1
    else:
        # Rätt svar
        if flashcard.repetitions == 0:
            flashcard.interval = 1
        elif flashcard.repetitions == 1:
            flashcard.interval = 6
        else:
            flashcard.interval = round(flashcard.interval * flashcard.ease_factor)
        
        flashcard.repetitions += 1
    
    # Uppdatera ease factor
    flashcard.ease_factor = max(1.3, flashcard.ease_factor + (0.1 - (5 - rating) * (0.08 + (5 - rating) * 0.02)))
    
    # Sätt nästa review datum
    flashcard.next_review = datetime.now().date() + timedelta(days=flashcard.interval)
    
    print(f"[SPACED_REP] Updated flashcard: rating={rating}, interval={flashcard.interval}, ease={flashcard.ease_factor:.2f}, next={flashcard.next_review}")


def update_flashcard_with_spaced_repetition(flashcard, rating, time_taken):
    """
    Uppdatera flashcard med spaced repetition algoritm (SM-2)
    Rating: 1-5 (1=mycket svår, 5=mycket lätt)
    """
    from datetime import datetime, timedelta
    
    # Spara rating och tid
    flashcard.rating = rating
    flashcard.time_taken = time_taken
    flashcard.updated_at = datetime.utcnow()
    
    # SM-2 algoritm
    if rating < 3:
        # Fel svar - återställ repetitioner
        flashcard.repetitions = 0
        flashcard.interval = 1
    else:
        # Rätt svar
        if flashcard.repetitions == 0:
            flashcard.interval = 1
        elif flashcard.repetitions == 1:
            flashcard.interval = 6
        else:
            flashcard.interval = round(flashcard.interval * flashcard.ease_factor)
        
        flashcard.repetitions += 1
    
    # Uppdatera ease factor
    flashcard.ease_factor = max(1.3, flashcard.ease_factor + (0.1 - (5 - rating) * (0.08 + (5 - rating) * 0.02)))
    
    # Sätt nästa review datum
    flashcard.next_review = datetime.now().date() + timedelta(days=flashcard.interval)
    
    print(f"[SPACED_REP] Updated flashcard: rating={rating}, interval={flashcard.interval}, ease={flashcard.ease_factor:.2f}, next={flashcard.next_review}")

def update_flashcard_rating(flashcard, rating, time_taken):
    """
    Uppdatera flashcard utan spaced repetition (gamla metoden)
    """
    flashcard.rating = rating
    flashcard.time_taken = time_taken
    flashcard.updated_at = datetime.utcnow()


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


# Utility route for debugging
@app.route('/debug_flashcard/<int:flashcard_id>')
@login_required
def debug_flashcard(flashcard_id):
    """Debug route to see flashcard spaced repetition data"""
    try:
        flashcard = Flashcard.query.filter_by(
            id=flashcard_id,
            user_id=current_user.id
        ).first()
        
        if not flashcard:
            return jsonify({'error': 'Flashcard not found'}), 404
        
        return jsonify({
            'id': flashcard.id,
            'question': flashcard.question[:100] + '...',
            'subject': flashcard.subject,
            'topic': flashcard.topic,
            'ease_factor': flashcard.ease_factor,
            'interval': flashcard.interval,
            'repetitions': flashcard.repetitions,
            'next_review': flashcard.next_review.isoformat() if flashcard.next_review else None,
            'rating': flashcard.rating,
            'time_taken': flashcard.time_taken,
            'created_at': flashcard.created_at.isoformat(),
            'updated_at': flashcard.updated_at.isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
        
        # Hitta och återställ flashcard i SQL-databasen
        flashcard = Flashcard.query.filter_by(
            user_id=current_user.id,
            subject=subject,
            topic=quiz_title,
            question=question
        ).first()
        
        if flashcard:
            flashcard.ease_factor = 2.5
            flashcard.interval = 0
            flashcard.repetitions = 0
            flashcard.next_review = datetime.now().date()
            flashcard.rating = None
            flashcard.time_taken = None
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Question reset'})
        else:
            return jsonify({'status': 'error', 'message': 'Question not found'}), 404
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to reset question'}), 500

@app.route('/api/events', methods=['GET'])
@login_required
def get_events():
    try:
        # Hämta events som användaren har skapat
        owned_events = Event.query.filter_by(user_id=current_user.id).all()
        
        # Hämta shared events från subjects som användaren är medlem i
        shared_events = db.session.query(Event).join(Subject).join(SubjectMember).filter(
            SubjectMember.user_id == current_user.id,
            Event.is_shared == True,
            Event.user_id != current_user.id  # Exkludera egna events
        ).all()
        
        # Kombinera alla events
        all_events = owned_events + shared_events
        
        return jsonify([event.to_dict() for event in all_events])
    except Exception as e:
        print(f"Error fetching events: {e}")
        return jsonify({'error': 'Failed to fetch events'}), 500


@app.route('/api/user_subjects', methods=['GET'])
@login_required
def get_user_subjects():
    """Hämta alla subjects som användaren har tillgång till och deras roll"""
    try:
        user_subjects = []
        
        # Hämta ägda subjects
        owned_subjects = Subject.query.filter_by(user_id=current_user.id).all()
        for subject in owned_subjects:
            user_subjects.append({
                'id': subject.id,
                'name': subject.name,
                'user_role': 'owner'
            })
        
        # Hämta subjects som användaren är medlem i
        member_subjects = db.session.query(Subject).join(SubjectMember).filter(
            SubjectMember.user_id == current_user.id
        ).all()
        
        for subject in member_subjects:
            user_subjects.append({
                'id': subject.id,
                'name': subject.name,
                'user_role': 'member'
            })
        
        return jsonify(user_subjects)
        
    except Exception as e:
        print(f"Error fetching user subjects: {e}")
        return jsonify({'error': 'Failed to fetch user subjects'}), 500



# Uppdaterad API route för att skapa events
@app.route('/api/events', methods=['POST'])
@login_required
def create_event():
    try:
        data = request.get_json()
        
        # Validera required fields
        required_fields = ['date', 'subject', 'testType', 'title']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Hitta subject_id baserat på subject name
        subject = Subject.query.filter_by(name=data['subject']).first()
        if not subject:
            return jsonify({'error': 'Subject not found'}), 404
        
        # Kontrollera om användaren har rätt att skapa events för detta subject
        # Endast ägare kan skapa events
        if subject.user_id != current_user.id:
            return jsonify({'error': 'You can only create events for subjects you own'}), 403
        
        # Skapa eventet
        event = Event(
            date=data['date'],
            subject=data['subject'],
            subject_id=subject.id,  # Spara subject_id
            test_type=data['testType'],
            title=data['title'],
            description=data.get('description', ''),
            user_id=current_user.id,
            is_shared=data.get('share_with_members', False)
        )
        
        db.session.add(event)
        db.session.commit()
        
        message = 'Event created successfully'
        if event.is_shared:
            message += ' and shared with all members'
        
        return jsonify({
            'status': 'success',
            'message': message,
            'event': event.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating event: {e}")
        return jsonify({'error': 'Failed to create event'}), 500

@app.route('/api/events/<int:event_id>/share', methods=['POST'])
@login_required
def toggle_event_sharing(event_id):
    try:
        event = Event.query.get_or_404(event_id)
        
        # Kontrollera om användaren har rätt att ändra sharing
        # Användaren kan ändra om de är skaparen ELLER ägaren av subjektet
        can_modify = (event.user_id == current_user.id)
        
        if event.subject_id:
            subject = Subject.query.get(event.subject_id)
            if subject and subject.user_id == current_user.id:
                can_modify = True
        
        if not can_modify:
            return jsonify({'error': 'You do not have permission to modify this event'}), 403
        
        # Toggle sharing status
        event.is_shared = not event.is_shared
        db.session.commit()
        
        message = 'Event is now shared with all members' if event.is_shared else 'Event is now private'
        
        return jsonify({
            'status': 'success',
            'message': message,
            'is_shared': event.is_shared
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error toggling event sharing: {e}")
        return jsonify({'error': 'Failed to update sharing settings'}), 500


# Hjälpfunktion för att migrera befintliga events
def migrate_events():
    """Migrera befintliga events för att lägga till subject_id och is_shared"""
    try:
        events_without_subject_id = Event.query.filter_by(subject_id=None).all()
        
        for event in events_without_subject_id:
            # Hitta subject baserat på namn
            subject = Subject.query.filter_by(name=event.subject).first()
            if subject:
                event.subject_id = subject.id
                # Sätt is_shared till False för befintliga events
                if not hasattr(event, 'is_shared') or event.is_shared is None:
                    event.is_shared = False
        
        db.session.commit()
        print(f"Migrated {len(events_without_subject_id)} events")
        
    except Exception as e:
        print(f"Error migrating events: {e}")
        db.session.rollback()

@app.route('/api/events/<int:event_id>', methods=['DELETE'])
@login_required
def delete_event(event_id):
    try:
        event = Event.query.get_or_404(event_id)
        
        # Kontrollera om användaren har rätt att ta bort eventet
        # Användaren kan ta bort om de är skaparen ELLER ägaren av subjektet
        can_delete = (event.user_id == current_user.id)
        
        if event.subject_id:
            subject = Subject.query.get(event.subject_id)
            if subject and subject.user_id == current_user.id:
                can_delete = True
        
        if not can_delete:
            return jsonify({'error': 'You do not have permission to delete this event'}), 403
        
        db.session.delete(event)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Event deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting event: {e}")
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





@app.route('/api/quizzes/<subject_name>')
@login_required
def api_get_quizzes(subject_name):
    """API för att hämta quizzes för ett subject"""
    subject_obj = Subject.query.filter_by(name=subject_name).first()
    if not subject_obj or not current_user.is_member_of_subject(subject_obj.id):
        return jsonify({'error': 'Access denied'}), 403
    
    user_role = current_user.get_role_in_subject(subject_obj.id)
    
    # Hämta quizzes baserat på användarens roll
    if user_role in ['owner', 'admin']:
        subject_quizzes = Quiz.query.filter_by(subject_id=subject_obj.id, is_personal=False).all()
        personal_quizzes = Quiz.query.filter_by(subject_id=subject_obj.id, user_id=current_user.id, is_personal=True).all()
        all_quizzes = subject_quizzes + personal_quizzes
    else:
        subject_quizzes = Quiz.query.filter_by(subject_id=subject_obj.id, is_personal=False).all()
        personal_quizzes = Quiz.query.filter_by(subject_id=subject_obj.id, user_id=current_user.id, is_personal=True).all()
        all_quizzes = subject_quizzes + personal_quizzes
    
    quizzes_data = []
    for quiz in all_quizzes:
        quizzes_data.append({
            'id': quiz.id,
            'title': quiz.title,
            'quiz_type': quiz.quiz_type,
            'description': quiz.description,
            'is_personal': quiz.is_personal,
            'created_at': quiz.created_at.isoformat() if quiz.created_at else None,
            'user_id': quiz.user_id,
            'can_delete': quiz.user_id == current_user.id or user_role in ['owner', 'admin']
        })
    
    return jsonify(quizzes_data)



@app.route('/api/quiz/<int:quiz_id>', methods=['DELETE'])
@login_required
def delete_quiz_api(quiz_id):
    """API endpoint för att ta bort ett quiz via ID"""
    try:
        quiz = Quiz.query.filter_by(
            id=quiz_id,
            user_id=current_user.id
        ).first()
        
        if not quiz:
            return jsonify({'status': 'error', 'message': 'Quiz not found'}), 404
        
        # Ta bort associerade flashcards INNAN vi tar bort quiz
        delete_flashcards_for_quiz(quiz)
        
        # Ta bort associerade filer om de finns
        files = quiz.files
        if isinstance(files, str):
            try:
                files = json.loads(files)
            except:
                files = []
        
        if files:
            for file_path in files:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f"Warning: Could not delete file {file_path}: {e}")
        
        quiz_title = quiz.title
        db.session.delete(quiz)
        db.session.commit()
        
        return jsonify({
            'status': 'success', 
            'message': f'Quiz "{quiz_title}" has been deleted'
        })
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Failed to delete quiz: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


def delete_flashcards_for_quiz(quiz):
    """Ta bort alla flashcards som skapats från ett specifikt quiz"""
    try:
        if not quiz.questions:
            return 0
        
        deleted_count = 0
        
        # Om det är ett personligt quiz - ta bara bort för skaparen
        if quiz.is_personal:
            for q_data in quiz.questions:
                # Hantera både dict-format och sträng-format
                if isinstance(q_data, dict):
                    question_text = q_data.get('question', '')
                elif isinstance(q_data, str) and '|' in q_data:
                    question_text = q_data.split('|', 1)[0].strip()
                else:
                    continue
                
                if question_text:
                    # Ta bort flashcard för quiz-skaparen
                    flashcards_to_delete = Flashcard.query.filter(
                        Flashcard.user_id == quiz.user_id,
                        Flashcard.question == question_text,
                        Flashcard.subject_id == quiz.subject_id,
                        Flashcard.topic == quiz.title
                    ).all()
                    
                    for flashcard in flashcards_to_delete:
                        db.session.delete(flashcard)
                        deleted_count += 1
        
        # Om det är ett delat quiz - ta bort för alla medlemmar
        else:
            subject_obj = Subject.query.get(quiz.subject_id)
            if subject_obj:
                # Hämta alla medlemmar
                members = db.session.query(SubjectMember.user_id).filter_by(subject_id=subject_obj.id).all()
                member_ids = [member.user_id for member in members]
                
                # Lägg till ägaren om den inte redan finns
                if subject_obj.user_id not in member_ids:
                    member_ids.append(subject_obj.user_id)
                
                # Ta bort flashcards för alla medlemmar
                for user_id in member_ids:
                    for q_data in quiz.questions:
                        # Hantera både dict-format och sträng-format
                        if isinstance(q_data, dict):
                            question_text = q_data.get('question', '')
                        elif isinstance(q_data, str) and '|' in q_data:
                            question_text = q_data.split('|', 1)[0].strip()
                        else:
                            continue
                        
                        if question_text:
                            flashcards_to_delete = Flashcard.query.filter(
                                Flashcard.user_id == user_id,
                                Flashcard.question == question_text,
                                Flashcard.subject_id == quiz.subject_id,
                                Flashcard.topic == quiz.title
                            ).all()
                            
                            for flashcard in flashcards_to_delete:
                                db.session.delete(flashcard)
                                deleted_count += 1
        
        print(f"[INFO] Deleted {deleted_count} flashcards for quiz '{quiz.title}'")
        return deleted_count
        
    except Exception as e:
        print(f"[ERROR] Failed to delete flashcards for quiz: {e}")
        db.session.rollback()
        raise e

@app.route('/api/subjects')
@login_required  
def get_subjects_api():
    """API endpoint för att hämta alla ämnen för användaren"""
    try:
        subjects = Subject.query.filter_by(user_id=current_user.id).order_by(Subject.name).all()
        subject_list = []
        
        for subject in subjects:
            subject_data = {
                'id': subject.id,
                'name': subject.name,
                'created_at': subject.created_at.isoformat() if subject.created_at else None,
                'quiz_count': len(subject.quizzes),
                'flashcard_count': len(subject.flashcards),
            }
            subject_list.append(subject_data)
        
        return jsonify(subject_list)
    except Exception as e:
        return jsonify({'error': 'Failed to get subjects'}), 500

@app.route('/api/subject/<subject_name>/stats')
@login_required
def get_subject_stats_api(subject_name):
    """API endpoint för att hämta statistik för ett specifikt ämne"""
    try:
        subject_obj = Subject.query.filter_by(
            user_id=current_user.id,
            name=subject_name
        ).first()
        
        if not subject_obj:
            return jsonify({'error': 'Subject not found'}), 404
        
        # Räkna quiz
        quiz_count = Quiz.query.filter_by(
            user_id=current_user.id,
            subject_name=subject_name
        ).count()
        
        # Räkna flashcards och deras status
        total_flashcards = Flashcard.query.filter_by(
            user_id=current_user.id,
            subject=subject_name
        ).count()
        
        today = datetime.now().date()
        due_flashcards = Flashcard.query.filter(
            Flashcard.user_id == current_user.id,
            Flashcard.subject == subject_name,
            Flashcard.next_review <= today
        ).count()
        
        
        stats = {
            'quiz_count': quiz_count,
            'total_flashcards': total_flashcards,
            'due_flashcards': due_flashcards,
            'created_at': subject_obj.created_at.isoformat() if subject_obj.created_at else None
        }
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': 'Failed to get subject stats'}), 500

@app.route('/flashcards_by_date')
@login_required
def flashcards_by_date():
    """Get flashcards grouped by their next review date - integrerad med spaced repetition"""
    try:
        from datetime import datetime, timedelta
        
        # Hämta alla flashcards för användaren
        flashcards = Flashcard.query.filter_by(user_id=current_user.id).all()
        
        schedule = {}
        today = datetime.now().date()
        
        for flashcard in flashcards:
            # Bestäm vilket datum kortet ska repeteras
            if flashcard.next_review is None:
                # Nya kort - lägg till idag
                review_date = today
                status = 'new'
            elif flashcard.next_review <= today:
                # Förfallna kort - lägg under deras ursprungliga datum eller idag
                review_date = today if flashcard.next_review < today else flashcard.next_review
                status = 'due' if flashcard.next_review == today else 'overdue'
            else:
                # Framtida kort - lägg under deras schemalagda datum
                review_date = flashcard.next_review
                status = 'scheduled'
            
            # Konvertera till string för JSON
            date_key = review_date.isoformat()
            
            if date_key not in schedule:
                schedule[date_key] = []
            
            # Gruppera efter subject och topic för att skapa quiz-grupper
            quiz_key = f"{flashcard.subject}#{flashcard.topic}"
            
            # Hitta befintlig quiz-grupp eller skapa ny
            existing_quiz = None
            for item in schedule[date_key]:
                if item.get('quiz_key') == quiz_key:
                    existing_quiz = item
                    break
            
            if existing_quiz:
                # Lägg till fråga till befintlig quiz-grupp
                existing_quiz['questions'].append({
                    'id': flashcard.id,
                    'question': flashcard.question,
                    'answer': flashcard.answer,
                    'ease_factor': flashcard.ease_factor,
                    'interval': flashcard.interval,
                    'repetitions': flashcard.repetitions,
                    'last_rating': flashcard.rating
                })
                existing_quiz['count'] += 1
            else:
                # Skapa ny quiz-grupp
                schedule[date_key].append({
                    'quiz_key': quiz_key,
                    'subject': flashcard.subject,
                    'topic': flashcard.topic,
                    'quiz_title': flashcard.topic,
                    'status': status,
                    'count': 1,
                    'is_spaced_repetition': True,
                    'questions': [{
                        'id': flashcard.id,
                        'question': flashcard.question,
                        'answer': flashcard.answer,
                        'ease_factor': flashcard.ease_factor,
                        'interval': flashcard.interval,
                        'repetitions': flashcard.repetitions,
                        'last_rating': flashcard.rating
                    }],
                    'quiz_url': url_for('spaced_repetition_quiz', 
                                      subject=flashcard.subject, 
                                      topic=flashcard.topic.replace(' ', '_'),
                                      date=date_key)
                })
        
        return jsonify(schedule)
        
    except Exception as e:
        print(f"[ERROR] Failed to get flashcards by date: {e}")
        return jsonify({}), 500

@app.route('/spaced_repetition_quiz/<subject>/<topic>/<date>')
@login_required 
def spaced_repetition_quiz(subject, topic, date):
    """Quiz för spaced repetition på specifikt datum"""
    try:
        # Parse datum
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
        today = datetime.now().date()
        
        # Ersätt understreck med mellanslag i topic
        topic = topic.replace('_', ' ')
        
        # Hämta flashcards som ska repeteras detta datum
        flashcards = Flashcard.query.filter(
            Flashcard.user_id == current_user.id,
            Flashcard.subject == subject,
            Flashcard.topic == topic,
            db.or_(
                Flashcard.next_review == target_date,
                db.and_(Flashcard.next_review == None, target_date == today),
                db.and_(Flashcard.next_review < today, target_date == today)
            )
        ).all()
        
        if not flashcards:
            flash('Inga flashcards hittades för repetition', 'info')
            return redirect(url_for('index'))
        
        # Konvertera till quiz-format
        questions = []
        for flashcard in flashcards:
            questions.append(f"{flashcard.question}|{flashcard.answer}")
        
        return render_template('flashcards.html',
                             subject_name=subject,
                             quiz_title=topic,
                             questions=questions,
                             is_spaced_repetition=True,
                             review_date=date)
                             
    except Exception as e:
        print(f"[ERROR] Failed to load spaced repetition quiz: {e}")
        flash('Fel vid laddning av repetitionsquiz', 'error')
        return redirect(url_for('index'))


# Hjälpfunktion för att migrera befintliga events
def migrate_events():
    """Migrera befintliga events för att lägga till subject_id och is_shared"""
    try:
        events_without_subject_id = Event.query.filter_by(subject_id=None).all()
        
        for event in events_without_subject_id:
            # Hitta subject baserat på namn
            subject = Subject.query.filter_by(name=event.subject).first()
            if subject:
                event.subject_id = subject.id
                # Sätt is_shared till False för befintliga events
                if not hasattr(event, 'is_shared') or event.is_shared is None:
                    event.is_shared = False
        
        db.session.commit()
        print(f"Migrated {len(events_without_subject_id)} events")
        
    except Exception as e:
        print(f"Error migrating events: {e}")
        db.session.rollback()





@app.route('/daily_quiz/<date>/<subject>/<topic>')
@login_required 
def daily_quiz(date, subject, topic):
    """Show quiz for specific date, subject and topic"""
    try:
        # Parse datum
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
        today = datetime.now().date()
        
        # Hämta flashcards för detta datum, ämne och topic
        flashcards = Flashcard.query.filter(
            Flashcard.user_id == current_user.id,
            Flashcard.subject == subject,
            Flashcard.topic == topic,
            db.or_(
                Flashcard.next_review == target_date,
                db.and_(Flashcard.next_review == None, target_date == today),
                db.and_(Flashcard.next_review < today, target_date == today)  # Förfallna kort
            )
        ).all()
        
        if not flashcards:
            flash('Inga flashcards hittades för detta datum', 'info')
            return redirect(url_for('index'))
        
        # Konvertera till quiz-format
        questions = []
        for flashcard in flashcards:
            questions.append(f"{flashcard.question}|{flashcard.answer}")
        
        return render_template('flashcards.html',
                             subject_name=subject,
                             quiz_title=f"{topic} - {date}",
                             questions=questions,
                             is_spaced_repetition=True,
                             flashcard_ids=[fc.id for fc in flashcards])
                             
    except Exception as e:
        print(f"[ERROR] Failed to load daily quiz: {e}")
        flash('Fel vid laddning av quiz', 'error')
        return redirect(url_for('index'))

@app.route('/daily_quiz/<date>')
@login_required 
def daily_quiz_all(date):
    """Show all flashcards for a specific date, grouped by subject and topic"""
    try:
        # Parse datum
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
        today = datetime.now().date()
        
        # Hämta alla flashcards för detta datum
        flashcards = Flashcard.query.filter(
            Flashcard.user_id == current_user.id,
            db.or_(
                Flashcard.next_review == target_date,
                db.and_(Flashcard.next_review == None, target_date == today),
                db.and_(Flashcard.next_review < today, target_date == today)  # Förfallna kort
            )
        ).all()
        
        if not flashcards:
            flash('Inga flashcards hittades för detta datum', 'info')
            return redirect(url_for('index'))
        
        # Gruppera efter ämne och topic
        grouped_flashcards = {}
        for flashcard in flashcards:
            key = f"{flashcard.subject}#{flashcard.topic}"
            if key not in grouped_flashcards:
                grouped_flashcards[key] = []
            grouped_flashcards[key].append(flashcard)
        
        return render_template('daily_flashcards_overview.html',
                             date=date,
                             grouped_flashcards=grouped_flashcards,
                             target_date=target_date)
                             
    except Exception as e:
        print(f"[ERROR] Failed to load daily flashcards overview: {e}")
        flash('Fel vid laddning av dagens flashcards', 'error')
        return redirect(url_for('index'))
    


















if __name__ == '__main__':
    
    migrate_database()
    
    app.run(debug=True)
    cleanup_on_startup()
    create_shared_files_table()
    ensure_upload_directories()
