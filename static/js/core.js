const $ = s => document.querySelector(s);
const nfmt = n => n.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});

const api = async (path, opts = {}) => {
  const r = await fetch('/api/v1' + path,
    { ...opts, headers: { 'Content-Type': 'application/json' } });
  if (!r.ok) { const e = await r.json().catch(() => ({}));
               alert(e.detail || r.statusText); throw new Error(e.detail || r.status); }
  return r.json();
};

// Shared state
let ACCOUNTS = [];        // account cache; feeds Accounts tab + entry modal dropdown
let editingGuid = null;    // journal entry currently being edited, if any
let page = 1;             // journal pagination
const TXNS = {};          // guid → full transaction object, for editing from journal rows