


window.onload = function () {
  let extractedPdfText = "";
  const modal = document.getElementById("subject-modal");
  const btn = document.getElementById("left-subject-btn");
  const close = document.querySelector(".close");

  btn.onclick = () => {
    modal.style.display = "block";
  };
  close.onclick = () => {
    modal.style.display = "none";
  };

  
  const calendarBtn = document.getElementById("btn-2");
  const calendarModal = document.getElementById("calendar-modal");
  const calendarClose = document.querySelector(".calendar-close");

  const prevBtn = document.getElementById("prev-month-btn");
  const nextBtn = document.getElementById("next-month-btn");
  const monthYearDisplay = document.getElementById("month-year");
  const calendarBody = document.getElementById("calendar-body");

  let currentMonth, currentYear;

  calendarBtn.onclick = () => {
    const now = new Date();
    currentMonth = now.getMonth();
    currentYear = now.getFullYear();
    generateCalendar(currentMonth, currentYear);
    calendarModal.style.display = "block";
  };

  calendarClose.onclick = () => {
    calendarModal.style.display = "none";
  };

  window.onclick = (event) => {
    if (event.target === modal) {
      modal.style.display = "none";
    }
    if (event.target === calendarModal) {
      calendarModal.style.display = "none";
    }
    if (event.target === newDataModal) {
      newDataModal.style.display = "none";
    }
  };

  prevBtn.onclick = () => {
    currentMonth--;
    if (currentMonth < 0) {
      currentMonth = 11;
      currentYear--;
    }
    generateCalendar(currentMonth, currentYear);
  };

  nextBtn.onclick = () => {
    currentMonth++;
    if (currentMonth > 11) {
      currentMonth = 0;
      currentYear++;
    }
    generateCalendar(currentMonth, currentYear);
  };

  function generateCalendar(month, year) {
    calendarBody.innerHTML = "";

    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);

    const monthName = firstDay.toLocaleString("default", { month: "long" });
    monthYearDisplay.textContent = `${monthName} ${year}`;

    let date = 1;
    let row = document.createElement("tr");
    const today = new Date();

    for (let i = 0; i < firstDay.getDay(); i++) {
      const emptyCell = document.createElement("td");
      row.appendChild(emptyCell);
    }

    while (date <= lastDay.getDate()) {
      if (row.children.length === 7) {
        calendarBody.appendChild(row);
        row = document.createElement("tr");
      }

      const cell = document.createElement("td");
      cell.textContent = date;
      cell.classList.add("calendar-cell");

      if (
        date === today.getDate() &&
        month === today.getMonth() &&
        year === today.getFullYear()
      ) {
        cell.classList.add("today");
      }

      const cellDate = new Date(year, month, date);
      cell.onclick = () => {
        const event = prompt(`Add event for ${cellDate.toDateString()}:`);
        if (event) {
          alert(`Saved event: "${event}"`);
        }
      };

      row.appendChild(cell);
      date++;
    }

    while (row.children.length < 7) {
      const emptyCell = document.createElement("td");
      row.appendChild(emptyCell);
    }

    calendarBody.appendChild(row);
  }

  const newDataBtn = document.getElementById("new-data-btn");
  const newDataModal = document.getElementById("new-data-modal");
  const closeNewDataBtn = document.getElementById("close-new-data");

  newDataBtn.onclick = () => {
    newDataModal.style.display = "block";
  };

  closeNewDataBtn.onclick = () => {
    newDataModal.style.display = "none";
  };

  const pdfUpload = document.getElementById("pdf-upload");
  const pdfViewer = document.getElementById("pdf-viewer");

  pdfUpload.addEventListener("change", async (event) => {
    const file = event.target.files[0];
    extractedPdfText = "";

    if (file && file.type === "application/pdf") {
      const fileURL = URL.createObjectURL(file);
      pdfViewer.src = fileURL;

    
      const arrayBuffer = await file.arrayBuffer();

      const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
      loadingTask.promise.then(async (pdf) => {
        let textContent = "";

        const maxPages = pdf.numPages;
        for (let pageNum = 1; pageNum <= maxPages; pageNum++) {
          const page = await pdf.getPage(pageNum);
          const text = await page.getTextContent();

          text.items.forEach((item) => {
            textContent += item.str + " ";
          });
        }

        extractedPdfText = textContent.trim();
        console.log("Extracted PDF Text:", extractedPdfText);
      }).catch((error) => {
        console.error("Error extracting PDF text:", error);
      });
    } else {
      pdfViewer.src = "";
      extractedPdfText = "";
    }
  });

  document.querySelectorAll(".desc-example").forEach((example) => {
    example.addEventListener("click", () => {
      const notesTextarea = document.getElementById("pdf-notes");
      const exampleText = example.textContent.trim();
      let currentText = notesTextarea.value.trim();

      if (currentText.length > 0 && !currentText.endsWith(" ")) {
        currentText += " ";
      }

      notesTextarea.value = currentText + exampleText;
      notesTextarea.focus();
    });
  });

  const notesTextarea = document.getElementById("pdf-notes");
  const generatedPDF = document.getElementById("generated-pdf");

  notesTextarea.addEventListener("blur", async () => {
    const prompt = notesTextarea.value.trim();
    if (!prompt) return;

    const combinedPrompt = `Here is the document content:\n\n${extractedPdfText}\n\nPlease ${prompt}`;

    const response = await fetch("https://ai.hackclub.com/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: [{ role: "user", content: combinedPrompt }],
      }),
    });

    if (!response.ok) {
      console.error("AI API error:", response.statusText);
      return;
    }

    const data = await response.json();
    const aiText = data.choices[0].message.content;

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    const lines = doc.splitTextToSize(aiText, 180);
    doc.text(lines, 10, 10);

    const pdfBlob = doc.output("blob");
    const pdfURL = URL.createObjectURL(pdfBlob);
    generatedPDF.src = pdfURL;
  });



  function getSelectedSubject() {
    const selected = document.querySelector('input[name="selected_subject"]:checked');
    return selected ? selected.value : null;
  }
};
