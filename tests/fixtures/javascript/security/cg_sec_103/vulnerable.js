// MUST trigger CG-SEC-103
function render(el, userHtml, pos) {
  el.innerHTML = userHtml;
  el.outerHTML = "<div>" + userHtml + "</div>";
  document.write(userHtml);
  el.insertAdjacentHTML(pos, userHtml);
}
