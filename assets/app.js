(function(){
  var K = window.KEPLER || {};
  function goal(name){ try{ if(K.ym && window.ym) ym(+K.ym, 'reachGoal', name); }catch(e){} }

  // меню на телефоне
  var burger = document.querySelector('[data-burger]'), nav = document.querySelector('[data-nav]');
  if(burger) burger.addEventListener('click', function(){
    var o = nav.classList.toggle('open'); burger.setAttribute('aria-expanded', o);
  });

  // цели Метрики на кликах
  document.addEventListener('click', function(e){
    var g = e.target.closest('[data-goal]'); if(g) goal(g.getAttribute('data-goal'));
  });

  // окно заявки
  var modal = document.querySelector('[data-modal]');
  document.addEventListener('click', function(e){
    var b = e.target.closest('[data-open-form]');
    if(b && modal){
      var svc = b.getAttribute('data-service') || '';
      modal.querySelector('[name=service]').value = svc;
      modal.showModal ? modal.showModal() : modal.setAttribute('open', '');
      goal('open_form');
      setTimeout(function(){ modal.querySelector('[name=phone]').focus(); }, 50);
    }
    if(e.target.closest('[data-close]') && modal) modal.close();
  });
  if(modal) modal.addEventListener('click', function(e){ if(e.target === modal) modal.close(); });

  // маска телефона +375 (__) ___-__-__
  function mask(v){
    var d = v.replace(/\D/g, '');
    if(d.indexOf('375') === 0) d = d.slice(3); else if(d.indexOf('80') === 0) d = d.slice(2);
    d = d.slice(0, 9);
    var o = '+375';
    if(d.length) o += ' (' + d.slice(0, 2);
    if(d.length >= 2) o += ')';
    if(d.length > 2) o += ' ' + d.slice(2, 5);
    if(d.length > 5) o += '-' + d.slice(5, 7);
    if(d.length > 7) o += '-' + d.slice(7, 9);
    return o;
  }
  document.querySelectorAll('input[type=tel]').forEach(function(i){
    i.addEventListener('focus', function(){ if(!i.value) i.value = '+375 ('; });
    i.addEventListener('input', function(){ i.value = mask(i.value); });
  });

  // отправка заявки
  document.querySelectorAll('[data-form]').forEach(function(f){
    f.addEventListener('submit', function(e){
      e.preventDefault();
      var digits = f.phone.value.replace(/\D/g, '');
      if(digits.length < 12){ f.phone.focus(); f.phone.setCustomValidity('Введите номер полностью'); f.phone.reportValidity(); f.phone.setCustomValidity(''); return; }
      f.page.value = location.pathname;
      var btn = f.querySelector('button[type=submit]'); btn.disabled = true; btn.textContent = 'Отправляем…';
      // заявка уходит в онлайн-чат → бот пересылает операторам в Telegram
      var sid = (Math.random().toString(36) + Math.random().toString(36) + Date.now().toString(36)).replace(/[^a-z0-9]/g, '').slice(0, 24);
      var text = '📝 Заявка с сайта\nТелефон: ' + f.phone.value + '\nКак удобнее: ' + f.how.value +
                 '\nУслуга: ' + (f.service.value || document.title) + '\nСтраница: ' + location.href;
      fetch(K.form, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sid: sid, text: text }) })
        .then(function(r){ if(!r.ok) throw new Error(r.status); done(); })
        .catch(function(){ btn.disabled = false; btn.textContent = 'Жду звонка';
          alertBox('Не удалось отправить. Позвоните нам: ' + (document.querySelector('a[href^="tel:"]') || {}).textContent); });
      function alertBox(t){ var o = f.querySelector('.form-ok'); o.hidden = false; o.style.background = '#fdecec'; o.style.color = '#7f1d1d'; o.textContent = t; }
      function done(){
        f.querySelector('.form-ok').hidden = false;
        btn.textContent = 'Отправлено'; goal('form_sent');
        f.querySelector('.form-row').style.display = 'none';
      }
    });
  });

  // вкладки цен на главной
  document.querySelectorAll('.tabs').forEach(function(t){
    t.addEventListener('click', function(e){
      var b = e.target.closest('[data-tab]'); if(!b) return;
      var box = t.parentNode;
      t.querySelectorAll('[data-tab]').forEach(function(x){ x.setAttribute('aria-selected', x === b); });
      box.querySelectorAll('[data-pane]').forEach(function(p){ p.hidden = p.getAttribute('data-pane') !== b.getAttribute('data-tab'); });
    });
  });
})();
