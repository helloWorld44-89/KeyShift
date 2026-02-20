const html = document.documentElement;
const themeToggle = document.getElementById("themeToggle");
const themeIcon = document.getElementById("themeIcon");
function applyTheme(t) {
  html.setAttribute("data-bs-theme", t);
  themeIcon.className =
    t === "dark" ? "bi bi-sun-fill" : "bi bi-moon-stars-fill";
  localStorage.setItem("ks-theme", t);
}
applyTheme(localStorage.getItem("ks-theme") || "light");
themeToggle.addEventListener("click", () => {
  applyTheme(html.getAttribute("data-bs-theme") === "dark" ? "light" : "dark");
});
