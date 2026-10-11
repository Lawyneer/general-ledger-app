function accountLabel(a) {
  let parts = [a.name]; let seen = new Set([a.guid]);
  const byId = Object.fromEntries(ACCOUNTS.map(x => [x.guid, x]));
  let p = byId[a.parent_guid];
  while (p && !seen.has(p.guid)) { parts.unshift(p.name); seen.add(p.guid); p = byId[p.parent_guid]; }
  return parts.join(':');
}

async function loadAccounts() {
  ACCOUNTS = await api('/accounts');
  const opts = `<option value="">(top level)</option>` +
    ACCOUNTS.map(a => `<option value="${a.guid}">${a.name} (${a.type})</option>`).join('');
  $('#a-parent').innerHTML = opts;
  $('#a-list').innerHTML = ACCOUNTS.map(a => `<tr>
      <td>${accountLabel(a)}</td><td>${a.type}</td>
      <td class="num">${a.balance}</td>
      <td><button onclick="renameAccount('${a.guid}')">Rename</button>
          <button onclick="deleteAccount('${a.guid}')">Delete</button></td>
  </tr>`).join('');
}

async function createAccount() {
  const name = $('#a-name').value.trim();
  if (!name) { alert('Please enter an account name.'); $('#a-name').focus(); return; }
  const parent = $('#a-parent').value || null;
  const dup = ACCOUNTS.find(a =>
    a.name.toLowerCase() === name.toLowerCase() &&
    (a.parent_guid ?? null) === parent);
  if (dup) { alert(`An account named "${name}" already exists under this parent.`); return; }
  await api('/accounts', { method: 'POST', body: JSON.stringify({
    name, type: $('#a-type').value, parent }) });
  $('#a-name').value = ''; loadAccounts();
}

async function renameAccount(guid) {
  const a = ACCOUNTS.find(x => x.guid === guid);
  if (!a) return;
  const newName = prompt('Rename account:', a.name);
  if (!newName || !newName.trim()) return;
  const trimmed = newName.trim();
  const parent = a.parent_guid ?? null;
  const dup = ACCOUNTS.find(x =>
    x.guid !== guid && x.name.toLowerCase() === trimmed.toLowerCase() &&
    (x.parent_guid ?? null) === parent);
  if (dup) { alert(`An account named "${trimmed}" already exists under this parent.`); return; }
  await api(`/accounts/${guid}`, { method: 'PATCH', body: JSON.stringify({
    name: trimmed, type: a.type, parent }) });
  loadAccounts();
}

async function deleteAccount(guid) {
  const a = ACCOUNTS.find(x => x.guid === guid);
  if (!confirm(`Delete account "${a?.name}"?`)) return;
  await api(`/accounts/${guid}`, { method: 'DELETE' });
  loadAccounts();
}