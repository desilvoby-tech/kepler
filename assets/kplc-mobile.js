(function () {
  function init() {
    var p = document.getElementById('kplc-panel');
    if (!p) return;
    var vv = window.visualViewport;
    function fit() {
      if (window.innerWidth > 480 || !p.classList.contains('open')) {
        p.style.removeProperty('top'); p.style.removeProperty('height'); return;
      }
      var h = vv ? vv.height : window.innerHeight, top = vv ? vv.offsetTop : 0;
      var kb = (window.innerHeight - h) > 120 || (screen.height - h) > screen.height * 0.4;
      var panelH = kb ? h - 16 : Math.min(h - 16, Math.round(h * 0.78));
      var y = kb ? top + 8 : top + h - panelH - 8;
      p.style.setProperty('height', panelH + 'px', 'important');
      p.style.setProperty('top', y + 'px', 'important');
      var m = document.getElementById('kplc-msgs');
      if (m) m.scrollTop = m.scrollHeight;
    }
    if (vv) { vv.addEventListener('resize', fit); vv.addEventListener('scroll', fit); }
    window.addEventListener('resize', fit);
    window.addEventListener('orientationchange', function () { setTimeout(fit, 300); });
    new MutationObserver(fit).observe(p, { attributes: true, attributeFilter: ['class'] });
    var inp = document.getElementById('kplc-in');
    if (inp) { inp.addEventListener('focus', function () { setTimeout(fit, 250); setTimeout(fit, 600); });
               inp.addEventListener('blur', function () { setTimeout(fit, 250); }); }
    fit();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
