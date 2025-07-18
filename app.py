import json
from flask import Flask, render_template, request, redirect, url_for, flash, render_template_string, jsonify, send_file, abort
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

# Lägg till denna model i din models.py
class SharedFile(db.Model):
    __tablename__ = 'shared_files'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Upladdaren
    filename = db.Column(db.String(255), nullable=False)  # Ursprungligt filnamn
    file_path = db.Column(db.String(500), nullable=False)  # Sökväg på servern
    file_size = db.Column(db.Integer)  # Storlek i bytes
    file_type = db.Column(db.String(100))  # MIME-typ
    description = db.Column(db.Text)  # Valfri beskrivning
    is_active = db.Column(db.Boolean, default=True)  # För att "ta bort" filer
    download_count = db.Column(db.Integer, default=0)  # Statistik
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subject = db.relationship('Subject', backref='shared_files')
    uploader = db.relationship('User', backref='uploaded_files')
    
    def __repr__(self):
        return f"SharedFile('{self.filename}', subject='{self.subject.name if self.subject else 'Unknown'}')"
    
    def get_file_extension(self):
        """Hämta filens extension"""
        return self.filename.split('.')[-1].lower() if '.' in self.filename else ''
    
    def get_display_size(self):
        """Formatera filstorlek för visning"""
        if not self.file_size:
            return "Okänd storlek"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} TB"
    
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


# Uppdatera Subject model
class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    #owner = db.relationship('User', backref='owned_subjects', lazy=True)


    # Kolumner som kommer att läggas till via migration
    share_code = db.Column(db.String(8), unique=True, nullable=True)  # Gör nullable först
    is_shared = db.Column(db.Boolean, default=False)
    
    # Relationships
    quizzes = db.relationship('Quiz', backref='subject_ref', lazy=True, cascade='all, delete-orphan',
                             foreign_keys='Quiz.subject_id')
    flashcards = db.relationship('Flashcard', backref='subject_ref', lazy=True, cascade='all, delete-orphan',
                                foreign_keys='Flashcard.subject_id')
    krav_documents = db.relationship('KravDocument', backref='subject_ref', lazy=True, cascade='all, delete-orphan',
                                    foreign_keys='KravDocument.subject_id')
    members = db.relationship('SubjectMember', backref='subject', lazy=True, cascade='all, delete-orphan')

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
    
    def update_subject_model():
            shared_files = db.relationship('SharedFile', backref='subject_ref', lazy=True, cascade='all, delete-orphan')
    pass

    


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
    
    # Ny relationship för subject memberships
    subject_memberships = db.relationship('SubjectMember', backref='user', lazy=True, cascade='all, delete-orphan')

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
            return 'admin'
        
        # Kontrollera membership
        membership = SubjectMember.query.filter_by(subject_id=subject_id, user_id=self.id).first()
        return membership.role if membership else None
    def get_all_subjects(self):
        """Hämta alla ämnen som användaren har tillgång till (äger eller är medlem i)"""
        # Ämnen som användaren äger
        owned_subjects = Subject.query.filter_by(user_id=self.id).all()
        
        # Ämnen som användaren är medlem i
        member_subjects = db.session.query(Subject).join(SubjectMember).filter(
            SubjectMember.user_id == self.id
        ).all()
        
        # Kombinera och returnera unika ämnen
        all_subjects = owned_subjects + member_subjects
        return list(set(all_subjects))  # Ta bort duplicates
    
    def is_member_of_subject(self, subject_id):
        """Kontrollera om användaren har tillgång till ett ämne"""
        # Kontrollera om användaren äger ämnet
        owned_subject = Subject.query.filter_by(id=subject_id, user_id=self.id).first()
        if owned_subject:
            return True
        
        # Kontrollera om användaren är medlem
        membership = SubjectMember.query.filter_by(
            subject_id=subject_id, 
            user_id=self.id
        ).first()
        return membership is not None
    
    def get_role_in_subject(self, subject_id):
        """Hämta användarens roll i ett ämne"""
        # Kontrollera om användaren äger ämnet
        owned_subject = Subject.query.filter_by(id=subject_id, user_id=self.id).first()
        if owned_subject:
            return 'owner'
        
        # Kontrollera medlemskap
        membership = SubjectMember.query.filter_by(
            subject_id=subject_id, 
            user_id=self.id
        ).first()
        
        if membership:
            return membership.role
        
        return None
    
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



