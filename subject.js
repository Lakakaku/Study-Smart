document.addEventListener('DOMContentLoaded', () => {
  // PDF.js worker setup (prioriterad från andra dokumentet)
  if (typeof pdfjsLib !== 'undefined') {
    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
  }

  // Initiera gemensam filuppladdning (endast ägare)
  initializeSharedFiles();

  // Initiera hantering av krav-dokument
  initializeDocumentHandling();

  // Ladda initiala data
  loadSharedFiles();
  if (userRole === 'owner') {
    loadMemberCount();
    loadFileStats();
  }

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

  // Quiz-hantering
  if (typeof currentSubject !== 'undefined') {
    loadExistingDocuments();
    initializeQuizHandling();
  }
});

// ----------- DOCUMENT HANDLING FUNKTIONER -----------
function initializeDocumentHandling() {
  if (userRole !== 'owner' && userRole !== 'admin') return;

  const pdfUpload = document.getElementById('pdf-upload');
  const documentTypeSelect = document.getElementById('document-type');
  const documentsContainer = document.getElementById('documents-container');

  if (!pdfUpload || !documentTypeSelect || !documentsContainer) {
    console.log('Document handling elements not found');
    return;
  }

  // Sätt upp event listener för filuppladdning
  pdfUpload.addEventListener('change', async (e) => {
    const files = e.target.files;
    if (files.length > 0) {
      const file = files[0];
      const docType = documentTypeSelect.value;
      
      // Validera filtyp
      if (!file.type.includes('pdf')) {
        showNotification('Endast PDF-filer är tillåtna', 'error');
        return;
      }

      // Ladda upp och visa PDF
      await uploadAndDisplayPDF(file, docType);
      
      // Återställ input
      pdfUpload.value = '';
    }
  });

  // Hantera borttagning av dokument
  documentsContainer.addEventListener('click', async (e) => {
    if (e.target.classList.contains('remove-document')) {
      const docType = e.target.dataset.docType;
      const docId = e.target.dataset.docId;
      
      if (confirm('Är du säker på att du vill ta bort detta dokument?')) {
        await removeDocument(docType, docId);
      }
    }
  });
}

async function uploadAndDisplayPDF(file, type) {
  try {
    // Visa loading indikator
    showLoadingIndicator('Laddar upp dokument...');

    // Spara filen på servern
    const formData = new FormData();
    formData.append('subject', currentSubject);
    formData.append('type', type);
    formData.append('file', file);

    const response = await fetch('/upload_krav_pdf', {
      method: 'POST',
      body: formData
    });
    
    const data = await response.json();
    
    if (data.status === 'success') {
      // Skapa elementet
      const documentsContainer = document.getElementById('documents-container');
      const item = document.createElement('div');
      item.className = 'document-item';
      item.dataset.docType = type;
      item.dataset.docId = data.document_id || '';

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
      // Använd backend-returnerad URL eller konstruera den
      iframe.src = data.file_url || `/static/uploads/krav/${currentUserId}/${encodeURIComponent(currentSubject)}/${encodeURIComponent(type)}.pdf`;
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
      
      showNotification(`${getDocumentTypeDisplayName(type)} har laddats upp!`, 'success');
      
    } else {
      showNotification('Kunde inte ladda upp dokument: ' + (data.message || 'Okänt fel'), 'error');
    }
  } catch (err) {
    console.error('Upload error:', err);
    showNotification('Fel vid uppladdning av PDF: ' + err.message, 'error');
  } finally {
    hideLoadingIndicator();
  }
}

async function removeDocument(docType, docId) {
  try {
    showLoadingIndicator('Tar bort dokument...');
    
    const response = await fetch('/remove_krav_pdf', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        subject: currentSubject,
        type: docType,
        document_id: docId
      })
    });
    
    const data = await response.json();
    
    if (data.status === 'success') {
      // Ta bort elementet från DOM
      const docElement = document.querySelector(`[data-doc-type="${docType}"][data-doc-id="${docId}"]`);
      if (docElement) {
        docElement.remove();
      }
      
      showNotification('Dokument borttaget', 'success');
    } else {
      showNotification('Kunde inte ta bort dokument: ' + (data.message || 'Okänt fel'), 'error');
    }
  } catch (err) {
    console.error('Remove error:', err);
    showNotification('Fel vid borttagning av dokument: ' + err.message, 'error');
  } finally {
    hideLoadingIndicator();
  }
}

