document.addEventListener('DOMContentLoaded', () => {
  let currentCardIndex = 0;
  let startTime = null;
  const responses = [];

  const questionDiv = document.getElementById('question');
  const answerDiv = document.getElementById('answer');
  const showAnswerBtn = document.getElementById('show-answer-btn');
  const ratingSection = document.getElementById('rating-section');
  const backToQuestionBtn = document.getElementById('back-to-question-btn');
  const prevBtn = document.getElementById('prev-btn');
  const ratingButtons = document.querySelectorAll('.rating-btn');

  function showCard(index) {
    if (index >= questions.length) {
      questionDiv.textContent = "🎉 You have finished all flashcards!";
      answerDiv.style.display = 'none';
      showAnswerBtn.style.display = 'none';
      ratingSection.style.display = 'none';
      prevBtn.style.display = 'none';

      // Skicka hela batchen responses till backend
      fetch('/submit_ratings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject: subjectName,
          quiz_title: quizTitle,
          responses: responses
        })
      })
      .then(res => res.json())
      .then(data => {
        if (data.error) {
          alert("Error saving ratings: " + data.error);
        } else {
          alert("Thanks! Your ratings were saved.");
          window.location.href = `/subject/${subjectName}`;
        }
      })
      .catch(err => {
        alert("Network error: " + err.message);
      });

      return;
    }

    let [questionText, answerText] = questions[index].split('|');
    questionDiv.textContent = questionText.trim();
    answerDiv.textContent = (answerText || "[Answer not provided]").trim();
    answerDiv.style.display = 'none';
    showAnswerBtn.style.display = 'inline-block';
    ratingSection.style.display = 'none';

    prevBtn.style.display = (index > 0) ? 'inline-block' : 'none';

    startTime = Date.now(); 
  }

  showAnswerBtn.addEventListener('click', () => {
    answerDiv.style.display = 'block';
    showAnswerBtn.style.display = 'none';
    ratingSection.style.display = 'block';
  });

  backToQuestionBtn.addEventListener('click', () => {
    answerDiv.style.display = 'none';
    showAnswerBtn.style.display = 'inline-block';
    ratingSection.style.display = 'none';
  });

  prevBtn.addEventListener('click', () => {
    if (currentCardIndex > 0) {
      currentCardIndex--;
      if (responses.length > currentCardIndex) {
        responses.pop();
      }
      showCard(currentCardIndex);
    }
  });

  ratingButtons.forEach(button => {
    button.addEventListener('click', () => {
      const value = parseInt(button.getAttribute('data-value'));
      const timeTaken = Math.round((Date.now() - startTime) / 1000); // sekunder

      let [questionText] = questions[currentCardIndex].split('|');

      // Lägg till eller uppdatera response för aktuell fråga
      if (responses.length === currentCardIndex) {
        responses.push({
          question: questionText.trim(),
          rating: value,
          time: timeTaken
        });
      } else {
        responses[currentCardIndex] = {
          question: questionText.trim(),
          rating: value,
          time: timeTaken
        };
      }

      currentCardIndex++;
      showCard(currentCardIndex);
    });
  });

  // Initial visa första kortet
  showCard(currentCardIndex);
});