# Uppdatera init_database funktionen
def init_database():
    """Initiera databas och hantera migrationer"""
    with app.app_context():
        # Skapa tabeller om de inte finns
        db.create_all()
        migrate_krav_documents()
        
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
                ('is_personal', 'BOOLEAN')  # Lägg till denna
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
        
        # Resten av din befintliga init_database kod...
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


class KravDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_name = db.Column(db.String(100), nullable=False)  # Behåll för bakåtkompatibilitet
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=True)  # Ny foreign key
    doc_type = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FlashcardResponse(db.Model):
    __tablename__ = 'flashcard_responses'
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100), nullable=False)
    quiz_title = db.Column(db.String(100), nullable=False)
    question = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    time_taken = db.Column(db.Integer, nullable=False)  # i sekunder
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def __repr__(self):
        return f"KravDocument('{self.subject_name}', '{self.doc_type}')"



def migrate_krav_documents():
    """Migrera befintliga krav-dokument för att sätta subject_id"""
    try:
        # Hämta alla krav-dokument som saknar subject_id
        krav_docs = KravDocument.query.filter_by(subject_id=None).all()
        
        for doc in krav_docs:
            # Hitta matching subject baserat på subject_name och user_id
            subject = Subject.query.filter_by(
                name=doc.subject_name, 
                user_id=doc.user_id
            ).first()
            if subject:
                doc.subject_id = subject.id
                db.session.add(doc)
        
        db.session.commit()
        print(f"[INFO] Migrated {len(krav_docs)} krav documents with subject_id")
        
    except Exception as e:
        print(f"[ERROR] Failed to migrate krav documents: {e}")
        db.session.rollback()

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






def init_database():
    """Initiera databas och hantera migrationer"""
    with app.app_context():
        # Skapa tabeller om de inte finns
        db.create_all()
        migrate_krav_documents()
        
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
                ('is_personal', 'BOOLEAN')  # LÄGG TILL DENNA RAD
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
                        elif column_type == 'VARCHAR(8)' and column_name == 'share_code':
                            default_value = ''  # Kommer fyllas i av generate_share_code()
                        else:
                            default_value = ''
                        
                        alter_query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}{default_value}"
                        db.session.execute(db.text(alter_query))
                        print(f"Added column {column_name} to {table_name}")
                    except Exception as e:
                        print(f"Error adding column {column_name} to {table_name}: {e}")
        
        # Skapa unique index för share_code om det inte finns
        try:
            db.session.execute(db.text("CREATE UNIQUE INDEX IF NOT EXISTS idx_subject_share_code ON subject(share_code)"))
            print("Created unique index for share_code")
        except Exception as e:
            print(f"Error creating share_code index: {e}")
        
        # Generera share_codes för befintliga subjects som saknar dem
        try:
            subjects_without_code = Subject.query.filter_by(share_code=None).all()
            for subject in subjects_without_code:
                subject.share_code = subject.generate_share_code()
                db.session.add(subject)
            print(f"Generated share codes for {len(subjects_without_code)} subjects")
        except Exception as e:
            print(f"Error generating share codes: {e}")
        
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
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Skapa tabeller om de inte finns
init_database()



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
    
    # Hämta krav-dokument (alla medlemmar kan se dessa)
    krav_docs = KravDocument.query.filter_by(subject_id=subject_obj.id).all()
    
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
        'krav_docs': krav_docs,
        'user_role': user_role,
        'can_create_shared': user_role in ['owner', 'admin'],
        'can_create_personal': True  # Alla kan skapa personliga quizzes
    }
    
    return render_template('subject.html', **context)