function loadExistingDocuments() {
  // Ladda befintliga dokument från servern
  fetch(`/api/krav_documents/${encodeURIComponent(currentSubject)}`)
    .then(response => response.json())
    .then(data => {
      if (data.status === 'success') {
        displayExistingDocuments(data.documents);
      }
    })
    .catch(err => {
      console.error('Error loading existing documents:', err);
    });
}

function displayExistingDocuments(documents) {
  const documentsContainer = document.getElementById('documents-container');
  if (!documentsContainer) return;

  // Rensa befintligt innehåll
  documentsContainer.innerHTML = '';

  if (documents.length === 0) {
    documentsContainer.innerHTML = '<p>Inga dokument uppladdade än.</p>';
    return;
  }

  documents.forEach(doc => {
    const item = document.createElement('div');
    item.className = 'document-item';
    item.dataset.docType = doc.doc_type;
    item.dataset.docId = doc.id;

    item.innerHTML = `
      <button class="remove-document" data-doc-type="${doc.doc_type}" data-doc-id="${doc.id}">×</button>
      <div class="document-header">
        <span class="document-title">${getDocumentTypeDisplayName(doc.doc_type)}</span>
        <span class="document-date">${formatDate(doc.created_at)}</span>
        <span class="document-filename">${doc.filename}</span>
      </div>
      <div class="document-preview">
        <iframe src="${doc.file_url}" width="100%" height="300px" style="border:1px solid #ccc; border-radius: 4px;"></iframe>
      </div>
    `;

    documentsContainer.appendChild(item);
  });
}

function getDocumentTypeDisplayName(type) {
  const displayNames = {
    'begrippslista': 'Begrippslista',
    'kunskapskrav': 'Kunskapskrav',
    'kunskapsmal': 'Kunskapsmål'
  };
  return displayNames[type] || type;
}

function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleDateString('sv-SE');
}

function initializeQuizHandling() {
  // Implementera quiz-hantering om behövs
  console.log('Quiz handling initialized');
}

