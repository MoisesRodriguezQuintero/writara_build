/*
 * Writara · paginación visual.
 *
 * Divide un documento (el editor Quill o el HTML exportado) en "hojas" del
 * tamaño elegido SIN tocar su contenido: cuando un bloque (párrafo, título,
 * elemento de lista…) no cabe en lo que queda de la página, se le añade un
 * margin-top inline para empujarlo al inicio de la página siguiente. Las hojas
 * se dibujan con un fondo CSS (ver writara.css / export.html).
 *
 * Limitación conocida: un bloque más alto que el área útil de una página
 * (p. ej. un bloque de código enorme) no se parte; se desborda sobre el hueco.
 * La paginación definitiva de PDF/ODT la hacen WeasyPrint / LibreOffice.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.WritaraPages = api;
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var MM = 96 / 25.4;          // px CSS por milímetro
  var EPS = 0.5;               // tolerancia de medición (px)
  var MARK = 'data-pg';        // atributo que marca los bloques empujados

  /** page = {w, h, margin} en mm → medidas en px. */
  function geometry(page, gap) {
    return {
      pageW: page.w * MM,
      pageH: page.h * MM,
      margin: page.margin * MM,
      gap: gap == null ? 28 : gap
    };
  }

  /**
   * Núcleo puro (sin DOM). `units` = [{top, height}] con las posiciones
   * NATURALES (sin empujes) de cada bloque, en px desde el borde superior.
   * Devuelve cuánto empujar cada bloque y cuántas páginas resultan.
   */
  function computeLayout(units, g) {
    var period = g.pageH + g.gap;
    var contentH = g.pageH - 2 * g.margin;
    var shift = 0;
    var extras = [];
    for (var i = 0; i < units.length; i++) {
      var top = units[i].top + shift;
      var bottom = top + units[i].height;
      var page = Math.max(0, Math.floor((top + EPS) / period));
      var limit = page * period + g.pageH - g.margin;   // fin del área útil
      var extra = 0;
      if (bottom > limit + EPS && (units[i].height <= contentH || top >= limit)) {
        extra = (page + 1) * period + g.margin - top;   // inicio útil de la siguiente
        shift += extra;
      }
      extras.push(extra);
    }
    var last = units[units.length - 1];
    var endBottom = last ? last.top + shift + last.height : 0;
    var pages = Math.max(1, Math.floor((endBottom - 1) / period) + 1);
    return {
      extras: extras,
      pages: pages,
      totalHeight: pages * g.pageH + (pages - 1) * g.gap
    };
  }

  /** Bloques que se paginan: hijos directos; en listas, cada <li>. */
  function unitsOf(el) {
    var out = [];
    for (var i = 0; i < el.children.length; i++) {
      var c = el.children[i];
      if (c.tagName === 'UL' || c.tagName === 'OL') {
        for (var j = 0; j < c.children.length; j++) out.push(c.children[j]);
      } else {
        out.push(c);
      }
    }
    return out;
  }

  /** Quita los empujes (deja el documento en su flujo natural). */
  function clear(el) {
    var marked = el.querySelectorAll('[' + MARK + ']');
    for (var i = 0; i < marked.length; i++) {
      marked[i].removeAttribute(MARK);
      marked[i].style.removeProperty('margin-top');
      if (!marked[i].getAttribute('style')) marked[i].removeAttribute('style');
    }
    el.style.minHeight = '';
  }

  /**
   * Recalcula la paginación de `el` (necesita position:relative y
   * box-sizing:border-box, con el margen de página como padding).
   * Devuelve {pages, totalHeight}.
   */
  function layout(el, g) {
    clear(el);
    el.style.width = g.pageW + 'px';
    el.style.setProperty('--page-h', g.pageH + 'px');
    el.style.setProperty('--page-margin', g.margin + 'px');
    el.style.setProperty('--page-gap', g.gap + 'px');

    var els = unitsOf(el);
    var units = els.map(function (e) { return { top: e.offsetTop, height: e.offsetHeight }; });
    var res = computeLayout(units, g);

    for (var i = 0; i < els.length; i++) {
      if (res.extras[i] > 0) {
        // Hueco natural entre el bloque anterior y este: los márgenes colapsan,
        // así que el margin-top nuevo debe SUMAR el empuje a ese hueco.
        var natural = i === 0 ? 0 :
          Math.max(0, units[i].top - (units[i - 1].top + units[i - 1].height));
        els[i].style.marginTop = (natural + res.extras[i]) + 'px';
        els[i].setAttribute(MARK, '1');
      }
    }
    el.style.minHeight = res.totalHeight + 'px';
    return { pages: res.pages, totalHeight: res.totalHeight };
  }

  /**
   * Reduce la hoja (transform) si no cabe en `availWidth` y la centra.
   * Devuelve la escala aplicada.
   */
  function fit(el, availWidth, g, edge) {
    edge = edge == null ? 20 : edge;
    var scale = Math.min(1, Math.max(0.25, (availWidth - 2 * edge) / g.pageW));
    el.style.transformOrigin = 'top left';
    el.style.transform = scale < 1 ? 'scale(' + scale + ')' : '';
    el.style.marginLeft = Math.max(edge, (availWidth - g.pageW * scale) / 2) + 'px';
    return scale;
  }

  /** Número de página (1…) de un bloque ya maquetado. */
  function pageOf(blockEl, g) {
    return Math.floor((blockEl.offsetTop + EPS) / (g.pageH + g.gap)) + 1;
  }

  /** Número de página para una coordenada y (px de layout) dentro de la hoja. */
  function pageAtY(y, g) {
    return Math.max(0, Math.floor((y + EPS) / (g.pageH + g.gap))) + 1;
  }

  return {
    MM: MM, geometry: geometry, computeLayout: computeLayout, unitsOf: unitsOf,
    clear: clear, layout: layout, fit: fit, pageOf: pageOf, pageAtY: pageAtY
  };
});
