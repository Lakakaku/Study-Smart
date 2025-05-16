

const modal = document.getElementById("subject-modal");
const btn = document.getElementById("left-subject-btn");
const close = document.querySelector(".close");
const form = document.getElementById("create-subject-form");
const subjectList = document.querySelector(".subject-list");
const subjectInput = document.getElementById("subject-name");

btn.onclick = () => {
  modal.style.display = "block";
};

close.onclick = () => {
  modal.style.display = "none";
};

window.onclick = (event) => {
  if (event.target === modal) {
    modal.style.display = "none";
  }
};

form.addEventListener("submit", function (e) {
  e.preventDefault();

  const subjectName = subjectInput.value.trim();
  if (subjectName) {
    const newSubject = document.createElement("div");
    newSubject.classList.add("subject");

    const subjectText = document.createElement("span");
    subjectText.textContent = subjectName;
    const removeBtn = document.createElement("button");
    removeBtn.classList.add("remove-btn");
    removeBtn.title = "Remove subject";
    removeBtn.textContent = "×";

    removeBtn.addEventListener("click", () => {
      if (confirm(`Are you sure you want to remove "${subjectName}"?`)) {
        newSubject.remove();
      }
    });

    newSubject.appendChild(subjectText);
    newSubject.appendChild(removeBtn);

    subjectList.appendChild(newSubject);

    subjectInput.value = "";
    modal.style.display = "none";
  }
});
