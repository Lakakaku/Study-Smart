

document.addEventListener("DOMContentLoaded", function () {
  const fileInput = document.getElementById('data-upload');
  const container = document.querySelector('.pdf-container');

  let filesArray = [];

  function renderFiles() {
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
    const dataTransfer = new DataTransfer();
    filesArray.forEach(file => dataTransfer.items.add(file));
    fileInput.files = dataTransfer.files;
  }

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

  const form = document.getElementById('quiz-form');
  if (form) {
    form.addEventListener('submit', () => {
      console.log(`Submitting ${filesArray.length} files`);
    });
  }

  const subjectDropdown = document.getElementById('subject');
  const testSection = document.getElementById('test-selector-section');
  const testDropdown = document.getElementById('test-dropdown');

  subjectDropdown.addEventListener('change', function () {
    const selectedSubject = this.value;

    // Filter tests matching the selected subject
    const matchingTests = allEvents.filter(event => event.subject === selectedSubject);

    // Clear old options
    testDropdown.innerHTML = '<option value="" disabled selected hidden>Select a test</option>';

    if (matchingTests.length > 0) {
      matchingTests.forEach(test => {
        const option = document.createElement('option');
        option.value = test.id; // you can choose any identifier
        option.textContent = `${test.title} (${test.testType} on ${test.date})`;
        testDropdown.appendChild(option);
      });

      testSection.style.display = 'block';
    } else {
      testSection.style.display = 'none';
    }
  });

});
