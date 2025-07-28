
//index_script.js:


document.addEventListener('DOMContentLoaded', () => {
  // ----------- Part 0: Fetch the entire repetition schedule -----------
  let schedule = {};
  let userSubjects = {};

  async function fetchSchedule() {
    try {
      const res = await fetch('/flashcards_by_date');
      if (!res.ok) throw new Error(res.statusText);
      schedule = await res.json();
      console.log('[DEBUG] Fetched schedule:', schedule);
    } catch (e) {
      console.error('Could not load repetition schedule:', e);
    }
  }

  async function loadUserSubjects() {
    try {
      const response = await fetch('/api/user_subjects');
      if (response.ok) {
        const data = await response.json();
        userSubjects = data.reduce((acc, subject) => {
          acc[subject.id] = subject.user_role; // 'owner' eller 'member'
          return acc;
        }, {});
        console.log('[DEBUG] User subjects loaded:', userSubjects);
      }
    } catch (error) {
      console.error('Error loading user subjects:', error);
    }
  }

  // ----------- Part 1: Date selector + quiz loading per date -----------
  let currentDate = new Date();

  function formatKey(d) {
    return d.toISOString().split('T')[0];
  }

  function updateDateHeader() {
    const opts = { year: 'numeric', month: 'long', day: 'numeric' };
    document.getElementById('current-date').textContent =
      currentDate.toLocaleDateString(undefined, opts);
  }

  async function loadQuizzesForDate() {
    // 1) Hämta alltid senaste schemat
    await fetchSchedule();

    const key = formatKey(currentDate);
    const entries = schedule[key] || [];
    const container = document.getElementById('quizzes-container');
    container.innerHTML = ''; // Rensa ut

    console.log(`[DEBUG] Loading quizzes for date: ${key}, found ${entries.length} entries`);

    if (entries.length === 0) {
      container.innerHTML = '<p>No repetitions scheduled for this date.</p>';
      return;
    }

    // Förbättrad grupp-logik som räknar faktiska frågor
    const grouped = {};
    entries.forEach(e => {
      const id = `${e.subject}|||${e.topic}`;
      if (!grouped[id]) {
        grouped[id] = { 
          subject: e.subject, 
          topic: e.topic, 
          count: 0,
          questions: [] // Lägg till array för att hålla koll på alla frågor
        };
      }
      
      // Om det finns questions-array i entry, räkna dem
      if (e.questions && Array.isArray(e.questions)) {
        grouped[id].count += e.questions.length;
        grouped[id].questions.push(...e.questions);
      } else {
        // Fallback för äldre format
        grouped[id].count++;
      }
    });

    console.log('[DEBUG] Grouped quizzes:', grouped);

    Object.values(grouped).forEach(qz => {
      const link = `/daily_quiz/${key}/` +
                   encodeURIComponent(qz.subject) + '/' +
                   encodeURIComponent(qz.topic);
      const card = document.createElement('div');
      card.className = 'quiz-card';
      card.innerHTML = `
        <h3>${qz.subject} – ${qz.topic}</h3>
        <p>${qz.count} question${qz.count > 1 ? 's' : ''}</p>
        <a href="${link}"><button>Start Quiz</button></a>
      `;
      container.appendChild(card);
    });
  }

  // Datum‐knapparna
  document.getElementById('prev-day-btn').addEventListener('click', async () => {
    currentDate.setDate(currentDate.getDate() - 1);
    updateDateHeader();
    await loadQuizzesForDate();
  });

  document.getElementById('next-day-btn').addEventListener('click', async () => {
    currentDate.setDate(currentDate.getDate() + 1);
    updateDateHeader();
    await loadQuizzesForDate();
  });

  // ----------- Part 2: Calendar modal and event handling -----------
  const calendarBtn = document.getElementById('btn-2');
  const calendarModal = document.getElementById('calendar-modal');
  const calendarCloseBtn = calendarModal?.querySelector('.calendar-close');
  const monthYearSpan = document.getElementById('month-year');
  const prevMonthBtn = document.getElementById('prev-month-btn');
  const nextMonthBtn = document.getElementById('next-month-btn');
  const calendarBody = document.getElementById('calendar-body');

  const addEventModal = document.getElementById('add-event-modal');
  const addEventModalClose = document.getElementById('add-event-modal-close');
  const saveEventBtn = document.getElementById('save-event-btn');
  const cancelEventBtn = document.getElementById('cancel-event-btn');

  const eventsDisplay = document.getElementById('events-display');
  const selectedDateTitle = document.getElementById('selected-date-title');
  const eventsList = document.getElementById('events-list');
  const closeEventsDisplay = document.getElementById('close-events-display');

  let selectedDate = null;
  let calendarEvents = [];

  async function loadEvents() {
    try {
      const resp = await fetch('/api/events');
      if (resp.ok) {
        calendarEvents = await resp.json();
        if (calendarModal.style.display === 'block') {
          renderCalendar(currentDate);
        }
      }
    } catch (err) {
      console.error('Error loading events:', err);
    }
  }

  async function saveEvent(eventData) {
    try {
      const resp = await fetch('/api/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(eventData)
      });
      if (!resp.ok) throw new Error('Failed to save event');
      calendarEvents.push(eventData);
      renderCalendar(currentDate);
    } catch (error) {
      console.error('Error saving event:', error);
      alert('Error saving event.');
    }
  }

  calendarBtn?.addEventListener('click', () => {
    calendarModal.style.display = 'block';
    renderCalendar(new Date());
  });

  calendarCloseBtn?.addEventListener('click', () => {
    calendarModal.style.display = 'none';
  });

  addEventModalClose?.addEventListener('click', () => { 
    addEventModal.style.display = 'none'; 
    clearEventForm(); 
  });

  closeEventsDisplay?.addEventListener('click', () => {
    eventsDisplay.style.display = 'none';
  });

  saveEventBtn?.addEventListener('click', async () => {
    const subject = document.getElementById('subject-select').value;
    const testType = document.getElementById('test-type-select').value;
    const title = document.getElementById('event-title').value;
    const desc = document.getElementById('event-description').value;
    const shareWithMembers = document.getElementById('share-with-members')?.checked || false;

    if (subject && testType && title && selectedDate) {
      const eventData = {
        date: formatKey(selectedDate),
        subject: subject,
        testType: testType,
        title: title,
        description: desc,
        share_with_members: shareWithMembers
      };
      try {
        const response = await fetch('/api/events', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(eventData)
        });
        const data = await response.json();
        if (response.ok && data.status === 'success') {
          alert(data.message);
          await loadEvents();
          renderCalendar(currentDate);
          addEventModal.style.display = 'none';
          clearEventForm();
        } else {
          alert(data.error || 'Failed to create event');
        }
      } catch (error) {
        console.error('Error creating event:', error);
        alert('Network error occurred while creating event');
      }
    } else {
      alert('Please fill all required fields');
    }
  });

  cancelEventBtn?.addEventListener('click', () => { 
    addEventModal.style.display = 'none'; 
    clearEventForm(); 
  });

  function clearEventForm() {
    ['subject-select','test-type-select','event-title','event-description'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    const shareCheckbox = document.getElementById('share-with-members');
    if (shareCheckbox) shareCheckbox.checked = false;
    selectedDate = null;
  }

  function getEventsForDate(d) {
    const ds = formatKey(d);
    return calendarEvents.filter(e => e.date === ds);
  }

  function displayEventsForDate(d) {
    const evs = getEventsForDate(d);
    selectedDateTitle.textContent =
      `Events for ${d.toLocaleDateString('en-US',{ weekday:'long', year:'numeric', month:'long', day:'numeric'})}`;
    
    if (evs.length === 0) {
      eventsList.innerHTML = '<p class="no-events">No events scheduled for this date.</p>';
    } else {
      eventsList.innerHTML = evs.map(e => `
        <div class="event-item ${e.is_shared ? 'shared-event' : 'private-event'}">
          <div class="event-header">
            <h4>${e.title}</h4>
            <div class="event-badges">
              <span class="test-type-badge">${e.testType}</span>
              ${e.is_shared ? '<span class="shared-badge">Shared</span>' : ''}
            </div>
          </div>
          <div class="event-details">
            <p><strong>Subject:</strong> ${e.subject}</p>
            ${e.description ? `<p><strong>Description:</strong> ${e.description}</p>` : ''}
          </div>
          <div class="event-actions">
            ${canDeleteEvent(e) ? `<button onclick="deleteEvent(${e.id})" class="delete-btn">Delete</button>` : ''}
            ${canToggleSharing(e) ? `<button onclick="toggleEventSharing(${e.id}, ${e.is_shared})" class="share-btn">${e.is_shared ? 'Make Private' : 'Share with Members'}</button>` : ''}
          </div>
        </div>
      `).join('');
    }
    eventsDisplay.style.display = 'block';
  }

  window.toggleEventSharing = async function(eventId, isCurrentlyShared) {
    try {
      const response = await fetch(`/api/events/${eventId}/share`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await response.json();
      if (response.ok && data.status === 'success') {
        alert(data.message);
        await loadEvents();
        renderCalendar(currentDate);
        if (eventsDisplay.style.display === 'block' && selectedDate) {
          displayEventsForDate(selectedDate);
        }
      } else {
        alert(data.error || 'Failed to update sharing settings');
      }
    } catch (error) {
      console.error('Error toggling event sharing:', error);
      alert('Network error occurred while updating sharing settings');
    }
  };

  function canDeleteEvent(event) {
    if (!event.subject_id) {
      return true;
    }
    const userRole = userSubjects[event.subject_id];
    return userRole === 'owner';
  }

  function canToggleSharing(event) {
    if (!event.subject_id) {
      return true;
    }
    const userRole = userSubjects[event.subject_id];
    return userRole === 'owner';
  }

  window.deleteEvent = async function(id) {
    if (!confirm('Delete this event?')) return;
    try {
      const response = await fetch(`/api/events/${id}`, { 
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await response.json();
      if (response.ok && data.status === 'success') {
        alert(data.message);
        await loadEvents();
        renderCalendar(currentDate);
        if (eventsDisplay.style.display === 'block' && selectedDate) {
          displayEventsForDate(selectedDate);
        }
      } else {
        alert(data.error || 'Failed to delete event');
      }
    } catch (error) {
      console.error('Error deleting event:', error);
      alert('Network error occurred while deleting event');
    }
  };

  window.addEventListener('click', e => {
    if (e.target === calendarModal) {
      calendarModal.style.display = 'none';
    }
    if (addEventModal && addEventModal.style.display === 'block' && !e.target.closest('#add-event-modal')) {
      addEventModal.style.display = 'none';
      clearEventForm();
    }
    if (e.target === subjectModal) {
      subjectModal.style.display = 'none';
    }
  });

  prevMonthBtn?.addEventListener('click', () => {
    const newDate = new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1);
    renderCalendar(newDate);
  });

  nextMonthBtn?.addEventListener('click', () => {
    const newDate = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1);
    renderCalendar(newDate);
  });

  window.renderCalendar = date => {
    monthYearSpan.textContent = `${date.toLocaleString('default',{month:'long'})} ${date.getFullYear()}`;
    calendarBody.innerHTML = '';

    let start = new Date(date.getFullYear(), date.getMonth(), 1);
    start.setDate(start.getDate() - start.getDay());

    for (let r = 0; r < 6; r++) {
      const tr = document.createElement('tr');
      for (let c = 0; c < 7; c++) {
        const td = document.createElement('td');
        td.className = 'calendar-cell';

        const d = new Date(start);
        d.setDate(start.getDate() + (r * 7 + c));

        if (d.toDateString() === new Date().toDateString()) {
          td.classList.add('today');
        }
        if (d.getMonth() !== date.getMonth()) {
          td.classList.add('other-month');
        }

        const dayDiv = document.createElement('div');
        dayDiv.className = 'day-container';

        const hdr = document.createElement('div');
        hdr.className = 'day-header';
        hdr.textContent = d.getDate();
        hdr.onclick = () => {
          selectedDate = new Date(d);
          displayEventsForDate(d);
        };
        dayDiv.appendChild(hdr);

        const dayEvents = getEventsForDate(d);
        const scheduledQuizzes = schedule[formatKey(d)] || [];

        if (dayEvents.length > 0 || scheduledQuizzes.length > 0) {
          const indicator = document.createElement('div');
          indicator.className = 'event-indicator';

          const ownEvents = dayEvents.filter(e => !e.is_shared);
          const sharedEvents = dayEvents.filter(e => e.is_shared);

          if (ownEvents.length > 0) {
            indicator.classList.add('has-events');
          }
          if (sharedEvents.length > 0) {
            indicator.classList.add('has-shared-events');
          }
          if (scheduledQuizzes.length > 0) {
            indicator.classList.add('has-repetitions');
          }

          let tooltipText = '';
          if (ownEvents.length > 0) {
            tooltipText += `${ownEvents.length} event(s)`;
          }
          if (sharedEvents.length > 0) {
            tooltipText += (tooltipText ? ', ' : '') + `${sharedEvents.length} shared event(s)`;
          }
          if (scheduledQuizzes.length > 0) {
            tooltipText += (tooltipText ? ', ' : '') + `${scheduledQuizzes.length} repetition(s)`;
          }

          indicator.title = tooltipText;
          dayDiv.appendChild(indicator);
        }

        const addBtn = document.createElement('div');
        addBtn.className = 'add-event-btn';
        addBtn.textContent = '+';
        addBtn.onclick = e => {
          e.stopPropagation();
          selectedDate = new Date(d);
          addEventModal.style.display = 'block';
        };
        dayDiv.appendChild(addBtn);

        td.appendChild(dayDiv);
        tr.appendChild(td);
      }
      calendarBody.appendChild(tr);
    }
  };

  // ----------- Subject Modal Logic -----------
  const subjectModal = document.getElementById('subject-modal');
  const subjectBtn = document.getElementById('left-subject-btn');
  const subjectClose = subjectModal?.querySelector('.close');
  const subjectForm = document.getElementById('create-subject-form');

  subjectBtn?.addEventListener('click', () => {
    subjectModal.style.display = 'block';
  });

  subjectClose?.addEventListener('click', () => {
    subjectModal.style.display = 'none';
  });

  subjectForm?.addEventListener('submit', e => {
    e.preventDefault();
    subjectModal.style.display = 'none';
  });

  // ----------- Quiz Completion Handling -----------
  window.handleQuizCompletion = function(subject, quizTitle, responses) {
    console.log('[DEBUG] Quiz completion data received:', { subject, quizTitle, responses });

    const submitData = {
      subject: subject,
      quiz_title: quizTitle,
      responses: responses
    };

    console.log('[DEBUG] Submitting data:', submitData);

    return fetch('/submit_ratings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(submitData)
    })
    .then(response => response.json())
    .then(data => {
      console.log('[DEBUG] Response:', data);
      if (data.status === 'success') {
        alert(`Quiz completed! Updated ${data.updated_count} questions.`);
        if (data.resolved_subject && data.resolved_topic) {
          console.log(`[DEBUG] Used subject: ${data.resolved_subject}, topic: ${data.resolved_topic}`);
        }
        fetchSchedule().then(() => {
          loadQuizzesForDate();
        });
        return data;
      } else {
        alert('Error: ' + (data.error || 'Unknown error'));
        throw new Error(data.error || 'Unknown error');
      }
    })
    .catch(error => {
      console.error('Error:', error);
      alert('Network error occurred');
      throw error;
    });
  };

  // ----------- Init everything asynchronously -----------
  (async () => {
    console.log('[DEBUG] Initializing application...');
    await fetchSchedule();
    await loadUserSubjects();
    updateDateHeader();
    await loadQuizzesForDate();
    await loadEvents();
    console.log('[DEBUG] Application initialized successfully');
  })();
}); // End of DOMContentLoaded

