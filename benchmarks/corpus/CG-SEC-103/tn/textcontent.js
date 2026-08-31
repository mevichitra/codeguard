// MUST NOT trigger CG-SEC-103
function render(el, userText) {
  el.textContent = userText;
  el.innerHTML = "<p>static</p>";
  document.write("<hr>");
}
