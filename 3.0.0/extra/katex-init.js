(function () {
  function renderKaTeX(root) {
    if (typeof renderMathInElement !== 'function') return;
    renderMathInElement(root || document.body, {
      delimiters: [
        { left: '$$', right: '$$', display: true },
        { left: '$', right: '$', display: false },
        { left: '\\(', right: '\\)', display: false },
        { left: '\\[', right: '\\]', display: true }
      ],
      throwOnError: false
    });
  }

  // Initial render on first load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { renderKaTeX(document.body); });
  } else {
    renderKaTeX(document.body);
  }

  // Re-render on MkDocs Material page changes (instant navigation)
  if (typeof document$ !== 'undefined' && document$.subscribe) {
    document$.subscribe(function () {
      renderKaTeX(document.body);
    });
  }
})();