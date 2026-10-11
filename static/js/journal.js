async function loadJournal() {
  const p = new URLSearchParams({ page, size: 50 });
  if ($('#j-from').value) p.set('from', $('#j-from').value);
  if ($('#j-to').value) p.set('to', $('#j-to').value);
  const d = await api('/journal?' + p);
  const tb = $('#journal-table tbody');
  if (page === 1) tb.innerHTML = '';
  let td = 0, tc = 0;
  for (const t of d.transactions) {
    TXNS[t.guid] = t;   // cache for the Edit button
    t.splits.forEach((s, i) => {
      const amt = parseFloat(s.amount.replace(',', '')), isDebit = amt > 0;
      if (isDebit) td += Math.abs(amt); else tc += Math.abs(amt);
      tb.insertAdjacentHTML('beforeend', `<tr>
        ${i === 0 ? `<td rowspan="${t.splits.length}">${t.date}</td>
                     <td rowspan="${t.splits.length}">${t.description}</td>` : ''}
        <td>${s.account_name}</td><td class="muted">${s.memo}</td>
        <td class="num">${isDebit ? nfmt(Math.abs(amt)) : ''}</td>
        <td class="num">${!isDebit ? nfmt(Math.abs(amt)) : ''}</td>
        ${i === 0 ? `<td rowspan="${t.splits.length}">
                       <button onclick="editTxn('${t.guid}')">Edit</button>
                       <button onclick="delTxn('${t.guid}')">Delete</button>
                     </td>` : ''}
      </tr>`);
    });
  }
  $('#tot-d').textContent = nfmt(td);
  $('#tot-c').textContent = nfmt(tc);
  $('#j-more').hidden = !d.has_more;
}

function editTxn(guid) {
  if (TXNS[guid]) openModal(TXNS[guid]);
}

async function delTxn(guid) {
  if (!confirm('Delete this journal entry?')) return;
  await api('/journal/' + guid, { method: 'DELETE' });
  page = 1; loadJournal(); loadAccounts();
}

function openModal(txn = null) {
  editingGuid = txn ? txn.guid : null;
  $('#m-title').textContent = txn ? 'Edit Entry' : 'New Entry';
  $('#m-date').value = txn ? txn.date : new Date().toISOString().slice(0, 10);
  $('#m-desc').value = txn ? txn.description : '';
  $('#m-num').value = txn ? txn.num : '';
  $('#m-splits tbody').innerHTML = '';
  if (txn) txn.splits.forEach(s => {
    addSplitRow();
    const row = lastRow();
    row.querySelector('select').value = s.account;
    const amt = parseFloat(s.amount.replace(',', ''));
    (amt > 0 ? row.querySelector('.debit') : row.querySelector('.credit'))
      .value = Math.abs(amt).toFixed(2);   // plain format inside inputs
    row.querySelector('.memo').value = s.memo;
  });
  else { addSplitRow(); addSplitRow(); }
  updateBal();
  $('#overlay').hidden = false;
}

const closeModal = () => $('#overlay').hidden = true;
const lastRow = () => $('#m-splits tbody').lastElementChild;

function addSplitRow() {
  const tr = document.createElement('tr');
  tr.innerHTML = `<td><select>${ACCOUNTS.map(a =>
      `<option value="${a.guid}">${a.name} (${a.type})</option>`).join('')}</select></td>
    <td><input class="debit" oninput="updateBal()"></td>
    <td><input class="credit" oninput="updateBal()"></td>
    <td><input class="memo"></td>
    <td><button onclick="this.closest('tr').remove();updateBal()">×</button></td>`;
  $('#m-splits tbody').appendChild(tr);
}

function updateBal() {
  let bal = 0, n = 0;
  $('#m-splits tbody').querySelectorAll('tr').forEach(tr => {
    const d = parseFloat(tr.querySelector('.debit').value || 0);
    const c = parseFloat(tr.querySelector('.credit').value || 0);
    if (d) bal += d; if (c) bal -= c; if (d || c) n++;
  });
  const el = $('#m-balance');
  if (n < 2) { el.textContent = 'add at least 2 splits'; el.className = 'muted'; }
  else if (Math.abs(bal) < 0.005) { el.textContent = '✓ Balanced'; el.className = 'ok'; }
  else { el.textContent = 'Unbalanced: ' + (bal > 0 ? '+' : '') + bal.toFixed(2); el.className = 'bad'; }
}

async function saveEntry() {
  const splits = [...$('#m-splits tbody').querySelectorAll('tr')].map(tr => ({
    account: tr.querySelector('select').value,
    debit: tr.querySelector('.debit').value || null,
    credit: tr.querySelector('.credit').value || null,
    memo: tr.querySelector('.memo').value })).filter(s => s.debit || s.credit);
  const body = { date: $('#m-date').value, description: $('#m-desc').value,
                 num: $('#m-num').value, splits };
  if (editingGuid) await api('/journal/' + editingGuid, { method: 'PUT', body: JSON.stringify(body) });
  else await api('/journal', { method: 'POST', body: JSON.stringify(body) });
  closeModal(); page = 1; loadJournal(); loadAccounts();
}