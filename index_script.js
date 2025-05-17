


const modal = document.getElementById("subject-modal");
const btn = document.getElementById("left-subject-btn");
const close = document.querySelector(".close");

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
