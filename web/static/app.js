/**
 * Редактируйте этот файл для изменения логики отображения.
 * Данные приходят с /api/registry, /api/status, /api/up
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

async function refresh() {
  try {
    const [registry, status, up] = await Promise.all([
      fetchJSON('/api/registry'),
      fetchJSON('/api/status'),
      fetchJSON('/api/up').catch(() => ({ stores: [] })),
    ]);

    // Карточки
    document.getElementById('prom-url').textContent = status.prometheus_url;
    const promBadge = document.getElementById('prom-status');
    promBadge.textContent = status.prometheus_reachable ? 'OK' : 'Ошибка';
    promBadge.className = 'badge ' + (status.prometheus_reachable ? 'ok' : 'err');

    document.getElementById('stores-up').textContent = status.stores_up_now ?? up.stores?.length ?? 0;
    document.getElementById('stores-registry').textContent = status.stores_in_registry;
    document.getElementById('last-sync').textContent = formatDate(status.last_sync);
    if (status.last_sync_error) {
      document.getElementById('last-sync').title = status.last_sync_error;
    }

    // Таблица реестра
    const tbody = document.querySelector('#registry-table tbody');
    tbody.innerHTML = registry.stores
      .map(({ store, last_seen_iso }) =>
        `<tr><td>${store}</td><td>${formatDate(last_seen_iso)}</td></tr>`
      )
      .join('') || '<tr><td colspan="2">Нет данных</td></tr>';

    // Сырой статус (для отладки)
    document.getElementById('status-raw').textContent = JSON.stringify(status, null, 2);
  } catch (e) {
    document.getElementById('status-raw').textContent = 'Ошибка: ' + e.message;
  }
}

refresh();
setInterval(refresh, 10000); // каждые 10 сек
