$('#s-kind').onchange = () => {
  const period = ['income-statement', 'cash-flow'].includes($('#s-kind').value);
  $('#s-from-l').hidden = $('#s-to-l').hidden = !period;
  $('#s-asof-l').hidden = period;
};

function mkTable(headers, rows) {
  return `<table><thead><tr>${headers.map(h => `<th class="${isNaN(h) ? '' : 'num'}">${h}</th>`).join('')}</tr></thead>
    <tbody>${rows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
}

async function runStatement() {
  const kind = $('#s-kind').value, p = new URLSearchParams();
  if (['income-statement', 'cash-flow'].includes(kind)) {
    p.set('from', $('#s-from').value || '1900-01-01');
    p.set('to', $('#s-to').value || '2999-12-31');
  } else if ($('#s-asof').value) p.set('as_of', $('#s-asof').value);
  const d = await api(`/statements/${kind}?` + p);
  let html = '';
  if (kind === 'trial-balance') {
    html = mkTable(['Account', 'Type', 'Debit', 'Credit'],
      [...d.lines.map(l => [l.account, l.type, l.debit ?? '', l.credit ?? '']),
       [`<b>Totals</b>`, '', `<b>${d.total_debits}</b>`, `<b>${d.total_credits}</b>`]])
      + `<p class="${d.balanced ? 'ok' : 'bad'}">${d.balanced ? '✓ Books balance' : '✗ OUT OF BALANCE'}</p>`;
  } else if (kind === 'income-statement') {
    html = mkTable(['Income', 'Amount'], [...d.income.map(i => [i.account, i.amount]),
        ['<b>Total Income</b>', `<b>${d.total_income}</b>`]])
      + mkTable(['Expenses', 'Amount'], [...d.expenses.map(e => [e.account, e.amount]),
        ['<b>Total Expenses</b>', `<b>${d.total_expenses}</b>`]])
      + `<p><b>Net Income: ${d.net_income}</b></p>`;
  } else if (kind === 'balance-sheet') {
    html = mkTable(['Assets', 'Amount'], [...d.assets.map(a => [a.account, a.amount]),
        ['<b>Total Assets</b>', `<b>${d.total_assets}</b>`]])
      + mkTable(['Liabilities', 'Amount'], [...d.liabilities.map(a => [a.account, a.amount]),
        ['<b>Total Liabilities</b>', `<b>${d.total_liabilities}</b>`]])
      + mkTable(['Equity', 'Amount'], [...d.equity.map(a => [a.account, a.amount]),
        ['<b>Total Equity</b>', `<b>${d.total_equity}</b>`]])
      + `<p class="${d.balanced ? 'ok' : 'bad'}">${d.balanced ? '✓ A = L + E' : '✗ DOES NOT BALANCE'}</p>`;
  } else {
    html = mkTable(['Inflows', 'Amount'], d.inflows.map(i => [i.category, i.amount]))
      + mkTable(['Outflows', 'Amount'], d.outflows.map(o => [o.category, o.amount]))
      + `<p>Cash: begin ${d.cash_begin} → end ${d.cash_end} (net ${d.net_change_cash})</p>`;
  }
  $('#s-out').innerHTML = html;
}

function exportTB() {
  const p = new URLSearchParams();
  if ($('#s-asof').value) p.set('as_of', $('#s-asof').value);
  window.location.href = '/api/v1/statements/trial-balance/excel?' + p;
}