import json
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
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



app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

SUBJECTS_FILE = 'subjects.json'
QUIZZES_FILE = 'quizzes.json'
DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'data')
RATINGS_FILE = os.path.join(DATA_FOLDER, 'ratings.json')
FLASHCARDS_DATA_FILE = 'flashcards_data.json'


# -------------------- Utility Functions --------------------
def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return default

def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# -------------------- Subjects --------------------
def load_subjects():
    return load_json(SUBJECTS_FILE, [])


def save_subjects(subjects):
    save_json(subjects, SUBJECTS_FILE)


# -------------------- Quizzes --------------------
def load_quizzes():
    return load_json(QUIZZES_FILE, {})


def save_quizzes(quizzes):
    save_json(quizzes, QUIZZES_FILE)


# -------------------- Ratings --------------------
def load_ratings():
    return load_json(RATINGS_FILE, {})


def save_ratings(ratings):
    save_json(ratings, RATINGS_FILE)


def save_flashcard_data(data):
    save_ratings(data)


from datetime import datetime, timedelta

from datetime import datetime, timedelta

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


# -------------------- Routes --------------------

@app.route('/', methods=['GET', 'POST'])
def home():
    subjects = load_json(SUBJECTS_FILE, [])
    if request.method == 'POST':
        sub = request.form['subject'].strip()
        if sub and sub not in subjects:
            subjects.append(sub)
            save_json(subjects, SUBJECTS_FILE)
        return redirect(url_for('home'))
    return render_template('index.html', subjects=subjects)

@app.route('/delete_krav_document', methods=['POST'])
def delete_krav_document():
    data = request.get_json()
    subject = data.get('subject')
    doc_type = data.get('doc_type')

    krav_path = 'data/krav.json'

    if os.path.exists(krav_path):
        with open(krav_path, 'r', encoding='utf-8') as f:
            krav_data = json.load(f)
    else:
        return {'status': 'error', 'message': 'Krav-data finns inte'}, 400

    if subject in krav_data and doc_type in krav_data[subject]:
        del krav_data[subject][doc_type]
        # Ta bort subject om tomt
        if not krav_data[subject]:
            del krav_data[subject]
        
        with open(krav_path, 'w', encoding='utf-8') as f:
            json.dump(krav_data, f, ensure_ascii=False, indent=2)
        return {'status': 'success'}
    else:
        return {'status': 'error', 'message': 'Dokument hittades inte'}, 404


@app.route('/subject/<subject_name>')
def subject(subject_name):
    quizzes = load_quizzes().get(subject_name, [])
    
    # Läs krav.json
    krav_path = 'data/krav.json'
    if os.path.exists(krav_path):
        with open(krav_path, 'r', encoding='utf-8') as f:
            krav_data = json.load(f)
    else:
        krav_data = {}

    # Hämta dokument för subject (eller tomt dict)
    documents = krav_data.get(subject_name, {})

    return render_template('subject.html', subject_name=subject_name, quizzes=quizzes, documents=documents)

@app.route('/delete_subject', methods=['POST'])
def delete_subject():
    subject_to_delete = request.form.get('subject')
    subjects = load_subjects()
    if subject_to_delete in subjects:
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


@app.route('/upload_krav_pdf', methods=['POST'])
def upload_krav_pdf():
    subject = request.form['subject']
    doc_type = request.form['type']
    file = request.files.get('file')
    if not file:
        return jsonify(status='error', message='Ingen fil'), 400

    # Spara filen på disk
    folder = os.path.join('static', 'uploads', 'krav', subject)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{doc_type}.pdf")
    file.save(path)

    # Läs in texten som tidigare för JSON-innehåll
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

    # Uppdatera krav.json
    krav_path = os.path.join('data', 'krav.json')
    krav_data = load_json(krav_path, {})
    krav_data.setdefault(subject, {})[doc_type] = {'innehåll': text}
    save_json(krav_data, krav_path)

    return jsonify(status='success')



@app.route('/create-quiz', methods=['GET', 'POST'])
def create_quiz():
    subjects = load_subjects()

    if request.method == 'POST':
        # Form inputs
        uploaded_files = request.files.getlist('data1')
        user_title = request.form.get('quiz_title', '').strip()
        subject = request.form.get('subject')
        quiz_type = request.form.get('quiz-drop')  # 'ten', 'twenty-five', etc.
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
        upload_folder = os.path.join('uploads', subject)
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
            krav_path = os.path.join('data', 'krav.json')
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
        prompt = (
            f"You're an AI quiz generator – create"
        )
        # Specify number if applicable
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

    # GET
    events = []
    if os.path.exists('events.json'):
        with open('events.json', 'r', encoding='utf-8') as f:
            events = json.load(f)
    return render_template('create-quiz.html', subjects=subjects, events=events)



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

