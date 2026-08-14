const drop = document.getElementById('drop');
const fileInput = document.getElementById('fileInput');
const cardsEl = document.getElementById('cards');
const actionsEl = document.getElementById('actions');
const statusEl = document.getElementById('status');
const generateBtn = document.getElementById('generate');
let items = [];
let accessCode = localStorage.getItem('poster2ics_code') || '';
let adminPassword = localStorage.getItem('poster2ics_admin') || '';
const clientTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || '';

async function apiFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (accessCode) headers.set('x-access-code', accessCode);
  if (adminPassword) headers.set('x-admin-password', adminPassword);
  const resp = await fetch(url, { ...options, headers });
  if (resp.status === 403 && !url.startsWith('/api/config')) {
    showAccessOverlay();
  }
  return resp;
}

function applySettingsVisibility(cfg) {
  const adminRow = document.getElementById('adminRow');
  const settingsBody = document.getElementById('settingsBody');
  if (cfg.admin_required && !adminPassword) {
    adminRow.style.display = 'block';
    settingsBody.style.display = 'none';
  } else {
    adminRow.style.display = 'none';
    settingsBody.style.display = 'block';
  }
}

async function unlockAdmin() {
  const pw = document.getElementById('adminInput').value.trim();
  const err = document.getElementById('adminError');
  if (!pw) { err.textContent = '请输入管理员密码'; return; }
  const resp = await fetch('/api/config', { headers: { 'x-admin-password': pw } });
  if (resp.status === 403) { err.textContent = '管理员密码错误'; return; }
  err.textContent = '';
  adminPassword = pw;
  localStorage.setItem('poster2ics_admin', pw);
  await loadKeys();
}

function showAccessOverlay() {
  document.getElementById('accessOverlay').style.display = 'block';
}

function hideAccessOverlay() {
  document.getElementById('accessOverlay').style.display = 'none';
}

async function submitAccess() {
  const code = document.getElementById('accessInput').value.trim();
  const err = document.getElementById('accessError');
  if (!code) { err.textContent = '请输入访问码'; return; }
  accessCode = code;
  localStorage.setItem('poster2ics_code', code);
  const resp = await fetch('/api/config', { headers: { 'x-access-code': code } });
  if (resp.status === 403) {
    err.textContent = '访问码错误';
    return;
  }
  err.textContent = '';
  hideAccessOverlay();
  await loadKeys();
}

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
    resp = await apiFetch('/api/ocr', { method: 'POST', body: fd });
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
  let cardIndex = 0;
  items.forEach((item) => {
    const evs = (item.events && item.events.length)
      ? item.events
      : [{ title: '', start: null, end: null, location: '', description: item.text || '', warnings: [] }];
    evs.forEach((ev, ei) => {
      cardsEl.insertAdjacentHTML('beforeend', `
        <div class="card">
          <div>
            ${ei === 0 ? `<img class="thumb" src="${item.thumb || ''}">` : ''}
            ${ei === 0 ? `<div style="font-size:11px;color:#999;margin-top:4px">${esc(item.filename)}</div>` : ''}
            ${evs.length > 1 ? `<div style="font-size:11px;color:#007aff;margin-top:4px">事件 ${ei + 1}/${evs.length}</div>` : ''}
          </div>
          <div class="fields">
            <div class="pick">
              <input type="checkbox" data-i="${cardIndex}" ${ev.start ? '' : 'disabled'} ${item.error ? '' : 'checked'}>
              <span style="font-size:13px">导入此事件</span>
            </div>
            <label>标题<input class="f-title" data-i="${cardIndex}" value="${esc(ev.title || '')}"></label>
            <label>开始<input class="f-start" type="datetime-local" data-i="${cardIndex}" value="${toLocal(ev.start)}"></label>
            <label>结束<input class="f-end" type="datetime-local" data-i="${cardIndex}" value="${toLocal(ev.end)}"></label>
            <label>地点<input class="f-loc" data-i="${cardIndex}" value="${esc(ev.location || '')}"></label>
            <label>描述<textarea class="f-desc" data-i="${cardIndex}">${esc(ev.description || '')}</textarea></label>
            ${item.error ? `<div class="error">${esc(item.error)}</div>` : ''}
            ${item.source === 'llm' ? '<div class="warn">智能解析（LLM）</div>' : ''}
            ${(ev.warnings || []).map(w => `<div class="warn">${esc(w)}</div>`).join('')}
          </div>
        </div>`);
      cardIndex++;
    });
  });
  actionsEl.style.display = 'block';
  document.getElementById('cardsSection').style.display = 'block';
  updateGenerateState();
}