# 3. Uppdatera create_quiz funktionen för att sätta is_personal korrekt
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
        
        # Resten av din befintliga create_quiz logik...
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
            krav_docs = KravDocument.query.filter_by(subject_id=subject_obj.id).all()
            krav_texts = []
            for doc in krav_docs:
                if doc.content.strip():
                    krav_texts.append(f"{doc.doc_type.capitalize()}: {doc.content}")
            
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
            is_personal=is_personal  # LÄGG TILL DENNA RAD
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
        flash(f'{quiz_type_text.capitalize()} "{quiz_title}" created successfully', 'success')
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




def get_user_krav_documents(subject_name=None):
    """Hämta krav-dokument för nuvarande användare (både egna och från ämnen man är medlem i)"""
    if not current_user.is_authenticated:
        return {}
    
    if subject_name:
        # För ett specifikt ämne, hämta dokument från alla användare som har tillgång till ämnet
        subject_obj = Subject.query.filter_by(name=subject_name).first()
        if not subject_obj:
            return {}
        
        # Kontrollera om användaren har tillgång till detta ämne
        if not current_user.is_member_of_subject(subject_obj.id):
            return {}
        
        # Hämta alla krav-dokument för detta ämne (från ägaren)
        documents = KravDocument.query.filter_by(subject_id=subject_obj.id).all()
        
        # Returnera dictionary för specifikt ämne
        result = {}
        for doc in documents:
            result[doc.doc_type] = {'innehåll': doc.content}
        return result
    else:
        # Hämta alla ämnen användaren har tillgång till
        accessible_subjects = current_user.get_all_subjects()
        
        # Hämta dokument för alla dessa ämnen
        subject_ids = [subject.id for subject in accessible_subjects]
        documents = KravDocument.query.filter(KravDocument.subject_id.in_(subject_ids)).all()
        
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
    subject_obj = Subject.query.filter_by(name=subject_name).first()
    if not subject_obj:
        return False
    
    # Kontrollera om användaren har tillgång till detta ämne
    if not current_user.is_member_of_subject(subject_obj.id):
        return False
    
    # Endast ägaren eller admins kan redigera krav-dokument
    user_role = current_user.get_role_in_subject(subject_obj.id)
    if user_role not in ['owner', 'admin']:
        return False
    
    # Leta efter befintligt dokument (sök efter subject_id istället för user_id)
    existing = KravDocument.query.filter_by(
        subject_id=subject_obj.id,
        doc_type=doc_type
    ).first()
    
    if existing:
        existing.content = content
    else:
        doc = KravDocument(
            subject_name=subject_name,
            subject_id=subject_obj.id,
            doc_type=doc_type,
            content=content,
            user_id=current_user.id  # Behåll för att spåra vem som skapade/redigerade
        )
        db.session.add(doc)
    
    db.session.commit()
    return True



