/**
 * Редактируйте этот файл для изменения логики отображения.
 * Данные приходят с /api/registry, /api/status, /api/up, /api/store/<name>
 */

async function fetchJSON(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString('ru');
}

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

function openStoreDetail(store) {
  document.getElementById('modal-title').textContent = 'Точка: ' + store;
  document.getElementById('store-modal').hidden = false;
  document.getElementById('detail-windows').innerHTML = '<span class="loading">Загрузка...</span>';
  document.getElementById('detail-interfaces').innerHTML = '';
  document.getElementById('detail-snmp-raw').textContent = '';
  document.getElementById('detail-windows-raw').textContent = '';

  fetchJSON('/api/store/' + encodeURIComponent(store))
    .then(data => {
      // Windows
      const winEl = document.getElementById('detail-windows');
      if (data.error) {
        winEl.innerHTML = '<p class="err">' + data.error + '</p>';
      } else if (data.windows.length === 0) {
        winEl.innerHTML = '<p>Нет данных от ПК</p>';
      } else {
        const up = data.windows.find(m => m.metric === 'up');
        const mem = data.windows.find(m => m.metric === 'windows_memory_available_bytes');
        const total = data.windows.find(m => m.metric === 'windows_memory_physical_total_bytes');
        let html = '';
        if (up) html += '<p class="metric-row">up = ' + up.value + ' ' + (up.value === '1' ? '(онлайн)' : '(офлайн)') + '</p>';
        if (mem && total) {
          const pct = (100 * (1 - mem.value / total.value)).toFixed(1);
          html += '<p class="metric-row">Память занята ≈ ' + pct + '%</p>';
        }
        html += '<p class="metric-row">Всего метрик: ' + data.windows.length + '</p>';
        winEl.innerHTML = html;
      }

      // SNMP интерфейсы
      const ifEl = document.getElementById('detail-interfaces');
      if (data.snmp_interfaces.length > 0) {
        ifEl.innerHTML = '<table class="if-table"><thead><tr><th>Интерфейс</th><th>Alias (ICCID/UICC)</th><th>Статус</th></tr></thead><tbody>' +
          data.snmp_interfaces.map(i => '<tr><td>' + i.ifName + '</td><td>' + (i.ifAlias || '—') + '</td><td class="' + (i.status === 'Up' ? 'up' : 'down') + '">' + i.status + '</td></tr>').join('') +
          '</tbody></table>';
      } else if (data.mikrotik.length > 0) {
        ifEl.innerHTML = '<p>Метрик SNMP: ' + data.mikrotik.length + '</p>';
      } else {
        ifEl.innerHTML = '<p>Нет данных от роутера</p>';
      }

      document.getElementById('detail-snmp-raw').textContent = JSON.stringify(data.mikrotik, null, 2);
      document.getElementById('detail-windows-raw').textContent = JSON.stringify(data.windows, null, 2);
    })
    .catch(e => {
      document.getElementById('detail-windows').innerHTML = '<p class="err">Ошибка: ' + e.message + '</p>';
    });
}

function closeModal() {
  document.getElementById('store-modal').hidden = true;
}

document.getElementById('store-modal').addEventListener('click', e => {
  if (e.target.id === 'store-modal') closeModal();
});

async function refresh() {
  try {
    const [registry, status, up] = await Promise.all([
      fetchJSON('/api/registry'),
      fetchJSON('/api/status'),
      fetchJSON('/api/up').catch(() => ({ stores: [] })),
    ]);

    document.getElementById('prom-url').textContent = status.prometheus_url;
    const promBadge = document.getElementById('prom-status');
    promBadge.textContent = status.prometheus_reachable ? 'OK' : 'Ошибка';
    promBadge.className = 'badge ' + (status.prometheus_reachable ? 'ok' : 'err');

    if (status.version) document.getElementById('version-badge').textContent = status.version;
    document.getElementById('stores-up').textContent = status.stores_up_now ?? up.stores?.length ?? 0;
    document.getElementById('stores-registry').textContent = status.stores_in_registry;
    document.getElementById('last-sync').textContent = formatDate(status.last_sync);
    if (status.last_sync_error) {
      document.getElementById('last-sync').title = status.last_sync_error;
    }

    const tbody = document.querySelector('#registry-table tbody');
    tbody.innerHTML = registry.stores
      .map(({ store, last_seen_iso }) =>
        '<tr><td><span class="store-link" data-store="' + escapeHtml(store) + '">' + escapeHtml(store) + '</span></td><td>' + escapeHtml(formatDate(last_seen_iso)) + '</td></tr>'
      )
      .join('') || '<tr><td colspan="2">Нет данных</td></tr>';

    tbody.querySelectorAll('.store-link').forEach(el => {
      el.onclick = () => openStoreDetail(el.dataset.store);
    });

    document.getElementById('status-raw').textContent = JSON.stringify(status, null, 2);
  } catch (e) {
    document.getElementById('status-raw').textContent = 'Ошибка: ' + e.message;
  }
}

refresh();
setInterval(refresh, 10000);
