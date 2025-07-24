document.addEventListener("DOMContentLoaded", function () {
  const fileInput = document.getElementById('data1');
  const container = document.querySelector('.pdf-container');
  const subjectDropdown = document.getElementById('subject');
  const useDocumentsCheckbox = document.getElementById('use_documents');
  const documentsInfoDiv = document.getElementById('documents-info');

  let filesArray = [];

  function renderFiles() {
    if (!container) return;
    
    container.innerHTML = ''; 

    filesArray.forEach((file, index) => {
      const fileBox = document.createElement('div');
      fileBox.classList.add('file-box');

      const fileName = document.createElement('div');
      fileName.textContent = file.name;
      fileName.style.padding = '5px 0';
      fileName.style.fontWeight = 'bold';
      fileBox.appendChild(fileName);

      if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
        const iframe = document.createElement('iframe');
        iframe.src = URL.createObjectURL(file);
        iframe.width = '100%';
        iframe.height = '160px';
        iframe.style.border = 'none';
        iframe.style.marginTop = '5px';
        fileBox.appendChild(iframe);
      } else {
        const msg = document.createElement('div');
        msg.textContent = 'File preview not available';
        msg.style.color = 'gray';
        fileBox.appendChild(msg);
      }

      const removeBtn = document.createElement('button');
      removeBtn.textContent = '×';
      removeBtn.classList.add('remove-btn');
      removeBtn.style.marginTop = '5px';
      removeBtn.addEventListener('click', () => {
        filesArray.splice(index, 1);
        renderFiles();
        updateFileInput();
      });
      fileBox.appendChild(removeBtn);

      container.appendChild(fileBox);
    });
  }

  function updateFileInput() {
    if (!fileInput) return;
    
    const dataTransfer = new DataTransfer();
    filesArray.forEach(file => dataTransfer.items.add(file));
    fileInput.files = dataTransfer.files;
  }

  if (fileInput) {
    fileInput.addEventListener('change', (event) => {
      const newFiles = Array.from(event.target.files);
      newFiles.forEach(newFile => {
        if (!filesArray.some(f => f.name === newFile.name && f.size === newFile.size && f.lastModified === newFile.lastModified)) {
          filesArray.push(newFile);
        }
      });
      renderFiles();
      updateFileInput();
    });
  }

  const form = document.getElementById('quiz-form');
  if (form) {
    form.addEventListener('submit', () => {
      console.log(`Submitting ${filesArray.length} files`);
    });
  }

  // **NYA FUNKTIONER FÖR KRAV-DOKUMENT**
  
  // Ladda krav-dokument när subject ändras
  if (subjectDropdown) {
    subjectDropdown.addEventListener('change', function () {
      const selectedSubject = this.value;
      
      if (selectedSubject) {
        loadKravDocuments(selectedSubject);
      } else {
        clearDocumentsInfo();
      }

      // Befintlig kod för tests (om den finns)
      handleTestSelection(selectedSubject);
    });
  }

  // Visa/dölj dokumentinformation när checkbox ändras
  if (useDocumentsCheckbox) {
    useDocumentsCheckbox.addEventListener('change', function () {
      updateDocumentsVisibility();
    });
  }

  function loadKravDocuments(subjectName) {
    fetch(`/api/krav_documents/${encodeURIComponent(subjectName)}`)
      .then(response => response.json())
      .then(data => {
        if (data.status === 'success') {
          displayKravDocuments(data.documents);
        } else {
          console.error('Error loading krav documents:', data.message);
          displayNoDocuments();
        }
      })
      .catch(error => {
        console.error('Error loading krav documents:', error);
        displayNoDocuments();
      });
  }

  function displayKravDocuments(documents) {
    if (!documentsInfoDiv) {
      createDocumentsInfoDiv();
    }

    const docTypes = ['kunskapsmal', 'kunskapskrav', 'begrippslista'];
    const typeNames = {
      'kunskapsmal': 'Kunskapsmål',
      'kunskapskrav': 'Kunskapskrav',
      'begrippslista': 'Begrippslista'
    };

    let availableDocs = [];
    let missingDocs = [];

    docTypes.forEach(type => {
      const doc = documents.find(d => d.doc_type === type);
      if (doc) {
        availableDocs.push({
          type: type,
          name: typeNames[type],
          filename: doc.filename,
          size: formatFileSize(doc.file_size)
        });
      } else {
        missingDocs.push(typeNames[type]);
      }
    });

    let html = '<div class="krav-documents-status">';
    
    if (availableDocs.length > 0) {
      html += '<h4>📚 Tillgängliga krav-dokument:</h4>';
      html += '<ul class="available-docs">';
      availableDocs.forEach(doc => {
        html += `<li>✅ <strong>${doc.name}</strong> (${doc.filename}, ${doc.size})</li>`;
      });
      html += '</ul>';
    }

    if (missingDocs.length > 0) {
      html += '<p class="missing-docs"><strong>⚠️ Saknade dokument:</strong> ' + missingDocs.join(', ') + '</p>';
      html += '<p class="missing-docs-help"><small>Dessa kan laddas upp av subject-ägaren för att förbättra quiz-genereringen.</small></p>';
    }

    if (availableDocs.length === 0) {
      html += '<p class="no-docs">❌ Inga krav-dokument finns uppladdade för detta ämne.</p>';
      html += '<p class="no-docs-help"><small>Subject-ägaren kan ladda upp kunskapsmål, kunskapskrav och begreppslistor för att förbättra quiz-genereringen.</small></p>';
    }

    html += '</div>';
    
    documentsInfoDiv.innerHTML = html;
    updateDocumentsVisibility();
  }

  function displayNoDocuments() {
    if (!documentsInfoDiv) {
      createDocumentsInfoDiv();
    }

    documentsInfoDiv.innerHTML = `
      <div class="krav-documents-status">
        <p class="no-docs">❌ Inga krav-dokument finns tillgängliga för detta ämne.</p>
        <p class="no-docs-help"><small>Subject-ägaren kan ladda upp kunskapsmål, kunskapskrav och begreppslistor för att förbättra quiz-genereringen.</small></p>
      </div>
    `;
    updateDocumentsVisibility();
  }

  function clearDocumentsInfo() {
    if (documentsInfoDiv) {
      documentsInfoDiv.innerHTML = '';
      documentsInfoDiv.style.display = 'none';
    }
  }

  function createDocumentsInfoDiv() {
    if (documentsInfoDiv) return;

    const newDiv = document.createElement('div');
    newDiv.id = 'documents-info';
    newDiv.className = 'documents-info';
    
    // Hitta checkbox-gruppen och lägg till efter den
    const checkboxGroup = useDocumentsCheckbox ? useDocumentsCheckbox.closest('.form-group') : null;
    if (checkboxGroup && checkboxGroup.nextSibling) {
      checkboxGroup.parentNode.insertBefore(newDiv, checkboxGroup.nextSibling);
    } else {
      // Fallback: lägg till före submit-knappen
      const submitBtn = document.querySelector('.submit-btn');
      if (submitBtn) {
        submitBtn.parentNode.insertBefore(newDiv, submitBtn.parentNode.lastElementChild);
      }
    }
  }

  function updateDocumentsVisibility() {
    if (!documentsInfoDiv) return;
    
    const isChecked = useDocumentsCheckbox ? useDocumentsCheckbox.checked : false;
    documentsInfoDiv.style.display = isChecked ? 'block' : 'none';
  }

  function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  // Befintlig test-hantering (om den finns)
  function handleTestSelection(selectedSubject) {
    const testSection = document.getElementById('test-selector-section');
    const testDropdown = document.getElementById('test-dropdown');
    
    if (!testSection || !testDropdown || typeof allEvents === 'undefined') {
      return;
    }

    // Filter tests matching the selected subject
    const matchingTests = allEvents.filter(event => event.subject === selectedSubject);

    // Clear old options
    testDropdown.innerHTML = '<option value="" disabled selected hidden>Select a test</option>';

    if (matchingTests.length > 0) {
      matchingTests.forEach(test => {
        const option = document.createElement('option');
        option.value = test.id;
        option.textContent = `${test.title} (${test.testType} on ${test.date})`;
        testDropdown.appendChild(option);
      });

      testSection.style.display = 'block';
    } else {
      testSection.style.display = 'none';
    }
  }
});
