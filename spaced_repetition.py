import json
import os
from datetime import datetime, timedelta
from flask_login import current_user

def get_user_ratings_file():
    """Returnerar sökvägen till användarens ratings-fil"""
    if not current_user.is_authenticated:
        return None
    
    data_folder = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(data_folder, exist_ok=True)
    return os.path.join(data_folder, f'ratings_{current_user.id}.json')

def load_ratings():
    """Laddar användarens ratings-data"""
    ratings_file = get_user_ratings_file()
    if not ratings_file or not os.path.exists(ratings_file):
        return {}
    
    try:
        with open(ratings_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_ratings(ratings_data):
    """Sparar användarens ratings-data"""
    ratings_file = get_user_ratings_file()
    if not ratings_file:
        return False
    
    try:
        with open(ratings_file, 'w', encoding='utf-8') as f:
            json.dump(ratings_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[ERROR] Could not save ratings: {e}")
        return False

def update_rating(subject, topic, question, rating, time_taken=None):
    """
    Uppdaterar en frågas rating och beräknar nästa review-datum
    
    Args:
        subject (str): Ämne
        topic (str): Topic/Quiz titel
        question (str): Frågan
        rating (int): Betyg 1-4 (1=svårt, 2=lätt med ansträngning, 3=lätt, 4=mycket lätt)
        time_taken (float): Tid i sekunder (optional)
    """
    try:
        # Ladda aktuell data
        ratings_data = load_ratings()
        
        # Skapa nödvändiga nästlade strukturer
        if subject not in ratings_data:
            ratings_data[subject] = {}
        if topic not in ratings_data[subject]:
            ratings_data[subject][topic] = {}
        if question not in ratings_data[subject][topic]:
            ratings_data[subject][topic][question] = {
                "ease_factor": 2.5,
                "repetitions": 0,
                "interval": 0,
                "next_review": datetime.now().strftime("%Y-%m-%d")
            }
        
        # Hämta nuvarande flashcard-data
        flashcard = ratings_data[subject][topic][question]
        
        # Extrahera nuvarande värden
        ease_factor = flashcard.get("ease_factor", 2.5)
        repetitions = flashcard.get("repetitions", 0)
        prev_interval = flashcard.get("interval", 0)
        
        # Konvertera rating till int
        q = int(rating)
        
        # SuperMemo-2 algoritm
        # 1. Uppdatera ease factor
        ease_factor = max(1.3, ease_factor + (0.1 - (4 - q) * (0.08 + (4 - q) * 0.02)))
        
        # 2. Beräkna nytt intervall och repetitioner
        if q < 3:  # Svårt svar - börja om
            repetitions = 0
            interval = 1
        else:  # Bra svar
            repetitions += 1
            if repetitions == 1:
                interval = int(round(ease_factor)) if q == 4 else 1
            elif repetitions == 2:
                interval = 6
            else:
                interval = int(round(prev_interval * ease_factor))
        
        # 3. Bonus för supersnabbt perfekt svar
        if q == 4 and time_taken is not None and time_taken < 5:
            interval = max(interval, int(round((prev_interval or 1) * ease_factor * 1.2)))
        
        # 4. Beräkna nästa review-datum
        next_review_date = datetime.now() + timedelta(days=interval)
        next_review = next_review_date.strftime("%Y-%m-%d")
        
        # 5. Uppdatera flashcard-data
        flashcard.update({
            "rating": q,
            "time": time_taken,
            "ease_factor": round(ease_factor, 2),
            "repetitions": repetitions,
            "interval": interval,
            "next_review": next_review,
            "timestamp": datetime.now().isoformat(),
            "last_reviewed": datetime.now().strftime("%Y-%m-%d")
        })
        
        # 6. Spara uppdaterad data
        success = save_ratings(ratings_data)
        
        if success:
            print(f"[SUCCESS] Updated question: {question[:50]}... -> Rating: {q}, Next review: {next_review}, Interval: {interval} days")
        else:
            print(f"[ERROR] Failed to save ratings for question: {question[:50]}...")
            
        return success
        
    except Exception as e:
        print(f"[ERROR] Failed to update rating for question '{question[:50]}...': {e}")
        import traceback
        traceback.print_exc()
        return False

def get_due_questions(target_date=None):
    """
    Hämtar alla frågor som är klara för repetition på ett specifikt datum
    
    Args:
        target_date (str): Datum i format 'YYYY-MM-DD', default är idag
    
    Returns:
        list: Lista med frågor som är klara för repetition
    """
    if target_date is None:
        target_date = datetime.now().strftime("%Y-%m-%d")
    
    ratings_data = load_ratings()
    due_questions = []
    
    for subject, topics in ratings_data.items():
        for topic, questions in topics.items():
            for question, data in questions.items():
                next_review = data.get('next_review')
                if next_review and next_review <= target_date:
                    due_questions.append({
                        'subject': subject,
                        'topic': topic,
                        'question': question,
                        'next_review': next_review,
                        'interval': data.get('interval', 0),
                        'repetitions': data.get('repetitions', 0),
                        'ease_factor': data.get('ease_factor', 2.5)
                    })
    
    return due_questions

def get_statistics():
    """
    Returnerar statistik om användarens flashcards
    
    Returns:
        dict: Statistik om flashcards
    """
    ratings_data = load_ratings()
    
    total_cards = 0
    cards_due_today = 0
    cards_overdue = 0
    new_cards = 0
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Räkna från ratings-data
    for subject, topics in ratings_data.items():
        for topic, questions in topics.items():
            for question, data in questions.items():
                total_cards += 1
                next_review = data.get('next_review')
                
                if not next_review:
                    new_cards += 1
                elif next_review == today:
                    cards_due_today += 1
                elif next_review < today:
                    cards_overdue += 1
    
    return {
        'total_cards': total_cards,
        'cards_due_today': cards_due_today,
        'cards_overdue': cards_overdue,
        'new_cards': new_cards,
        'cards_upcoming': total_cards - cards_due_today - cards_overdue - new_cards
    }

def reset_question(subject, topic, question):
    """
    Återställer en fråga till standardvärden (för debugging)
    
    Args:
        subject (str): Ämne
        topic (str): Topic/Quiz titel  
        question (str): Frågan
    """
    try:
        ratings_data = load_ratings()
        
        if (subject in ratings_data and 
            topic in ratings_data[subject] and 
            question in ratings_data[subject][topic]):
            
            # Återställ till standardvärden
            ratings_data[subject][topic][question] = {
                "ease_factor": 2.5,
                "repetitions": 0,
                "interval": 0,
                "next_review": datetime.now().strftime("%Y-%m-%d")
            }
            
            success = save_ratings(ratings_data)
            if success:
                print(f"[SUCCESS] Reset question: {question[:50]}...")
            return success
        else:
            print(f"[WARNING] Question not found: {question[:50]}...")
            return False
            
    except Exception as e:
        print(f"[ERROR] Failed to reset question: {e}")
        return False

def cleanup_old_data():
    """
    Rensar bort gamla ratings som inte längre har motsvarande quiz
    (kan användas för underhåll)
    """
    try:
        from flask import current_app
        with current_app.app_context():
            ratings_data = load_ratings()
            
            # Här skulle man kunna implementera logik för att 
            # ta bort ratings som inte längre har motsvarande quiz
            # Detta är optional och kan implementeras senare
            
            pass
            
    except Exception as e:
        print(f"[ERROR] Cleanup failed: {e}")
