const DATA_URL = `data.json?v=${Date.now()}`;
const REFRESH_MS = 30_000;
let currentData = null;
let query = '';

const ranking = document.querySelector('#ranking');
const statusText = document.querySelector('#refresh-status');
const safeText = (value) => String(value ?? '');

function formatTime(value) {
  if (!value) return '尚未更新';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '尚未更新';
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

function render() {
  if (!currentData) return;
  const characters = [...(currentData.characters || [])]
    .sort((a, b) => Number(b.sales) - Number(a.sales) || Number(a.order) - Number(b.order));
  const filtered = characters.filter((character) => safeText(character.name).toLowerCase().includes(query.toLowerCase()));
  document.querySelector('#character-count').textContent = characters.length;
  document.querySelector('#last-updated').textContent = formatTime(currentData.lastUpdated);
  const verified = characters.some((character) => character.salesVerified);
  document.querySelector('#data-status').textContent = verified ? '已接入有效销量数据' : '初始占位数据';
  document.querySelector('#data-status').className = verified ? 'verified-tag' : '';
  ranking.replaceChildren();
  for (const [index, character] of filtered.entries()) {
    const card = document.createElement('article');
    card.className = 'character-card';
    const rank = document.createElement('div');
    rank.className = `rank${index < 3 ? ' top-three' : ''}`;
    rank.textContent = `#${index + 1}`;
    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    if (character.image) {
      const image = document.createElement('img');
      image.src = character.image;
      image.alt = '';
      image.loading = 'lazy';
      image.onerror = () => { avatar.textContent = safeText(character.name).slice(0, 1); };
      avatar.append(image);
    } else avatar.textContent = safeText(character.name).slice(0, 1);
    const info = document.createElement('div');
    info.className = 'character-info';
    const name = document.createElement('div');
    name.className = 'character-name';
    name.textContent = safeText(character.name);
    const sales = document.createElement('div');
    sales.className = 'sales';
    const count = document.createElement('strong');
    count.textContent = Number(character.sales).toLocaleString('zh-CN');
    sales.append(count, document.createTextNode('票数'));
    const tag = document.createElement('span');
    tag.className = `placeholder-tag${character.salesVerified ? ' verified-tag' : ''}`;
    tag.textContent = character.salesVerified ? '已核验' : '初始占位';
    info.append(name, sales, tag);
    const link = document.createElement('a');
    link.className = 'card-link';
    link.href = character.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = '微店商品 ↗';
    link.setAttribute('aria-label', `打开${safeText(character.name)}的微店商品`);
    card.append(rank, avatar, info, link);
    ranking.append(card);
  }
  document.querySelector('#empty-state').hidden = filtered.length > 0;
}

async function refresh() {
  try {
    const response = await fetch(`${DATA_URL}&t=${Date.now()}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const next = await response.json();
    if (!Array.isArray(next.characters)) throw new Error('Invalid data schema');
    currentData = next;
    render();
    statusText.textContent = `数据已加载 · ${new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`;
    statusText.dataset.error = 'false';
  } catch {
    statusText.textContent = currentData ? '刷新失败，继续显示上次可用数据' : '暂时无法加载数据，请稍后重试';
    statusText.dataset.error = 'true';
  }
}

document.querySelector('#search').addEventListener('input', (event) => { query = event.target.value.trim(); render(); });
refresh();
window.setInterval(refresh, REFRESH_MS);
