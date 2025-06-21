document.addEventListener('DOMContentLoaded', () => {
  // ----------- Part 0: Fetch the entire repetition schedule -----------
  let schedule = {};
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

    // Grupp‐logiken
    const grouped = {};
    entries.forEach(e => {
      const id = `${e.subject}|||${e.topic}`;
      if (!grouped[id]) {
        grouped[id] = { subject: e.subject, topic: e.topic, count: 0 };
      }
      grouped[id].count++;
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
        if (calendarModal.style.display === 'block') renderCalendar(currentDate);
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

  calendarCloseBtn?.addEventListener('click', () => calendarModal.style.display = 'none');
  addEventModalClose?.addEventListener('click', () => { 
    addEventModal.style.display = 'none'; 
    clearEventForm(); 
  });
  closeEventsDisplay?.addEventListener('click', () => eventsDisplay.style.display = 'none');

  saveEventBtn?.addEventListener('click', async () => {
    const subject = document.getElementById('subject-select').value;
    const testType = document.getElementById('test-type-select').value;
    const title = document.getElementById('event-title').value;
    const desc = document.getElementById('event-description').value;

    if (subject && testType && title && selectedDate) {
      const ev = {
        id: Date.now(),
        date: selectedDate.toISOString().split('T')[0],
        subject,
        testType,
        title,
        description: desc,
        created: new Date().toISOString()
      };
      await saveEvent(ev);
      alert(`Event "${title}" saved!`);
      addEventModal.style.display = 'none';
      clearEventForm();
    } else {
      alert('Please fill all fields');
    }
  });

  cancelEventBtn?.addEventListener('click', () => { 
    addEventModal.style.display = 'none'; 
    clearEventForm(); 
  });

  function clearEventForm() {
    ['subject-select','test-type-select','event-title','event-description'].forEach(id => {
      const element = document.getElementById(id);
      if (element) element.value = '';
    });
    selectedDate = null;
  }

  function getEventsForDate(d) {
    const ds = d.toISOString().split('T')[0];
    return calendarEvents.filter(e => e.date === ds);
  }

  function displayEventsForDate(d) {
    const evs = getEventsForDate(d);
    selectedDateTitle.textContent =
      `Events for ${d.toLocaleDateString('en-US',{ weekday:'long',year:'numeric',month:'long',day:'numeric'})}`;
    eventsList.innerHTML = evs.length
      ? evs.map(e => `
          <div class="event-item">
            <div class="event-header">
              <h4>${e.title}</h4><span>${e.testType}</span>
            </div>
            <div class="event-details">
              <p><strong>Subject:</strong> ${e.subject}</p>
              ${e.description?`<p><strong>Description:</strong> ${e.description}</p>`:''}
            </div>
            <button onclick="deleteEvent(${e.id})">Delete</button>
          </div>
        `).join('')
      : '<p class="no-events">No events scheduled for this date.</p>';
    eventsDisplay.style.display = 'block';
  }

  window.deleteEvent = async id => {
    if (!confirm('Delete this event?')) return;
    try {
      const resp = await fetch(`/api/events/${id}`, { method: 'DELETE' });
      if (!resp.ok) throw new Error('Failed to delete event');
      calendarEvents = calendarEvents.filter(e => e.id !== id);
      renderCalendar(currentDate);
      if (eventsDisplay.style.display === 'block' && selectedDate) {
        displayEventsForDate(selectedDate);
      }
      alert('Event deleted');
    } catch (error) {
      console.error('Error deleting event:', error);
      alert('Could not delete event');
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

        // Markera dagens datum
        if (d.toDateString() === new Date().toDateString()) {
          td.classList.add('today');
        }

        // Markera dagar som inte tillhör aktuell månad
        if (d.getMonth() !== date.getMonth()) {
          td.classList.add('other-month');
        }

        const dayDiv = document.createElement('div');
        dayDiv.className = 'day-container';

        const hdr = document.createElement('div');
        hdr.className = 'day-header';
        hdr.textContent = d.getDate();
        hdr.onclick = async () => {
          selectedDate = new Date(d);
          // Visa events för det valda datumet utan att stänga kalendern
          displayEventsForDate(d);
          // Ta INTE bort kalendern - låt den vara öppen
        };
        dayDiv.appendChild(hdr);

        // Event indicator
        const dayEvents = getEventsForDate(d);
        const scheduleKey = formatKey(d);
        const scheduledQuizzes = schedule[scheduleKey] || [];
        
        if (dayEvents.length > 0 || scheduledQuizzes.length > 0) {
          const indicator = document.createElement('div');
          indicator.className = 'event-indicator';
          
          if (dayEvents.length > 0) {
            indicator.classList.add('has-events');
            indicator.title = `${dayEvents.length} event(s)`;
          }
          
          if (scheduledQuizzes.length > 0) {
            indicator.classList.add('has-repetitions');
            indicator.title += (indicator.title ? ', ' : '') + `${scheduledQuizzes.length} repetition(s)`;
          }
          
          dayDiv.appendChild(indicator);
        }

        // Add event button
        const addBtn = document.createElement('div');
        addBtn.className = 'add-event-btn';
        addBtn.textContent = '+';
        addBtn.onclick = (e) => {
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

  window.addEventListener('click', event => {
    if (event.target === subjectModal) {
      subjectModal.style.display = 'none';
    }
  });

  subjectForm?.addEventListener('submit', () => {
    subjectModal.style.display = 'none';
  });

  // ----------- Quiz Completion Handling -----------
  // Global function to handle quiz completion data from flashcards.html
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
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(submitData)
    })
    .then(response => response.json())
    .then(data => {
      console.log('[DEBUG] Response:', data);
      if (data.status === 'success') {
        alert(`Quiz completed! Updated ${data.updated_count} questions.`);
        // Optionellt: visa vilka subject/topic som användes
        if (data.resolved_subject && data.resolved_topic) {
          console.log(`[DEBUG] Used subject: ${data.resolved_subject}, topic: ${data.resolved_topic}`);
        }
        
        // Uppdatera schemat efter quiz completion
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
    updateDateHeader();
    await loadQuizzesForDate();
    await loadEvents();
    console.log('[DEBUG] Application initialized successfully');
  })();
});
