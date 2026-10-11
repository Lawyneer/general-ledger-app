function toggleTheme() {
  const dark = document.documentElement.classList.toggle('dark');
  try { localStorage.setItem('theme', dark ? 'dark' : 'light'); } catch (e) {}
  $('#theme-toggle').textContent = dark ? '☀️' : '🌙';
}
$('#theme-toggle').textContent =
  document.documentElement.classList.contains('dark') ? '☀️' : '🌙';