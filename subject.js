document.addEventListener('DOMContentLoaded', () => {
  // Flashcard navigation
  document.querySelectorAll('.flashcard-trigger').forEach(elem => {
    elem.addEventListener('click', () => {
      const subject = elem.dataset.subject;
      const quizIndex = elem.dataset.quizIndex;
      if (subject && quizIndex !== undefined) {
        window.location.href = `/subject/${encodeURIComponent(subject)}/flashcards/${quizIndex}`;
      }
    });
  });

  // PDF.js worker
  pdfjsLib.GlobalWorkerOptions.workerSrc =
    'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

  const pdfUpload = document.getElementById('pdf-upload');
  const documentType = document.getElementById('document-type');
  const documentsContainer = document.getElementById('documents-container');

  // När användaren väljer PDF-filer
  pdfUpload.addEventListener('change', async (event) => {
    const files = Array.from(event.target.files);
    const type = documentType.value;

    for (const file of files) {
      if (file.type === 'application/pdf') {
        await uploadAndDisplayPDF(file, type);
      }
    }
    pdfUpload.value = '';
  });

  // Ladda upp filen (FormData) och lägg till iframe i DOM
  async function uploadAndDisplayPDF(file, type) {
    try {
      // Visa loading indikator
      showLoadingIndicator('Laddar upp dokument...');

      // Spara filen på servern
      const form = new FormData();
      form.append('subject', currentSubject);
      form.append('type', type);
      form.append('file', file);

      const res = await fetch('/upload_krav_pdf', {
        method: 'POST',
        body: form
      });
      
      const data = await res.json();
      
      if (data.status === 'success') {
        // Skapa elementet
        const item = document.createElement('div');
        item.className = 'document-item';
        item.dataset.docType = type;
        item.dataset.docId = data.document_id || ''; // SQL ID från backend

        // Ta bort-knapp
        const removeBtn = document.createElement('button');
        removeBtn.className = 'remove-document';
        removeBtn.dataset.docType = type;
        removeBtn.dataset.docId = data.document_id || '';
        removeBtn.textContent = '×';
        removeBtn.title = 'Ta bort dokument';
        item.appendChild(removeBtn);

        // Header med metadata
        const header = document.createElement('div');
        header.className = 'document-header';
        
        const title = document.createElement('span');
        title.className = 'document-title';
        title.textContent = getDocumentTypeDisplayName(type);
        header.appendChild(title);

        // Lägg till datum och filnamn om tillgängligt
        if (data.created_at) {
          const dateSpan = document.createElement('span');
          dateSpan.className = 'document-date';
          dateSpan.textContent = formatDate(data.created_at);
          header.appendChild(dateSpan);
        }

        if (data.filename) {
          const filenameSpan = document.createElement('span');
          filenameSpan.className = 'document-filename';
          filenameSpan.textContent = data.filename;
          header.appendChild(filenameSpan);
        }

        item.appendChild(header);

        // Preview via iframe
        const preview = document.createElement('div');
        preview.className = 'document-preview';
        const iframe = document.createElement('iframe');
        // Använd användarspecifik sökväg
        iframe.src = `/static/uploads/krav/${currentUserId}/${encodeURIComponent(currentSubject)}/${encodeURIComponent(type)}.pdf`;
        iframe.width = '100%';
        iframe.height = '300px';
        iframe.style.border = '1px solid #ccc';
        iframe.style.borderRadius = '4px';
        preview.appendChild(iframe);
        item.appendChild(preview);

        // Ta bort befintligt dokument av samma typ
        const existingDoc = documentsContainer.querySelector(`[data-doc-type="${type}"]`);
        if (existingDoc) {
          existingDoc.remove();
        }

        documentsContainer.appendChild(item);
        
        showSuccessMessage(`${getDocumentTypeDisplayName(type)} har laddats upp!`);
        
      } else {
        showErrorMessage('Kunde inte ladda upp dokument: ' + (data.message || 'Okänt fel'));
      }
    } catch (err) {
      console.error('Upload error:', err);
      showErrorMessage('Fel vid uppladdning av PDF: ' + err.message);
    } finally {
      hideLoadingIndicator();
    }
  }

  // Ta bort dokument med SQL-baserad hantering
  document.addEventListener('click', async (e) => {
    if (!e.target.classList.contains('remove-document')) return;
    
    const type = e.target.dataset.docType;
    const docId = e.target.dataset.docId;
    
    if (!confirm(`Vill du verkligen ta bort ${getDocumentTypeDisplayName(type).toLowerCase()}?`)) {
      return;
    }

    try {
      showLoadingIndicator('Tar bort dokument...');

      const payload = {
        subject: currentSubject,
        doc_type: type
      };

      // Lägg till document ID om tillgängligt för mer specifik borttagning
      if (docId) {
        payload.doc_id = docId;
      }

      const res = await fetch('/delete_krav_document', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      const data = await res.json();
      
      if (data.status === 'success') {
        const el = e.target.closest('.document-item');
        if (el) {
          // Animerad borttagning
          el.style.transition = 'opacity 0.3s ease-out';
          el.style.opacity = '0';
          setTimeout(() => el.remove(), 300);
        }
        showSuccessMessage(`${getDocumentTypeDisplayName(type)} har tagits bort!`);
      } else {
        showErrorMessage('Kunde inte ta bort dokument: ' + (data.message || 'Okänt fel'));
      }
    } catch (err) {
      console.error('Deletion error:', err);
      showErrorMessage('Fel vid borttagning: ' + err.message);
    } finally {
      hideLoadingIndicator();
    }
  });

  // Ladda befintliga dokument från SQL-databas
  async function loadExistingDocuments() {
    try {
      const res = await fetch(`/api/krav_documents/${encodeURIComponent(currentSubject)}`);
      if (!res.ok) {
        console.warn('Could not load existing documents');
        return;
      }
      
      const documents = await res.json();
      
      // Rendera befintliga dokument
      Object.entries(documents).forEach(([docType, docData]) => {
        displayExistingDocument(docType, docData);
      });
      
    } catch (err) {
      console.error('Error loading existing documents:', err);
    }
  }

  // Visa befintligt dokument
  function displayExistingDocument(type, docData) {
    const item = document.createElement('div');
    item.className = 'document-item existing-document';
    item.dataset.docType = type;
    item.dataset.docId = docData.id || '';

    // Ta bort-knapp
    const removeBtn = document.createElement('button');
    removeBtn.className = 'remove-document';
    removeBtn.dataset.docType = type;
    removeBtn.dataset.docId = docData.id || '';
    removeBtn.textContent = '×';
    removeBtn.title = 'Ta bort dokument';
    item.appendChild(removeBtn);

    // Header
    const header = document.createElement('div');
    header.className = 'document-header';
    
    const title = document.createElement('span');
    title.className = 'document-title';
    title.textContent = getDocumentTypeDisplayName(type);
    header.appendChild(title);

    // Metadata
    if (docData.created_at) {
      const dateSpan = document.createElement('span');
      dateSpan.className = 'document-date';
      dateSpan.textContent = formatDate(docData.created_at);
      header.appendChild(dateSpan);
    }

    item.appendChild(header);

    // Preview
    const preview = document.createElement('div');
    preview.className = 'document-preview';
    const iframe = document.createElement('iframe');
    iframe.src = `/static/uploads/krav/${currentUserId}/${encodeURIComponent(currentSubject)}/${encodeURIComponent(type)}.pdf`;
    iframe.width = '100%';
    iframe.height = '300px';
    iframe.style.border = '1px solid #ccc';
    iframe.style.borderRadius = '4px';
    
    // Hantera fel vid iframe-laddning
    iframe.onerror = () => {
      preview.innerHTML = '<p style="text-align: center; padding: 20px; color: #666;">Förhandsvisning ej tillgänglig</p>';
    };
    
    preview.appendChild(iframe);
    item.appendChild(preview);

    documentsContainer.appendChild(item);
  }

  // Hjälpfunktioner
  function getDocumentTypeDisplayName(type) {
    const displayNames = {
      'begrippslista': 'Begrippslista',
      'kunskapskrav': 'Kunskapskrav',
      'kunskapsmal': 'Kunskapsmål',
      'kursmål': 'Kursmål',
      'betygskriterier': 'Betygskriterier'
    };
    return displayNames[type] || type.charAt(0).toUpperCase() + type.slice(1);
  }

  function formatDate(dateString) {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('sv-SE', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch (err) {
      return dateString;
    }
  }

  function showLoadingIndicator(message = 'Laddar...') {
    // Ta bort befintlig indikator
    hideLoadingIndicator();
    
    const indicator = document.createElement('div');
    indicator.id = 'loading-indicator';
    indicator.innerHTML = `
      <div style="
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: rgba(0,0,0,0.8);
        color: white;
        padding: 20px;
        border-radius: 8px;
        z-index: 1000;
        text-align: center;
      ">
        <div style="margin-bottom: 10px;">
          <div style="
            border: 3px solid #f3f3f3;
            border-top: 3px solid #007bff;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
          "></div>
        </div>
        ${message}
      </div>
      <style>
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      </style>
    `;
    document.body.appendChild(indicator);
  }

  function hideLoadingIndicator() {
    const indicator = document.getElementById('loading-indicator');
    if (indicator) {
      indicator.remove();
    }
  }

  function showSuccessMessage(message) {
    showMessage(message, 'success');
  }

  function showErrorMessage(message) {
    showMessage(message, 'error');
  }

  function showMessage(message, type = 'info') {
    const messageEl = document.createElement('div');
    messageEl.className = `flash-message flash-${type}`;
    messageEl.textContent = message;
    messageEl.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      padding: 15px 20px;
      background: ${type === 'success' ? '#d4edda' : type === 'error' ? '#f8d7da' : '#d1ecf1'};
      color: ${type === 'success' ? '#155724' : type === 'error' ? '#721c24' : '#0c5460'};
      border: 1px solid ${type === 'success' ? '#c3e6cb' : type === 'error' ? '#f5c6cb' : '#bee5eb'};
      border-radius: 4px;
      z-index: 1001;
      box-shadow: 0 2px 5px rgba(0,0,0,0.2);
      transition: opacity 0.3s ease-out;
    `;

    document.body.appendChild(messageEl);

    // Auto-remove efter 3 sekunder
    setTimeout(() => {
      messageEl.style.opacity = '0';
      setTimeout(() => messageEl.remove(), 300);
    }, 3000);
  }

  // Quiz-hantering med SQL-baserad data
  function initializeQuizHandling() {
    // Ladda quiz-data från SQL via backend API
    loadQuizzesFromSQL();
    
    // Hantera quiz-borttagning
    document.addEventListener('click', async (e) => {
      if (e.target.classList.contains('delete-quiz-btn')) {
        const quizId = e.target.dataset.quizId;
        const quizTitle = e.target.dataset.quizTitle;
        
        if (!confirm(`Vill du verkligen ta bort quiz "${quizTitle}"?`)) {
          return;
        }
        
        try {
          const res = await fetch(`/api/quiz/${quizId}`, {
            method: 'DELETE'
          });
          
          const data = await res.json();
          
          if (data.status === 'success') {
            e.target.closest('.quiz-item').remove();
            showSuccessMessage('Quiz har tagits bort!');
          } else {
            showErrorMessage('Kunde inte ta bort quiz: ' + (data.message || 'Okänt fel'));
          }
        } catch (err) {
          console.error('Error deleting quiz:', err);
          showErrorMessage('Fel vid borttagning av quiz');
        }
      }
    });
  }

  async function loadQuizzesFromSQL() {
    try {
      const res = await fetch(`/api/quizzes/${encodeURIComponent(currentSubject)}`);
      if (!res.ok) return;
      
      const quizzes = await res.json();
      updateQuizDisplay(quizzes);
    } catch (err) {
      console.error('Error loading quizzes:', err);
    }
  }

  function updateQuizDisplay(quizzes) {
    const quizContainer = document.getElementById('quiz-container');
    if (!quizContainer) return;
    
    // Uppdatera quiz-visning baserat på SQL-data
    // Detta beror på din HTML-struktur för quiz-visning
    quizzes.forEach((quiz, index) => {
      const quizElement = quizContainer.querySelector(`[data-quiz-index="${index}"]`);
      if (quizElement) {
        // Uppdatera med SQL ID och annan metadata
        quizElement.dataset.quizId = quiz.id;
        quizElement.dataset.quizTitle = quiz.title;
      }
    });
  }

  // Initiera allt när sidan laddas
  if (typeof currentSubject !== 'undefined') {
    loadExistingDocuments();
    initializeQuizHandling();
  }
});

// Global funktion för att uppdatera quiz-data från SQL
window.refreshQuizData = async function() {
  if (typeof currentSubject !== 'undefined') {
    const res = await fetch(`/api/quizzes/${encodeURIComponent(currentSubject)}`);
    if (res.ok) {
      const quizzes = await res.json();
      window.dispatchEvent(new CustomEvent('quizDataUpdated', { detail: quizzes }));
    }
  }
};
