



document.addEventListener("DOMContentLoaded", function () {
  const fileInput = document.getElementById('data-upload');
  const container = document.querySelector('#right-data .pdf-container');


  fileInput.addEventListener('change', function (event) {
    const files = Array.from(event.target.files);
    
    files.forEach(file => {
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
        msg.textContent = 'File is not a PDF';
        msg.style.color = 'red';
        fileBox.appendChild(msg);
      }

      const removeBtn = document.createElement('button');
      removeBtn.textContent = 'x';
      removeBtn.classList.add('remove-btn');
      removeBtn.style.marginTop = '5px';
      removeBtn.style.padding = '2px 8px';
      removeBtn.style.fontSize = '0.8rem';
      removeBtn.style.cursor = 'pointer';
      removeBtn.style.borderRadius = '5px';
      removeBtn.style.border = '1px solid #ccc';
      removeBtn.addEventListener('click', () => {
        fileBox.remove();
      });
      fileBox.appendChild(removeBtn);

      container.appendChild(fileBox);
    });

    fileInput.value = '';
  });
});





