// Tab navigation — scoped to data-tab buttons ONLY, so the theme toggle
// (and any future non-tab nav buttons) don't trigger tab hiding.
document.querySelectorAll('nav button[data-tab]').forEach(b => b.onclick = () => {
  document.querySelectorAll('nav button[data-tab]').forEach(x => x.classList.toggle('active', x === b));
  ['register', 'accounts', 'statements'].forEach(t =>
    $('#tab-' + t).hidden = (t !== b.dataset.tab));
  if (b.dataset.tab === 'accounts') loadAccounts();   // refresh stale balances
});

// Boot
loadAccounts().then(() => loadJournal());