def delete_krav_document(subject_name, doc_type):
    """Ta bort krav-dokument"""
    if not current_user.is_authenticated:
        return False
    
    # Hitta Subject-objektet
    subject_obj = Subject.query.filter_by(name=subject_name).first()
    if not subject_obj:
        return False
    
    # Kontrollera om användaren har tillgång till detta ämne
    if not current_user.is_member_of_subject(subject_obj.id):
        return False
    
    # Endast ägaren eller admins kan ta bort krav-dokument
    user_role = current_user.get_role_in_subject(subject_obj.id)
    if user_role not in ['owner', 'admin']:
        return False
    
    doc = KravDocument.query.filter_by(
        subject_id=subject_obj.id,
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
        # Ta bort ämnet från databasen
        subject_obj = Subject.query.filter_by(user_id=current_user.id, name=subject_to_delete).first()
        if subject_obj:
            db.session.delete(subject_obj)
            db.session.commit()
    return redirect(url_for('home'))

# Add these routes to your Flask app to make flashcard quizzes work




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

# Uppdaterad create_flashcards_for_all_members funktion
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


@app.route('/create_krav_document', methods=['POST'])
@login_required
def create_krav_document():
    """Skapa krav-dokument - nu med stöd för shared subjects"""
    try:
        data = request.get_json()
        subject_name = data.get('subject_name')
        doc_type = data.get('doc_type')
        content = data.get('content')
        
        if not all([subject_name, doc_type, content]):
            return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
        
        # Hitta subject
        subject_obj = Subject.query.filter_by(name=subject_name).first()
        if not subject_obj:
            return jsonify({'status': 'error', 'message': 'Subject not found'}), 404
        
        # Kontrollera om användaren har tillgång och behörighet
        if not current_user.is_member_of_subject(subject_obj.id):
            return jsonify({'status': 'error', 'message': 'You do not have access to this subject'}), 403
        
        user_role = current_user.get_role_in_subject(subject_obj.id)
        if user_role not in ['admin', 'owner']:
            return jsonify({'status': 'error', 'message': 'You do not have permission to create documents'}), 403
        
        # Skapa krav-dokument med både subject_name och subject_id
        krav_doc = KravDocument(
            subject_name=subject_name,
            subject_id=subject_obj.id,  # Viktigt: Sätt subject_id
            doc_type=doc_type,
            content=content,
            user_id=current_user.id
        )
        
        db.session.add(krav_doc)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'{doc_type} document created successfully',
            'document': {
                'id': krav_doc.id,
                'doc_type': krav_doc.doc_type,
                'content': krav_doc.content
            }
        })
        
    except Exception as e:
        print(f"[ERROR] Failed to create krav document: {e}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Failed to create document'}), 500


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
        # Hitta subject först
        subject_obj = Subject.query.filter_by(name=subject_name).first()
        
        if not subject_obj:
            flash("Subject not found.", "error")
            return redirect(url_for('index'))
        
        # Kontrollera om användaren har tillgång till detta subject
        if not current_user.is_member_of_subject(subject_obj.id):
            flash('You do not have access to this subject', 'error')
            return redirect(url_for('index'))
        
        # Hitta quiz baserat på subject_id och index
        quiz_to_delete = Quiz.query.filter_by(
            subject_id=subject_obj.id
        ).offset(quiz_index).first()
        
        if quiz_to_delete:
            quiz_title = quiz_to_delete.title
            db.session.delete(quiz_to_delete)
            db.session.commit()
            flash(f"Deleted quiz: {quiz_title}", "success")
        else:
            flash("Quiz not found.", "error")
        
    except Exception as e:
        print(f"[ERROR] Failed to delete quiz: {e}")
        flash("Error deleting quiz.", "error")
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


@app.route('/api/krav_documents/<subject_name>')
@login_required
def get_krav_documents_api(subject_name):
    """API endpoint för att hämta krav-dokument för ett ämne"""
    try:
        # Hämta dokument direkt från SQL-databasen
        documents = KravDocument.query.filter_by(
            user_id=current_user.id,
            subject_name=subject_name
        ).all()
        
        # Formatera dokumenten
        enhanced_documents = {}
        for doc in documents:
            enhanced_documents[doc.doc_type] = {
                'id': doc.id,
                'innehåll': doc.content,
                'created_at': doc.created_at.isoformat() if doc.created_at else None,
                'subject_id': doc.subject_id
            }
        
        return jsonify(enhanced_documents)
    except Exception as e:
        print(f"[ERROR] Failed to get krav documents: {e}")
        return jsonify({'error': 'Failed to get documents'}), 500




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

@app.route('/upload_krav_pdf', methods=['POST'])
@login_required
def upload_krav_pdf():
    """Uppdaterad version som returnerar mer detaljerad information och använder SQL"""
    try:
        subject = request.form['subject']
        doc_type = request.form['type']
        file = request.files.get('file')
        
        if not file:
            return jsonify(status='error', message='Ingen fil'), 400

        # Skapa användarspecifik mapp
        folder = os.path.join('static', 'uploads', 'krav', str(current_user.id), subject)
        os.makedirs(folder, exist_ok=True)
        
        # Säker filnamn
        original_filename = secure_filename(file.filename)
        file_path = os.path.join(folder, f"{doc_type}.pdf")
        file.save(file_path)

        # Extrahera text från PDF
        text = ''
        try:
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text()
            
            # Fallback OCR om tomt
            if not text.strip():
                from pdf2image import convert_from_path
                images = convert_from_path(file_path)
                for img in images:
                    text += pytesseract.image_to_string(img)
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            text = "Kunde inte extrahera text från PDF"

        # Spara till SQL-databas
        # Kontrollera om dokumentet redan finns
        existing_doc = KravDocument.query.filter_by(
            user_id=current_user.id,
            subject_name=subject,
            doc_type=doc_type
        ).first()
        
        if existing_doc:
            # Uppdatera befintligt dokument
            existing_doc.content = text
            existing_doc.created_at = datetime.now()
            doc_obj = existing_doc
        else:
            # Skapa nytt dokument
            doc_obj = KravDocument(
                user_id=current_user.id,
                subject_name=subject,
                doc_type=doc_type,
                content=text,
                created_at=datetime.now()
            )
            db.session.add(doc_obj)
        
        db.session.commit()

        response_data = {
            'status': 'success',
            'message': 'Dokument uppladdat framgångsrikt',
            'filename': original_filename,
            'doc_type': doc_type,
            'document_id': doc_obj.id,
            'created_at': doc_obj.created_at.isoformat() if doc_obj.created_at else None
        }

        return jsonify(response_data)
        
    except Exception as e:
        print(f"Upload error: {e}")
        db.session.rollback()
        return jsonify(status='error', message=f'Fel vid uppladdning: {str(e)}'), 500

@app.route('/delete_krav_document', methods=['POST'])
@login_required
def delete_krav_document_route():
    """Uppdaterad version som hanterar både doc_type och doc_id och använder SQL"""
    try:
        data = request.get_json()
        subject = data.get('subject')
        doc_type = data.get('doc_type')
        doc_id = data.get('doc_id')  # Ny parameter

        if not subject or not doc_type:
            return jsonify({'status': 'error', 'message': 'Saknar subject eller doc_type'}), 400

        # Ta bort från SQL-databas
        query = KravDocument.query.filter_by(
            user_id=current_user.id,
            subject_name=subject,
            doc_type=doc_type
        )
        
        # Om doc_id är specificerat, lägg till det i filtret
        if doc_id:
            try:
                query = query.filter_by(id=int(doc_id))
            except ValueError:
                return jsonify({'status': 'error', 'message': 'Ogiltigt dokument-ID'}), 400

        doc = query.first()
        
        if not doc:
            return jsonify({'status': 'error', 'message': 'Dokument hittades inte'}), 404

        # Ta bort fysisk fil
        file_path = os.path.join('static', 'uploads', 'krav', str(current_user.id), subject, f"{doc_type}.pdf")
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Warning: Could not delete file {file_path}: {e}")

        # Ta bort från SQL-databas
        db.session.delete(doc)
        db.session.commit()

        return jsonify({'status': 'success', 'message': 'Dokument borttaget'})
        
    except Exception as e:
        db.session.rollback()
        print(f"Delete error: {e}")
        return jsonify({'status': 'error', 'message': f'Fel vid borttagning: {str(e)}'}), 500

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
                'document_count': len(subject.krav_documents)
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
        
        # Räkna dokument
        document_count = KravDocument.query.filter_by(
            user_id=current_user.id,
            subject_name=subject_name
        ).count()
        
        stats = {
            'quiz_count': quiz_count,
            'total_flashcards': total_flashcards,
            'due_flashcards': due_flashcards,
            'document_count': document_count,
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
