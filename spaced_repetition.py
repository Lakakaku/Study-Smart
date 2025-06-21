import os
import json
import datetime
from datetime import timedelta, date

DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'data')
RATINGS_FILE = os.path.join(DATA_FOLDER, 'ratings.json')

def load_ratings():
    """Läs in ratings.json om den finns, annars tom dict"""
    try:
        if os.path.exists(RATINGS_FILE):
            with open(RATINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"[DEBUG] Loaded ratings from {RATINGS_FILE}")
                return data
        else:
            print(f"[DEBUG] No ratings file found at {RATINGS_FILE}, returning empty dict")
            return {}
    except Exception as e:
        print(f"[ERROR] Failed to load ratings: {e}")
        return {}

def save_ratings(ratings_data):
    """Spara ratings till fil"""
    try:
        os.makedirs(DATA_FOLDER, exist_ok=True)
        
        # Backup old file
        if os.path.exists(RATINGS_FILE):
            backup_file = f"{RATINGS_FILE}.backup"
            os.rename(RATINGS_FILE, backup_file)
        
        with open(RATINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(ratings_data, f, ensure_ascii=False, indent=2)
        
        print(f"[DEBUG] Saved ratings to {RATINGS_FILE}")
        
    except Exception as e:
        print(f"[ERROR] Failed to save ratings: {e}")
        raise



def update_rating(subject: str, quiz_title: str, question: str, rating: int, time_taken: float = None) -> None:
    """
    Uppdaterar spaced repetition-data i ratings.json med extra debug-loggning
    """
    try:
        print(f"[DEBUG] update_rating called:")
        print(f"  - subject: '{subject}'")
        print(f"  - quiz_title: '{quiz_title}'") 
        print(f"  - question: '{question[:50]}...'")
        print(f"  - rating: {rating}")
        print(f"  - time_taken: {time_taken}")
        
        today = date.today()
        ratings_data = load_ratings()
        
        print(f"[DEBUG] Loaded ratings_data structure:")
        for subj in ratings_data.keys():
            print(f"  Subject: '{subj}'")
            for quiz in ratings_data[subj].keys():
                print(f"    Quiz: '{quiz}' ({len(ratings_data[subj][quiz])} questions)")
        
        # Hämta befintligt, eller initiera med standardvärden
        qdata = ratings_data \
            .setdefault(subject, {}) \
            .setdefault(quiz_title, {}) \
            .setdefault(question, {
                "ease_factor": 2.5,
                "repetitions": 0,
                "interval": 0,
                "next_review": today.isoformat(),
                "first_seen": today.isoformat(),
                "total_reviews": 0
            })

        print(f"[DEBUG] Current question data before update: {qdata}")

        # Hämta nuvarande värden
        ef = qdata.get("ease_factor", 2.5)
        reps = qdata.get("repetitions", 0)
        prev_interval = qdata.get("interval", 0)
        total_reviews = qdata.get("total_reviews", 0)
        q = int(rating)

        print(f"[DEBUG] Before calculation: ef={ef}, reps={reps}, prev_interval={prev_interval}, total_reviews={total_reviews}")

        # 1) Uppdatera ease-factor baserat på SuperMemo 2 algoritm
        ef_new = max(1.3, ef + (0.1 - (4 - q) * (0.08 + (4 - q) * 0.02)))

        # 2) Uppdatera repetitioner och interval
        if q < 3:  # Dåligt svar - börja om
            reps_new = 0
            interval_new = 1
            print(f"[DEBUG] Poor answer (rating {q}) - resetting interval")
        else:  # Bra svar - öka intervallet
            reps_new = reps + 1
            if reps_new == 1:
                interval_new = int(round(ef_new)) if q == 4 else 1
                print(f"[DEBUG] First repetition - interval set to {interval_new}")
            elif reps_new == 2:
                interval_new = 6
                print(f"[DEBUG] Second repetition - interval set to 6")
            else:
                interval_new = max(1, int(round(prev_interval * ef_new)))
                print(f"[DEBUG] Subsequent repetition - interval: {prev_interval} * {ef_new} = {interval_new}")

        # 3) Bonus för super-snabbt perfekt svar
        if q == 4 and time_taken is not None and time_taken < 5:
            bonus_interval = int(round((prev_interval or 1) * ef_new * 1.2))
            old_interval = interval_new
            interval_new = max(interval_new, bonus_interval)
            print(f"[DEBUG] Speed bonus applied: {old_interval} -> {interval_new}")

        # 4) Beräkna nästa review datum
        next_rev = (today + timedelta(days=interval_new)).isoformat()

        print(f"[DEBUG] Final calculation results:")
        print(f"  - ease_factor: {ef} -> {ef_new}")
        print(f"  - repetitions: {reps} -> {reps_new}")
        print(f"  - interval: {prev_interval} -> {interval_new}")
        print(f"  - next_review: {next_rev}")

        # 5) Uppdatera alla värden
        qdata.update({
            "ease_factor": round(ef_new, 2),
            "repetitions": reps_new,
            "interval": interval_new,
            "next_review": next_rev,
            "rating": q,
            "time": time_taken,
            "timestamp": datetime.datetime.now().isoformat(),
            "total_reviews": total_reviews + 1,
            "last_reviewed": today.isoformat()
        })

        print(f"[DEBUG] Updated question data: {qdata}")

        # 6) Spara uppdaterad data
        print(f"[DEBUG] Saving to file: {RATINGS_FILE}")
        save_ratings(ratings_data)
        
        # 7) Verifiera att det sparades
        verification_data = load_ratings()
        saved_qdata = verification_data.get(subject, {}).get(quiz_title, {}).get(question, {})
        saved_next_review = saved_qdata.get('next_review', 'NOT_FOUND')
        print(f"[DEBUG] Verification - saved next_review: {saved_next_review}")
        
        print(f"[DEBUG] SUCCESS: Updated '{question[:50]}...' - Rating: {q}, New interval: {interval_new} days, Next review: {next_rev}")
        
    except Exception as e:
        print(f"[ERROR] Failed to update rating for question '{question[:50]}...': {e}")
        import traceback
        traceback.print_exc()
        raise



def get_due_questions(subject=None, quiz_title=None, include_new=True):
    """
    Hämta alla frågor som är redo för repetition idag eller tidigare.
    """
    try:
        ratings_data = load_ratings()
        today = date.today().isoformat()
        due_questions = []
        
        for subj, quizzes in ratings_data.items():
            if subject and subj != subject:
                continue
                
            for quiz, questions in quizzes.items():
                if quiz_title and quiz != quiz_title:
                    continue
                    
                for question, data in questions.items():
                    next_review = data.get('next_review', today)
                    
                    # Inkludera frågan om den är förfallen eller försenad
                    if next_review <= today:
                        due_questions.append({
                            'subject': subj,
                            'quiz_title': quiz,
                            'question': question,
                            'data': data
                        })
        
        return due_questions
        
    except Exception as e:
        print(f"[ERROR] Failed to get due questions: {e}")
        return []

def get_questions_for_date(target_date):
    """
    Hämta alla frågor schemalagda för ett specifikt datum.
    """
    try:
        if isinstance(target_date, date):
            target_date = target_date.isoformat()
        
        ratings_data = load_ratings()
        result = {}
        
        for subject, quizzes in ratings_data.items():
            for quiz_title, questions in quizzes.items():
                questions_for_date = []
                
                for question, data in questions.items():
                    next_review = data.get('next_review')
                    if next_review == target_date:
                        questions_for_date.append({
                            'question': question,
                            'data': data
                        })
                
                if questions_for_date:
                    if subject not in result:
                        result[subject] = {}
                    result[subject][quiz_title] = questions_for_date
        
        return result
        
    except Exception as e:
        print(f"[ERROR] Failed to get questions for date {target_date}: {e}")
        return {}

def get_schedule_summary(days_ahead=30):
    """
    Få en översikt över repetitionsschema för kommande dagar.
    """
    try:
        ratings_data = load_ratings()
        today = date.today()
        summary = {}
        
        # Initiera alla datum med 0
        for i in range(days_ahead + 1):
            date_key = (today + timedelta(days=i)).isoformat()
            summary[date_key] = 0
        
        # Räkna frågor per datum
        for subject, quizzes in ratings_data.items():
            for quiz_title, questions in quizzes.items():
                for question, data in questions.items():
                    next_review = data.get('next_review')
                    if next_review in summary:
                        summary[next_review] += 1
        
        return summary
        
    except Exception as e:
        print(f"[ERROR] Failed to get schedule summary: {e}")
        return {}

def reset_question(subject: str, quiz_title: str, question: str):
    """
    Återställ en fråga till ursprungsläge (för debugging/testing).
    """
    try:
        ratings_data = load_ratings()
        
        if (subject in ratings_data and 
            quiz_title in ratings_data[subject] and 
            question in ratings_data[subject][quiz_title]):
            
            today = date.today()
            ratings_data[subject][quiz_title][question] = {
                "ease_factor": 2.5,
                "repetitions": 0,
                "interval": 0,
                "next_review": today.isoformat(),
                "first_seen": today.isoformat(),
                "total_reviews": 0
            }
            
            save_ratings(ratings_data)
            print(f"[DEBUG] Reset question: {question[:50]}...")
            
    except Exception as e:
        print(f"[ERROR] Failed to reset question: {e}")

def get_statistics():
    """
    Få statistik över hela systemet.
    """
    try:
        ratings_data = load_ratings()
        today = date.today().isoformat()
        
        stats = {
            'total_questions': 0,
            'due_today': 0,
            'overdue': 0,
            'subjects': len(ratings_data),
            'avg_ease_factor': 0,
            'total_reviews': 0
        }
        
        ease_factors = []
        
        for subject, quizzes in ratings_data.items():
            for quiz_title, questions in quizzes.items():
                for question, data in questions.items():
                    stats['total_questions'] += 1
                    stats['total_reviews'] += data.get('total_reviews', 0)
                    
                    next_review = data.get('next_review', today)
                    if next_review == today:
                        stats['due_today'] += 1
                    elif next_review < today:
                        stats['overdue'] += 1
                    
                    ease_factors.append(data.get('ease_factor', 2.5))
        
        if ease_factors:
            stats['avg_ease_factor'] = round(sum(ease_factors) / len(ease_factors), 2)
        
        return stats
        
    except Exception as e:
        print(f"[ERROR] Failed to get statistics: {e}")
        return {}
