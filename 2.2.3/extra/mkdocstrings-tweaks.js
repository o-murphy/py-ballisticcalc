// Ensure category headings under classes are consistent and ToC labels are updated
(function () {
  function extractClassFromId(id) {
    if (!id) return '';
    const lastDot = id.lastIndexOf('.');
    const afterDot = lastDot >= 0 ? id.slice(lastDot + 1) : id;
    const firstDash = afterDot.indexOf('-');
    if (firstDash === -1) return afterDot;
    return afterDot.slice(0, firstDash);
  }

  function renameAndPrefix() {
    // Body: iterate class blocks and adjust category headings
    document.querySelectorAll('.doc.doc-class').forEach(cls => {
      const classTitle = cls.querySelector('.doc-heading .doc-class-name, .doc-heading .doc-object-name, .doc-heading code');
      let clsNameFallback = (classTitle?.textContent || '').trim();

      // Handle Methods (was Functions) — may be multiple blocks
      cls.querySelectorAll('h4[id$="-functions"], h3[id$="-functions"], .doc-children h4[id$="-functions"], .doc-children h3[id$="-functions"]').forEach(meth => {
        const id = meth.getAttribute('id') || '';
        let clsName = extractClassFromId(id) || clsNameFallback;
        const targetText = clsName ? `${clsName} Methods` : 'Methods';
        if (!meth.dataset.prefixed || meth.textContent.trim() === 'Functions' || meth.textContent.trim() === 'Methods') {
          meth.dataset.prefixed = '1';
          meth.textContent = targetText;
        }
      });

      // Handle Attributes
      cls.querySelectorAll('h4[id$="-attributes"], h3[id$="-attributes"], .doc-children h4[id$="-attributes"], .doc-children h3[id$="-attributes"]').forEach(attrs => {
        const id = attrs.getAttribute('id') || '';
        let clsName = extractClassFromId(id) || clsNameFallback;
        const targetText = clsName ? `${clsName} Attributes` : 'Attributes';
        if (!attrs.dataset.prefixed || attrs.textContent.trim() === 'Attributes') {
          attrs.dataset.prefixed = '1';
          attrs.textContent = targetText;
        }
      });

      // Fallback: generic category headers under this class
      cls.querySelectorAll('.doc-contents h3, .doc-contents h4, .doc-children h3, .doc-children h4').forEach(h => {
        const raw = (h.textContent || '').trim();
        if (raw === 'Functions') h.textContent = 'Methods';
      });
    });

    // ToC: rename Functions -> Methods by href suffix
    document.querySelectorAll('nav.md-nav a[href$="-functions"], #toc a[href$="-functions"], .md-sidebar a[href$="-functions"]').forEach(a => {
      a.textContent = 'Methods';
    });
  }

  const schedule = () => setTimeout(renameAndPrefix, 0);

  function observeMutations(root) {
    const obs = new MutationObserver(schedule);
    obs.observe(root, { childList: true, subtree: true });
  }

  if (window.document$ && typeof window.document$.subscribe === 'function') {
    window.document$.subscribe(() => {
      schedule();
      observeMutations(document.body);
    });
  } else {
    if (document.readyState === 'complete' || document.readyState === 'interactive') schedule();
    else document.addEventListener('DOMContentLoaded', schedule);
    observeMutations(document.body);
  }
})();