function updateGenerateState() {
  const total = document.querySelectorAll('.pick input[type=checkbox]').length;
  let anyChecked = false;
  for (let i = 0; i < total; i++) {
    const cb = document.querySelector(`.pick input[data-i="${i}"]`);
    const start = document.querySelector(`.f-start[data-i="${i}"]`);
    if (cb && cb.checked && start && start.value) anyChecked = true;
  }
  generateBtn.disabled = !anyChecked;
}

document.addEventListener('input', () => updateGenerateState());
document.addEventListener('change', () => updateGenerateState());

async function generateIcs() {
  const payload = [];
  const total = document.querySelectorAll('.pick input[type=checkbox]').length;
  for (let i = 0; i < total; i++) {
    const cb = document.querySelector(`.pick input[data-i="${i}"]`);
    if (!cb || !cb.checked) continue;
    const val = sel => { const el = document.querySelector(`.${sel}[data-i="${i}"]`); return el ? el.value : ''; };
    const start = val('f-start');
    const end = val('f-end');
    if (!start) continue;
    payload.push({
      title: val('f-title'),
      start: start + ':00',
      end: end ? end + ':00' : null,
      location: val('f-loc'),
      description: val('f-desc'),
      timezone: clientTimezone,
    });
  }
  if (!payload.length) return;
  const resp = await apiFetch('/api/ics', {
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
  const mobileEvents = payload.map(p => ({
    title: p.title,
    start: p.start,
    end: p.end,
    location: p.location,
    description: (p.description || '').slice(0, 500),
  }));
  const mobileBtn = document.getElementById('mobileImport');
  let url = '/api/ics?e=' + encodeURIComponent(JSON.stringify(mobileEvents));
  if (clientTimezone) url += '&tz=' + encodeURIComponent(clientTimezone);
  if (accessCode) url += '&code=' + encodeURIComponent(accessCode);
  mobileBtn.href = url;
  mobileBtn.style.display = 'inline-block';
  statusEl.textContent = '已生成 events.ics。iPhone 上点绿色按钮可直接进入日历导入（需与电脑同一 WiFi，或使用云端部署地址）';
}

async function saveKey() {
  const body = {};
  const ocrKey = document.getElementById('keyInput').value.trim();
  const llmKey = document.getElementById('llmKeyInput').value.trim();
  const accessCodeInput = document.getElementById('accessCodeInput').value.trim();
  const mode = document.getElementById('modeSelect').value;
  if (ocrKey) body.key = ocrKey;
  if (llmKey) body.llm_key = llmKey;
  if (accessCodeInput) body.access_code = accessCodeInput;
  body.public_mode = mode === 'public';
  if (!Object.keys(body).length) return;
  const resp = await apiFetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  let saved = false;
  let detail = '';
  try { const data = await resp.json(); saved = data.ok; detail = data.detail || ''; } catch (e) {}
  document.getElementById('keyStatus').textContent = saved
    ? '已保存，以后自动生效'
    : (detail || '保存失败（云端部署请用环境变量配置 Key）');
}

async function loadKeys() {
  try {
    const resp = await apiFetch('/api/config');
    if (resp.status === 403) { showAccessOverlay(); return; }
    if (!resp.ok) return;
    const cfg = await resp.json();
    applySettingsVisibility(cfg);
    if (cfg.ocr_key) document.getElementById('keyInput').value = cfg.ocr_key;
    if (cfg.llm_key) document.getElementById('llmKeyInput').value = cfg.llm_key;
    document.getElementById('modeSelect').value = cfg.public_mode ? 'public' : 'private';
    if (cfg.ocr_key || cfg.llm_key) {
      document.getElementById('keyStatus').textContent = '已加载已保存的 Key';
    }
  } catch (e) {}
}
loadKeys();