// Exempel på hur JavaScript bör hantera add_subject response
function addSubject() {
  const subjectName = document.getElementById('subject-name').value.trim();
  const isShared = document.getElementById('is-shared').checked;

  if (!subjectName) {
    alert('Please enter a subject name');
    return;
  }

  fetch('/add_subject', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: subjectName, is_shared: isShared })
  })
    .then(response => response.json())
    .then(data => {
      if (data.status === 'success') {
        addSubjectToDOM(data.subject);
        document.getElementById('subject-name').value = '';
        document.getElementById('is-shared').checked = false;
        showMessage(data.message, 'success');
      } else {
        showMessage(data.message, 'error');
      }
    })
    .catch(error => {
      console.error('Error:', error);
      showMessage('Failed to create subject', 'error');
    });
}

function addSubjectToDOM(subject) {
  const ownedSubjectsContainer = document.getElementById('owned-subjects');
  const subjectHTML = `
    <div class="subject-card" data-subject-id="${subject.id}">
      <h3><a href="/subject/${subject.name}">${subject.name}</a></h3>
      <div class="subject-stats">
        <p>Quizzes: ${subject.quiz_count}</p>
        <p>Flashcards: ${subject.flashcard_count}</p>
        <p>Due: ${subject.due_flashcards}</p>
        <p>Role: ${subject.user_role}</p>
      </div>
      ${subject.is_shared ? `<p class="share-code">Share Code: ${subject.share_code}</p>` : ''}
    </div>
  `;
  ownedSubjectsContainer.insertAdjacentHTML('beforeend', subjectHTML);
}
