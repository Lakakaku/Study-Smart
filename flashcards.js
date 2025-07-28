// static/js/flashcards.js
// Updated to work with database-based flashcard system

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
  
  // Add progress indicator
  const progressDiv = document.createElement('div');
  progressDiv.id = 'progress-indicator';
  progressDiv.className = 'progress-indicator';
  document.querySelector('.flashcard-container').insertBefore(progressDiv, document.getElementById('flashcard'));

  function updateProgress() {
    const progress = Math.round((currentCardIndex / questions.length) * 100);
    progressDiv.innerHTML = `
      <div class="progress-bar">
        <div class="progress-fill" style="width: ${progress}%"></div>
      </div>
      <div class="progress-text">Flashcard ${currentCardIndex + 1} av ${questions.length}</div>
    `;
  }

  function showCard(index) {
    if (index >= questions.length) {
      // All cards completed
      questionDiv.innerHTML = `
        <div class="completion-message">
          <h2>🎉 Grymt Jobbat!</h2>
          <p>Du har spelat ${questions.length} flashcards!</p>
          <div class="completion-stats">
            <p>Flashcards spelade: ${responses.length}</p>
            <p>Tid: ${formatTime(getTotalTime())}</p>
          </div>
        </div>
      `;
      
      answerDiv.style.display = 'none';
      showAnswerBtn.style.display = 'none';
      ratingSection.style.display = 'none';
      prevBtn.style.display = 'none';
      progressDiv.style.display = 'none';

      // Submit all responses to the backend
      submitAllResponses();
      return;
    }

    const [questionText, answerText] = questions[index].split('|');
    questionDiv.textContent = questionText.trim();
    answerDiv.textContent = (answerText || "[Answer not provided]").trim();
    
    answerDiv.style.display = 'none';
    showAnswerBtn.style.display = 'inline-block';
    ratingSection.style.display = 'none';

    prevBtn.style.display = (index > 0) ? 'inline-block' : 'none';

    updateProgress();
    startTime = Date.now();
  }

  function submitAllResponses() {
    if (responses.length === 0) {
      showCompletionMessage("No responses to submit.");
      return;
    }

    // Show loading state
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading-message';
    loadingDiv.innerHTML = '<p>💾 Saving your progress...</p>';
    questionDiv.appendChild(loadingDiv);

    fetch('/submit_ratings', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify({
        subject: subjectName,
        quiz_title: quizTitle,
        responses: responses
      })
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    })
    .then(data => {
      loadingDiv.remove();
      
      if (data.error) {
        showCompletionMessage(`❌ Error saving progress: ${data.error}`, 'error');
      } else {
        showCompletionMessage(
          `✅ Progress saved successfully! ${data.message || ''}`, 
          'success'
        );
        
        // Auto-redirect to dashboard after a delay
        setTimeout(() => {
          window.location.href = '/';
        }, 3000);
      }
    })
    .catch(error => {
      loadingDiv.remove();
      console.error('Error submitting responses:', error);
      showCompletionMessage(
        `❌ Network error: ${error.message}. Your progress was not saved.`, 
        'error'
      );
    });
  }

  function showCompletionMessage(message, type = 'info') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `completion-notification ${type}`;
    messageDiv.innerHTML = `
      <p>${message}</p>
      <div class="completion-actions">
        <button onclick="window.location.href='/'" class="button">
          Tillbaka till Huvudsidan
        </button>
        <button onclick="window.location.href='/subject/${encodeURIComponent(subjectName)}'" class="button">
          Tillbaka till Ämnet
        </button>
      </div>
    `;
    questionDiv.appendChild(messageDiv);
  }

  function getTotalTime() {
    return responses.reduce((total, response) => total + (response.time || 0), 0);
  }

  function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`;
    }
    return `${remainingSeconds}s`;
  }

  // Event Listeners
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
      // Remove the last response if going back
      if (responses.length > currentCardIndex) {
        responses.pop();
      }
      showCard(currentCardIndex);
    }
  });

  ratingButtons.forEach(button => {
    button.addEventListener('click', () => {
      const rating = parseInt(button.getAttribute('data-value'));
      const timeTaken = Math.round((Date.now() - startTime) / 1000);

      const [questionText] = questions[currentCardIndex].split('|');

      // Add visual feedback
      button.classList.add('selected');
      setTimeout(() => button.classList.remove('selected'), 200);

      // Store or update response for current card
      const response = {
        question: questionText.trim(),
        rating: rating,
        time: timeTaken
      };

      if (responses.length === currentCardIndex) {
        responses.push(response);
      } else {
        responses[currentCardIndex] = response;
      }

      // Move to next card
      currentCardIndex++;
      showCard(currentCardIndex);
    });
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', (event) => {
    // Only handle shortcuts if not typing in an input
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
      return;
    }

    switch(event.key) {
      case ' ': // Spacebar to show/hide answer
        event.preventDefault();
        if (showAnswerBtn.style.display !== 'none') {
          showAnswerBtn.click();
        } else if (backToQuestionBtn.offsetParent !== null) {
          backToQuestionBtn.click();
        }
        break;
      case '1':
      case '2':
      case '3':
      case '4':
        // Rate with number keys
        const ratingBtn = document.querySelector(`[data-value="${event.key}"]`);
        if (ratingBtn && ratingSection.style.display !== 'none') {
          event.preventDefault();
          ratingBtn.click();
        }
        break;
      case 'ArrowLeft':
        // Previous card
        if (prevBtn.style.display !== 'none') {
          event.preventDefault();
          prevBtn.click();
        }
        break;
      case 'Escape':
        // Return to dashboard
        window.location.href = '/';
        break;
    }
  });

  // Show keyboard shortcuts help
  const helpDiv = document.createElement('div');
  helpDiv.className = 'keyboard-help';
  helpDiv.innerHTML = `
    <div class="help-toggle" onclick="this.parentElement.classList.toggle('expanded')">
      ⌨️ Genvägar
    </div>
    <div class="help-content">
      <p><kbd>Space</kbd> - Visa/Göm Svar</p>
      <p><kbd>1-4</kbd> - Betygsätt Flashcard</p>
      <p><kbd>←</kbd> - Tidigare Kort</p>
      <p><kbd>Esc</kbd> - Tillbaka till Huvudsida</p>
    </div>
  `;
  document.body.appendChild(helpDiv);

  // Initialize - show first card
  if (questions && questions.length > 0) {
    showCard(currentCardIndex);
  } else {
    questionDiv.innerHTML = '<p>❌ Inga flashcards tillgängliga.</p>';
    showAnswerBtn.style.display = 'none';
    progressDiv.style.display = 'none';
  }

  // Auto-save progress on page unload (in case user closes window)
  window.addEventListener('beforeunload', (event) => {
    if (responses.length > 0) {
      // Use sendBeacon for reliable delivery on page unload
      if ('sendBeacon' in navigator) {
        const data = JSON.stringify({
          subject: subjectName,
          quiz_title: quizTitle,
          responses: responses
        });
        
        navigator.sendBeacon('/submit_ratings', new Blob([data], {
          type: 'application/json'
        }));
      }
    }
  });
});