function showLoadingIndicator(message) {
  let indicator = document.getElementById('loading-indicator');
  if (!indicator) {
    indicator = document.createElement('div');
    indicator.id = 'loading-indicator';
    indicator.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: rgba(0, 0, 0, 0.8);
      color: white;
      padding: 20px;
      border-radius: 8px;
      z-index: 1000;
      font-size: 16px;
    `;
    document.body.appendChild(indicator);
  }
  indicator.textContent = message;
  indicator.style.display = 'block';
}

function hideLoadingIndicator() {
  const indicator = document.getElementById('loading-indicator');
  if (indicator) {
    indicator.style.display = 'none';
  }
}

// ----------- SHARED FILES FUNKTIONER -----------
function initializeSharedFiles() {
  if (userRole !== 'owner') return;

  const fileInput = document.getElementById('file-upload-input');
  const uploadArea = document.getElementById('file-upload-area');
  const progressBar = document.getElementById('progress-bar');
  const progressDiv = document.getElementById('upload-progress');

  if (!fileInput || !uploadArea) return;

  uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
  });

  uploadArea.addEventListener('dragleave', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
  });

  uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFileUpload(files[0]);
  });

  uploadArea.addEventListener('click', () => {
    fileInput.click();
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) handleFileUpload(e.target.files[0]);
  });

  const uploadForm = document.getElementById('file-upload-form');
  if (uploadForm) {
    uploadForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const formData = new FormData(uploadForm);
      uploadFile(formData);
    });
  }
}

function handleFileUpload(file) {
  const maxSize = 50 * 1024 * 1024;
  if (file.size > maxSize) {
    showNotification('Filen är för stor. Maximal storlek är 50MB.', 'error');
    return;
  }

  const allowedExtensions = [
    'pdf', 'doc', 'docx', 'txt', 'rtf',
    'jpg', 'jpeg', 'png', 'gif', 'bmp',
    'mp4', 'avi', 'mov', 'wmv', 'flv',
    'mp3', 'wav', 'ogg', 'flac',
    'zip', 'rar', '7z', 'tar', 'gz'
  ];

  const fileExtension = file.name.split('.').pop().toLowerCase();
  if (!allowedExtensions.includes(fileExtension)) {
    showNotification('Filtyp inte tillåten. Kontrollera tillåtna filtyper.', 'error');
    return;
  }

  const formData = new FormData();
  formData.append('file', file);
  formData.append('subject', currentSubject);
  formData.append('description', document.getElementById('file-description')?.value || '');

  uploadFile(formData);
}

function uploadFile(formData) {
  const progressDiv = document.getElementById('upload-progress');
  const progressBar = document.getElementById('progress-bar');
  const uploadButton = document.getElementById('upload-button');

  if (progressDiv) progressDiv.style.display = 'block';
  if (progressBar) progressBar.style.width = '0%';
  if (uploadButton) {
    uploadButton.disabled = true;
    uploadButton.textContent = 'Laddar upp...';
  }

  const xhr = new XMLHttpRequest();

  xhr.upload.addEventListener('progress', (e) => {
    if (e.lengthComputable && progressBar) {
      const percent = (e.loaded / e.total) * 100;
      progressBar.style.width = percent + '%';
      progressBar.textContent = Math.round(percent) + '%';
    }
  });

  xhr.addEventListener('load', () => {
    if (uploadButton) {
      uploadButton.disabled = false;
      uploadButton.textContent = 'Ladda upp fil';
    }
    if (progressDiv) progressDiv.style.display = 'none';

    try {
      const res = JSON.parse(xhr.responseText);
      if (res.status === 'success') {
        showNotification('Fil uppladdad framgångsrikt!', 'success');
        loadSharedFiles();
        resetUploadForm();
      } else {
        showNotification(res.message || 'Uppladdning misslyckades', 'error');
      }
    } catch (err) {
      showNotification('Ett fel uppstod vid uppladdning', 'error');
    }
  });

  xhr.addEventListener('error', () => {
    if (uploadButton) {
      uploadButton.disabled = false;
      uploadButton.textContent = 'Ladda upp fil';
    }
    if (progressDiv) progressDiv.style.display = 'none';
    showNotification('Nätverksfel vid uppladdning', 'error');
  });

  xhr.open('POST', '/upload_shared_file');
  xhr.send(formData);
}

function resetUploadForm() {
  const fileInput = document.getElementById('file-upload-input');
  const descriptionInput = document.getElementById('file-description');
  const uploadArea = document.getElementById('file-upload-area');

  if (fileInput) fileInput.value = '';
  if (descriptionInput) descriptionInput.value = '';
  if (uploadArea) uploadArea.classList.remove('drag-over');
}

function loadSharedFiles() {
  if (typeof currentSubject === 'undefined') return;
  
  fetch(`/api/shared_files/${encodeURIComponent(currentSubject)}`)
    .then(res => res.json())
    .then(data => {
      if (data.status === 'success') {
        displaySharedFiles(data.files);
      } else {
        console.error('Error loading shared files:', data.message);
      }
    })
    .catch(err => console.error('Error loading shared files:', err));
}

function displaySharedFiles(files) {
  const container = document.getElementById('shared-files-list');
  if (!container) return;

  if (files.length === 0) {
    container.innerHTML = '<p class="no-files">Inga filer uppladdade ännu.</p>';
    return;
  }

  container.innerHTML = files.map(file => `
    <div class="file-item" data-file-id="${file.id}">
      <div class="file-info">
        <div class="file-name">
          <i class="fas fa-file-${getFileIcon(file.extension)}"></i>
          <span>${file.filename}</span>
        </div>
        <div class="file-details">
          <span class="file-size">${file.file_size}</span>
          <span class="file-date">${file.created_at}</span>
          <span class="file-uploader">av ${file.uploader}</span>
          <span class="download-count">${file.download_count} nedladdningar</span>
        </div>
        ${file.description ? `<div class="file-description">${file.description}</div>` : ''}
      </div>
      <div class="file-actions">
        <button class="btn btn-sm btn-primary" onclick="downloadFile(${file.id})">
          <i class="fas fa-download"></i> Ladda ned
        </button>
        ${file.can_delete ? `
          <button class="btn btn-sm btn-danger" onclick="deleteFile(${file.id})">
            <i class="fas fa-trash"></i> Ta bort
          </button>` : ''}
      </div>
    </div>
  `).join('');
}

function getFileIcon(ext) {
  const icons = {
    pdf: 'pdf', doc: 'word', docx: 'word', txt: 'text', rtf: 'text',
    jpg: 'image', jpeg: 'image', png: 'image', gif: 'image', bmp: 'image',
    mp4: 'video', avi: 'video', mov: 'video', wmv: 'video', flv: 'video',
    mp3: 'audio', wav: 'audio', ogg: 'audio', flac: 'audio',
    zip: 'archive', rar: 'archive', '7z': 'archive', tar: 'archive', gz: 'archive'
  };
  return icons[ext] || 'alt';
}

function downloadFile(id) {
  const link = document.createElement('a');
  link.href = `/download_shared_file/${id}`;
  link.style.display = 'none';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function deleteFile(id) {
  if (!confirm('Är du säker på att du vill ta bort denna fil?')) return;

  fetch('/delete_shared_file', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_id: id })
  })
    .then(res => res.json())
    .then(data => {
      if (data.status === 'success') {
        showNotification('Fil borttagen framgångsrikt', 'success');
        loadSharedFiles();
        if (userRole === 'owner') loadFileStats();
      } else {
        showNotification(data.message || 'Kunde inte ta bort filen', 'error');
      }
    })
    .catch(err => {
      console.error('Error deleting file:', err);
      showNotification('Ett fel uppstod vid borttagning', 'error');
    });
}

function loadFileStats() {
  if (userRole !== 'owner') return;
  if (typeof subjectId === 'undefined') return;
  
  fetch(`/api/shared_files/${subjectId}/stats`)
    .then(res => res.json())
    .then(data => {
      if (data.status === 'success') {
        updateFileStats(data.total_files, data.total_downloads);
      }
    })
    .catch(err => console.error('Error loading file stats:', err));
}

function updateFileStats(totalFiles, totalDownloads) {
  const fileCount = document.getElementById('files-count');
  const downloadCount = document.getElementById('downloads-count');
  if (fileCount) fileCount.textContent = totalFiles;
  if (downloadCount) downloadCount.textContent = totalDownloads;
}

function loadMemberCount() {
  if (userRole !== 'owner') return;
  if (typeof subjectId === 'undefined') return;
  
  fetch(`/api/subject/${subjectId}/members`)
    .then(res => res.json())
    .then(data => {
      if (data.status === 'success') {
        const memberCount = document.getElementById('members-count');
        if (memberCount) {
          memberCount.textContent = `👥 ${data.total_members} medlem${data.total_members !== 1 ? 'mar' : ''}`;
        }
      }
    })
    .catch(err => console.error('Error loading member count:', err));
}

// ----------- NOTIFICATION SYSTEM -----------
function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.innerHTML = `
    <span>${message}</span>
    <button class="notification-close" onclick="this.parentElement.remove()">×</button>
  `;

  let container = document.getElementById('notifications-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'notifications-container';
    container.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 1000;
      max-width: 300px;
    `;
    document.body.appendChild(container);
  }

  container.appendChild(notification);
  setTimeout(() => notification.remove(), 5000);
}
