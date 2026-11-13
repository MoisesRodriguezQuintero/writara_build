// Ejecuta el JS real del editor de notas contra un DOM simulado.
// Uso:  node tests_js/note_editor.test.js <página-editar-nota.html>   (lo lanza la suite de Django)
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const html = fs.readFileSync(process.argv[2], 'utf8');
const tagsJson = html.match(/<script id="note-tags-data" type="application\/json">(.*?)<\/script>/s)[1];
const scripts = [...html.matchAll(/<script(?![^>]*\bsrc=)(?![^>]*type="application\/json")[^>]*>(.*?)<\/script>/gs)].map(m => m[1]);
const code = scripts.find(s => s.includes('NOTE_SLUG'));
assert.ok(code, 'no se encontró el script del editor de notas');

const make = (id, extra = {}) => Object.assign({
  id, value: '', textContent: '', style: {}, className: '', children: [], listeners: {},
  addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); },
  remove() { this.removed = true; },
  querySelectorAll() { return this.children.filter(c => c.className === 'tag' && !c.removed); },
  insertBefore(node) { this.children.push(node); },
}, extra);
const els = {
  'tags-display': make('tags-display'), 'tag-input': make('tag-input'), 'note-status': make('note-status'),
  'note-content': make('note-content', { value: 'texto de la nota' }), 'note-title': make('note-title', { value: 'Mi nota' }),
  'note-tags-data': make('note-tags-data', { textContent: JSON.parse(JSON.stringify(tagsJson)) }),
};
const docListeners = {}, winListeners = {}, fetches = [], toasts = [];
const ctx = {
  document: { getElementById: id => els[id], createElement: () => make('span'), visibilityState: 'visible',
              addEventListener(t, f) { (docListeners[t] = docListeners[t] || []).push(f); } },
  window: { addEventListener(t, f) { (winListeners[t] = winListeners[t] || []).push(f); } },
  fetch: async (url, opt) => { fetches.push({ url, opt }); return { ok: true, json: async () => ({ saved_at: '12:00:00' }) }; },
  getCookie: () => 'tok', showToast: m => toasts.push(m), console, setTimeout, clearTimeout, JSON,
};
vm.createContext(ctx);
vm.runInContext(code, ctx);

// 1) Las etiquetas existentes se pintan (incluida una con </script>) como texto
const shown = els['tags-display'].children.map(c => c.textContent);
assert.deepStrictEqual(shown.sort(), ["</script>x ×", "o'brien ×"].sort());

// 2) Varias etiquetas separadas por comas
els['tag-input'].value = 'a, b ,,c';
vm.runInContext('addTagFromInput()', ctx);
assert.strictEqual(els['tags-display'].children.filter(c => !c.removed).length, 5);
assert.strictEqual(els['tag-input'].value, '');
assert.strictEqual(els['note-status'].textContent, 'Sin guardar…');

// 3) Guardar envía título, contenido y etiquetas con CSRF
(async () => {
  await vm.runInContext('saveNote()', ctx);
  const sent = fetches.pop();
  assert.ok(sent.url.endsWith('/save/') && sent.opt.method === 'POST');
  assert.strictEqual(sent.opt.headers['X-CSRFToken'], 'tok');
  const body = JSON.parse(sent.opt.body);
  assert.strictEqual(body.title, 'Mi nota'); assert.strictEqual(body.content, 'texto de la nota');
  assert.deepStrictEqual(body.tags.sort(), ['</script>x', 'a', "o'brien", 'b', 'c'].sort());
  assert.ok(els['note-status'].textContent.startsWith('Guardado 12:00:00'));

  // 4) Ctrl+S (Alpine llama a noteEditor().save())
  fetches.length = 0;
  await vm.runInContext('noteEditor().save()', ctx);
  assert.strictEqual(fetches.length, 1, 'Ctrl+S no guardó');

  // 5) Sin cambios, salir de la página no guarda; con cambios sí (keepalive)
  fetches.length = 0;
  winListeners.pagehide.forEach(f => f());
  assert.strictEqual(fetches.length, 0);
  els['note-content'].listeners.input.forEach(f => f());       // el usuario escribe
  assert.strictEqual(els['note-status'].textContent, 'Sin guardar…');
  winListeners.pagehide.forEach(f => f());
  assert.strictEqual(fetches.length, 1); assert.strictEqual(fetches[0].opt.keepalive, true);

  await new Promise(r => setTimeout(r, 20));   // deja terminar el guardado al salir

  // 6) Un fallo del servidor se muestra, no se da por guardado
  ctx.fetch = async () => ({ ok: false, status: 403, json: async () => ({}) });
  await vm.runInContext('saveNote()', ctx);
  assert.strictEqual(els['note-status'].textContent, 'Error al guardar (403)');
  console.log('editor de notas (JS real con DOM simulado): OK');
  process.exit(0);
})().catch(e => { console.error(e); process.exit(1); });
