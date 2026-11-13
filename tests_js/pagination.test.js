// Ejecutar con:  node tests_js/pagination.test.js
const assert = require('assert');
const P = require('../main/static/js/pagination.js');

const g = P.geometry({ w: 148, h: 210, margin: 18 }, 28);   // A5
const period = g.pageH + g.gap, contentH = g.pageH - 2 * g.margin;
const approx = (a, b, m) => assert.ok(Math.abs(a - b) < 0.01, `${m || ''} ${a} != ${b}`);

// Bloques de 100 px con 10 px de hueco, empezando en el margen superior
function flow(n, h = 100, gapBetween = 10) {
  return Array.from({ length: n }, (_, i) => ({ top: g.margin + i * (h + gapBetween), height: h }));
}

// 1) Un texto corto cabe en una sola página y no se empuja nada
let r = P.computeLayout(flow(3), g);
assert.deepStrictEqual(r.extras, [0, 0, 0]); assert.strictEqual(r.pages, 1);
approx(r.totalHeight, g.pageH);

// 2) Ningún bloque cruza el final del área útil de su página
const units = flow(40, 60, 10);
r = P.computeLayout(units, g);
let shift = 0;
units.forEach((u, i) => {
  shift += r.extras[i];
  const top = u.top + shift, bottom = top + u.height;
  const page = Math.floor((top + 0.5) / period);
  assert.ok(bottom <= page * period + g.pageH - g.margin + 0.5, `bloque ${i} cruza la página ${page}`);
  assert.ok(top >= page * period + g.margin - 0.5, `bloque ${i} empieza en el margen`);
});
assert.ok(r.pages > 1);

// 3) Un bloque empujado empieza exactamente en el margen superior de la página siguiente
const two = [{ top: g.margin, height: contentH - 20 }, { top: g.margin + contentH - 10, height: 50 }];
r = P.computeLayout(two, g);
assert.strictEqual(r.extras[0], 0);
approx(two[1].top + r.extras[1], period + g.margin, 'segundo bloque');
assert.strictEqual(r.pages, 2);
approx(r.totalHeight, 2 * g.pageH + g.gap);

// 4) Un bloque más alto que la página no se empuja si ya empezó dentro de ella (se desborda)
r = P.computeLayout([{ top: g.margin, height: 30 }, { top: g.margin + 40, height: contentH + 200 }], g);
assert.deepStrictEqual(r.extras, [0, 0]);

// 5) Un bloque que empieza dentro del hueco entre páginas pasa al inicio de la siguiente
r = P.computeLayout([{ top: g.margin, height: contentH + 60 }, { top: g.margin + contentH + 70, height: 40 }], g);
assert.strictEqual(r.extras[0], 0);
assert.ok(r.extras[1] > 0);
const nextTop = g.margin + contentH + 70 + r.extras[1];
approx(nextTop % period, g.margin, 'tras desbordar');

// 6) Documento vacío: una página
r = P.computeLayout([], g);
assert.strictEqual(r.pages, 1); assert.deepStrictEqual(r.extras, []);

// 7) Los empujes son acumulativos: tras N páginas el último bloque está en la página correcta
const many = flow(200, 40, 10);
r = P.computeLayout(many, g);
const total = r.extras.reduce((a, b) => a + b, 0);
const lastTop = many[many.length - 1].top + total;
assert.strictEqual(Math.floor((lastTop + 0.5) / period) + 1, r.pages);

// 8) Distintos tamaños de página producen distinta cantidad de páginas (A6 > A5 > A4 > A3)
const count = (page) => P.computeLayout(
  Array.from({ length: 120 }, (_, i) => ({ top: P.geometry(page).margin + i * 50, height: 40 })),
  P.geometry(page)).pages;
const pages = { A6: count({ w: 105, h: 148, margin: 12 }), A5: count({ w: 148, h: 210, margin: 18 }),
                A4: count({ w: 210, h: 297, margin: 20 }), A3: count({ w: 297, h: 420, margin: 25 }) };
assert.ok(pages.A6 > pages.A5 && pages.A5 > pages.A4 && pages.A4 > pages.A3, JSON.stringify(pages));

console.log('pagination.js: todos los tests OK', JSON.stringify(pages));
