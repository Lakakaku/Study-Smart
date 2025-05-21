import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from datetime import datetime
import requests
import fitz  
import pytesseract
from pdf2image import convert_from_path

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

SUBJECTS_FILE = 'subjects.json'
QUIZZES_FILE = 'quizzes.json'


def load_subjects():
    if os.path.exists(SUBJECTS_FILE):
        with open(SUBJECTS_FILE, 'r') as f:
            return json.load(f)
    return []


def save_subjects(subjects):
    with open(SUBJECTS_FILE, 'w') as f:
        json.dump(subjects, f)


def load_quizzes():
    if os.path.exists(QUIZZES_FILE):
        with open(QUIZZES_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_quizzes(quizzes):
    with open(QUIZZES_FILE, 'w') as f:
        json.dump(quizzes, f)


@app.route('/', methods=['GET', 'POST'])
def home():
    subjects = load_subjects()
    if request.method == 'POST':
        subject_name = request.form['subject']
        if subject_name and subject_name not in subjects:
            subjects.append(subject_name)
            save_subjects(subjects)
        return redirect(url_for('home'))
    return render_template('index.html', subjects=subjects)


@app.route('/subject/<subject_name>')
def subject(subject_name):
    quizzes = load_quizzes().get(subject_name, [])
    return render_template('subject.html', subject_name=subject_name, quizzes=quizzes)


@app.route('/delete_subject', methods=['POST'])
def delete_subject():
    subject_to_delete = request.form.get('subject')
    subjects = load_subjects()
    if subject_to_delete and subject_to_delete in subjects:
        subjects.remove(subject_to_delete)
        save_subjects(subjects)
    return redirect(url_for('home'))


@app.route('/subject/<subject_name>/quiz/<int:quiz_index>')
def start_quiz(subject_name, quiz_index):
    quizzes = load_quizzes().get(subject_name, [])
    if 0 <= quiz_index < len(quizzes):
        quiz = quizzes[quiz_index]
        return render_template('start_quiz.html', subject_name=subject_name, quiz=quiz)
    return "Quiz not found", 404


@app.route('/create-quiz', methods=['GET', 'POST'])
def create_quiz():
    subjects = load_subjects()

    if request.method == 'POST':
        uploaded_files = request.files.getlist('data1')
        user_title = request.form.get('quiz_title', '').strip()
        subject = request.form.get('subject')
        quiz_type = request.form.get('quiz-drop')
        description = request.form.get('quiz-description')

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        quiz_title = user_title if user_title else f"{subject} - {quiz_type.replace('-', ' ').title()} - {now}"

        saved_files = []
        file_contents = []

        upload_folder = os.path.join('uploads', subject)
        os.makedirs(upload_folder, exist_ok=True)

        for file in uploaded_files:
            if file.filename == '':
                continue

            filename = secure_filename(file.filename)
            ext = os.path.splitext(filename)[1].lower()
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)

            try:
                if ext == '.pdf':
                    text = ""
                    with fitz.open(filepath) as doc:
                        for page in doc:
                            text += page.get_text()

                    if not text.strip():
                        images = convert_from_path(filepath)
                        ocr_text = ""
                        for image in images:
                            ocr_text += pytesseract.image_to_string(image)
                        file_contents.append(ocr_text)
                    else:
                        file_contents.append(text)

                elif ext == '.txt':
                    with open(filepath, 'r', encoding='utf-8') as f:
                        file_contents.append(f.read())

            except Exception as e:
                print(f"[ERROR] Failed to process '{filename}': {e}")

            saved_files.append(filepath)

        combined_text = "\n\n".join(file_contents) if file_contents else 'No file content provided.'

        prompt = f"""
You're an AI quiz generator. Use the material's content to create questions, (not questions like: who wrote this book? (if the user linked a pdf from a book)), so ask questions that is relevant from the content in the files TOGETHER with the user's description/prompt, create a {quiz_type.replace('-', ' ')} with clear, direct questions and answers in this format:

Q: [Question]
A: [Answer]

Description: {description}

Material:
{combined_text}
"""

        api_url = "https://ai.hackclub.com/chat/completions"
        response = requests.post(api_url, json={
            "messages": [{"role": "user", "content": prompt}]
        }, headers={"Content-Type": "application/json"})

        if response.ok:
            raw = response.json().get("choices", [])[0].get("message", {}).get("content", "")
            print(f"[DEBUG] Raw AI response:\n{raw[:1000]}")
            lines = raw.strip().split("\n")
            questions = []
            q, a = None, None
            for line in lines:
                line = line.strip()
                if line.lower().startswith("q:"):
                    q = line[2:].strip()
                elif line.lower().startswith("a:"):
                    a = line[2:].strip()
                    if q and a:
                        questions.append({"question": q, "answer": a})
                        q, a = None, None
        else:
            print(f"[ERROR] AI API error: {response.status_code} - {response.text}")
            questions = [{"question": "[Error]", "answer": "Failed to generate quiz questions and answers."}]

        quizzes = load_quizzes()
        if subject not in quizzes:
            quizzes[subject] = []

        quizzes[subject].append({
            'title': quiz_title,
            'type': quiz_type,
            'description': description,
            'files': saved_files,
            'questions': questions
        })

        save_quizzes(quizzes)
        return redirect(url_for('subject', subject_name=subject))

    return render_template('create-quiz.html', subjects=subjects)


@app.route('/subject/<subject_name>/delete_quiz/<int:quiz_index>', methods=['POST'])
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
def flashcards(subject_name, quiz_index):
    quizzes = load_quizzes().get(subject_name, [])
    if 0 <= quiz_index < len(quizzes):
        quiz = quizzes[quiz_index]
        flashcards = [
            f"{q['question']}|{q['answer']}"
            for q in quiz.get('questions', [])
            if 'question' in q and 'answer' in q and not q['question'].startswith("[Error]")
        ]
        return render_template('flashcards.html', subject_name=subject_name, questions=flashcards)
    return "Flashcards not found", 404


if __name__ == '__main__':
    app.run(debug=True)
