/* Формы Elementor на статической копии kepler.by.
   Вид и поля — как в WordPress; отправка — в тот же канал, что и онлайн-чат:
   заявка уходит боту, бот пересылает операторам в Telegram. */
(function () {
  var API = '/?rest_route=/kpl/v1/send';
  var YM = 100574248;

  function goal(n) { try { window.ym && ym(YM, 'reachGoal', n); } catch (e) {} }

  function label(f, el) {
    if (el.type === 'tel') return 'Телефон';
    var l = el.id && f.querySelector('label[for="' + el.id + '"]');
    var t = (l && l.textContent) || el.getAttribute('placeholder') || el.name || '';
    return t.replace(/\s+/g, ' ').trim().replace(/:$/, '');
  }

  function message(f, ok, text) {
    var old = f.querySelector('.elementor-message'); if (old) old.remove();
    var m = document.createElement('div');
    m.className = 'elementor-message ' + (ok ? 'elementor-message-success' : 'elementor-message-danger');
    m.setAttribute('role', 'alert');
    m.textContent = text;
    f.appendChild(m);
  }

  document.addEventListener('submit', function (e) {
    var f = e.target;
    if (!f || !f.matches || !f.matches('form.elementor-form')) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    if (f.reportValidity && !f.reportValidity()) return;
    var lines = [], phoneOk = true;
    f.querySelectorAll('input, select, textarea').forEach(function (el) {
      if (el.type === 'hidden' || el.type === 'submit' || el.type === 'button' || !el.name) return;
      if ((el.type === 'checkbox' || el.type === 'radio') && !el.checked) return;
      var v = (el.value || '').trim(); if (!v) return;
      if (el.tagName === 'SELECT' && el.selectedIndex === 0 && v === label(f, el)) return;
      if (el.type === 'tel' && v.replace(/\D/g, '').length < 12) phoneOk = false;
      lines.push(label(f, el) + ': ' + v);
    });
    var tel = f.querySelector('input[type=tel]');
    if (!phoneOk && tel) {
      tel.setCustomValidity('Введите номер полностью'); tel.reportValidity(); tel.setCustomValidity('');
      return;
    }
    var btn = f.querySelector('[type=submit]');
    f.classList.add('elementor-form-waiting'); if (btn) btn.disabled = true;
    var sid = (Math.random().toString(36) + Math.random().toString(36) + Date.now().toString(36)).replace(/[^a-z0-9]/g, '').slice(0, 24);
    var text = '📝 Заявка с сайта' + (f.getAttribute('name') ? ' («' + f.getAttribute('name') + '»)' : '') + '\n' +
               lines.join('\n') + '\nСтраница: ' + location.href;
    fetch(API, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sid: sid, text: text }) })
      .then(function (r) { if (!r.ok) throw new Error(r.status);
        message(f, true, 'Спасибо! Заявка принята — скоро перезвоним.'); f.reset(); goal('form_sent'); })
      .catch(function () {
        message(f, false, 'Не удалось отправить. Позвоните нам: +375 (29) 321-33-33'); })
      .then(function () { f.classList.remove('elementor-form-waiting'); if (btn) btn.disabled = false; });
  }, true);
})();
