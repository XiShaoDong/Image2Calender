const drop = document.getElementById('drop');
const fileInput = document.getElementById('fileInput');
const cardsEl = document.getElementById('cards');
const actionsEl = document.getElementById('actions');
const statusEl = document.getElementById('status');
const generateBtn = document.getElementById('generate');
let items = [];

drop.addEventListener('click', () => fileInput.click());
drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('dragover'); });
drop.addEventListener('dragleave', () => drop.classList.remove('dragover'));
drop.addEventListener('drop', e => { e.preventDefault(); drop.classList.remove('dragover'); handleFiles(e.dataTransfer.files); });
fileInput.addEventListener('change', () => { handleFiles(fileInput.files); fileInput.value = ''; });

async function compressImage(file) {
  if (file.size <= 1024 * 1024) return file;
  const img = await createImageBitmap(file);
  const scale = Math.min(1, 2000 / Math.max(img.width, img.height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(img.width * scale);
  canvas.height = Math.round(img.height * scale);
  canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
  let blob = await new Promise(r => canvas.toBlob(r, 'image/jpeg', 0.85));
  let guard = 0;
  while (blob.size > 1024 * 1024 && guard < 5) {
    blob = await new Promise(r => canvas.toBlob(r, 'image/jpeg', 0.4));
    guard++;
  }
  return new File([blob], file.name.replace(/\.[^.]+$/, '.jpg'), { type: 'image/jpeg' });
}

async function handleFiles(files) {
  statusEl.textContent = `正在处理 ${files.length} 张图片...`;
  const fd = new FormData();
  const thumbs = [];
  for (const f of files) {
    fd.append('files', await compressImage(f));
    thumbs.push(URL.createObjectURL(f));
  }
  let resp;
  try {
    resp = await fetch('/api/ocr', { method: 'POST', body: fd });
  } catch (e) {
    statusEl.textContent = '请求失败：' + e.message;
    return;
  }
  const data = await resp.json();
  if (resp.status !== 200) { statusEl.textContent = data.detail || 'OCR 请求失败'; return; }
  data.items.forEach((it, idx) => { it.thumb = thumbs[idx] || ''; });
  items = data.items;
  renderCards();
  statusEl.textContent = '处理完成，请确认每张卡片的信息后生成';
}

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function toLocal(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d)) return '';
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function renderCards() {
  cardsEl.innerHTML = '';
  items.forEach((item, i) => {
    const ev = item.event || {};
    cardsEl.insertAdjacentHTML('beforeend', `
      <div class="card">
        <div>
          <img class="thumb" src="${item.thumb || ''}">
          <div style="font-size:11px;color:#999;margin-top:4px">${esc(item.filename)}</div>
        </div>
        <div class="fields">
          <div class="pick">
            <input type="checkbox" data-i="${i}" ${ev.start ? '' : 'disabled'} ${item.error ? '' : 'checked'}>
            <span style="font-size:13px">导入此事件</span>
          </div>
          <label>标题<input class="f-title" data-i="${i}" value="${esc(ev.title || '')}"></label>
          <label>开始<input class="f-start" type="datetime-local" data-i="${i}" value="${toLocal(ev.start)}"></label>
          <label>结束<input class="f-end" type="datetime-local" data-i="${i}" value="${toLocal(ev.end)}"></label>
          <label>地点<input class="f-loc" data-i="${i}" value="${esc(ev.location || '')}"></label>
          <label>描述<textarea class="f-desc" data-i="${i}">${esc(ev.description || '')}</textarea></label>
          ${item.error ? `<div class="error">${esc(item.error)}</div>` : ''}
          ${(ev.warnings || []).map(w => `<div class="warn">${esc(w)}</div>`).join('')}
        </div>
      </div>`);
  });
  actionsEl.style.display = 'block';
  updateGenerateState();
}

function updateGenerateState() {
  const anyChecked = items.some((it, i) => {
    const cb = document.querySelector(`.pick input[data-i="${i}"]`);
    const start = document.querySelector(`.f-start[data-i="${i}"]`);
    return cb && cb.checked && start && start.value;
  });
  generateBtn.disabled = !anyChecked;
}

document.addEventListener('input', () => updateGenerateState());
document.addEventListener('change', () => updateGenerateState());

async function generateIcs() {
  const payload = [];
  items.forEach((it, i) => {
    const cb = document.querySelector(`.pick input[data-i="${i}"]`);
    if (!cb || !cb.checked) return;
    const val = sel => { const el = document.querySelector(`.${sel}[data-i="${i}"]`); return el ? el.value : ''; };
    const start = val('f-start');
    const end = val('f-end');
    if (!start) return;
    payload.push({
      title: val('f-title'),
      start: start + ':00',
      end: end ? end + ':00' : null,
      location: val('f-loc'),
      description: val('f-desc'),
    });
  });
  if (!payload.length) return;
  const resp = await fetch('/api/ics', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) { statusEl.textContent = '生成失败'; return; }
  const blob = await resp.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'events.ics';
  a.click();
  URL.revokeObjectURL(a.href);
  statusEl.textContent = '已下载 events.ics，传到 iPhone 点开即可导入';
}

async function saveKey() {
  const key = document.getElementById('keyInput').value.trim();
  if (!key) return;
  const resp = await fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key }),
  });
  document.getElementById('keyStatus').textContent = resp.ok ? '已保存' : '保存失败';
}