def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_today_flashcards(data, subject, category):
    today = datetime.today().strftime("%Y-%m-%d")
    cards = []

    for question, info in data.get(subject, {}).get(category, {}).items():
        if info.get("next_review") == today:
            cards.append((question, info))

    return cards


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
        quiz_title = quiz.get('title', 'Untitled Quiz')
        return render_template('flashcards.html', subject_name=subject_name, questions=flashcards, quiz_title=quiz_title)
    return "Flashcards not found", 404




@app.route('/submit_ratings', methods=['POST'])
def submit_rating():
    """Förbättrad version som korrekt hanterar både originala quiz och daily quiz repetitioner"""
    try:
        payload = request.get_json()
       
        
        subject = payload.get('subject')
        quiz_title = payload.get('quiz_title') 
        responses = payload.get('responses', [])

        if not (subject and quiz_title and responses):
            return jsonify({'error': 'Missing data'}), 400

        # Extrahera rätt subject och topic från quiz_title om det är en daily quiz
        actual_subject = subject
        actual_topic = quiz_title
        
        # Kolla om det är en daily quiz (format: "subject — topic" eller "Repetition YYYY-MM-DD — subject / topic")
        if " — " in subject:
            # Format: "subject — topic"
            parts = subject.split(" — ")
            if len(parts) == 2:
                actual_subject = parts[0]
                actual_topic = parts[1]
        elif quiz_title.startswith("Repetition") and " — " in quiz_title:
            # Format: "Repetition YYYY-MM-DD — subject / topic"
            parts = quiz_title.split(" — ")
            if len(parts) == 2:
                subject_topic = parts[1]
                if " / " in subject_topic:
                    subj_parts = subject_topic.split(" / ")
                    if len(subj_parts) == 2:
                        actual_subject = subj_parts[0]
                        actual_topic = subj_parts[1]

        

        # Import här för att undvika circular imports
        from spaced_repetition import update_rating
        
        updated_count = 0
        
        # Uppdatera varje fråga med den nya funktionen
        for resp in responses:
            question = resp.get('question')
            rating = resp.get('rating')
            time_taken = resp.get('time')
            
            
            
            if question and rating is not None:
                try:
                    rating = int(rating)
                    if 1 <= rating <= 4:
                        # Anropa update_rating funktionen med rätt subject/topic
                        update_rating(actual_subject, actual_topic, question, rating, time_taken)
                        updated_count += 1
                        
                    else:
                        print("yo")
                except ValueError:
                    print(f"[ERROR] Could not convert rating to int: {rating}")
                except Exception as e:
                    print(f"[ERROR] Failed to update question '{question[:50]}...': {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"[WARNING] Skipping question due to missing data: question={bool(question)}, rating={rating}")
        
        
        
        return jsonify({
            'status': 'success', 
            'message': f'Updated {updated_count} questions',
            'updated_count': updated_count,
            'total_responses': len(responses),
            'resolved_subject': actual_subject,
            'resolved_topic': actual_topic
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to update ratings: {str(e)}'}), 500


@app.route('/api/statistics')
def get_statistics_api():
    """API endpoint för att få stat istik"""
    try:
        from spaced_repetition import get_statistics
        stats = get_statistics()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': 'Failed to get statistics'}), 500

@app.route('/api/due_questions')
def get_due_questions_api():
    """API endpoint för att få alla förfallna frågor"""
    try:
        due_questions = get_due_questions()
        return jsonify({
            'count': len(due_questions),
            'questions': due_questions
        })
    except Exception as e:
        return jsonify({'error': 'Failed to get due questions'}), 500


@app.route('/reset_question', methods=['POST'])
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
def get_events():
    try:
        if os.path.exists('events.json'):
            with open('events.json', 'r') as f:
                events = json.load(f)
        else:
            events = []
        return jsonify(events)
    except Exception as e:
        return jsonify([]), 500


@app.route('/api/events', methods=['POST'])
def save_event():
    try:
        event_data = request.get_json()
        required_fields = ['date', 'subject', 'testType', 'title']
        for field in required_fields:
            if field not in event_data or not event_data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        events = []
        if os.path.exists('events.json'):
            with open('events.json', 'r') as f:
                events = json.load(f)

        if 'created' not in event_data:
            event_data['created'] = datetime.now().isoformat()

        events.append(event_data)

        with open('events.json', 'w') as f:
            json.dump(events, f, indent=2)

        return jsonify({'success': True, 'message': 'Event saved successfully'})

    except Exception as e:
        return jsonify({'error': 'Failed to save event'}), 500


@app.route('/api/events/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    try:
        events = []
        if os.path.exists('events.json'):
            with open('events.json', 'r') as f:
                events = json.load(f)

        events = [event for event in events if event.get('id') != event_id]

        with open('events.json', 'w') as f:
            json.dump(events, f, indent=2)

        return jsonify({'success': True, 'message': 'Event deleted successfully'})

    except Exception as e:
        return jsonify({'error': 'Failed to delete event'}), 500


@app.route("/get_events_for_date")
def get_events_for_date():
    date = request.args.get("date")
    if not date:
        return jsonify([])

    try:
        if os.path.exists("events.json"):
            with open("events.json", "r") as f:
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
def flashcards_by_date():
    """
    Returnerar både nya frågor och due-frågor grupperade per next_review-datum.
    Nya frågor (utan metadata) får next_review = idag.
    """
    try:
        # 1) Läs in metadata och alla sparade quizzar
        ratings     = load_ratings()       # läser från DATA_FOLDER/ratings.json
        all_quizzes = load_quizzes()       # läser från quizzes.json
        today       = datetime.now().date()

        schedule = {}

        # 2) För varje subject → varje quiz → varje fråga
        for subject, quiz_list in all_quizzes.items():
            for quiz in quiz_list:
                topic = quiz['title']
                questions = quiz.get('questions', [])
                
                # Filtrera bort frågor som börjar med [Error]
                valid_questions = [q for q in questions 
                                 if q.get('question') and not q['question'].startswith("[Error]")]
                
                for item in valid_questions:
                    question = item.get('question')
                    if not question:
                        continue

                    # 3) Hämta next_review från metadata om den finns
                    meta = ratings \
                        .get(subject, {}) \
                        .get(topic, {}) \
                        .get(question)

                    if meta and 'next_review' in meta:
                        try:
                            nr_date = datetime.strptime(
                                meta['next_review'], '%Y-%m-%d'
                            ).date()
                        except ValueError:
                            nr_date = today
                    else:
                        # Ny fråga → review idag
                        nr_date = today

                    # 4) Lägg in i schemat under rätt nyckel
                    key = nr_date.isoformat()
                    schedule.setdefault(key, []).append({
                        'subject': subject,
                        'topic':   topic,
                        'question': question
                    })

        return jsonify(schedule)

    except Exception as e:
        return jsonify({}), 500

    except Exception as e:
        return jsonify({}), 500



@app.route('/daily_quiz/<date>/<subject>/<path:topic>')
def daily_quiz(date, subject, topic):
    """Förbättrad version som korrekt skickar subject/topic till frontend"""
    subject = urllib.parse.unquote(subject)
    topic = urllib.parse.unquote(topic)
    
   
    
    try:
        # Hämta alla frågor från den ursprungliga quizen
        all_quizzes = load_quizzes().get(subject, [])
        quiz = next((z for z in all_quizzes if z['title'] == topic), None)
        
        if not quiz:
            return f"Quiz '{topic}' not found for subject '{subject}'", 404

        

        # Hämta spaced repetition data
        ratings_data = load_ratings()
        questions_meta = ratings_data.get(subject, {}).get(topic, {})
        
        
        cards = []
        today_date = datetime.strptime(date, '%Y-%m-%d').date()
        today_str = today_date.isoformat()
        
        
        
        # Gå igenom alla frågor i quizet
        for item in quiz['questions']:
            question = item.get('question', '')
            answer = item.get('answer', '')
            
            # Skippa error-frågor
            if question.startswith("[Error]") or not question or not answer:
                continue
            
            if question in questions_meta:
                # Frågan har redan metadata - kontrollera om den ska repeteras
                next_review = questions_meta[question].get('next_review')
                
                # Inkludera om schemalagd för idag eller tidigare (försenade)
                if next_review and next_review <= today_str:
                    cards.append(f"{question}|{answer}")
            else:
                # Ny fråga som aldrig testats - inkludera den
                cards.append(f"{question}|{answer}")


        if not cards:
            return render_template('flashcards.html',
                                 subject_name=subject,  # Skicka bara subject här
                                 quiz_title=f"No repetitions for {date}",
                                 questions=[],
                                 message=f"No cards scheduled for {subject} / {topic} on {date}")

        # Använd original topic som quiz_title för korrekt spårning
        return render_template('flashcards.html',
                             subject_name=subject,      # Skicka bara subject
                             quiz_title=topic,          # Skicka original topic som quiz_title
                             questions=cards,
                             is_daily_quiz=True,        # Markera att det är en daily quiz
                             quiz_date=date)            # Skicka med datumet för display
                             
    except Exception as e:
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
