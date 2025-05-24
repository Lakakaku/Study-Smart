document.addEventListener('DOMContentLoaded', () => {
  let currentCardIndex = 0;
  let startTime = null;
  const ratings = [];
  const times = [];

  const questionDiv = document.getElementById('question');
  const answerDiv = document.getElementById('answer');
  const showAnswerBtn = document.getElementById('show-answer-btn');
  const ratingSection = document.getElementById('rating-section');

  function showCard(index) {
    if (index >= questions.length) {
      questionDiv.textContent = "🎉 You have finished all flashcards!";
      answerDiv.style.display = 'none';
      showAnswerBtn.style.display = 'none';
      ratingSection.style.display = 'none';

      fetch('/submit_ratings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject: subjectName,
          quiz_title: quizTitle,
          ratings: ratings,
          times: times  
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

    startTime = Date.now(); 
  }

  showAnswerBtn.addEventListener('click', () => {
    answerDiv.style.display = 'block';
    showAnswerBtn.style.display = 'none';
    ratingSection.style.display = 'block';
  });

  window.submitRating = function (value) {
    const timeTaken = Math.round((Date.now() - startTime) / 1000);  // in seconds
    ratings.push(value);
    times.push(timeTaken);
    currentCardIndex++;
    showCard(currentCardIndex);
  };

  showCard(currentCardIndex);
});
