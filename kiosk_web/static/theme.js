document.addEventListener("DOMContentLoaded", () => {
    if (localStorage.getItem("theme") === "dark") {
        document.body.classList.add("dark");
    }
});

function toggleTheme() {
    const isDark = document.body.classList.toggle("dark");
    localStorage.setItem("theme", isDark ? "dark" : "light");

    const btn = document.getElementById("themeToggle");
    if (btn) btn.innerHTML = isDark ? "☀️" : "🌙";
}

function confirmLogout() {
    if (confirm("Are you sure you want to logout?")) {
        window.location.href = "/logout";
    }
}
