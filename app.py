import json
from flask import Flask, render_template, request, redirect, url_for, flash, render_template_string, jsonify, send_file, abort
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import requests
import fitz  # PyMuPDF
import pytesseract
import threading
from pydub import AudioSegment  # IMPORTERA AudioSegment
import calendar

from threading import Thread

import whisper

import base64
from moviepy import VideoFileClip
import speech_recognition as sr
import io
import wave

import math

from flask_migrate import Migrate



import ssl
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass





import urllib.parse
from pdf2image import convert_from_path
import os
import json.decoder
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from sqlalchemy import JSON, Text, distinct, or_
from extensions import db
import string
import secrets
import uuid
import mimetypes
basedir = os.path.abspath(os.path.dirname(__file__))

from sqlalchemy.orm import joinedload


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
migrate = Migrate(app, db)

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



# models.py



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
    # I din SharedFile model, lägg till:
    is_message = db.Column(db.Boolean, default=False)  # För att skilja meddelanden från filer
    original_filename = db.Column(db.String(255))  # Lägg till denna också om den saknas
    file_extension = db.Column(db.String(10))  # Lägg till denna också om den saknas
    file_path = db.Column(db.String(500), nullable=True)  # Ändra till nullable=True för meddelanden
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
    lessons = db.relationship('Lesson', backref='subject', lazy=True, cascade='all, delete-orphan')

    # Kolumner som kommer att läggas till via migration
    share_code = db.Column(db.String(8), unique=True, nullable=True)
    is_shared = db.Column(db.Boolean, default=False)
    

    owner_email = db.Column(db.String(120), nullable=True)
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
    last_seen_shared_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Unique constraint för att förhindra duplicerade medlemskap
    __table_args__ = (db.UniqueConstraint('subject_id', 'user_id', name='unique_subject_member'),)
    
    def __repr__(self):
        return f"SubjectMember(subject_id={self.subject_id}, user_id={self.user_id}, role='{self.role}')"
# Uppdatera User model för att inkludera subject memberships


# Lägg till denna modell i din models.py eller där du har dina databasmodeller

class LunchMenu(db.Model):
    """Matsedel för skolor"""
    __tablename__ = 'lunch_menu'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    menu_date = db.Column(db.Date, nullable=False)
    main_dish = db.Column(db.Text)
    vegetarian_dish = db.Column(db.Text)
    side_dishes = db.Column(db.Text)
    dessert = db.Column(db.Text)
    allergens = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relation till School
    school = db.relationship('School', backref='lunch_menus')
    
    def to_dict(self):
        return {
            'id': self.id,
            'school_id': self.school_id,
            'menu_date': self.menu_date.isoformat() if self.menu_date else None,
            'main_dish': self.main_dish,
            'vegetarian_dish': self.vegetarian_dish,
            'side_dishes': self.side_dishes,
            'dessert': self.dessert,
            'allergens': self.allergens
        }
    
    def __repr__(self):
        return f"LunchMenu(school_id={self.school_id}, date={self.menu_date})"


def create_sample_lunch_menu():
    """Skapa exempel-matsedel för test"""
    from datetime import date, timedelta
    
    # Hämta första skolan (eller skapa en om ingen finns)
    school = School.query.first()
    if not school:
        school = School(
            name="Test Skola",
            address="Testgatan 1",
            city="Stockholm",
            postal_code="12345",
            school_code="TEST001"
        )
        db.session.add(school)
        db.session.commit()
    
    # Skapa matsedel för denna vecka
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    
    # Exempel-matsedel för veckan
    menu_items = [
        {
            'day': 0,  # Måndag
            'main_dish': 'Köttbullar med potatismos och lingonsylt',
            'vegetarian_dish': 'Vegetariska köttbullar med potatismos',
            'side_dishes': 'Gurksallad, knäckebröd',
            'dessert': 'Äppelkaka med vaniljsås',
            'allergens': 'Gluten, mjölk, ägg'
        },
        {
            'day': 1,  # Tisdag
            'main_dish': 'Fiskgratäng med dillsås',
            'vegetarian_dish': 'Pasta med tomatsås och ost',
            'side_dishes': 'Kokt potatis, blandsallad',
            'dessert': 'Frukt',
            'allergens': 'Fisk, mjölk, gluten'
        },
        {
            'day': 2,  # Onsdag
            'main_dish': 'Kycklingwok med ris',
            'vegetarian_dish': 'Vegetarisk wok med tofu och ris',
            'side_dishes': 'Sojasås, chilisås',
            'dessert': 'Glass',
            'allergens': 'Soja, mjölk'
        },
        {
            'day': 3,  # Torsdag
            'main_dish': 'Pasta carbonara',
            'vegetarian_dish': 'Pasta med pestosås',
            'side_dishes': 'Riven ost, bröd',
            'dessert': 'Pannkaka med sylt',
            'allergens': 'Gluten, mjölk, ägg'
        },
        {
            'day': 4,  # Fredag
            'main_dish': 'Pizza margherita',
            'vegetarian_dish': 'Vegansk pizza med grönsaker',
            'side_dishes': 'Sallad',
            'dessert': 'Kaka',
            'allergens': 'Gluten, mjölk'
        }
    ]
    
    # Ta bort befintlig matsedel för denna vecka
    LunchMenu.query.filter(
        LunchMenu.school_id == school.id,
        LunchMenu.menu_date >= monday,
        LunchMenu.menu_date <= monday + timedelta(days=4)
    ).delete()
    
    # Lägg till ny matsedel
    for item in menu_items:
        menu_date = monday + timedelta(days=item['day'])
        
        lunch_menu = LunchMenu(
            school_id=school.id,
            menu_date=menu_date,
            main_dish=item['main_dish'],
            vegetarian_dish=item['vegetarian_dish'],
            side_dishes=item['side_dishes'],
            dessert=item['dessert'],
            allergens=item['allergens']
        )
        db.session.add(lunch_menu)
    
    db.session.commit()
    print(f"✅ Skapade matsedel för vecka {monday} - {monday + timedelta(days=4)}")


# Lägg till detta i din init_database() funktion eller kör separat
def setup_lunch_menu_data():
    """Setup matsedelsdata för test"""
    with app.app_context():
        try:
            create_sample_lunch_menu()
        except Exception as e:
            print(f"Error creating lunch menu data: {e}")
            db.session.rollback()

