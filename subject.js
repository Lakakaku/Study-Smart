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
    // Spara filen på servern
    const form = new FormData();
    form.append('subject', currentSubject);
    form.append('type', type);
    form.append('file', file);

    try {
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

        // Ta bort-knapp
        const removeBtn = document.createElement('button');
        removeBtn.className = 'remove-document';
        removeBtn.dataset.docType = type;
        removeBtn.textContent = '×';
        item.appendChild(removeBtn);

        // Header
        const header = document.createElement('div');
        header.className = 'document-header';
        const title = document.createElement('span');
        title.className = 'document-title';
        title.textContent = {
          'begrippslista': 'Begrippslista',
          'kunskapskrav': 'Kunskapskrav',
          'kunskapsmal': 'Kunskapsmål'
        }[type];
        header.appendChild(title);
        item.appendChild(header);

        // Preview via iframe
        const preview = document.createElement('div');
        preview.className = 'document-preview';
        const iframe = document.createElement('iframe');
        iframe.src = `/static/uploads/krav/${encodeURIComponent(currentSubject)}/${encodeURIComponent(type)}.pdf`;
        iframe.width = '100%';
        iframe.height = '300px';
        iframe.style.border = '1px solid #ccc';
        preview.appendChild(iframe);
        item.appendChild(preview);

        documentsContainer.appendChild(item);
      } else {
        alert('Kunde inte ladda upp dokument: ' + (data.message || 'Okänt fel'));
      }
    } catch (err) {
      console.error('Upload error:', err);
      alert('Fel vid uppladdning av PDF.');
    }
  }

  // Ta bort dokument
  document.addEventListener('click', async (e) => {
    if (!e.target.classList.contains('remove-document')) return;
    const type = e.target.dataset.docType;
    if (!confirm('Vill du verkligen ta bort dokumentet?')) return;

    try {
      const res = await fetch('/delete_krav_document', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject: currentSubject,
          doc_type: type
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        const el = e.target.closest('.document-item');
        if (el) el.remove();
      } else {
        alert('Kunde inte ta bort dokument: ' + (data.message || 'Okänt fel'));
      }
    } catch (err) {
      console.error('Deletion error:', err);
      alert('Fel vid borttagning.');
    }
  });
});