# Uppdatera User model för att inkludera subject memberships
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(60), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    email = db.Column(db.String(120), unique=True, nullable=False)
    
    # BEFINTLIGA KOLUMNER (matchar ditt schema)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), default=0)
    class_id = db.Column(db.Integer, db.ForeignKey('school_classes.id'), default=0)
    user_type = db.Column(db.String(20), default='student')  # 'student', 'teacher', 'admin'
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    personal_number = db.Column(db.String(12))  # personnummer
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    postal_code = db.Column(db.String(10))
    parent_name = db.Column(db.String(100))
    parent_phone = db.Column(db.String(20))
    parent_email = db.Column(db.String(120))
    teacher_subjects = db.Column(db.String(200))  # för lärare
    qualifications = db.Column(db.Text)  # för lärare
    is_active = db.Column(db.Boolean, default=True)
    
    # Resten av dina befintliga kolumner och relationer...
    subjects = db.relationship('Subject', backref='owner', lazy=True, cascade='all, delete-orphan')
    quizzes = db.relationship('Quiz', backref='owner', lazy=True, cascade='all, delete-orphan')
    flashcards = db.relationship('Flashcard', backref='owner', lazy=True, cascade='all, delete-orphan')
    events = db.relationship('Event', backref='owner', lazy=True, cascade='all, delete-orphan')
    subject_memberships = db.relationship('SubjectMember', backref='user', lazy=True, cascade='all, delete-orphan')
    krav_documents = db.relationship('KravDocument', backref='user', lazy=True, cascade='all, delete-orphan')
    shared_files = db.relationship('SharedFile', backref='uploader', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"User('{self.username}')"
    
    # NYA METODER för att hantera skola och klass (uppdaterade för utökat schema)
    def get_school_name(self):
        """Hämta skolans namn"""
        if self.school_id and self.school_id > 0:
            return self.school.name if self.school else "Okänd skola"
        return "Ingen skola"
    
    def get_class_name(self):
        """Hämta klassens namn"""
        if self.class_id and self.class_id > 0:
            return self.school_class.name if self.school_class else "Okänd klass"
        return "Ingen klass"
    
    def get_full_name(self):
        """Hämta användarens fullständiga namn"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        return self.username
    
    def is_teacher(self):
        """Kontrollera om användaren är lärare"""
        return self.user_type == 'teacher'
    
    def is_student(self):
        """Kontrollera om användaren är elev"""
        return self.user_type == 'student'
    
    def is_admin(self):
        """Kontrollera om användaren är administratör"""
        return self.user_type == 'admin'
    
    def get_classmates(self):
        """Hämta alla klasskompisar (användare i samma klass)"""
        if not self.class_id or self.class_id == 0:
            return []
        return User.query.filter(
            User.class_id == self.class_id,
            User.id != self.id,
            User.is_active == True
        ).all()
    
    def get_school_users(self):
        """Hämta alla användare på samma skola"""
        if not self.school_id or self.school_id == 0:
            return []
        return User.query.filter(
            User.school_id == self.school_id,
            User.id != self.id,
            User.is_active == True
        ).all()
    
    def get_students_in_class(self):
        """För lärare: hämta alla elever i samma klass"""
        if not self.class_id or self.class_id == 0:
            return []
        return User.query.filter(
            User.class_id == self.class_id,
            User.user_type == 'student',
            User.is_active == True
        ).all()
    
    def is_homeroom_teacher(self):
        """Kontrollera om användaren är klassföreståndare för någon klass"""
        if not self.is_teacher():
            return False
        return SchoolClass.query.filter_by(homeroom_teacher_id=self.id).first() is not None
    
    def get_homeroom_classes(self):
        """Hämta klasser där användaren är klassföreståndare"""
        if not self.is_teacher():
            return []
        return SchoolClass.query.filter_by(homeroom_teacher_id=self.id).all()
    
    # Dina befintliga metoder fortsätter här...
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



def init_database():
    """Initiera databas och hantera migrationer"""
    with app.app_context():
        # Skapa tabeller om de inte finns
        db.create_all()
        
        # Lista över alla kolumner som behövs för varje tabell
        required_columns = {
            'schools': [
                ('name', 'VARCHAR(200)'),
                ('address', 'VARCHAR(300)'),
                ('phone', 'VARCHAR(20)'),
                ('email', 'VARCHAR(120)'),
                ('created_at', 'DATETIME')
            ],
            'school_classes': [
                ('name', 'VARCHAR(50)'),
                ('school_id', 'INTEGER'),
                ('description', 'TEXT'),
                ('year_level', 'INTEGER'),
                ('created_at', 'DATETIME')
            ],
            'lunch_menu': [
                ('school_id', 'INTEGER'),
                ('menu_date', 'DATE'),
                ('main_dish', 'TEXT'),
                ('vegetarian_dish', 'TEXT'),
                ('side_dishes', 'TEXT'),
                ('dessert', 'TEXT'),
                ('allergens', 'TEXT'),
                ('created_at', 'DATETIME'),
                ('updated_at', 'DATETIME')
            ],
            'user': [
                ('school_id', 'INTEGER'),
                ('class_id', 'INTEGER')
            ],
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




# Lägg till dessa modeller i din Flask-app (models.py eller liknande)

class Attendance(db.Model):
    """Närvarorapport för en specifik lektion"""
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('class_schedule.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)  # Vilket datum lektionen genomfördes
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('school_classes.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=True)
    lesson_notes = db.Column(db.Text)  # Anteckningar om lektionen
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationer
    schedule_item = db.relationship('ClassSchedule', backref='attendance_records')
    teacher = db.relationship('User', foreign_keys=[teacher_id], backref='taught_lessons')
    school_class = db.relationship('SchoolClass', backref='attendance_records')
    subject = db.relationship('Subject', backref='attendance_records')
    student_attendances = db.relationship('StudentAttendance', backref='attendance_session', 
                                        cascade='all, delete-orphan')
    
    def get_attendance_summary(self):
        """Hämta sammanfattning av närvaro för denna lektion"""
        total_students = len(self.student_attendances)
        present_students = len([s for s in self.student_attendances if s.status == 'present'])
        absent_students = len([s for s in self.student_attendances if s.status == 'absent'])
        late_students = len([s for s in self.student_attendances if s.status == 'late'])
        
        return {
            'total': total_students,
            'present': present_students,
            'absent': absent_students,
            'late': late_students,
            'attendance_rate': round((present_students + late_students) / total_students * 100, 1) if total_students > 0 else 0
        }
    
    def __repr__(self):
        return f"Attendance(date={self.date}, class_id={self.class_id})"


class StudentAttendance(db.Model):
    """Enskild elevs närvaro för en specifik lektion"""
    __tablename__ = 'student_attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    attendance_id = db.Column(db.Integer, db.ForeignKey('attendance.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'present', 'absent', 'late', 'excused'
    arrival_time = db.Column(db.DateTime)  # När eleven kom (för sena ankomster)
    notes = db.Column(db.Text)  # Anteckningar om eleven specifikt
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint - en elev kan bara ha en närvaromarkering per lektion
    __table_args__ = (db.UniqueConstraint('attendance_id', 'student_id', name='unique_student_attendance'),)
    
    # Relationer
    student = db.relationship('User', foreign_keys=[student_id], backref='attendance_records')
    
    def __repr__(self):
        return f"StudentAttendance(student_id={self.student_id}, status='{self.status}')"




class School(db.Model):
    """Skola-modell för att hantera olika skolor"""
    __tablename__ = 'schools'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    address = db.Column(db.String(300))
    city = db.Column(db.String(100))
    postal_code = db.Column(db.String(10))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    school_code = db.Column(db.String(20), unique=True)
    school_type = db.Column(db.String(50))  # t.ex. "grundskola", "gymnasium"
    principal_name = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    classrooms = db.Column(db.Text, nullable=False, default='[]')
    # Relationer
    classes = db.relationship('SchoolClass', backref='school', lazy=True, cascade='all, delete-orphan')
    users = db.relationship('User', backref='school', lazy=True)
    
    def __repr__(self):
        return f"School('{self.name}', code='{self.school_code}')"


class ClassSchedule(db.Model):
    __tablename__ = 'class_schedule'

    id         = db.Column(db.Integer, primary_key=True)
    class_id   = db.Column(db.Integer, db.ForeignKey('school_classes.id', ondelete='CASCADE'), nullable=False)
    weekday    = db.Column(db.String(20),  nullable=False)   # 'måndag', 'tisdag' …
    start_time = db.Column(db.String(5),   nullable=False)   # '08:00'
    end_time   = db.Column(db.String(5),   nullable=False)   # '09:00'
    subject_id = db.Column(db.Integer,     db.ForeignKey('subject.id'), nullable=True)
    room       = db.Column(db.String(50),  nullable=True)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)

    # Relationer (valfritt)
    school_class = db.relationship('SchoolClass', backref='schedule')
    subject      = db.relationship('Subject')

    def get_students_for_lesson(self):
        """Hämta alla elever som ska gå på denna lektion (baserat på class_id)"""
        return User.query.filter(
            User.class_id == self.class_id,
            User.user_type == 'student',
            User.is_active == True
        ).order_by(User.last_name, User.first_name).all()

    def get_attendance_for_date(self, date):
        """Hämta närvarorapport för denna lektion på ett specifikt datum"""
        return Attendance.query.filter_by(
            schedule_id=self.id,
            date=date
        ).first()

    def has_attendance_for_date(self, date):
        """Kontrollera om närvaro redan är rapporterad för detta datum"""
        return self.get_attendance_for_date(date) is not None


class SchoolNews(db.Model):
    """Nyheter för skolan"""
    __tablename__ = 'school_news'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationer
    school = db.relationship('School', backref='news')
    author = db.relationship('User', backref='authored_news')
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'author_name': self.author.get_full_name() if self.author else 'Okänd',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f"SchoolNews('{self.title}', school_id={self.school_id})"

class SchoolClass(db.Model):
    """Klass-modell för att hantera klasser inom skolor"""
    __tablename__ = 'school_classes'
    
    id = db.Column(db.Integer, primary_key=True) 
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)  # t.ex. "9A", "Matematik 1"
    year_level = db.Column(db.Integer)  # årskurs, t.ex. 9
    class_code = db.Column(db.String(20))  # unik kod för klassen
    description = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    homeroom_teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint för att förhindra duplicerade klassnamn inom samma skola
    __table_args__ = (db.UniqueConstraint('school_id', 'name', name='unique_school_class'),)
    
    # Relationer - FIX: Specificera foreign_keys för att lösa ambiguiteten
    users = db.relationship('User', 
                           foreign_keys='User.class_id',
                           backref='school_class', 
                           lazy=True)
    
    homeroom_teacher = db.relationship('User', 
                                     foreign_keys=[homeroom_teacher_id], 
                                     backref='homeroom_classes')
    
    def __repr__(self):
        return f"SchoolClass('{self.name}', school_id={self.school_id})"

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    quiz_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)  # AI instructions, not for display
    display_description = db.Column(db.String(200))  # Short user-facing description
    subject_name = db.Column(db.String(100), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    use_documents = db.Column(db.Boolean, default=False)
    files = db.Column(db.JSON)
    questions = db.Column(db.JSON)
    is_personal = db.Column(db.Boolean, default=True)
    
    def get_questions(self):
        """
        Säkert sätt att hämta frågor för denna specifika quiz.
        Inkluderar extra validering för att säkerställa att frågorna tillhör denna quiz.
        """
        if not self.questions:
            return []
        
        # Grundläggande validering
        if not isinstance(self.questions, list):
            print(f"[WARNING] Quiz {self.id} has invalid questions format: {type(self.questions)}")
            return []
        
        # Filtrera och validera varje fråga
        validated_questions = []
        for i, question in enumerate(self.questions):
            if not isinstance(question, dict):
                print(f"[WARNING] Quiz {self.id}, question {i}: Invalid question format")
                continue
                
            # Kontrollera att frågan har nödvändiga fält
            if not all(key in question for key in ['question', 'answer']):
                print(f"[WARNING] Quiz {self.id}, question {i}: Missing required fields")
                continue
                
            # Extra validering - kontrollera quiz_id om det finns
            if 'quiz_id' in question and question['quiz_id'] != self.id:
                print(f"[ERROR] Quiz {self.id}, question {i}: Question belongs to quiz {question['quiz_id']}")
                continue
                
            # Lägg till implicit quiz_id om det saknas
            question_copy = question.copy()
            question_copy['quiz_id'] = self.id
            question_copy['belongs_to_quiz'] = self.id  # Extra säkerhet
            
            validated_questions.append(question_copy)
        
        return validated_questions
    
    def set_questions(self, questions_list):
        """
        Säkert sätt att sätta frågor för denna quiz.
        Lägger automatiskt till quiz_id för varje fråga.
        """
        if not isinstance(questions_list, list):
            raise ValueError("Questions must be a list")
        
        validated_questions = []
        for i, question in enumerate(questions_list):
            if not isinstance(question, dict):
                raise ValueError(f"Question {i} must be a dictionary")
                
            if not all(key in question for key in ['question', 'answer']):
                raise ValueError(f"Question {i} must have 'question' and 'answer' fields")
            
            # Säkerställ att varje fråga är kopplad till denna quiz
            question_copy = question.copy()
            question_copy['quiz_id'] = self.id
            question_copy['belongs_to_quiz'] = self.id
            question_copy['question_index'] = i
            question_copy['created_at'] = datetime.utcnow().isoformat()
            
            validated_questions.append(question_copy)
        
        self.questions = validated_questions
        print(f"[INFO] Set {len(validated_questions)} validated questions for quiz {self.id}")
    
    def verify_questions_integrity(self):
        """
        Verifiera att alla frågor verkligen tillhör denna quiz.
        Returnerar antal korrekta frågor och antal fel.
        """
        questions = self.get_questions()
        correct_count = 0
        error_count = 0
        
        for question in questions:
            if question.get('quiz_id') == self.id and question.get('belongs_to_quiz') == self.id:
                correct_count += 1
            else:
                error_count += 1
                
        return correct_count, error_count
    
    def get_display_description(self):
    
        if self.display_description and self.display_description.strip():
            return self.display_description.strip()
    
        # Förbättrad fallback om ingen display_description finns
        question_count = len(self.get_questions())
        quiz_type_readable = self.quiz_type.replace('-', ' ').title()
    
        if question_count == 0:
            return f"{quiz_type_readable} quiz - Inga frågor tillgängliga än"
        elif question_count <= 10:
            return f"{question_count} frågor för snabb kunskapsträning och grundläggande repetition"
        elif question_count <= 25:
            return f"{question_count} frågor för omfattande kunskapstest och fördjupad ämnesträning"
        else:
            return f"{question_count} frågor för fullständig genomgång och djupgående kunskapsbearbeitung"
        

    def to_dict(self):
        """Konvertera Quiz-objekt till dictionary för JSON-serialisering"""
        # Använd säkra getter för frågor
        safe_questions = self.get_questions()
        
        return {
            'id': self.id,
            'title': self.title,
            'quiz_type': self.quiz_type,
            'description': self.description,  # AI instructions
            'display_description': self.get_display_description(),  # User-facing description
            'subject_name': self.subject_name,
            'subject_id': self.subject_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'use_documents': self.use_documents,
            'files': self.files,
            'questions': safe_questions,  # Använd validerade frågor
            'is_personal': self.is_personal,
            'question_count': len(safe_questions),
            'integrity_check': self.verify_questions_integrity()
        }
    
    def get_question_count(self):
        """Säkert sätt att räkna frågor"""
        return len(self.get_questions())
    
    def get_question_by_index(self, index):
        """Hämta en specifik fråga baserat på index"""
        questions = self.get_questions()
        if 0 <= index < len(questions):
            return questions[index]
        return None
    
    def __repr__(self):
        question_count = self.get_question_count()
        return f"Quiz(id={self.id}, title='{self.title}', questions={question_count}, type='{self.quiz_type}')"

@app.template_filter('nl2br')
def nl2br_filter(text):
    if not text:
        return text
    from markupsafe import Markup, escape
    return Markup(escape(text).replace('\n', '<br>\n'))


# Hjälpfunktion för att migrera befintliga quizzes
def fix_existing_quizzes():
    """
    Använd denna funktion för att fixa befintliga quizzes som kanske har
    felaktiga eller saknade quiz_id-kopplingar i sina frågor.
    """
    all_quizzes = Quiz.query.all()
    fixed_count = 0
    
    for quiz in all_quizzes:
        if quiz.questions:
            needs_fix = False
            updated_questions = []
            
            for i, question in enumerate(quiz.questions):
                if not isinstance(question, dict):
                    continue
                    
                # Kontrollera om frågan behöver fixas
                if 'quiz_id' not in question or question['quiz_id'] != quiz.id:
                    needs_fix = True
                    
                question_copy = question.copy()
                question_copy['quiz_id'] = quiz.id
                question_copy['belongs_to_quiz'] = quiz.id
                question_copy['question_index'] = i
                question_copy['fixed_at'] = datetime.utcnow().isoformat()
                
                updated_questions.append(question_copy)
            
            if needs_fix:
                quiz.questions = updated_questions
                fixed_count += 1
                print(f"[FIX] Updated quiz {quiz.id} with {len(updated_questions)} questions")
    
    if fixed_count > 0:
        db.session.commit()
        print(f"[SUCCESS] Fixed {fixed_count} quizzes")
    else:
        print("[INFO] No quizzes needed fixing")
    
    return fixed_count


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

# Uppdaterade modeller för kommentarfunktionalitet

class Assignment(db.Model):
    """Uppgifter som skapas av ämnesägare"""
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.DateTime)
    allow_multiple_files = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationer
    subject = db.relationship('Subject', backref='assignments')
    creator = db.relationship('User', backref='created_assignments')
    submissions = db.relationship('AssignmentSubmission', backref='assignment', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Assignment {self.title}>'


class AssignmentSubmission(db.Model):
    """Elevernas inlämningar av uppgifter"""
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comment = db.Column(db.Text)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    seen = db.Column(db.Boolean, default=False)  # <— NYTT!

    # Relationer
    student = db.relationship('User', backref='assignment_submissions')
    files = db.relationship('AssignmentFile', backref='submission', cascade='all, delete-orphan')
    # NY: Relation till kommentarer från lärare
    teacher_comments = db.relationship('SubmissionComment', backref='submission', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<AssignmentSubmission {self.id}>'


class AssignmentFile(db.Model):
    """Filer som lämnats in för uppgifter"""
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('assignment_submission.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<AssignmentFile {self.filename}>'


# NY MODELL: Kommentarer från lärare på inlämningar
class SubmissionComment(db.Model):
    """Kommentarer från lärare/ägare på elevens inlämning"""
    __tablename__ = 'submission_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('assignment_submission.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationer
    teacher = db.relationship('User', backref='submission_comments')
    
    def __repr__(self):
        return f'<SubmissionComment {self.id}>'

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


# Uppdaterad route för att hantera både elev- och lärarscheman
# Add this updated route to your Flask app to replace the existing get_schedule_for_date route

@app.route('/api/schedule/<date>')
@login_required
def get_schedule_for_date(date):
    """Hämta schema för ett specifikt datum - fungerar för både elever och lärare"""
    try:
        # Parse datum (format: YYYY-MM-DD)
        schedule_date = datetime.strptime(date, '%Y-%m-%d')
        
        # Konvertera till svensk veckodag
        weekday_eng = schedule_date.strftime('%A').lower()
        weekday_mapping = {
            'monday': 'måndag',
            'tuesday': 'tisdag', 
            'wednesday': 'onsdag',
            'thursday': 'torsdag',
            'friday': 'fredag',
            'saturday': 'lördag',
            'sunday': 'söndag'
        }
        weekday_swe = weekday_mapping.get(weekday_eng, weekday_eng)
        
        if current_user.is_teacher():
            # LÄRARE: Hämta alla lektioner där läraren undervisar
            # Först, skapa en mapping av ämnets namn till de ämnen läraren undervisar
            teacher_subjects_list = []
            if current_user.teacher_subjects:
                # Antag att teacher_subjects är en kommaseparerad sträng
                teacher_subjects_list = [s.strip() for s in current_user.teacher_subjects.split(',')]
            
            # Hämta alla subjects som läraren äger (skapade)
            owned_subjects = Subject.query.filter_by(user_id=current_user.id).all()
            owned_subject_names = [s.name for s in owned_subjects]
            
            # Kombinera båda listorna
            all_teacher_subjects = list(set(teacher_subjects_list + owned_subject_names))
            
            print(f"[DEBUG] Teacher {current_user.username} teaches: {all_teacher_subjects}")
            
            # Hämta schema för läraren baserat på skola och ämnen
            schedule_items = []
            
            # Metod 1: Baserat på subjects som läraren äger/undervisar
            for subject_name in all_teacher_subjects:
                # Hitta subject objekt
                subject_obj = Subject.query.filter_by(name=subject_name).first()
                if subject_obj:
                    # Hämta schemalagda lektioner för detta ämne
                    schedule_query = db.session.query(ClassSchedule).filter(
                        ClassSchedule.weekday == weekday_swe,
                        ClassSchedule.subject_id == subject_obj.id
                    ).order_by(ClassSchedule.start_time).all()
                    
                    for item in schedule_query:
                        school_class = SchoolClass.query.get(item.class_id)
                        if school_class and school_class.school_id == current_user.school_id:
                            schedule_items.append({
                                'id': item.id,
                                'start_time': item.start_time,
                                'end_time': item.end_time,
                                'subject': subject_name,
                                'room': item.room or 'Okänt rum',
                                'weekday': item.weekday,
                                'class_name': school_class.name,
                                'type': 'teaching'
                            })
            
            # Metod 2: Om inga specifika ämnen, visa alla lektioner på skolan (fallback)
            if not schedule_items and current_user.school_id and current_user.school_id > 0:
                print(f"[DEBUG] No subject-specific lessons found, showing all school lessons as fallback")
                
                schedule_query = db.session.query(ClassSchedule).join(
                    SchoolClass, ClassSchedule.class_id == SchoolClass.id
                ).filter(
                    ClassSchedule.weekday == weekday_swe,
                    SchoolClass.school_id == current_user.school_id,
                    SchoolClass.is_active == True
                ).order_by(ClassSchedule.start_time).all()
                
                for item in schedule_query:
                    school_class = SchoolClass.query.get(item.class_id)
                    subject_name = "Matematik"  # Default
                    if item.subject_id:
                        subject = Subject.query.get(item.subject_id)
                        if subject:
                            subject_name = subject.name
                    
                    schedule_items.append({
                        'id': item.id,
                        'start_time': item.start_time,
                        'end_time': item.end_time,
                        'subject': subject_name,
                        'room': item.room or 'Okänt rum',
                        'weekday': item.weekday,
                        'class_name': school_class.name if school_class else "Okänd klass",
                        'type': 'teaching'
                    })
            
            # Metod 3: Om läraren är klassföreståndare, visa även klassens schema
            homeroom_classes = SchoolClass.query.filter_by(homeroom_teacher_id=current_user.id).all()
            for class_obj in homeroom_classes:
                class_schedule = db.session.query(ClassSchedule).filter(
                    ClassSchedule.class_id == class_obj.id,
                    ClassSchedule.weekday == weekday_swe
                ).order_by(ClassSchedule.start_time).all()
                
                for item in class_schedule:
                    # Kontrollera om vi redan har denna lektion (undvik duplicering)
                    existing = any(
                        s['id'] == item.id for s in schedule_items
                    )
                    if not existing:
                        subject_name = "Matematik"  # Default
                        if item.subject_id:
                            subject = Subject.query.get(item.subject_id)
                            if subject:
                                subject_name = subject.name
                        
                        schedule_items.append({
                            'id': item.id,
                            'start_time': item.start_time,
                            'end_time': item.end_time,
                            'subject': subject_name,
                            'room': item.room or 'Okänt rum',
                            'weekday': item.weekday,
                            'class_name': class_obj.name,
                            'type': 'homeroom'
                        })
            
            # Sortera efter tid
            schedule_items.sort(key=lambda x: x['start_time'])
            
            print(f"[DEBUG] Found {len(schedule_items)} lessons for teacher {current_user.username}")
            
            return jsonify({
                'status': 'success',
                'schedule': schedule_items,
                'date': date,
                'weekday': weekday_swe,
                'user_type': 'teacher',
                'school_name': current_user.get_school_name() if hasattr(current_user, 'get_school_name') else 'Okänd skola',
                'debug_info': {
                    'teacher_subjects': all_teacher_subjects,
                    'school_id': current_user.school_id,
                    'homeroom_classes': [c.name for c in homeroom_classes]
                }
            })
        
        else:
            # ELEV: Befintlig logik (fungerar redan)
            if not current_user.class_id or current_user.class_id == 0:
                return jsonify({
                    'status': 'success',
                    'schedule': [],
                    'message': 'Ingen klass tilldelad',
                    'user_type': 'student'
                })
            
            # Hämta schema från databasen
            schedule_query = db.session.query(ClassSchedule).filter_by(
                class_id=current_user.class_id,
                weekday=weekday_swe
            ).order_by(ClassSchedule.start_time).all()
            
            schedule_items = []
            for item in schedule_query:
                # Hämta ämnesnamn om subject_id finns
                subject_name = "Matematik"  # Default för test
                if item.subject_id:
                    subject = Subject.query.get(item.subject_id)
                    if subject:
                        subject_name = subject.name
                
                schedule_items.append({
                    'id': item.id,
                    'start_time': item.start_time,
                    'end_time': item.end_time,
                    'subject': subject_name,
                    'room': item.room or 'Okänt rum',
                    'weekday': item.weekday,
                    'type': 'lesson'
                })
            
            return jsonify({
                'status': 'success',
                'schedule': schedule_items,
                'date': date,
                'weekday': weekday_swe,
                'user_type': 'student',
                'class_name': current_user.get_class_name() if hasattr(current_user, 'get_class_name') else 'Okänd klass'
            })
        
    except ValueError:
        return jsonify({
            'status': 'error',
            'message': 'Ogiltigt datumformat. Använd YYYY-MM-DD'
        }), 400
    except Exception as e:
        print(f"Error fetching schedule: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Kunde inte hämta schema',
            'error_details': str(e)
        }), 500


# Also add this helper route to test teacher schedule setup
@app.route('/api/teacher/setup_schedule')
@login_required
def setup_teacher_schedule():
    """Helper route för att sätta upp ett testschema för lärare"""
    if not current_user.is_teacher():
        return jsonify({'error': 'Only teachers can access this'}), 403
    
    try:
        # Kontrollera om läraren har en skola och ämnen
        if not current_user.school_id or current_user.school_id == 0:
            return jsonify({
                'status': 'error',
                'message': 'Läraren har ingen skola tilldelad'
            })
        
        # Kontrollera lärarens ämnen
        teacher_subjects = []
        if current_user.teacher_subjects:
            teacher_subjects = [s.strip() for s in current_user.teacher_subjects.split(',')]
        
        owned_subjects = Subject.query.filter_by(user_id=current_user.id).all()
        
        return jsonify({
            'status': 'success',
            'teacher_info': {
                'id': current_user.id,
                'name': current_user.get_full_name(),
                'school_id': current_user.school_id,
                'school_name': current_user.get_school_name(),
                'teacher_subjects': teacher_subjects,
                'owned_subjects': [{'id': s.id, 'name': s.name} for s in owned_subjects],
                'is_homeroom_teacher': current_user.is_homeroom_teacher(),
                'homeroom_classes': [{'id': c.id, 'name': c.name} for c in current_user.get_homeroom_classes()]
            }
        })
        
    except Exception as e:
        print(f"Error in teacher setup: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Lägg till dessa routes i din Flask app

@app.route('/api/lunch_menu')
@login_required
def get_lunch_menu():
    """Hämta matsedel för användarens skola för en vecka"""
    try:
        # Hämta användarens skola
        user_school_id = current_user.school_id
        if not user_school_id or user_school_id == 0:
            return jsonify({
                'status': 'error',
                'message': 'Du är inte kopplad till någon skola'
            }), 400
        
        # Hämta datum från query parameter eller använd dagens datum
        from datetime import datetime, timedelta
        
        date_param = request.args.get('date')
        if date_param:
            try:
                target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                target_date = datetime.now().date()
        else:
            target_date = datetime.now().date()
        
        print(f"📅 Hämtar matsedel för datum: {target_date}, skola: {user_school_id}")
        
        # Hämta veckan (måndag till fredag)
        days_since_monday = target_date.weekday()
        monday = target_date - timedelta(days=days_since_monday)
        friday = monday + timedelta(days=4)
        
        print(f"📅 Vecka: {monday} till {friday}")
        
        # Hämta matsedel för veckan
        lunch_menus = LunchMenu.query.filter(
            LunchMenu.school_id == user_school_id,
            LunchMenu.menu_date >= monday,
            LunchMenu.menu_date <= friday
        ).order_by(LunchMenu.menu_date).all()
        
        print(f"🍽️ Hittade {len(lunch_menus)} matsedlar i databasen")
        
        # Debug: Visa vad som finns i databasen
        for menu in lunch_menus:
            print(f"   - {menu.menu_date}: {menu.main_dish[:30]}...")
        
        # Skapa en lista för alla veckodagar
        menu_data = []
        swedish_days = ['Måndag', 'Tisdag', 'Onsdag', 'Torsdag', 'Fredag']
        
        for i in range(5):  # Måndag till fredag
            current_date = monday + timedelta(days=i)
            menu_for_day = next((menu for menu in lunch_menus if menu.menu_date == current_date), None)
            
            day_data = {
                'date': current_date.isoformat(),
                'day_name': current_date.strftime('%A'),
                'day_name_sv': swedish_days[i],
                'has_menu': menu_for_day is not None
            }
            
            if menu_for_day:
                day_data.update({
                    'main_dish': menu_for_day.main_dish or 'Ingen huvudrätt angiven',
                    'vegetarian_dish': menu_for_day.vegetarian_dish or 'Ingen vegetarisk rätt angiven',
                    'side_dishes': menu_for_day.side_dishes or 'Inga tillbehör angivna',
                    'dessert': menu_for_day.dessert or 'Ingen efterrätt angiven',
                    'allergens': menu_for_day.allergens or 'Inga allergener angivna'
                })
                print(f"✅ Data för {swedish_days[i]}: {menu_for_day.main_dish}")
            else:
                day_data.update({
                    'main_dish': 'Ingen matsedel tillgänglig',
                    'vegetarian_dish': None,
                    'side_dishes': None,
                    'dessert': None,
                    'allergens': None
                })
                print(f"❌ Ingen data för {swedish_days[i]} ({current_date})")
            
            menu_data.append(day_data)
        
        return jsonify({
            'status': 'success',
            'school_id': user_school_id,
            'week_start': monday.isoformat(),
            'week_end': friday.isoformat(),
            'menu_data': menu_data,
            'debug_info': {
                'target_date': target_date.isoformat(),
                'monday': monday.isoformat(),
                'friday': friday.isoformat(),
                'menus_found': len(lunch_menus),
                'user_school_id': user_school_id
            }
        })
        
    except Exception as e:
        print(f"❌ Error fetching lunch menu: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'Kunde inte hämta matsedel: {str(e)}'
        }), 500
    

@app.route('/api/schedule/current')
@login_required 
def get_current_schedule():
    """Hämta schema för dagens datum"""
    today = datetime.now().strftime('%Y-%m-%d')
    return get_schedule_for_date(today)

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
        print(f"Extracting audio from {video_path} to {audio_output_path}")
        
        # Kontrollera att videofilen existerar
        if not os.path.exists(video_path):
            print(f"Video file not found: {video_path}")
            return False
            
        video = VideoFileClip(video_path)
        
        # Kontrollera att videon har ljud
        if video.audio is None:
            print("Video has no audio track")
            video.close()
            return False
            
        audio = video.audio
        
        # Ta bort verbose parametern som inte längre stöds
        audio.write_audiofile(audio_output_path, logger=None)
        
        # Stäng resurser
        audio.close()
        video.close()
        
        # Kontrollera att ljudfilen skapades
        if os.path.exists(audio_output_path) and os.path.getsize(audio_output_path) > 0:
            print(f"Audio extraction successful. File size: {os.path.getsize(audio_output_path) / (1024*1024):.1f}MB")
            return True
        else:
            print("Audio file was not created or is empty")
            return False
            
    except Exception as e:
        print(f"Error extracting audio: {str(e)}")
        return False

# Lägg till dessa routes i din Flask-app

@app.route('/attendance/lesson/<int:schedule_id>/<date>')
@login_required
def attendance_lesson(schedule_id, date):
    """Visa närvarorapporteringssida för en specifik lektion"""
    
    # Kontrollera att användaren är lärare
    if not current_user.is_teacher():
        flash('Endast lärare kan rapportera närvaro.', 'error')
        return redirect(url_for('index'))
    
    try:
        # Validera datum
        lesson_date = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        flash('Ogiltigt datumformat.', 'error')
        return redirect(url_for('index'))
    
    # Hämta lektionen från schemat
    schedule_item = ClassSchedule.query.get_or_404(schedule_id)
    
    # Kontrollera att läraren har behörighet att rapportera för denna lektion
    # (äger ämnet, är klassföreståndare, eller undervisar ämnet)
    can_report = False
    
    # Kontroll 1: Är klassföreståndare
    if schedule_item.school_class.homeroom_teacher_id == current_user.id:
        can_report = True
    
    # Kontrol 2: Undervisar ämnet
    if schedule_item.subject_id:
        subject = Subject.query.get(schedule_item.subject_id)
        if subject and subject.user_id == current_user.id:
            can_report = True
        
        # Eller om läraren undervisar ämnet enligt teacher_subjects
        if current_user.teacher_subjects:
            teacher_subjects = [s.strip().lower() for s in current_user.teacher_subjects.split(',')]
            if subject and subject.name.lower() in teacher_subjects:
                can_report = True
    
    # Kontroll 3: Samma skola
    if schedule_item.school_class.school_id != current_user.school_id:
        can_report = False
    
    if not can_report:
        flash('Du har inte behörighet att rapportera närvaro för denna lektion.', 'error')
        return redirect(url_for('index'))
    
    # Hämta alla elever i klassen
    students = schedule_item.get_students_for_lesson()
    
    # Kontrollera om närvaro redan är rapporterad
    existing_attendance = schedule_item.get_attendance_for_date(lesson_date)
    
    # Om närvaro redan existerar, hämta befintlig data
    student_attendance_data = {}
    if existing_attendance:
        for sa in existing_attendance.student_attendances:
            student_attendance_data[sa.student_id] = {
                'status': sa.status,
                'notes': sa.notes or '',
                'arrival_time': sa.arrival_time.strftime('%H:%M') if sa.arrival_time else ''
            }
    
    return render_template('attendance/report_attendance.html',
                         schedule_item=schedule_item,
                         lesson_date=lesson_date,
                         students=students,
                         existing_attendance=existing_attendance,
                         student_attendance_data=student_attendance_data)


@app.route('/api/attendance/save', methods=['POST'])
@login_required
def save_attendance():
    """Spara närvarorapport"""
    
    if not current_user.is_teacher():
        return jsonify({'status': 'error', 'message': 'Endast lärare kan rapportera närvaro'}), 403
    
    try:
        data = request.get_json()
        
        schedule_id = data.get('schedule_id')
        date_str = data.get('date')
        lesson_notes = data.get('lesson_notes', '')
        attendance_data = data.get('attendance_data', {})
        
        # Validera input
        if not schedule_id or not date_str:
            return jsonify({'status': 'error', 'message': 'Saknar obligatorisk data'}), 400
        
        lesson_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        schedule_item = ClassSchedule.query.get(schedule_id)
        
        if not schedule_item:
            return jsonify({'status': 'error', 'message': 'Lektion hittades inte'}), 404
        
        # Kontrollera behörighet (samma som ovan)
        can_report = False
        if schedule_item.school_class.homeroom_teacher_id == current_user.id:
            can_report = True
        elif schedule_item.subject_id:
            subject = Subject.query.get(schedule_item.subject_id)
            if subject and subject.user_id == current_user.id:
                can_report = True
        
        if not can_report:
            return jsonify({'status': 'error', 'message': 'Ingen behörighet'}), 403
        
        # Hitta eller skapa närvarorapport
        attendance = Attendance.query.filter_by(
            schedule_id=schedule_id,
            date=lesson_date
        ).first()
        
        if not attendance:
            attendance = Attendance(
                schedule_id=schedule_id,
                date=lesson_date,
                teacher_id=current_user.id,
                class_id=schedule_item.class_id,
                subject_id=schedule_item.subject_id,
                lesson_notes=lesson_notes
            )
            db.session.add(attendance)
            db.session.flush()  # För att få ID
        else:
            # Uppdatera befintlig
            attendance.lesson_notes = lesson_notes
            attendance.updated_at = datetime.utcnow()
        
        # Ta bort befintlig elevnärvaro för denna lektion
        StudentAttendance.query.filter_by(attendance_id=attendance.id).delete()
        
        # Lägg till ny elevnärvaro
        for student_id_str, student_data in attendance_data.items():
            student_id = int(student_id_str)
            status = student_data.get('status', 'present')
            notes = student_data.get('notes', '')
            arrival_time_str = student_data.get('arrival_time', '')
            
            # Parsa ankomsttid om den finns
            arrival_time = None
            if arrival_time_str and status == 'late':
                try:
                    arrival_time = datetime.combine(
                        lesson_date,
                        datetime.strptime(arrival_time_str, '%H:%M').time()
                    )
                except ValueError:
                    pass  # Ignorera felaktig tidsformatering
            
            student_attendance = StudentAttendance(
                attendance_id=attendance.id,
                student_id=student_id,
                status=status,
                arrival_time=arrival_time,
                notes=notes
            )
            db.session.add(student_attendance)
        
        db.session.commit()
        
        # Hämta sammanfattning
        summary = attendance.get_attendance_summary()
        
        return jsonify({
            'status': 'success',
            'message': 'Närvaro sparad framgångsrikt',
            'summary': summary
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error saving attendance: {e}")
        return jsonify({'status': 'error', 'message': 'Fel vid sparande av närvaro'}), 500


@app.route('/api/attendance/lesson/<int:schedule_id>/<date>')
@login_required
def get_lesson_attendance(schedule_id, date):
    """Hämta närvarodata för en specifik lektion"""
    
    if not current_user.is_teacher():
        return jsonify({'status': 'error', 'message': 'Ingen behörighet'}), 403
    
    try:
        lesson_date = datetime.strptime(date, '%Y-%m-%d').date()
        schedule_item = ClassSchedule.query.get_or_404(schedule_id)
        
        # Hämta närvarorapport om den finns
        attendance = schedule_item.get_attendance_for_date(lesson_date)
        
        if attendance:
            summary = attendance.get_attendance_summary()
            return jsonify({
                'status': 'success',
                'has_attendance': True,
                'attendance_id': attendance.id,
                'lesson_notes': attendance.lesson_notes,
                'summary': summary,
                'last_updated': attendance.updated_at.isoformat()
            })
        else:
            return jsonify({
                'status': 'success',
                'has_attendance': False
            })
            
    except Exception as e:
        print(f"Error getting attendance: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500



@app.route('/attendance/history/<int:class_id>')
@login_required
def attendance_history(class_id):
    # 1) Behörighet: bara lärare
    if not current_user.is_teacher():
        flash('Endast lärare kan se närvarohistorik.', 'error')
        return redirect(url_for('index'))

    # 2) Alla klasser där hen är mentor
    mentor_q = SchoolClass.query.filter(
        SchoolClass.homeroom_teacher_id == current_user.id
    )

    # 3) Alla klasser där hen undervisar via Subject
    taught_class_ids = db.session.query(
        distinct(ClassSchedule.class_id)
    ).join(Subject).filter(
        Subject.user_id == current_user.id
    )

    # 4) Slå ihop till en lista
    teacher_classes = SchoolClass.query.filter(
        or_(
            SchoolClass.id.in_(taught_class_ids),
            SchoolClass.homeroom_teacher_id == current_user.id
        )
    ).order_by(SchoolClass.name).all()

    # 5) Validera class_id, annars redirect till första giltiga
    valid_ids = {c.id for c in teacher_classes}
    if class_id not in valid_ids:
        return redirect(url_for('attendance_history', class_id=teacher_classes[0].id))

    school_class = SchoolClass.query.get_or_404(class_id)

    # —————— Periodhantering ——————
    period = request.args.get('period', '30')
    today = datetime.now().date()
    if period == '7':
        start_date = today - timedelta(days=7)
    elif period == 'all':
        start_date = school_class.start_date or (today - timedelta(days=3650))
    else:
        start_date = today - timedelta(days=30)
        period = '30'

    # —————— Hämta närvarorapporter ——————
    attendance_records = Attendance.query.options(
        joinedload(Attendance.student_attendances)
    ).filter(
        Attendance.class_id == class_id,
        Attendance.date.between(start_date, today)
    ).order_by(
        Attendance.date.desc(),
        Attendance.created_at.desc()
    ).all()

    # — Per-lektion-summeringar —  
    summaries = {rec.id: rec.get_attendance_summary() for rec in attendance_records}

    # — Aggregat —  
    total_lessons  = len(attendance_records)
    total_students = sum(d['total']   for d in summaries.values())
    total_present  = sum(d['present'] for d in summaries.values())
    total_late     = sum(d['late']    for d in summaries.values())
    total_absent   = sum(d['absent']  for d in summaries.values())
    total_excused  = sum(d.get('excused', 0) for d in summaries.values())
    avg_attendance = round(((total_present + total_late + total_excused) / total_students * 100) if total_students else 0, 1)

    # — Hämta elever i klassen —  
    students = User.query.filter_by(
        class_id=class_id,
        user_type='student'
    ).order_by(User.last_name, User.first_name).all()

    # — Per-elev-statistik —  
    student_stats = []
    for student in students:
        sats = [
            sa for rec in attendance_records
               for sa in rec.student_attendances
               if sa.student_id == student.id
        ]
        cnt_tot  = len(sats)
        cnt_pres = sum(1 for sa in sats if sa.status == 'present')
        cnt_late = sum(1 for sa in sats if sa.status == 'late')
        cnt_abs  = sum(1 for sa in sats if sa.status == 'absent')
        cnt_exc  = sum(1 for sa in sats if sa.status == 'excused')
        rate     = round(((cnt_pres + cnt_late + cnt_exc) / cnt_tot * 100) if cnt_tot else 0, 1)

        student_stats.append({
            'name':    f"{student.first_name} {student.last_name}",
            'total':   cnt_tot,
            'present': cnt_pres,
            'late':    cnt_late,
            'absent':  cnt_abs,
            'excused': cnt_exc,
            'rate':    rate
        })

    # — Returnera allt till templaten —  
    return render_template('attendance/history.html',
        school_class       = school_class,
        teacher_classes    = teacher_classes,
        current_class_id   = class_id,
        period             = period,

        attendance_records = attendance_records,
        summaries          = summaries,

        total_lessons      = total_lessons,
        total_present      = total_present,
        total_late         = total_late,
        total_absent       = total_absent,
        total_excused      = total_excused,
        avg_attendance     = avg_attendance,

        student_stats      = student_stats
    )


def compress_audio_if_needed(audio_path, max_size_mb=25):
    """Komprimera ljud om det är för stort - mer realistisk storlek"""
    try:
        # Kontrollera att filen existerar
        if not os.path.exists(audio_path):
            print(f"Audio file not found: {audio_path}")
            return audio_path
            
        # Kontrollera filstorlek
        file_size = os.path.getsize(audio_path)
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if file_size <= max_size_bytes:
            print(f"Audio file size OK: {file_size / (1024*1024):.1f}MB")
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
        target_bitrate_kbps = max(32, min(128, target_bitrate_kbps))  # Sänkt minimum till 32kbps
        
        print(f"Compressing to {target_bitrate_kbps}kbps...")
        
        # Exportera med lägre kvalitet för mindre filstorlek
        audio.export(
            temp_compressed,
            format="wav",
            parameters=[
                "-ac", "1",      # Mono
                "-ar", "16000",  # Lägre samplerate
                "-b:a", f"{target_bitrate_kbps}k"  # Bitrate
            ]
        )
        
        # Kontrollera att den komprimerade filen blev mindre
        if os.path.exists(temp_compressed):
            compressed_size = os.path.getsize(temp_compressed)
            print(f"Compression result: {compressed_size / (1024*1024):.1f}MB")
            
            if compressed_size < max_size_bytes:
                print("Compression successful!")
                return temp_compressed
            else:
                print(f"File still too large after compression: {compressed_size / (1024*1024):.1f}MB")
                return temp_compressed  # Returnera ändå, kanske fungerar
        else:
            print("Compressed file was not created")
            return audio_path
            
    except Exception as e:
        print(f"Error compressing audio: {str(e)}")
        return audio_path 

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


def get_user_role_in_subject(user_id, subject_id):
    """Hjälpfunktion för att få användarens roll i ett ämne"""
    user = User.query.get(user_id)
    if not user:
        return None
    return user.get_role_in_subject(subject_id)


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


def transcribe_with_huggingface(audio_file_path, chunk_duration_ms=30_000):
    """
    Transkribera ljud med Hugging Face Inference API genom att dela upp
    filen i chunk_duration_ms-långa segment och slå ihop resultaten.
    """
    hf_token = os.getenv("HF_API_TOKEN")
    if not hf_token:
        print("Ingen HF_API_TOKEN uppsatt, kan inte använda Hugging Face API")
        return None

    # Ladda hela ljudfilen
    audio = AudioSegment.from_file(audio_file_path)
    total_length_ms = len(audio)
    num_chunks = math.ceil(total_length_ms / chunk_duration_ms)
    print(f"Total längd: {total_length_ms/1000:.1f}s, delar i {num_chunks} chunkar om {chunk_duration_ms/1000:.1f}s vardera")

    full_transcription = []

    API_URL = "https://api-inference.huggingface.co/models/openai/whisper-tiny"
    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": "audio/wav"
    }

    for i in range(num_chunks):
        start_ms = i * chunk_duration_ms
        end_ms = min((i+1) * chunk_duration_ms, total_length_ms)
        chunk = audio[start_ms:end_ms]

        # Exportera chunk till wav i minnesfil
        chunk_wav_path = f"/tmp/chunk_{i}.wav"
        chunk.set_frame_rate(16000).set_channels(1).export(chunk_wav_path, format="wav")

        # Läs in och kontrollera storlek
        data = open(chunk_wav_path, 'rb').read()
        size_mb = len(data) / (1024*1024)
        print(f"Chunk {i+1}/{num_chunks}: {size_mb:.2f}MB")

        if size_mb > 10:
            print(f"  ⚠️ Chunk {i+1} är för stor ({size_mb:.2f}MB), minska chunk_duration_ms eller komprimera mer.")
            return None

        # Skicka till API
        resp = requests.post(API_URL, headers=headers, data=data, timeout=120)
        if resp.status_code == 200:
            result = resp.json()
            text = (result.get('text') or result.get('generated_text') or "").strip()
            full_transcription.append(text)
            print(f"  ✅ Chunk {i+1} transkriberad ({len(text)} tecken)")
        elif resp.status_code == 503:
            # Model loading – vänta och gör ett försök till
            time.sleep(10)
            resp = requests.post(API_URL, headers=headers, data=data, timeout=180)
            if resp.status_code == 200:
                text = resp.json().get('text', '').strip()
                full_transcription.append(text)
            else:
                print(f"  ❌ API-fel vid chunk {i+1}: {resp.status_code}")
                full_transcription.append(f"[Fel vid chunk {i+1}: HTTP {resp.status_code}]")
        else:
            print(f"  ❌ API-fel vid chunk {i+1}: {resp.status_code}")
            full_transcription.append(f"[Fel vid chunk {i+1}: HTTP {resp.status_code}]")

        # Radera temporär chunk
        os.remove(chunk_wav_path)

    # Slå ihop alla chunk-transkriptioner
    return "\n\n".join(full_transcription)


def transcribe_with_local_whisper(audio_path, model_size="base"):
    """
    Transkribera med lokal Whisper-modell.
    model_size kan vara "tiny", "base", "small", "medium", eller "large".
    """
    try:
        print(f"🔊 Använder lokal Whisper ({model_size}) för: {audio_path}")
        model = whisper.load_model(model_size)
        result = model.transcribe(audio_path)
        return result.get("text", "").strip()
    except Exception as e:
        print(f"Fel vid lokal Whisper-transkribering: {e}")
        return None


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



# Lägg till dessa routes i din Flask-app

@app.route('/school_news')
@login_required
def school_news():
    """Separat sida för alla skolnyheter"""
    try:
        # Kontrollera att användaren har en skola
        if not current_user.school_id or current_user.school_id == 0:
            flash('Du är inte kopplad till någon skola', 'warning')
            return redirect(url_for('index'))
        
        # Hämta ALLA nyheter för användarens skola (inte bara 5 som på huvudsidan)
        news = SchoolNews.query.filter_by(
            school_id=current_user.school_id,
            is_active=True
        ).order_by(SchoolNews.created_at.desc()).all()
        
        # Hämta skolans namn
        school = School.query.get(current_user.school_id)
        school_name = school.name if school else "Din skola"
        
        return render_template('school_news.html', 
                             news=news, 
                             school_name=school_name)
        
    except Exception as e:
        print(f"[ERROR] Failed to load school news page: {e}")
        flash(f'Fel vid hämtning av nyheter: {str(e)}', 'error')
        return redirect(url_for('index'))

    

@app.route('/api/school_news')
@login_required
def api_school_news():
    """API endpoint för att hämta skolnyheter"""
    try:
        if not current_user.school_id or current_user.school_id == 0:
            return jsonify({
                'status': 'error',
                'message': 'Ingen skola tilldelad'
            }), 400
        
        news = SchoolNews.query.filter_by(
            school_id=current_user.school_id,
            is_active=True
        ).order_by(SchoolNews.created_at.desc()).all()
        
        return jsonify({
            'status': 'success',
            'news': [news_item.to_dict() for news_item in news]
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500



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
            if not transcription or transcription.startswith("Fel") or transcription.startswith("[Fel"):
                print("Alla API-metoder misslyckades, försöker lokal Whisper…")
                local_text = transcribe_with_local_whisper(audio_path, model_size="base")
                if local_text:
                    transcription = local_text

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


@app.route('/api/subjects/by-name/<subject_name>')
@login_required
def get_subject_by_name(subject_name):
    """Hämta subject_id baserat på subject name"""
    try:
        subject = Subject.query.filter_by(name=subject_name).first()
        
        if not subject:
            return jsonify({'status': 'error', 'message': 'Subject not found'}), 404
        
        # Kontrollera att användaren har tillgång
        if not current_user.is_member_of_subject(subject.id):
            return jsonify({'status': 'error', 'message': 'Access denied'}), 403
        
        return jsonify({
            'status': 'success',
            'subject_id': subject.id,
            'subject_name': subject.name
        })
        
    except Exception as e:
        print(f"Error in get_subject_by_name: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500



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
            'message': 'Lesson uploaded successfully',
            'lesson_id': lesson.id  # Lägg till denna rad
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


@app.route('/subject/<subject_name>/save-email', methods=['POST'])
@login_required
def save_owner_email(subject_name):
    try:
        # Hämta subject från databasen
        subject = Subject.query.filter_by(name=subject_name).first()
        if not subject:
            return jsonify({'success': False, 'error': 'Subject not found'}), 404
        
        # Kontrollera att användaren är ägare
        if subject.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Not authorized'}), 403
        
        # Hämta email från request
        data = request.get_json()
        if not data or 'email' not in data:
            return jsonify({'success': False, 'error': 'Email is required'}), 400
        
        email = data['email'].strip()
        
        # Validera email-format
        import re
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_pattern, email):
            return jsonify({'success': False, 'error': 'Invalid email format'}), 400
        
        # Spara email till subject
        subject.owner_email = email
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Email saved successfully'})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error saving owner email: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


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



@app.route('/api/subject/<int:subject_id>/members/detailed')
@login_required
def get_subject_members_detailed(subject_id):
    """Hämta detaljerad medlemslista för ett ämne"""
    try:
        # Kontrollera att användaren har tillgång till ämnet
        subject = Subject.query.get_or_404(subject_id)
        user_role = current_user.get_role_in_subject(subject_id)
        
        if not user_role:
            return jsonify({'status': 'error', 'message': 'Du har inte tillgång till detta ämne'})
        
        # Endast ägare kan se detaljerad medlemslista
        if user_role != 'owner':
            return jsonify({'status': 'error', 'message': 'Endast ägare kan se medlemslistan'})
        
        # Hämta alla medlemmar (inkluderar ägaren)
        members = []
        
        # Lägg till ägaren först
        owner = User.query.get(subject.user_id)
        if owner:
            members.append({
                'id': owner.id,
                'username': owner.username,
                'email': getattr(owner, 'email', None),  # Om du har email-fält
                'role': 'owner',
                'joined_at': subject.created_at.isoformat() if subject.created_at else None
            })
        
        # Hämta alla andra medlemmar
        subject_members = db.session.query(SubjectMember, User).join(
            User, SubjectMember.user_id == User.id
        ).filter(SubjectMember.subject_id == subject_id).all()
        
        for membership, user in subject_members:
            members.append({
                'id': user.id,
                'username': user.username,
                'email': getattr(user, 'email', None),  # Om du har email-fält
                'role': membership.role,
                'joined_at': membership.joined_at.isoformat() if membership.joined_at else None
            })
        
        return jsonify({
            'status': 'success',
            'members': members
        })
        
    except Exception as e:
        print(f"Error getting subject members: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Kunde inte hämta medlemmar'
        })
    





@app.route('/api/subject/kick_member', methods=['POST'])
@login_required
def kick_subject_member():
    """Kicka en medlem från ett ämne"""
    try:
        data = request.get_json()
        subject_id = data.get('subject_id')
        member_id = data.get('member_id')
        
        if not subject_id or not member_id:
            return jsonify({'status': 'error', 'message': 'Saknade parametrar'})
        
        # Kontrollera att användaren är ägare av ämnet
        subject = Subject.query.get_or_404(subject_id)
        if subject.user_id != current_user.id:
            return jsonify({'status': 'error', 'message': 'Endast ägare kan kicka medlemmar'})
        
        # Kontrollera att man inte försöker kicka sig själv
        if member_id == current_user.id:
            return jsonify({'status': 'error', 'message': 'Du kan inte kicka dig själv'})
        
        # Hitta och ta bort medlemskapet
        membership = SubjectMember.query.filter_by(
            subject_id=subject_id, 
            user_id=member_id
        ).first()
        
        if not membership:
            return jsonify({'status': 'error', 'message': 'Medlemmen hittades inte'})
        
        # Ta bort medlemskapet
        db.session.delete(membership)
        db.session.commit()
        
        # Hämta användarnamn för meddelande
        kicked_user = User.query.get(member_id)
        username = kicked_user.username if kicked_user else 'Okänd användare'
        
        return jsonify({
            'status': 'success',
            'message': f'{username} har kickats från ämnet'
        })
        
    except Exception as e:
        print(f"Error kicking member: {e}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Kunde inte kicka medlem'
        })

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




@app.route('/send_message_only', methods=['POST'])
@login_required
def send_message_only():
    try:
        data = request.get_json()
        subject_name = data.get('subject')
        message = data.get('message', '').strip()
        
        if not subject_name or not message:
            return jsonify({'status': 'error', 'message': 'Ämne och meddelande krävs'})
        
        # Hitta ämnet
        subject = Subject.query.filter_by(name=subject_name).first()
        if not subject:
            return jsonify({'status': 'error', 'message': 'Ämne hittades inte'})
        
        # Kontrollera behörighet - endast ägaren kan skicka meddelanden
        if subject.user_id != current_user.id:
            return jsonify({'status': 'error', 'message': 'Ingen behörighet'})
        
        # Skapa meddelande som en "fil" utan faktisk fil
        shared_file = SharedFile(
            subject_id=subject.id,
            user_id=current_user.id,
            filename='message',  # Placeholder filename
            original_filename='message',
            file_path='',  # Tom path för meddelanden
            file_size=0,
            file_extension='',
            file_type='message',
            description=message,
            is_message=True
        )
        
        db.session.add(shared_file)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Meddelande skickat'})
        
    except Exception as e:
        print(f"Error sending message: {e}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Serverfel'})


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
        
        # *** NYTT: Skapa flashcards för befintliga shared quizzes ***
        flashcards_created = create_flashcards_for_new_member(current_user.id, subject.id)
        
        response_message = f'Successfully joined "{subject.name}"'
        if flashcards_created > 0:
            response_message += f' and created {flashcards_created} flashcards for existing quizzes'
        
        return jsonify({
            'status': 'success',
            'message': response_message,
            'subject_name': subject.name,
            'flashcards_created': flashcards_created
        })
        
    except Exception as e:
        print(f"[ERROR] Failed to join subject: {e}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Failed to join subject'}), 500

# Also add a utility function to retroactively fix existing members
def fix_existing_members_flashcards():
    """
    Fixa flashcards för befintliga medlemmar som gått med innan denna funktionalitet fanns
    """
    try:
        fixed_members = 0
        total_flashcards = 0
        
        # Hämta alla subject memberships
        memberships = SubjectMember.query.all()
        
        for membership in memberships:
            # Kontrollera om medlemmen saknar flashcards för shared quizzes
            shared_quizzes = Quiz.query.filter_by(
                subject_id=membership.subject_id,
                is_personal=False
            ).all()
            
            for quiz in shared_quizzes:
                # Kontrollera om användaren redan har flashcards för detta quiz
                existing_flashcards = Flashcard.query.filter_by(
                    user_id=membership.user_id,
                    subject_id=quiz.subject_id,
                    topic=quiz.title
                ).count()
                
                expected_flashcards = len(quiz.questions or [])
                
                if existing_flashcards < expected_flashcards:
                    # Skapa saknade flashcards
                    created = create_flashcards_for_user(quiz, membership.user_id)
                    if created > 0:
                        total_flashcards += created
                        if membership.user_id not in [m.user_id for m in memberships[:memberships.index(membership)]]:
                            fixed_members += 1
        
        print(f"[FIX] Fixed {fixed_members} members with {total_flashcards} new flashcards")
        return fixed_members, total_flashcards
        
    except Exception as e:
        print(f"[ERROR] Failed to fix existing members: {e}")
        return 0, 0


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


@app.route('/')
@login_required
def index():
    """Huvudsida som visar alla ämnen användaren har tillgång till och skolnyheter"""
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
            
            # Räkna inlämnade uppgifter för medlemmar
            subject.pending_assignments = 0
            user_role = current_user.get_role_in_subject(subject.id)
            if user_role and user_role != 'owner':
                # Räkna uppgifter som inte är inlämnade än
                pending_assignments = db.session.query(Assignment).filter(
                    Assignment.subject_id == subject.id,
                    ~Assignment.id.in_(
                        db.session.query(AssignmentSubmission.assignment_id).filter(
                            AssignmentSubmission.student_id == current_user.id
                        )
                    )
                ).count()
                subject.pending_assignments = pending_assignments
            
            # Lägg till användarens roll
            subject.user_role = user_role
        
        # Hämta totala statistik för användaren
        total_due = Flashcard.query.filter(
            Flashcard.user_id == current_user.id,
            db.or_(
                Flashcard.next_review <= datetime.now().date(),
                Flashcard.next_review == None
            )
        ).count()
        
        # NYTT: Hämta skolnyheter om användaren har en skola
        news = []
        school_name = None
        if current_user.school_id and current_user.school_id != 0:
            try:
                # Hämta nyheter för användarens skola (senaste 5 nyheter)
                news = SchoolNews.query.filter_by(
                    school_id=current_user.school_id,
                    is_active=True
                ).order_by(SchoolNews.created_at.desc()).limit(5).all()
                
                # Hämta skolans namn
                school = School.query.get(current_user.school_id)
                school_name = school.name if school else "Din skola"
                
            except Exception as e:
                print(f"[WARNING] Could not load school news: {e}")
                # Fortsätt ändå utan nyheter
                news = []
        
        return render_template('index.html', 
                             owned_subjects=owned_subjects,
                             shared_subjects=shared_subjects,
                             total_due_flashcards=total_due,
                             news=news,
                             school_name=school_name)
        
    except Exception as e:
        print(f"[ERROR] Failed to load index: {e}")
        flash('Error loading page data', 'error')
        return render_template('index.html', 
                             owned_subjects=[], 
                             shared_subjects=[], 
                             total_due_flashcards=0,
                             news=[],
                             school_name=None)



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

@app.route('/api/subject/<int:subject_id>/shared_unread_count')
@login_required
def shared_unread_count(subject_id):
    # Hitta medlemspost
    member = SubjectMember.query.filter_by(
        subject_id=subject_id,
        user_id=current_user.id
    ).first_or_404()

    # Räkna alla aktiva SharedFile för ämnet med created_at > last_seen_shared_at
    unread = SharedFile.query.filter(
        SharedFile.subject_id == subject_id,
        SharedFile.created_at > member.last_seen_shared_at,
        SharedFile.is_active == True
    ).count()

    return jsonify({'status': 'success', 'unread_count': unread})


@app.route('/api/subject/<int:subject_id>/mark_shared_read', methods=['POST'])
@login_required
def mark_shared_read(subject_id):
    member = SubjectMember.query.filter_by(
        subject_id=subject_id,
        user_id=current_user.id
    ).first_or_404()

    member.last_seen_shared_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'status': 'success'})


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
    
    # Konvertera quiz-objekt till dictionaries och generera beskrivningar
    quizzes_dict = []
    for quiz in all_quizzes:
        quiz_dict = quiz.to_dict()
        
        # Generera kort beskrivning om den inte finns eller är tom
        if not quiz_dict.get('display_description'):
            quiz_dict['display_description'] = generate_quiz_description(quiz)
        
        quizzes_dict.append(quiz_dict)
    
    shared_quizzes_dict = [q for q in quizzes_dict if not q['is_personal']]
    personal_quizzes_dict = [q for q in quizzes_dict if q['is_personal'] and q['user_id'] == current_user.id]
    
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




def generate_quiz_description(quiz):
    """
    Generera en detaljerad beskrivning av quizet baserat på dess innehåll och frågor
    Fokuserar på vad quizet handlar om, inte antal frågor eller quiz-typ
    """
    try:
        questions = quiz.get_questions()
        
        if not questions or len(questions) == 0:
            return "Quiz utan frågor - innehåll ej tillgängligt"
        
        # Ta fler exempel frågor för bättre innehållsanalys
        sample_size = min(8, len(questions))  # Öka från 5 till 8 för bättre analys
        sample_questions = questions[:sample_size]
        
        # Extrahera både frågor och svar för djupare innehållsförståelse
        questions_and_answers = []
        for q in sample_questions:
            question_text = q['question'][:200] if len(q['question']) > 200 else q['question']
            answer_text = ""
            
            # Hantera olika svarsformat
            if isinstance(q.get('answer'), dict):
                if 'correct' in q['answer']:
                    answer_text = str(q['answer']['correct'])[:150]
                elif 'alternatives' in q['answer']:
                    alts = q['answer']['alternatives']
                    correct_idx = q['answer'].get('correct_index', 0)
                    if 0 <= correct_idx < len(alts):
                        answer_text = alts[correct_idx][:150]
            else:
                answer_text = str(q['answer'])[:150] if q.get('answer') else ""
            
            questions_and_answers.append(f"Fråga: {question_text}")
            if answer_text:
                questions_and_answers.append(f"Svar: {answer_text}")
        
        content_sample = "\n".join(questions_and_answers)
        
        # HELT NY PROMPT - fokuserar enbart på innehåll
        prompt = f"""Analysera detta quiz-innehåll och skriv en informativ beskrivning på svenska som förklarar vad quizet handlar om innehållsmässigt.

QUIZ-INNEHÅLL ATT ANALYSERA:
{content_sample}

INSTRUKTIONER:
- Fokusera ENDAST på vad quizet behandlar innehållsmässigt
- Nämn INTE antal frågor, quiz-typ eller tekniska detaljer
- Beskriv vilka specifika ämnesområden, koncept och kunskapsområden som behandlas
- Var konkret om vad studenten kommer att lära sig eller träna på
- Nämn specifika termer, teorier eller områden som tas upp
- Gör beskrivningen detaljerad nog att skilja detta quiz från andra liknande
- Längd: 180-280 tecken för att ge plats för detaljer
- Skriv som en sammanhängande text, inte punktlista

EXEMPEL PÅ BRA INNEHÅLLSFOKUSERADE BESKRIVNINGAR:
"Behandlar celldelning med fokus på mitos och meios, kromosombeteende under olika faser samt skillnader mellan somatiska celler och könsceller. Täcker även mutationer och deras påverkan på genetisk variation."

"Utforskar algebraiska ekvationslösning med andragradsekvationer, kvadratkomplettering och pq-formeln. Inkluderar grafisk tolkning av paraboler och praktisk problemlösning inom geometri och fysik."

"Fokuserar på svenska romantiken med Stagnelius och Tegnér, analyserar dikttolkning, stilfigurer och romantikens ideal. Behandlar även språkhistoria och utvecklingen från fornsvenska till moderna svenska."

Svara endast med innehållsbeskrivningen:"""
        
        response = requests.post(
            "https://ai.hackclub.com/chat/completions",
            json={
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 120,  # Öka för mer detaljerade beskrivningar
                "temperature": 0.8  # Lite högre för mer varierade beskrivningar
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.ok:
            ai_response = response.json().get("choices", [])[0].get("message", {}).get("content", "")
            
            # FÖRBÄTTRAD RENSNING av AI-svar
            description = ai_response.strip()
            
            # Ta bort vanliga AI-prefixer och meta-text
            prefixes_to_remove = [
                "här är beskrivningen:",
                "beskrivning:",
                "quiz-beskrivning:",
                "innehållsbeskrivning:",
                "description:",
                "här är en beskrivning:",
                "beskrivningen är:",
                "innehållet handlar om:",
                "quizet behandlar:",
                "detta quiz:",
                "svaret är:",
                "resultatet är:"
            ]
            
            for prefix in prefixes_to_remove:
                if description.lower().startswith(prefix):
                    description = description[len(prefix):].strip()
            
            # Ta bort citattecken och onödiga tecken
            description = description.replace('"', '').replace("'", "").replace('\n', ' ')
            
            # Ta bort AI-artefakter
            artifacts_to_remove = ['<think>', '</think>', '```', '---', '***', '<reasoning>', '</reasoning>']
            for artifact in artifacts_to_remove:
                description = description.replace(artifact, '').strip()
            
            # Ta bort meta-kommentarer i slutet
            meta_endings = [
                'detta ger en bra',
                'beskrivningen visar',
                'på detta sätt',
                'detta hjälper',
                'användaren förstår'
            ]
            
            for ending in meta_endings:
                if ending in description.lower():
                    cut_index = description.lower().find(ending)
                    if cut_index > 100:  # Behåll bara om det finns tillräckligt innehåll före
                        description = description[:cut_index].strip()
            
            # Säkerställ att beskrivningen börjar ordentligt
            if description and not description[0].isupper():
                description = description[0].upper() + description[1:]
            
            # Säkerställ att den slutar med punkt
            if description and not description.endswith('.'):
                description = description + '.'
            
            # Kontrollera längd och kvalitet
            if (len(description) < 100 or 
                len(description) > 350 or
                'quiz' in description.lower()[:50] or  # Undvik att börja med "quiz"
                any(bad_word in description.lower() for bad_word in ['antal frågor', 'frågor', 'quiz-typ', 'test med'])):
                raise Exception("Generated description contains unwanted elements or wrong length")
                
            return description.strip()
        else:
            raise Exception(f"API call failed with status {response.status_code}")
            
    except Exception as e:
        print(f"[ERROR] Failed to generate content-focused description for quiz {quiz.id}: {e}")
        return generate_smart_content_fallback(quiz)


def generate_smart_content_fallback(quiz):
    """Generera en smart fallback-beskrivning baserat på innehållsanalys av frågorna"""
    try:
        questions = quiz.get_questions()
        if not questions:
            return "Innehåll inte tillgängligt för analys"
        
        # Samla all text från frågor och svar för djupare analys
        question_texts = []
        answer_texts = []
        
        for q in questions[:10]:  # Analysera upp till 10 frågor
            if q.get('question'):
                question_texts.append(q['question'].lower())
            
            if q.get('answer'):
                if isinstance(q['answer'], dict):
                    if 'correct' in q['answer']:
                        answer_texts.append(str(q['answer']['correct']).lower())
                    elif 'alternatives' in q['answer']:
                        alts = q['answer']['alternatives']
                        correct_idx = q['answer'].get('correct_index', 0)
                        if 0 <= correct_idx < len(alts):
                            answer_texts.append(alts[correct_idx].lower())
                else:
                    answer_texts.append(str(q['answer']).lower())
        
        combined_text = " ".join(question_texts + answer_texts)
        
        # UTÖKADE ämnesområden med specifika termer
        subject_areas = {
            'biologi_cell': {
                'keywords': ['cell', 'cellmembran', 'mitokondrier', 'kloroplast', 'cellkärna', 'cytoplasma', 'ribosom', 'endoplasmatiska', 'golgi'],
                'description': 'Behandlar cellbiologi med fokus på cellorganeller, cellens struktur och funktion samt cellulära processer'
            },
            'biologi_genetik': {
                'keywords': ['dna', 'gen', 'kromosom', 'mutation', 'nedärvning', 'allel', 'genotyp', 'fenotyp', 'mitos', 'meios'],
                'description': 'Utforskar genetik och ärftlighet med DNA-struktur, genuttryck, kromosombeteende och evolutionära processer'
            },
            'biologi_ekologi': {
                'keywords': ['ekosystem', 'näringskedja', 'population', 'art', 'biotop', 'symbios', 'predator', 'evolution', 'naturligt urval'],
                'description': 'Fokuserar på ekologi och evolution med artinteraktioner, populationsdynamik och miljöpåverkan'
            },
            'matematik_algebra': {
                'keywords': ['ekvation', 'andragrad', 'polynom', 'faktorisering', 'rötter', 'koefficient', 'kvadratkomplettering', 'pq-formel'],
                'description': 'Tränar algebraisk problemlösning med ekvationer, polynomhantering och matematisk modellering'
            },
            'matematik_geometri': {
                'keywords': ['triangel', 'cirkel', 'area', 'volym', 'pythagoras', 'trigonometri', 'sinus', 'cosinus', 'vektor'],
                'description': 'Behandlar geometri och trigonometri med former, mätningar och rumsliga relationer'
            },
            'matematik_analys': {
                'keywords': ['derivata', 'integral', 'gränsvärde', 'funktion', 'graf', 'kontinuitet', 'extrempunkt', 'asymptoter'],
                'description': 'Utforskar matematisk analys med funktioner, derivering, integrering och kurvstudie'
            },
            'kemi_grundläggande': {
                'keywords': ['atom', 'proton', 'neutron', 'elektron', 'grundämne', 'periodiska systemet', 'molekyl', 'kemisk bindning'],
                'description': 'Fokuserar på grundläggande kemi med atomstruktur, periodiska systemet och kemiska bindningar'
            },
            'kemi_reaktioner': {
                'keywords': ['kemisk reaktion', 'balansering', 'katalysator', 'oxidation', 'reduktion', 'syra', 'bas', 'ph', 'jonbindning'],
                'description': 'Behandlar kemiska reaktioner, reaktionsmekanism, syra-basbalans och elektrokemi'
            },
            'fysik_mekanik': {
                'keywords': ['kraft', 'rörelse', 'hastighet', 'acceleration', 'massa', 'newtons lagar', 'energi', 'rörelsemängd'],
                'description': 'Utforskar klassisk mekanik med krafter, rörelse, energiomvandlingar och fysikaliska lagar'
            },
            'fysik_elektricitet': {
                'keywords': ['ström', 'spänning', 'resistans', 'ohms lag', 'elektrisk krets', 'kondensator', 'magnetfält'],
                'description': 'Behandlar elektricitet och magnetism med elektriska kretsar, elektromagnetiska fenomen'
            },
            'historia_sverige': {
                'keywords': ['gustav vasa', 'stormaktstiden', 'karl xii', 'sverige', 'union', 'reformation', 'trettioåriga kriget'],
                'description': 'Fokuserar på svensk historia med politiska förändringar, kungar och Sveriges utveckling'
            },
            'historia_världen': {
                'keywords': ['världskrig', 'revolution', 'imperialism', 'kolonialism', 'demokrati', 'diktatur', 'industrialisering'],
                'description': 'Behandlar världshistoria med stora konflikter, samhällsförändringar och globala processer'
            },
            'svenska_grammatik': {
                'keywords': ['verb', 'substantiv', 'adjektiv', 'tempus', 'subjekt', 'predikat', 'bisats', 'syntax'],
                'description': 'Tränar svensk grammatik med ordklasser, meningsanalys och språkstruktur'
            },
            'svenska_litteratur': {
                'keywords': ['författare', 'roman', 'dikt', 'novell', 'romantik', 'realism', 'modernism', 'symbolik', 'tema'],
                'description': 'Utforskar svensk litteratur med författarskap, litterära epoker och textanalys'
            }
        }
        
        # Hitta bäst matchande ämnesområden
        matches = []
        for area_key, area_data in subject_areas.items():
            keyword_matches = sum(1 for keyword in area_data['keywords'] if keyword in combined_text)
            if keyword_matches >= 2:  # Kräv minst 2 matchningar
                matches.append((area_key, keyword_matches, area_data['description']))
        
        # Sortera efter antal matchningar
        matches.sort(key=lambda x: x[1], reverse=True)
        
        if matches:
            # Använd den bäst matchande beskrivningen
            best_match = matches[0]
            base_description = best_match[2]
            
            # Lägg till specifika detaljer baserat på identifierade nyckelord
            area_key = best_match[0]
            area_keywords = subject_areas[area_key]['keywords']
            found_keywords = [kw for kw in area_keywords if kw in combined_text]
            
            if len(found_keywords) >= 3:
                # Lägg till specifika termer som hittades
                specific_terms = ', '.join(found_keywords[:4])  # Ta max 4 termer
                enhanced_description = f"{base_description}. Inkluderar specifikt {specific_terms} och relaterade koncept."
            else:
                enhanced_description = base_description + "."
            
            return enhanced_description
            
        else:
            # Generisk innehållsbaserad beskrivning
            if 'vad' in combined_text and 'är' in combined_text:
                return "Behandlar definitioner och grundläggande förståelse av centrala begrepp inom ämnesområdet."
            elif 'beräkna' in combined_text or 'räkna' in combined_text:
                return "Fokuserar på praktisk problemlösning och beräkningar med tillämpning av teoretiska koncept."
            elif 'förklara' in combined_text or 'beskriva' in combined_text:
                return "Tränar fördjupad förståelse och förmåga att förklara komplexa samband och processer."
            elif 'när' in combined_text or 'år' in combined_text:
                return "Behandlar tidsperspektiv, historiska skeenden och kronologisk förståelse av utvecklingsprocesser."
            else:
                return "Täcker viktiga kunskapsområden med fokus på förståelse och tillämpning av centrala koncept."
                
    except Exception as e:
        print(f"[ERROR] Smart content fallback failed: {e}")
        return "Behandlar viktiga ämnesområden och centrala koncept för kunskapsfördjupning."

def generate_smart_fallback_description(quiz):
    """Generera en smart fallback-beskrivning baserat på frågorna"""
    try:
        questions = quiz.get_questions()
        if not questions:
            return f"{quiz.quiz_type.replace('-', ' ').title()} quiz - Inga frågor tillgängliga"
        
        question_count = len(questions)
        quiz_type_readable = quiz.quiz_type.replace('-', ' ').title()
        
        # Analysera frågorna för att hitta nyckelord och teman
        question_texts = [q['question'].lower() for q in questions[:5]]
        combined_text = " ".join(question_texts)
        
        # Definiera ämnesområden och deras nyckelord
        subject_areas = {
            'biologi': ['cell', 'dna', 'protein', 'organism', 'evolution', 'ecosystem', 'photosynthesis', 
                       'membrane', 'mitosis', 'genetics', 'species', 'bacteria', 'virus', 'enzyme'],
            'matematik': ['equation', 'formula', 'calculate', 'solve', 'function', 'graph', 'derivative', 
                         'integral', 'algebra', 'geometry', 'statistics', 'probability', 'logarithm'],
            'historia': ['year', 'period', 'war', 'revolution', 'century', 'empire', 'king', 'democracy',
                        'treaty', 'battle', 'civilization', 'ancient', 'medieval', 'renaissance'],
            'kemi': ['atom', 'molecule', 'element', 'compound', 'reaction', 'acid', 'base', 'ion',
                    'periodic', 'bond', 'solution', 'ph', 'electron', 'neutron'],
            'fysik': ['force', 'energy', 'mass', 'velocity', 'acceleration', 'gravity', 'wave',
                     'light', 'electricity', 'magnetic', 'nuclear', 'quantum', 'momentum'],
            'geografi': ['continent', 'country', 'capital', 'mountain', 'river', 'climate', 'population',
                        'culture', 'economy', 'environment', 'urban', 'rural'],
            'svenska': ['verb', 'noun', 'adjective', 'sentence', 'grammar', 'literature', 'author',
                       'poem', 'novel', 'writing', 'language', 'syntax']
        }
        
        # Hitta matchande ämnesområden
        detected_subjects = []
        for subject, keywords in subject_areas.items():
            matches = sum(1 for keyword in keywords if keyword in combined_text)
            if matches >= 2:  # Kräv minst 2 matchningar
                detected_subjects.append((subject, matches))
        
        # Sortera efter antal matchningar
        detected_subjects.sort(key=lambda x: x[1], reverse=True)
        
        # Bygg beskrivning baserat på detekterade ämnen
        if detected_subjects:
            primary_subject = detected_subjects[0][0]
            
            subject_descriptions = {
                'biologi': f"Täcker grundläggande biologiska koncept och processer",
                'matematik': f"Tränar matematiska beräkningar och problemlösning",
                'historia': f"Behandlar historiska händelser och tidsperioder",
                'kemi': f"Fokuserar på kemiska reaktioner och ämnesegenskaper",
                'fysik': f"Undersöker fysikaliska lagar och fenomen",
                'geografi': f"Utforskar geografiska fakta och platser",
                'svenska': f"Tränar språkkunskap och grammatik"
            }
            
            base_desc = subject_descriptions.get(primary_subject, "Täcker viktiga kunskapsområden")
            
            # Lägg till information om omfattning
            if question_count <= 10:
                scope = "för snabb repetition och grundläggande förståelse"
            elif question_count <= 25:
                scope = "för omfattande träning och fördjupad kunskap"
            else:
                scope = "för grundlig genomgång och expertutbildning"
                
            return f"{base_desc} med {question_count} frågor {scope}."
            
        else:
            # Generisk men informativ beskrivning
            if question_count <= 10:
                return f"Kompakt {quiz_type_readable.lower()} med {question_count} välformulerade frågor för effektiv kunskapsträning"
            elif question_count <= 25:
                return f"Omfattande {quiz_type_readable.lower()} med {question_count} frågor för djupgående ämnesförståelse"
            else:
                return f"Heltäckande {quiz_type_readable.lower()} med {question_count} frågor för fullständig kunskapsgenomgång"
                
    except Exception as e:
        print(f"[ERROR] Fallback description generation failed: {e}")
        question_count = len(quiz.get_questions()) if quiz.questions else 0
        return f"{quiz.quiz_type.replace('-', ' ').title()} med {question_count} frågor för kunskapsträning"



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
    
# Migration script - kör detta en gång för att lägga till det nya fältet
# Du kan köra detta som en separat Python-fil eller lägga till det som en route

def migrate_add_display_description():
    """
    Lägg till display_description kolumn till Quiz-tabellen
    och generera beskrivningar för befintliga quizzes
    """
    try:
        # Lägg till kolumn (om den inte redan finns)
        with db.engine.connect() as conn:
            # Kontrollera om kolumnen redan finns
            result = conn.execute(text("""
                SELECT COUNT(*) as count 
                FROM pragma_table_info('quiz') 
                WHERE name='display_description'
            """)).fetchone()
            
            if result.count == 0:
                # Lägg till kolumn
                conn.execute(text("ALTER TABLE quiz ADD COLUMN display_description VARCHAR(200)"))
                conn.commit()
                print("[INFO] Added display_description column to quiz table")
            else:
                print("[INFO] display_description column already exists")
        
        # Generera beskrivningar för befintliga quizzes som saknar dem
        existing_quizzes = Quiz.query.filter(
            db.or_(
                Quiz.display_description.is_(None),
                Quiz.display_description == ''
            )
        ).all()
        
        print(f"[INFO] Found {len(existing_quizzes)} quizzes without descriptions")
        
        for quiz in existing_quizzes:
            try:
                print(f"[INFO] Generating description for quiz {quiz.id}: {quiz.title}")
                description = generate_quiz_description_sync(quiz)
                quiz.display_description = description
                db.session.add(quiz)
            except Exception as e:
                print(f"[ERROR] Failed to generate description for quiz {quiz.id}: {e}")
        
        db.session.commit()
        print(f"[SUCCESS] Updated descriptions for {len(existing_quizzes)} quizzes")
        
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        db.session.rollback()


def generate_quiz_description_sync(quiz):
    """
    Synkron version för migration - använder samma förbättrade logik
    """
    return generate_quiz_description(quiz)


# Hjälpfunktion för att regenerera alla beskrivningar
def regenerate_all_descriptions():
    """
    Kör denna för att regenerera alla quiz-beskrivningar med den nya logiken
    """
    try:
        all_quizzes = Quiz.query.all()
        updated_count = 0
        failed_count = 0
        
        for quiz in all_quizzes:
            try:
                print(f"[INFO] Regenerating description for quiz {quiz.id}: {quiz.title}")
                new_description = generate_quiz_description(quiz)
                quiz.display_description = new_description
                db.session.add(quiz)
                updated_count += 1
                print(f"[SUCCESS] Updated quiz {quiz.id}: {new_description[:50]}...")
            except Exception as e:
                print(f"[ERROR] Failed to update quiz {quiz.id}: {e}")
                failed_count += 1
        
        db.session.commit()
        print(f"[COMPLETE] Updated {updated_count} descriptions, {failed_count} failed")
        return updated_count, failed_count
        
    except Exception as e:
        print(f"[ERROR] Batch regeneration failed: {e}")
        db.session.rollback()
        return 0, 0

def generate_fallback_description(quiz):
    """Generera en bättre fallback-beskrivning baserat på frågorna"""
    questions = quiz.get_questions()
    if not questions:
        return f"{quiz.quiz_type.replace('-', ' ').title()} quiz - Inga frågor tillgängliga"
    
    question_count = len(questions)
    quiz_type_readable = quiz.quiz_type.replace('-', ' ').title()
    
    # Analysera frågorna för att hitta gemensamma teman
    question_texts = [q['question'].lower() for q in questions[:5]]  # Ta första 5
    combined_text = " ".join(question_texts)
    
    # Leta efter vanliga nyckelord för att gissa ämnesområde
    science_keywords = ['cell', 'dna', 'protein', 'organism', 'evolution', 'ecosystem', 'photosynthesis', 'membrane']
    math_keywords = ['equation', 'formula', 'calculate', 'solve', 'function', 'graph', 'derivative', 'integral']
    history_keywords = ['year', 'period', 'war', 'revolution', 'century', 'empire', 'king', 'democracy']
    
    detected_topics = []
    if any(keyword in combined_text for keyword in science_keywords):
        detected_topics.append("naturvetenskap")
    if any(keyword in combined_text for keyword in math_keywords):
        detected_topics.append("matematik")  
    if any(keyword in combined_text for keyword in history_keywords):
        detected_topics.append("historia")
    
    if detected_topics:
        topic_text = " och ".join(detected_topics)
        if question_count <= 10:
            return f"Tränar grundläggande {topic_text} med {question_count} frågor för snabb repetition"
        elif question_count <= 25:
            return f"Omfattande {topic_text}-quiz med {question_count} frågor för djupare förståelse"
        else:
            return f"Fullständig genomgång av {topic_text} med {question_count} frågor för grundlig kunskapsbearbetning"
    else:
        # Generisk men mer beskrivande fallback
        if question_count <= 10:
            return f"{quiz_type_readable} med {question_count} välutformade frågor för kunskapsträning och förståelse"
        elif question_count <= 25:
            return f"Omfattande {quiz_type_readable.lower()} med {question_count} frågor för djupgående ämnesförståelse och färdighetstestning"
        else:
            return f"Heltäckande {quiz_type_readable.lower()} med {question_count} frågor för fullständig kunskapsgenomgång och expertträning"


@app.route('/create-quiz', methods=['GET', 'POST'])
@login_required
def create_quiz():
    """Skapa quiz - nu med stöd för shared subjects, personliga quiz, lektioner och manuella frågor"""
    # Hämta alla subjects som användaren har tillgång till
    all_subjects = current_user.get_all_subjects()
    subject_names = [s.name for s in all_subjects]
    
    if request.method == 'POST':
        subject_name = request.form.get('subject')
        selected_lesson_id = request.form.get('selected_lesson')
        creation_method = request.form.get('creation_method', 'ai')  # 'ai' eller 'manual'
        
        # Kontrollera att användaren har tillgång till detta subject
        subject_obj = Subject.query.filter_by(name=subject_name).first()
        if not subject_obj or not current_user.is_member_of_subject(subject_obj.id):
            flash('You do not have access to this subject', 'error')
            return redirect(url_for('create_quiz'))
        
        # Kontrollera användarens roll för att avgöra om quiz ska vara personlig
        user_role = current_user.get_role_in_subject(subject_obj.id)
        is_personal = bool(request.form.get('is_personal'))
        
        # Om användaren inte är admin/owner, tvinga personlig quiz
        if user_role not in ['admin', 'owner']:
            is_personal = True
        
        # Hämta gemensam form data
        user_title = request.form.get('quiz_title', '').strip()
        quiz_type = request.form.get('quiz-drop')
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
        
        # Build title - INCLUDE UNIQUE IDENTIFIER
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        quiz_title = user_title or f"{subject_name} - {quiz_type.replace('-', ' ').title()} - {now} - {unique_id}"
        
        # SKAPÄ QUIZ I DATABASEN FÖRE GENERERING FÖR SÄKER ID
        try:
            new_quiz = Quiz(
                title=quiz_title,
                quiz_type=quiz_type,
                description="",  # Tom för manuella frågor, eller AI instructions
                files=[],
                use_documents=False,
                questions=[],
                subject_name=subject_name,
                subject_id=subject_obj.id,
                user_id=current_user.id,
                is_personal=is_personal
            )
            db.session.add(new_quiz)
            db.session.flush()
            
            quiz_db_id = new_quiz.id
            print(f"[INFO] Created quiz with database ID: {quiz_db_id} and unique ID: {unique_id}")
            
        except Exception as e:
            print(f"[ERROR] Failed to create initial quiz record: {e}")
            db.session.rollback()
            flash('Failed to create quiz. Please try again.', 'error')
            return redirect(url_for('create_quiz'))
        
        questions = []
        
        if creation_method == 'manual':
            # HANTERA MANUELLA FRÅGOR
            print(f"[INFO] Processing manual questions for quiz DB_ID:{quiz_db_id}")
            
            # Extrahera manuella frågor från formuläret
            manual_questions_data = {}
            for key, value in request.form.items():
                if key.startswith('manual_questions[') and value.strip():
                    # Parse nyckeln: manual_questions[0][question] eller manual_questions[0][answer]
                    import re
                    match = re.match(r'manual_questions\[(\d+)\]\[(question|answer)\]', key)
                    if match:
                        index = int(match.group(1))
                        field_type = match.group(2)
                        
                        if index not in manual_questions_data:
                            manual_questions_data[index] = {}
                        manual_questions_data[index][field_type] = value.strip()
            
            # Konvertera till questions format
            for index in sorted(manual_questions_data.keys()):
                question_data = manual_questions_data[index]
                if 'question' in question_data and 'answer' in question_data:
                    if question_data['question'] and question_data['answer']:
                        questions.append({
                            'question': question_data['question'],
                            'answer': question_data['answer'],
                            'quiz_id': quiz_db_id,
                            'question_number': len(questions),
                            'created_for_quiz': quiz_db_id,
                            'source': 'manual'
                        })
            
            print(f"[INFO] Processed {len(questions)} manual questions for quiz DB_ID:{quiz_db_id}")
            
            if not questions:
                print(f"[ERROR] No valid manual questions found for quiz DB_ID:{quiz_db_id}")
                db.session.delete(new_quiz)
                db.session.rollback()
                flash('Please provide at least one complete question and answer pair.', 'error')
                return redirect(url_for('create_quiz'))
            
            # Sätt beskrivning för manuella quiz
            new_quiz.description = f"Manual quiz with {len(questions)} questions created by user"
            
        else:
            # HANTERA AI-GENERERADE FRÅGOR (förbättrad kod)
            description = request.form.get('quiz-description', '').strip()
            use_docs = bool(request.form.get('use_documents'))
            
            # Handle file uploads and extract content
            uploaded_files = request.files.getlist('data1')
            saved_files = []
            file_contents = []
            upload_folder = os.path.join('static', 'uploads', str(current_user.id), subject_name, unique_id)
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
                        if text and text.strip():
                            file_contents.append(text)
                            print(f"[INFO] Extracted PDF content: {len(text)} characters from {filename}")
                    elif ext == '.txt':
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            text = f.read()
                            if text and text.strip():
                                file_contents.append(text)
                                print(f"[INFO] Extracted TXT content: {len(text)} characters from {filename}")
                    elif ext in ['.doc', '.docx']:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            text = f.read()
                            if text and text.strip():
                                file_contents.append(text)
                                print(f"[INFO] Extracted DOC content: {len(text)} characters from {filename}")
                except Exception as e:
                    print(f"[ERROR] Failed to process '{filename}': {e}")
            
            combined_text = "\n\n".join(file_contents) if file_contents else ''
            if combined_text:
                print(f"[INFO] Combined file content: {len(combined_text)} characters")
            
            # Lägg till lektionsinnehåll om en lektion är vald
            lesson_content = ""
            selected_lesson = None
            if selected_lesson_id and selected_lesson_id != "":
                try:
                    lesson_id = int(selected_lesson_id)
                    lesson = Lesson.query.filter_by(id=lesson_id, is_active=True).first()
                    
                    if lesson and lesson.is_accessible_by_user(current_user.id) and lesson.subject_id == subject_obj.id:
                        if lesson.transcription and lesson.transcription_status == 'completed':
                            lesson_content = f"=== LESSON: {lesson.title} ===\n{lesson.transcription}"
                            selected_lesson = lesson
                            print(f"[INFO] Added lesson content: {len(lesson_content)} characters")
                        else:
                            print(f"[WARNING] Selected lesson {lesson_id} has no completed transcription (status: {lesson.transcription_status})")
                            flash(f'Selected lesson "{lesson.title}" does not have a completed transcription yet.', 'warning')
                    else:
                        print(f"[WARNING] Invalid lesson selection: {lesson_id}")
                        flash('Selected lesson is not accessible or does not belong to this subject.', 'error')
                except (ValueError, TypeError) as e:
                    print(f"[WARNING] Invalid lesson ID: {selected_lesson_id}, error: {e}")
                    flash('Invalid lesson selection.', 'error')
            
            # FÖRBÄTTRAD HANTERING AV KRAV-DOKUMENT
            curriculum_guidelines = {}
            if use_docs:
                try:
                    print(f"[INFO] Loading curriculum documents for subject_id: {subject_obj.id}")
                    krav_documents = KravDocument.query.filter_by(subject_id=subject_obj.id).all()
                    print(f"[INFO] Found {len(krav_documents)} krav documents")
                    
                    for doc in krav_documents:
                        print(f"[INFO] Processing krav document: {doc.filename} (type: {doc.doc_type})")
                        if os.path.exists(doc.file_path):
                            try:
                                text_content = extract_text_from_pdf(doc.file_path)
                                if text_content and text_content.strip():
                                    curriculum_guidelines[doc.doc_type] = text_content
                                    print(f"[INFO] Loaded {doc.doc_type} guidelines: {len(text_content)} characters")
                                else:
                                    print(f"[WARNING] Empty content from {doc.filename}")
                            except Exception as e:
                                print(f"[ERROR] Failed to extract text from {doc.filename}: {e}")
                        else:
                            print(f"[ERROR] File not found at path: {doc.file_path}")
                    
                    print(f"[INFO] Successfully loaded {len(curriculum_guidelines)} curriculum guidelines")
                    
                except Exception as e:
                    print(f"[ERROR] Failed to load curriculum guidelines: {e}")
                    curriculum_guidelines = {}
            
            # Kontrollera att vi har åtminstone något INNEHÅLL att skapa quiz från
            main_content_sources = [combined_text, lesson_content]
            if not any(source.strip() for source in main_content_sources if source):
                flash('Please provide content to create quiz from: upload files or select a lesson with transcription.', 'error')
                db.session.delete(new_quiz)
                db.session.rollback()
                return redirect(url_for('create_quiz'))
            
            # Uppdatera quiz med filinfo och beskrivning
            new_quiz.files = saved_files
            new_quiz.description = description
            new_quiz.use_documents = use_docs
            
            # FÖRBÄTTRAD AI PROMPT - ROBUSTARE STRUKTUR
            prompt_parts = []
            
            # ADD MULTIPLE IDENTIFIERS TO PROMPT FOR MAXIMUM UNIQUENESS
            prompt_parts.append(f"Creating quiz - Database ID: {quiz_db_id}, Unique ID: {unique_id}")
            prompt_parts.append(f"Subject: {subject_name} (ID: {subject_obj.id})")
            prompt_parts.append(f"User: {current_user.id}")
            prompt_parts.append(f"Timestamp: {now}")
            
            # Grundläggande instruktion
            if desired_count:
                prompt_parts.append(f"You're an AI quiz generator. Create a {desired_count}-question {quiz_type.replace('-', ' ')} quiz based on the provided study materials.")
            else:
                prompt_parts.append(f"You're an AI quiz generator. Create an appropriate {quiz_type.replace('-', ' ')} quiz based on the provided study materials.")
            
            # PRIORITERA USER DESCRIPTION HÖGST
            if description:
                prompt_parts.append("=== QUIZ CREATOR'S SPECIFIC INSTRUCTIONS (HIGHEST PRIORITY) ===")
                prompt_parts.append(f"The quiz creator wants you to focus on: {description}")
                prompt_parts.append("These instructions should guide your question selection and focus areas from the study materials below.")
            
            # KRAV-DOKUMENT SOM RIKTLINJER (INTE INNEHÅLL)
            if curriculum_guidelines:
                prompt_parts.append("=== CURRICULUM GUIDELINES FOR QUESTION FOCUS ===")
                prompt_parts.append("Use these curriculum documents as GUIDELINES for what aspects to focus on from the study materials:")
                
                if 'kunskapsmal' in curriculum_guidelines:
                    prompt_parts.append("KNOWLEDGE GOALS (what students should learn):")
                    prompt_parts.append(curriculum_guidelines['kunskapsmal'][:5000])  # Begränsa storlek
                    prompt_parts.append("")
                
                if 'kunskapskrav' in curriculum_guidelines:
                    prompt_parts.append("ASSESSMENT CRITERIA (what levels of understanding to test):")
                    prompt_parts.append(curriculum_guidelines['kunskapskrav'][:5000])  # Begränsa storlek
                    prompt_parts.append("")
                
                if 'begrippslista' in curriculum_guidelines:
                    prompt_parts.append("KEY CONCEPTS TO FOCUS ON (look for these specific terms in the study materials):")
                    prompt_parts.append(curriculum_guidelines['begrippslista'][:3000])  # Mindre för begrepp
                    prompt_parts.append("PAY SPECIAL ATTENTION: When you find these concepts in the study materials below, create questions that test understanding of these specific terms and their applications.")
                    prompt_parts.append("")
            
            # HUVUDINNEHÅLL SOM KÄLLA FÖR FRÅGOR
            prompt_parts.append("=== STUDY MATERIALS (SOURCE FOR QUIZ QUESTIONS) ===")
            prompt_parts.append("Create quiz questions based on the content in these materials:")
            
            # Lägg till lektionsinnehåll först (högst prioritet av innehållet)
            if lesson_content:
                prompt_parts.append("PRIMARY SOURCE - LESSON MATERIAL:")
                prompt_parts.append(lesson_content[:15000])  # Begränsa storlek
                prompt_parts.append("")
            
            # Lägg till uppladdade material
            if combined_text:
                source_label = "SECONDARY SOURCE - UPLOADED MATERIALS:" if lesson_content else "PRIMARY SOURCE - UPLOADED MATERIALS:"
                prompt_parts.append(source_label)
                prompt_parts.append(combined_text[:15000])  # Begränsa storlek
                prompt_parts.append("")
            
            # FÖRBÄTTRADE INSTRUKTIONER
            instruction_parts = []
            instruction_parts.append("IMPORTANT INSTRUCTIONS:")
            
            # Prioritering av beskrivning
            if description:
                instruction_parts.append(f"1. HIGHEST PRIORITY: Follow the creator's specific instructions: '{description}'")
            
            # Krav-dokument som filter
            if curriculum_guidelines:
                if 'begrippslista' in curriculum_guidelines:
                    instruction_parts.append("2. CONCEPT FOCUS: Look specifically for the key concepts listed in the curriculum guidelines when creating questions from the study materials. If you find these concepts in the materials, prioritize creating questions about them.")
                
                if 'kunskapsmal' in curriculum_guidelines:
                    instruction_parts.append("3. ALIGNMENT: Ensure questions align with the knowledge goals - test what students should learn according to the curriculum.")
                
                if 'kunskapskrav' in curriculum_guidelines:
                    instruction_parts.append("4. DIFFICULTY LEVELS: Create questions at appropriate difficulty levels based on the assessment criteria.")
            
            instruction_parts.append("5. CONTENT SOURCE: Questions must be answerable from the study materials provided above. Do NOT ask about curriculum requirements themselves (like 'what should year 3 students know?').")
            instruction_parts.append("6. FOCUS: Ask about the actual content, concepts, facts, and applications found in the study materials.")
            
            # Specifika instruktioner baserat på tillgängligt innehåll
            content_sources = []
            if lesson_content: content_sources.append("lesson material")
            if combined_text: content_sources.append("uploaded study materials")
            
            if curriculum_guidelines and content_sources:
                if 'begrippslista' in curriculum_guidelines:
                    instruction_parts.append(f"7. CONCEPT INTEGRATION: When you find key concepts from the concept list in the {' and '.join(content_sources)}, create questions that test understanding of those specific concepts as they appear in the materials.")
                instruction_parts.append(f"8. GUIDELINE APPLICATION: Use the curriculum guidelines to determine WHAT to focus on from the {' and '.join(content_sources)}, not as content to ask about directly.")
            
            prompt_parts.extend(instruction_parts)
            
            # CRITICAL: ANVÄND KOMBINATION AV DATABASE ID OCH UNIQUE ID FÖR MAXIMAL SÄKERHET
            combined_identifier = f"{quiz_db_id}_{unique_id}"
            prompt_parts.append(f"\nFormat each question as:\nQUIZ{combined_identifier}_Q[number]: [Question]\nQUIZ{combined_identifier}_A[number]: [Answer]\n")
            prompt_parts.append(f"CRITICAL: Use the exact prefix QUIZ{combined_identifier}_Q and QUIZ{combined_identifier}_A for all questions and answers. This ensures proper parsing and prevents mix-ups.")
            
            prompt = "\n\n".join(prompt_parts)
            
            # Begränsa total prompt-storlek
            if len(prompt) > 50000:
                print(f"[WARNING] Prompt too long ({len(prompt)} chars), truncating...")
                prompt = prompt[:45000] + "\n\n[Content truncated for length]"
            
            print(f"[INFO] Sending prompt to AI for quiz DB_ID:{quiz_db_id}, UNIQUE_ID:{unique_id}: {len(prompt)} characters")
            
            # FÖRBÄTTRAD AI API CALL MED SSL/CONNECTION HANTERING
            try:
                import requests
                from requests.adapters import HTTPAdapter
                from urllib3.util.retry import Retry
                import ssl
                
                # Skapa en session med retry-logik och SSL-hantering
                session = requests.Session()
                
                # Retry strategi
                retry_strategy = Retry(
                    total=3,
                    backoff_factor=1,
                    status_forcelist=[429, 500, 502, 503, 504]
                )
                
                adapter = HTTPAdapter(max_retries=retry_strategy)
                session.mount("http://", adapter)
                session.mount("https://", adapter)
                
                # SSL context för att hantera SSL-problem
                session.verify = True  # Behåll certifikatverifiering
                
                # Försök API-anrop med förbättrad felhantering
                response = session.post(
                    "https://ai.hackclub.com/chat/completions",
                    json={"messages": [{"role": "user", "content": prompt}]},
                    headers={"Content-Type": "application/json"},
                    timeout=120,
                )
                response.raise_for_status()
                raw = response.json().get("choices", [])[0].get("message", {}).get("content", "")
                print(f"[INFO] AI response received for quiz DB_ID:{quiz_db_id}: {len(raw)} characters")
                
            except requests.exceptions.SSLError as ssl_err:
                print(f"[ERROR] SSL Error for quiz DB_ID:{quiz_db_id}: {ssl_err}")
                # Fallback: försök med mindre strikt SSL
                try:
                    print(f"[INFO] Retrying with adjusted SSL settings...")
                    session.verify = False  # Tillfällig lösning för SSL-problem
                    response = session.post(
                        "https://ai.hackclub.com/chat/completions",
                        json={"messages": [{"role": "user", "content": prompt}]},
                        headers={"Content-Type": "application/json"},
                        timeout=120,
                    )
                    response.raise_for_status()
                    raw = response.json().get("choices", [])[0].get("message", {}).get("content", "")
                    print(f"[INFO] AI response received (SSL retry) for quiz DB_ID:{quiz_db_id}: {len(raw)} characters")
                except Exception as retry_err:
                    print(f"[ERROR] SSL retry also failed for quiz DB_ID:{quiz_db_id}: {retry_err}")
                    db.session.delete(new_quiz)
                    db.session.rollback()
                    flash('Failed to generate quiz questions due to connection issues. Please try again.', 'error')
                    return redirect(url_for('create_quiz'))
                    
            except requests.exceptions.ConnectionError as conn_err:
                print(f"[ERROR] Connection Error for quiz DB_ID:{quiz_db_id}: {conn_err}")
                db.session.delete(new_quiz)
                db.session.rollback()
                flash('Failed to connect to AI service. Please check your internet connection and try again.', 'error')
                return redirect(url_for('create_quiz'))
                
            except requests.exceptions.Timeout as timeout_err:
                print(f"[ERROR] Timeout Error for quiz DB_ID:{quiz_db_id}: {timeout_err}")
                db.session.delete(new_quiz)
                db.session.rollback()
                flash('AI service timed out. Please try again with shorter content.', 'error')
                return redirect(url_for('create_quiz'))
                
            except Exception as e:
                print(f"[ERROR] AI API call failed for quiz DB_ID:{quiz_db_id}: {e}")
                db.session.delete(new_quiz)
                db.session.rollback()
                flash('Failed to generate quiz questions. Please try again.', 'error')
                return redirect(url_for('create_quiz'))
            
            finally:
                session.close()
            
            # FÖRBÄTTRAD PARSING MED UNIKA IDENTIFIERARE
            lines = raw.splitlines()
            current_question = None
            current_answer = None
            question_number = 0
            
            # Parse med kombinerade identifierare
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Leta efter våra unika prefix först
                quiz_q_prefix = f'quiz{combined_identifier}_q'.lower()
                quiz_a_prefix = f'quiz{combined_identifier}_a'.lower()
                
                if line.lower().startswith(quiz_q_prefix):
                    # Spara föregående fråga om den finns
                    if current_question and current_answer:
                        questions.append({
                            'question': current_question,
                            'answer': current_answer,
                            'quiz_id': quiz_db_id,
                            'question_number': question_number,
                            'created_for_quiz': quiz_db_id,
                            'source': 'ai'
                        })
                        question_number += 1
                    
                    # Starta ny fråga
                    current_question = line.split(':', 1)[1].strip() if ':' in line else line
                    current_answer = None
                    
                elif line.lower().startswith(quiz_a_prefix):
                    if current_question:
                        current_answer = line.split(':', 1)[1].strip() if ':' in line else line
                        
                # Fallback för standardformat (men mindre tillförlitligt)
                elif line.lower().startswith('q:') or line.lower().startswith('question:'):
                    if current_question and current_answer:
                        questions.append({
                            'question': current_question,
                            'answer': current_answer,
                            'quiz_id': quiz_db_id,
                            'question_number': question_number,
                            'created_for_quiz': quiz_db_id,
                            'source': 'ai'
                        })
                        question_number += 1
                        
                    current_question = line.split(':', 1)[1].strip() if ':' in line else line
                    current_answer = None
                    
                elif line.lower().startswith('a:') or line.lower().startswith('answer:'):
                    if current_question:
                        current_answer = line.split(':', 1)[1].strip() if ':' in line else line
                        
                elif current_question and not current_answer:
                    # Fortsättning av frågan
                    current_question += " " + line
                    
                elif current_question and current_answer:
                    # Fortsättning av svaret
                    current_answer += " " + line
            
            # Lägg till sista frågan
            if current_question and current_answer:
                questions.append({
                    'question': current_question,
                    'answer': current_answer,
                    'quiz_id': quiz_db_id,
                    'question_number': question_number,
                    'created_for_quiz': quiz_db_id,
                    'source': 'ai'
                })
            
            print(f"[INFO] Parsed {len(questions)} questions from AI response for quiz DB_ID:{quiz_db_id}")
            
            # Hantera fall då inga frågor genererades
            if not questions:
                print(f"[ERROR] No valid questions could be parsed from AI response for quiz DB_ID:{quiz_db_id}")
                print(f"[DEBUG] Raw AI response preview: {raw[:500]}...")
                # Radera den skapade quiz-posten
                db.session.delete(new_quiz)
                db.session.rollback()
                flash('Could not generate quiz questions from the provided content. Please try again or provide different content.', 'error')
                return redirect(url_for('create_quiz'))
        
        # GEMENSAM HANTERING FÖR BÅDE AI OCH MANUELLA FRÅGOR
        
        # Validera att frågorna verkligen tillhör denna quiz
        validated_questions = []
        for q in questions:
            if (q.get('question') and q.get('answer') and 
                q['question'].strip() and q['answer'].strip() and
                not q['question'].startswith('[Error]') and
                q.get('quiz_id') == quiz_db_id):
                validated_questions.append({
                    'question': q['question'].strip(),
                    'answer': q['answer'].strip(),
                    'quiz_id': quiz_db_id,
                    'created_for_quiz': quiz_db_id,
                    'source': q.get('source', 'unknown')
                })
        
        questions = validated_questions
        
        # Truncate to desired count (endast för AI-genererade)
        if creation_method == 'ai' and desired_count and len(questions) > desired_count:
            questions = questions[:desired_count]
        
        print(f"[INFO] Final validated question count for quiz DB_ID:{quiz_db_id}: {len(questions)}")
        
        # Uppdatera quiz med validerade frågor
        try:
            new_quiz.questions = questions
            db.session.commit()
            
            # EXTRA VALIDERING
            saved_quiz = Quiz.query.get(quiz_db_id)
            if not saved_quiz or not saved_quiz.questions or len(saved_quiz.questions) != len(questions):
                print(f"[ERROR] Quiz save validation failed for DB_ID:{quiz_db_id}")
                db.session.rollback()
                flash('Failed to save quiz questions correctly. Please try again.', 'error')
                return redirect(url_for('create_quiz'))
            
            print(f"[SUCCESS] Quiz DB_ID:{quiz_db_id} saved successfully with {len(saved_quiz.questions)} questions")
        
            # Generera AI-beskrivning endast för AI-skapade quiz
            if creation_method == 'ai':
                try:
                    print(f"[INFO] Generating AI description for quiz DB_ID:{quiz_db_id}")
                    ai_description = generate_quiz_description(saved_quiz)
                    saved_quiz.display_description = ai_description
                    db.session.commit()
                    print(f"[SUCCESS] Generated AI description for quiz DB_ID:{quiz_db_id}: {ai_description[:100]}...")
                except Exception as e:
                    print(f"[WARNING] Failed to generate AI description for quiz DB_ID:{quiz_db_id}: {e}")
                    fallback_desc = generate_fallback_description(saved_quiz)
                    saved_quiz.display_description = fallback_desc
                    db.session.commit()
            else:
                # För manuella quiz, skapa en enkel beskrivning
                manual_desc = f"Custom quiz with {len(questions)} manually created questions"
                saved_quiz.display_description = manual_desc
                db.session.commit()
        
        except Exception as e:
            print(f"[ERROR] Failed to update quiz DB_ID:{quiz_db_id} with questions: {e}")
            db.session.rollback()
            flash('Failed to save quiz. Please try again.', 'error')
            return redirect(url_for('create_quiz'))
        
        # Skapa flashcards
        if create_flashcards and questions and len(questions) > 0:
            try:
                if is_personal:
                    create_flashcards_for_user(new_quiz, current_user.id)
                    print(f"[INFO] Created personal flashcards for quiz DB_ID:{quiz_db_id}, user {current_user.id}")
                else:
                    create_flashcards_for_all_members(new_quiz, subject_obj)
                    print(f"[INFO] Created shared flashcards for quiz DB_ID:{quiz_db_id}, subject {subject_obj.id}")
            except Exception as e:
                print(f"[ERROR] Failed to create flashcards for quiz DB_ID:{quiz_db_id}: {e}")
        
        # Build success message
        quiz_type_text = "personal quiz" if is_personal else "shared quiz"
        creation_text = "manually created" if creation_method == 'manual' else "AI-generated"
        success_msg = f'{quiz_type_text.capitalize()} "{quiz_title}" created successfully with {len(questions)} {creation_text} questions'
        
        # Lägg till information om använda källor (endast för AI)
        if creation_method == 'ai':
            sources_used = []
            if use_docs and curriculum_guidelines:
                guidelines_count = len(curriculum_guidelines)
                sources_used.append(f"{guidelines_count} curriculum guideline{'s' if guidelines_count != 1 else ''}")
            if lesson_content and selected_lesson:
                sources_used.append(f"lesson '{selected_lesson.title}'")
            if file_contents:
                sources_used.append(f"{len(file_contents)} uploaded file{'s' if len(file_contents) != 1 else ''}")
            
            if sources_used:
                success_msg += f" (using {', '.join(sources_used)})"
        
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
    # Redirect authenticated users
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip().lower()
        email_confirm = request.form['email_confirm'].strip().lower()
        password = request.form['password']

        # Validation
        if len(username) < 3:
            flash('Användarnamn måste vara minst 3 tecken långt.', 'danger')
            return redirect(url_for('register'))
        if email != email_confirm:
            flash('E-postadresserna matchar inte.', 'danger')
            return redirect(url_for('register'))
        if not email or '@' not in email:
            flash('Ange en giltig e-postadress.', 'danger')
            return redirect(url_for('register'))
        if len(password) < 6:
            flash('Lösenord måste vara minst 6 tecken långt.', 'danger')
            return redirect(url_for('register'))

        # Check existing username or email
        if User.query.filter_by(username=username).first():
            flash('Användarnamn finns redan.', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('E-postadressen är redan registrerad.', 'danger')
            return redirect(url_for('register'))

        # Create user
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email, password_hash=hashed_pw)
        db.session.add(user)
        db.session.commit()
        flash('Kontot skapades! Nu kan du logga in.', 'success')
        return redirect(url_for('login'))

    # Render form
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
            <label>E-postadress:</label>
            <input type="email" name="email" required>
            <label>Bekräfta e-postadress:</label>
            <input type="email" name="email_confirm" required>
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
    # Redirect authenticated users
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        identity = request.form['identity'].strip()
        password = request.form['password']
        # Allow login via username or email
        user = User.query.filter(
            (User.username == identity) | (User.email == identity)
        ).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f'Välkommen {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Fel användarnamn/e-post eller lösenord.', 'danger')

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
            <label>Användarnamn eller e-post:</label>
            <input name="identity" required>
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


# Flask routes att lägga till i din app.py

@app.route('/api/assignments/<int:subject_id>')
def get_assignments(subject_id):
    """Hämta alla uppgifter för ett ämne"""
    try:
        # Kontrollera att användaren har tillgång till ämnet
        user_role = get_user_role_in_subject(current_user.id, subject_id)
        if not user_role:
            return jsonify({'status': 'error', 'message': 'Åtkomst nekad'}), 403

        # Hämta uppgifter
        assignments = Assignment.query.filter_by(subject_id=subject_id).order_by(Assignment.created_at.desc()).all()
        
        assignments_data = []
        for assignment in assignments:
            # För medlemmar, kontrollera inlämningsstatus
            submission_status = 'pending'
            if user_role != 'owner':
                submission = AssignmentSubmission.query.filter_by(
                    assignment_id=assignment.id,
                    student_id=current_user.id
                ).first()
                if submission:
                    submission_status = 'submitted'

            # För ägare, räkna antal inlämningar
            submission_count = 0
            if user_role == 'owner':
                submission_count = AssignmentSubmission.query.filter_by(assignment_id=assignment.id).count()

            assignments_data.append({
                'id': assignment.id,
                'title': assignment.title,
                'description': assignment.description,
                'due_date': assignment.due_date.isoformat() if assignment.due_date else None,
                'created_at': assignment.created_at.isoformat(),
                'submission_status': submission_status,
                'submission_count': submission_count
            })

        return jsonify({
            'status': 'success',
            'assignments': assignments_data
        })

    except Exception as e:
        print(f"Error loading assignments: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    


@app.route('/api/submission/<int:submission_id>/mark_seen', methods=['POST'])
def mark_submission_seen(submission_id):
    """Markera en inlämning som sedd (endast ägare)."""
    submission = AssignmentSubmission.query.get_or_404(submission_id)
    user_role = get_user_role_in_subject(current_user.id, submission.assignment.subject_id)
    if user_role != 'owner':
        return jsonify({'status':'error','message':'Åtkomst nekad'}),403

    submission.seen = True
    db.session.commit()
    return jsonify({'status':'success','message':'Inlämning markerad som sedd'})




@app.route('/api/assignments/create', methods=['POST'])
def create_assignment():
    """Skapa ny uppgift (endast ägare)"""
    try:
        data = request.get_json()
        
        subject_id = data.get('subject_id')
        user_role = get_user_role_in_subject(current_user.id, subject_id)
        
        if user_role != 'owner':
            return jsonify({'status': 'error', 'message': 'Endast ägare kan skapa uppgifter'}), 403

        # Skapa uppgift
        assignment = Assignment(
            subject_id=subject_id,
            title=data.get('title'),
            description=data.get('description'),
            due_date=datetime.fromisoformat(data.get('due_date')) if data.get('due_date') else None,
            allow_multiple_files=data.get('allow_multiple_files', True),
            created_by=current_user.id
        )

        db.session.add(assignment)
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': 'Uppgift skapad',
            'assignment_id': assignment.id
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error creating assignment: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/view_my_submission_file/<int:file_id>')
def view_my_submission_file(file_id):
    """Låt studenter öppna sina egna inlämnade filer"""
    try:
        file = AssignmentFile.query.get_or_404(file_id)
        submission = file.submission
        assignment = submission.assignment
        
        # Kontrollera att det är studenten som lämnade in filen
        if submission.student_id != current_user.id:
            return "Åtkomst nekad - du kan endast se dina egna filer", 403
        
        # Kontrollera att användaren har tillgång till ämnet
        user_role = get_user_role_in_subject(current_user.id, assignment.subject_id)
        if not user_role:
            return "Åtkomst nekad", 403

        # Kontrollera att filen existerar
        if not os.path.exists(file.file_path):
            return "Fil hittades inte", 404

        # Returnera filen för visning i webbläsaren
        return send_file(file.file_path, as_attachment=False)

    except Exception as e:
        print(f"Error viewing my submission file: {e}")
        return "Fel vid öppning av fil", 500


@app.route('/download_my_submission_file/<int:file_id>')
def download_my_submission_file(file_id):
    """Låt studenter ladda ner sina egna inlämnade filer"""
    try:
        file = AssignmentFile.query.get_or_404(file_id)
        submission = file.submission
        assignment = submission.assignment
        
        # Kontrollera att det är studenten som lämnade in filen
        if submission.student_id != current_user.id:
            return "Åtkomst nekad - du kan endast ladda ner dina egna filer", 403
        
        # Kontrollera att användaren har tillgång till ämnet
        user_role = get_user_role_in_subject(current_user.id, assignment.subject_id)
        if not user_role:
            return "Åtkomst nekad", 403

        return send_file(file.file_path, as_attachment=True, download_name=file.filename)

    except Exception as e:
        print(f"Error downloading my submission file: {e}")
        return "Fil hittades inte", 404


@app.route('/api/assignments/undo_submission', methods=['POST'])
def undo_assignment_submission():
    """Ångra inlämning (endast studenten som lämnade in)"""
    try:
        data = request.get_json()
        assignment_id = data.get('assignment_id')
        
        assignment = Assignment.query.get_or_404(assignment_id)
        user_role = get_user_role_in_subject(current_user.id, assignment.subject_id)
        
        if not user_role or user_role == 'owner':
            return jsonify({'status': 'error', 'message': 'Åtkomst nekad'}), 403

        # Hitta användarens inlämning
        submission = AssignmentSubmission.query.filter_by(
            assignment_id=assignment_id,
            student_id=current_user.id
        ).first()

        if not submission:
            return jsonify({'status': 'error', 'message': 'Ingen inlämning att ångra'}), 400

        # Ta bort filer från disk
        for file in submission.files:
            try:
                if os.path.exists(file.file_path):
                    os.remove(file.file_path)
            except Exception as e:
                print(f"Error removing file {file.file_path}: {e}")

        # Ta bort inlämningen från databasen (cascade tar hand om filer och kommentarer)
        db.session.delete(submission)
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': 'Inlämning har ångrats'
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error undoing submission: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/preview_upload_file', methods=['POST'])
def preview_upload_file():
    """Förhandsgranska uppladdad fil innan inlämning"""
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'Ingen fil skickad'}), 400

        file = request.files['file']
        if not file or not file.filename:
            return jsonify({'status': 'error', 'message': 'Ogiltig fil'}), 400

        # Spara temporärt för förhandsgranskning
        temp_dir = os.path.join('static', 'temp_uploads', str(current_user.id))
        os.makedirs(temp_dir, exist_ok=True)
        
        filename = secure_filename(file.filename)
        temp_path = os.path.join(temp_dir, filename)
        file.save(temp_path)

        # Returnera temporär URL för förhandsgranskning
        temp_url = f"/static/temp_uploads/{current_user.id}/{filename}"
        
        return jsonify({
            'status': 'success',
            'temp_url': temp_url,
            'filename': filename,
            'file_size': os.path.getsize(temp_path)
        })

    except Exception as e:
        print(f"Error previewing file: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/cleanup_temp_files', methods=['POST'])
def cleanup_temp_files():
    """Rensa temporära filer för förhandsgranskning"""
    try:
        temp_dir = os.path.join('static', 'temp_uploads', str(current_user.id))
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
            os.makedirs(temp_dir, exist_ok=True)
        
        return jsonify({'status': 'success', 'message': 'Temporära filer rensade'})
    
    except Exception as e:
        print(f"Error cleaning up temp files: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
# Nya routes för att öppna filer och hantera kommentarer

@app.route('/view_submission_file/<int:file_id>')
def view_submission_file(file_id):
    """Öppna inlämnad fil i webbläsaren"""
    try:
        file = AssignmentFile.query.get_or_404(file_id)
        assignment = file.submission.assignment
        user_role = get_user_role_in_subject(current_user.id, assignment.subject_id)
        
        # Endast ägare kan öppna filer
        if user_role != 'owner':
            return "Åtkomst nekad", 403

        # Kontrollera att filen existerar
        if not os.path.exists(file.file_path):
            return "Fil hittades inte", 404

        # Returnera filen för visning i webbläsaren
        return send_file(file.file_path, as_attachment=False)

    except Exception as e:
        print(f"Error viewing file: {e}")
        return "Fel vid öppning av fil", 500


@app.route('/api/submission/<int:submission_id>/comments')
def get_submission_comments(submission_id):
    """Hämta kommentarer för en inlämning"""
    try:
        submission = AssignmentSubmission.query.get_or_404(submission_id)
        assignment = submission.assignment
        user_role = get_user_role_in_subject(current_user.id, assignment.subject_id)
        
        # Både ägare och studenten som lämnade in kan se kommentarer
        if user_role != 'owner' and submission.student_id != current_user.id:
            return jsonify({'status': 'error', 'message': 'Åtkomst nekad'}), 403

        comments = SubmissionComment.query.filter_by(submission_id=submission_id).order_by(SubmissionComment.created_at.desc()).all()
        
        comments_data = []
        for comment in comments:
            comments_data.append({
                'id': comment.id,
                'comment': comment.comment,
                'teacher_name': comment.teacher.username,
                'created_at': comment.created_at.isoformat(),
                'updated_at': comment.updated_at.isoformat()
            })

        return jsonify({
            'status': 'success',
            'comments': comments_data
        })

    except Exception as e:
        print(f"Error loading comments: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/submission/<int:submission_id>/add_comment', methods=['POST'])
def add_submission_comment(submission_id):
    """Lägg till kommentar på inlämning (endast ägare)"""
    try:
        data = request.get_json()
        comment_text = data.get('comment', '').strip()
        
        if not comment_text:
            return jsonify({'status': 'error', 'message': 'Kommentar krävs'}), 400

        submission = AssignmentSubmission.query.get_or_404(submission_id)
        assignment = submission.assignment
        user_role = get_user_role_in_subject(current_user.id, assignment.subject_id)
        
        if user_role != 'owner':
            return jsonify({'status': 'error', 'message': 'Endast ägare kan kommentera'}), 403

        # Skapa kommentar
        comment = SubmissionComment(
            submission_id=submission_id,
            teacher_id=current_user.id,
            comment=comment_text
        )
        
        db.session.add(comment)
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': 'Kommentar tillagd',
            'comment': {
                'id': comment.id,
                'comment': comment.comment,
                'teacher_name': comment.teacher.username,
                'created_at': comment.created_at.isoformat(),
                'updated_at': comment.updated_at.isoformat()
            }
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error adding comment: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/submission/<int:submission_id>/edit_comment/<int:comment_id>', methods=['POST'])
def edit_submission_comment(submission_id, comment_id):
    """Redigera kommentar (endast av den som skrev den)"""
    try:
        data = request.get_json()
        new_comment_text = data.get('comment', '').strip()
        
        if not new_comment_text:
            return jsonify({'status': 'error', 'message': 'Kommentar krävs'}), 400

        comment = SubmissionComment.query.get_or_404(comment_id)
        
        # Endast den som skrev kommentaren kan redigera
        if comment.teacher_id != current_user.id:
            return jsonify({'status': 'error', 'message': 'Du kan endast redigera dina egna kommentarer'}), 403

        comment.comment = new_comment_text
        comment.updated_at = datetime.utcnow()
        
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': 'Kommentar uppdaterad',
            'comment': {
                'id': comment.id,
                'comment': comment.comment,
                'teacher_name': comment.teacher.username,
                'created_at': comment.created_at.isoformat(),
                'updated_at': comment.updated_at.isoformat()
            }
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error editing comment: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/submission/<int:submission_id>/delete_comment/<int:comment_id>', methods=['POST'])
def delete_submission_comment(submission_id, comment_id):
    """Ta bort kommentar (endast av den som skrev den)"""
    try:
        comment = SubmissionComment.query.get_or_404(comment_id)
        
        # Endast den som skrev kommentaren kan ta bort den
        if comment.teacher_id != current_user.id:
            return jsonify({'status': 'error', 'message': 'Du kan endast ta bort dina egna kommentarer'}), 403

        db.session.delete(comment)
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': 'Kommentar borttagen'
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error deleting comment: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500






def create_submission_comments_table():
    """Skapa submission_comments tabellen"""
    try:
        # Kontrollera om tabellen redan finns
        db.session.execute(db.text("SELECT name FROM sqlite_master WHERE type='table' AND name='submission_comments'"))
        result = db.session.fetchone()
        
        if result:
            print("submission_comments table already exists")
            return
        
        # Skapa tabellen
        create_table_sql = """
        CREATE TABLE submission_comments (
            id INTEGER PRIMARY KEY,
            submission_id INTEGER NOT NULL,
            teacher_id INTEGER NOT NULL,
            comment TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (submission_id) REFERENCES assignment_submission (id) ON DELETE CASCADE,
            FOREIGN KEY (teacher_id) REFERENCES user (id) ON DELETE CASCADE
        )
        """
        
        db.session.execute(db.text(create_table_sql))
        db.session.commit()
        print("✓ Created submission_comments table")
        
    except Exception as e:
        print(f"Error creating submission_comments table: {e}")
        db.session.rollback()

def run_assignment_migrations():
    """Kör alla migrations för uppgiftssystemet"""
    print("Running assignment system migrations...")
    
    # Skapa submission_comments tabellen
    create_submission_comments_table()
    
    print("Assignment migrations completed!")


# Route för studenter att se sina egna inlämningar med kommentarer
@app.route('/api/my_submissions/<int:assignment_id>')
def get_my_submission(assignment_id):
    """Hämta egen inlämning för en uppgift (studenter)"""
    try:
        assignment = Assignment.query.get_or_404(assignment_id)
        user_role = get_user_role_in_subject(current_user.id, assignment.subject_id)
        
        if not user_role or user_role == 'owner':
            return jsonify({'status': 'error', 'message': 'Åtkomst nekad'}), 403

        submission = AssignmentSubmission.query.filter_by(
            assignment_id=assignment_id,
            student_id=current_user.id
        ).first()

        if not submission:
            return jsonify({
                'status': 'success',
                'submission': None
            })

        files_data = []
        for file in submission.files:
            files_data.append({
                'id': file.id,
                'filename': file.filename,
                'file_size': file.file_size
            })

        # Hämta kommentarer
        comments = SubmissionComment.query.filter_by(submission_id=submission.id).order_by(SubmissionComment.created_at.desc()).all()
        comments_data = []
        for comment in comments:
            comments_data.append({
                'id': comment.id,
                'comment': comment.comment,
                'teacher_name': comment.teacher.username,
                'created_at': comment.created_at.isoformat(),
                'updated_at': comment.updated_at.isoformat()
            })

        return jsonify({
            'status': 'success',
            'submission': {
                'id': submission.id,
                'comment': submission.comment,
                'submitted_at': submission.submitted_at.isoformat(),
                'files': files_data,
                'teacher_comments': comments_data
            }
        })

    except Exception as e:
        print(f"Error loading my submission: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/assignments/delete', methods=['POST'])
def delete_assignment():
    """Ta bort uppgift (endast ägare)"""
    try:
        data = request.get_json()
        assignment_id = data.get('assignment_id')
        
        assignment = Assignment.query.get_or_404(assignment_id)
        user_role = get_user_role_in_subject(current_user.id, assignment.subject_id)
        
        if user_role != 'owner':
            return jsonify({'status': 'error', 'message': 'Endast ägare kan ta bort uppgifter'}), 403

        db.session.delete(assignment)
        db.session.commit()

        return jsonify({'status': 'success', 'message': 'Uppgift borttagen'})

    except Exception as e:
        db.session.rollback()
        print(f"Error deleting assignment: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500




@app.route('/api/assignments/<int:assignment_id>/submissions')
def get_assignment_submissions(assignment_id):
    """Hämta inlämningar för en uppgift (endast ägare)"""
    try:
        assignment = Assignment.query.get_or_404(assignment_id)
        if get_user_role_in_subject(current_user.id, assignment.subject_id) != 'owner':
            return jsonify({'status': 'error', 'message': 'Åtkomst nekad'}), 403

        submissions = AssignmentSubmission.query.filter_by(assignment_id=assignment_id).all()
        submissions_data = []
        for submission in submissions:
            comment_count = SubmissionComment.query.filter_by(submission_id=submission.id).count()

            # NYTT: lista upp inlämnade filer
            files = []
            for f in submission.files:
                files.append({
                    'id': f.id,
                    'filename': f.filename
                })

            submissions_data.append({
                'id': submission.id,
                'student_name': submission.student.username,
                'submitted_at': submission.submitted_at.isoformat(),
                'comment_count': comment_count,
                'seen': submission.seen,
                'comment': submission.comment or '',
                'files': files                    # <-- Skicka med fil-listan
            })

        return jsonify({'status': 'success', 'submissions': submissions_data})

    except Exception as e:
        print(f"Error loading submissions: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500




@app.route('/api/assignments/submit', methods=['POST'])
def submit_assignment():
    """Lämna in uppgift (medlemmar)"""
    try:
        assignment_id = request.form.get('assignment_id')
        comment = request.form.get('comment', '')
        
        assignment = Assignment.query.get_or_404(assignment_id)
        user_role = get_user_role_in_subject(current_user.id, assignment.subject_id)
        
        if not user_role or user_role == 'owner':
            return jsonify({'status': 'error', 'message': 'Åtkomst nekad'}), 403

        # Kontrollera om redan inlämnat
        existing_submission = AssignmentSubmission.query.filter_by(
            assignment_id=assignment_id,
            student_id=current_user.id
        ).first()

        if existing_submission:
            return jsonify({'status': 'error', 'message': 'Du har redan lämnat in denna uppgift'}), 400

        # Skapa inlämning
        submission = AssignmentSubmission(
            assignment_id=assignment_id,
            student_id=current_user.id,
            comment=comment
        )
        db.session.add(submission)
        db.session.flush()  # För att få submission.id

        # Hantera filer
        uploaded_files = request.files.getlist('files')
        if not uploaded_files:
            return jsonify({'status': 'error', 'message': 'Minst en fil krävs'}), 400

        # Skapa upload-mapp
        upload_dir = os.path.join('static', 'uploads', 'assignments', str(assignment.subject_id), str(assignment_id))
        os.makedirs(upload_dir, exist_ok=True)

        for file in uploaded_files:
            if file and file.filename:
                # Säker filnamn
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_filename = f"{current_user.id}_{timestamp}_{filename}"
                
                file_path = os.path.join(upload_dir, unique_filename)
                file.save(file_path)

                # Spara i databas
                assignment_file = AssignmentFile(
                    submission_id=submission.id,
                    filename=filename,
                    file_path=file_path,
                    file_size=os.path.getsize(file_path)
                )
                db.session.add(assignment_file)

        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': 'Uppgift inlämnad'
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error submitting assignment: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/assignments/<int:subject_id>/unseen_count')
def unseen_count(subject_id):
    # kolla att current_user är owner
    if get_user_role_in_subject(current_user.id, subject_id) != 'owner':
        return jsonify({'status':'error'}),403
    cnt = db.session.query(AssignmentSubmission).\
          join(Assignment).\
          filter(Assignment.subject_id==subject_id, AssignmentSubmission.seen==False).\
          count()
    return jsonify({'status':'success','unseen_count': cnt})


@app.route('/api/submission/<int:submission_id>/mark_seen', methods=['POST'])
def mark_seen(submission_id):
    submission = AssignmentSubmission.query.get_or_404(submission_id)
    # Kontroll: bara owner får göra detta
    if get_user_role_in_subject(current_user.id, submission.assignment.subject_id) != 'owner':
        return jsonify({'status':'error'}), 403

    submission.seen = True
    db.session.commit()
    return jsonify({'status':'success'})


@app.route('/download_submission_file/<int:file_id>')
def download_submission_file(file_id):
    """Ladda ner inlämnad fil"""
    try:
        file = AssignmentFile.query.get_or_404(file_id)
        assignment = file.submission.assignment
        user_role = get_user_role_in_subject(current_user.id, assignment.subject_id)
        
        if user_role != 'owner':
            return "Åtkomst nekad", 403

        return send_file(file.file_path, as_attachment=True, download_name=file.filename)

    except Exception as e:
        print(f"Error downloading file: {e}")
        return "Fil hittades inte", 404


@app.route('/view_shared_file/<int:file_id>')
@login_required
def view_shared_file(file_id):
    shared = SharedFile.query.get_or_404(file_id)
    if not shared.is_downloadable_by_user(current_user.id):
        abort(403)
    try:
        # as_attachment=False öppnar filen i webbläsaren (inline),
        # och vi anger inte download_name då vi inte behöver ett fönster-spar-namn.
        return send_file(
            shared.file_path,
            mimetype=shared.file_type,
            as_attachment=False,
            download_name=shared.filename
        )
    except FileNotFoundError:
        abort(404)
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



@app.route('/subject/<subject_name>/delete_quiz/<int:quiz_id>', methods=['POST'])
@login_required
def delete_quiz(subject_name, quiz_id):
    """
    Förbättrad quiz-radering som använder quiz ID istället för index
    """
    try:
        # Hämta subject
        subject_obj = Subject.query.filter_by(name=subject_name).first()
        if not subject_obj:
            flash("Subject not found.", "error")
            return redirect(url_for('index'))
        
        # Kolla att användaren är medlem eller ägare av ämnet
        if not current_user.is_member_of_subject(subject_obj.id) and current_user.id != subject_obj.creator_id:
            flash('Du har inte tillgång till detta ämne', 'error')
            return redirect(url_for('index'))
        
        # Hämta quiz direkt via ID istället för offset
        quiz_to_delete = Quiz.query.filter_by(
            id=quiz_id,
            subject_id=subject_obj.id
        ).first()
        
        if not quiz_to_delete:
            flash("Quiz not found.", "error")
            return redirect(url_for('subject', subject_name=subject_name))
        
        # Säkerhetskontroll: Endast skapare av quiz kan radera det
        # ELLER ägare av ämnet kan radera alla quiz i sitt ämne
        if quiz_to_delete.user_id != current_user.id and current_user.id != subject_obj.creator_id:
            flash("Du kan bara ta bort dina egna quiz, eller som ägare av ämnet kan du ta bort alla quiz.", "error")
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
        
        # Ta bort quiz
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




# Add this function to handle flashcard creation for new members
def create_flashcards_for_new_member(user_id, subject_id):
    """
    Skapa flashcards för en ny medlem baserat på alla shared quizzes i subject
    """
    try:
        # Hämta alla shared quizzes i detta subject
        shared_quizzes = Quiz.query.filter_by(
            subject_id=subject_id,
            is_personal=False
        ).all()
        
        total_created = 0
        for quiz in shared_quizzes:
            created_count = create_flashcards_for_user(quiz, user_id)
            total_created += created_count
            
        print(f"[INFO] Created {total_created} flashcards for new member {user_id} in subject {subject_id}")
        return total_created
        
    except Exception as e:
        print(f"[ERROR] Failed to create flashcards for new member: {e}")
        return 0









# Uppdatera flashcards_by_date funktionen för att inkludera quiz_id och user_role info
@app.route('/flashcards_by_date')
@login_required
def flashcards_by_date():
    """Get flashcards grouped by their next review date - now includes shared subjects and quiz info"""
    try:
        from datetime import datetime, timedelta
        
        # Hämta alla flashcards för användaren från alla tillgängliga subjects
        all_subjects = current_user.get_all_subjects()
        subject_ids = [s.id for s in all_subjects]
        
        flashcards = Flashcard.query.filter(
            Flashcard.user_id == current_user.id,
            Flashcard.subject_id.in_(subject_ids)  # Filter by accessible subjects
        ).all()
        
        schedule = {}
        today = datetime.now().date()
        
        for flashcard in flashcards:
            # Bestäm vilket datum kortet ska repeteras
            if flashcard.next_review is None:
                review_date = today
                status = 'new'
            elif flashcard.next_review <= today:
                review_date = today if flashcard.next_review < today else flashcard.next_review
                status = 'due' if flashcard.next_review == today else 'overdue'
            else:
                review_date = flashcard.next_review
                status = 'scheduled'
            
            date_key = review_date.isoformat()
            
            if date_key not in schedule:
                schedule[date_key] = []
            
            # Gruppera efter subject och topic
            quiz_key = f"{flashcard.subject}#{flashcard.topic}"
            
            # Hitta befintlig quiz-grupp eller skapa ny
            existing_quiz = None
            for item in schedule[date_key]:
                if item.get('quiz_key') == quiz_key:
                    existing_quiz = item
                    break
            
            if existing_quiz:
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
                # Hämta subject info för extra metadata
                subject = Subject.query.get(flashcard.subject_id)
                user_role = current_user.get_role_in_subject(subject.id) if subject else 'unknown'
                
                # Försök hitta quiz-objektet baserat på topic
                quiz = None
                is_personal_quiz = True  # Default assumption
                if subject:
                    # Först försök hitta shared quiz (is_personal=False)
                    quiz = Quiz.query.filter_by(
                        subject_id=subject.id,
                        title=flashcard.topic,
                        is_personal=False
                    ).first()
                    
                    if quiz:
                        is_personal_quiz = False
                    else:
                        # Om ingen shared quiz hittas, kolla efter personal quiz
                        quiz = Quiz.query.filter_by(
                            subject_id=subject.id,
                            title=flashcard.topic,
                            is_personal=True,
                            user_id=current_user.id  # Personal quiz should belong to current user
                        ).first()
                        
                        is_personal_quiz = True
                
                schedule[date_key].append({
                    'quiz_key': quiz_key,
                    'subject': flashcard.subject,
                    'subject_id': flashcard.subject_id,
                    'topic': flashcard.topic,
                    'quiz_title': flashcard.topic,
                    'quiz_id': quiz.id if quiz else None,
                    'status': status,
                    'count': 1,
                    'is_spaced_repetition': True,
                    'user_role': user_role,
                    'is_shared_subject': subject.user_id != current_user.id if subject else False,
                    'is_personal_quiz': is_personal_quiz,  # NEW: Add this field
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

# Enhanced User method to get quiz calendar data
def get_user_quiz_calendar_data(user_id, date=None):
    """
    Hämta quiz-kalendersdata för en användare, inklusive shared subject quizzes
    """
    try:
        if date is None:
            date = datetime.now().date()
        
        # Hämta alla subjects som användaren har tillgång till
        user = User.query.get(user_id)
        all_subjects = user.get_all_subjects()
        subject_ids = [s.id for s in all_subjects]
        
        # Hämta flashcards från alla tillgängliga subjects
        flashcards = Flashcard.query.filter(
            Flashcard.user_id == user_id,
            Flashcard.subject_id.in_(subject_ids),
            db.or_(
                Flashcard.next_review == date,
                db.and_(Flashcard.next_review == None, date == datetime.now().date()),
                db.and_(Flashcard.next_review < datetime.now().date(), date == datetime.now().date())
            )
        ).all()
        
        # Gruppera efter ämne och topic
        grouped_data = {}
        for flashcard in flashcards:
            # Hämta subject info
            subject = Subject.query.get(flashcard.subject_id)
            user_role = user.get_role_in_subject(subject.id)
            
            key = f"{flashcard.subject}#{flashcard.topic}"
            if key not in grouped_data:
                grouped_data[key] = {
                    'subject': flashcard.subject,
                    'subject_id': flashcard.subject_id,
                    'topic': flashcard.topic,
                    'quiz_title': flashcard.topic,
                    'count': 0,
                    'flashcards': [],
                    'user_role': user_role,
                    'is_shared_subject': subject.user_id != user_id,
                    'quiz_url': url_for('spaced_repetition_quiz', 
                                      subject=flashcard.subject, 
                                      topic=flashcard.topic.replace(' ', '_'),
                                      date=date.isoformat())
                }
            
            grouped_data[key]['count'] += 1
            grouped_data[key]['flashcards'].append({
                'id': flashcard.id,
                'question': flashcard.question,
                'answer': flashcard.answer,
                'next_review': flashcard.next_review.isoformat() if flashcard.next_review else None,
                'status': 'new' if flashcard.next_review is None else (
                    'overdue' if flashcard.next_review < datetime.now().date() else 'due'
                )
            })
        
        return grouped_data
        
    except Exception as e:
        print(f"[ERROR] Failed to get user quiz calendar data: {e}")
        return {}

@app.route('/api/leave_quiz', methods=['POST'])
@login_required
def leave_quiz_api():
    """API endpoint för medlemmar att lämna ett specifikt quiz"""
    try:
        data = request.get_json()
        subject = data.get('subject')
        topic = data.get('topic')
        quiz_id = data.get('quiz_id')
        
        if not subject or not topic:
            return jsonify({'status': 'error', 'error': 'Subject and topic are required'}), 400
        
        # Hitta subject-objektet
        subject_obj = Subject.query.filter_by(name=subject).first()
        if not subject_obj:
            return jsonify({'status': 'error', 'error': 'Subject not found'}), 404
        
        # Kontrollera att användaren är medlem (inte ägare)
        user_role = current_user.get_role_in_subject(subject_obj.id)
        if user_role != 'member':
            return jsonify({'status': 'error', 'error': 'Only members can leave quizzes'}), 403
        
        # Hitta quiz om quiz_id finns
        quiz = None
        if quiz_id:
            quiz = Quiz.query.filter_by(
                id=quiz_id,
                subject_id=subject_obj.id,
                is_personal=False  # Endast shared quizzes
            ).first()
        
        # Om quiz inte hittas via ID, försök hitta via topic
        if not quiz:
            quiz = Quiz.query.filter_by(
                title=topic,
                subject_id=subject_obj.id,
                is_personal=False
            ).first()
        
        if not quiz:
            return jsonify({'status': 'error', 'error': 'Quiz not found'}), 404
        
        # Ta bort alla flashcards för denna användare från detta quiz
        deleted_count = remove_user_flashcards_from_quiz(current_user.id, subject_obj.id, topic)
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully left quiz "{topic}". Removed {deleted_count} flashcards.',
            'deleted_flashcards': deleted_count
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Failed to leave quiz: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500


def remove_user_flashcards_from_quiz(user_id, subject_id, topic):
    """
    Ta bort alla flashcards för en specifik användare från ett specifikt quiz/topic
    """
    try:
        # Hitta alla flashcards för denna användare, subject och topic
        flashcards_to_delete = Flashcard.query.filter(
            Flashcard.user_id == user_id,
            Flashcard.subject_id == subject_id,
            Flashcard.topic == topic
        ).all()
        
        deleted_count = len(flashcards_to_delete)
        
        # Ta bort flashcards
        for flashcard in flashcards_to_delete:
            db.session.delete(flashcard)
        
        db.session.commit()
        
        print(f"[INFO] Removed {deleted_count} flashcards for user {user_id} from quiz '{topic}' in subject {subject_id}")
        return deleted_count
        
    except Exception as e:
        print(f"[ERROR] Failed to remove user flashcards from quiz: {e}")
        db.session.rollback()
        raise e





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
    
    with app.app_context():
        migrate_database()
        run_assignment_migrations()
        create_shared_files_table()
        ensure_upload_directories()
        setup_lunch_menu_data()  

    cleanup_on_startup()   # om den inte behöver context
    app.run(debug=True)
