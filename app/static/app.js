(function(){
  var root=document.documentElement,appEl=document.getElementById('app');
  function ic(id){return '<svg class="ic"><use href="#'+id+'"/></svg>'}
  window.toast=function(msg,type){var t=document.createElement('div');t.className='toast '+(type||'');t.textContent=msg;
    document.getElementById('toasts').appendChild(t);setTimeout(function(){t.remove()},3200)};
  window.api=function(url,opts){opts=opts||{};opts.headers=Object.assign({'X-Requested-With':'fetch'},opts.headers||{});
    return fetch(url,opts).then(function(r){return r.json().catch(function(){return{}}).then(function(j){if(!r.ok)throw new Error(j.error||('Erreur '+r.status));return j})})};
  function setThemeIcon(){var b=document.getElementById('theme-btn');if(b)b.innerHTML=ic(root.getAttribute('data-theme')==='dark'?'i-sun':'i-moon')}
  setThemeIcon();
  document.getElementById('theme-btn').addEventListener('click',function(){
    var n=root.getAttribute('data-theme')==='dark'?'light':'dark';root.setAttribute('data-theme',n);
    try{localStorage.setItem('nexa-theme',n)}catch(e){}setThemeIcon()});
  document.getElementById('collapse-btn').addEventListener('click',function(){
    var c=root.getAttribute('data-collapsed')==='1';
    if(c)root.removeAttribute('data-collapsed');else root.setAttribute('data-collapsed','1');
    try{localStorage.setItem('nexa-collapsed',c?'0':'1')}catch(e){}});
  function nav(open){appEl.classList.toggle('nav-open',open);document.getElementById('burger').setAttribute('aria-expanded',open)}
  document.getElementById('burger').addEventListener('click',function(){nav(!appEl.classList.contains('nav-open'))});
  document.getElementById('scrim').addEventListener('click',function(){nav(false)});
  document.addEventListener('keydown',function(e){if(e.key==='Escape')nav(false)});
  window.NexaStatus=fetch('/api/status').then(function(r){return r.json()}).then(function(s){
    var p=document.getElementById('mode-pill');
    if(s.mode==='ia'){p.textContent='IA · '+s.provider+' · '+s.model;p.className='pill lbl ok'}
    else{p.textContent='MODE DÉMO (sans IA)';p.className='pill lbl warn';var b=document.getElementById('demo-banner');if(b)b.hidden=false;
      var n=document.getElementById('ai-note');if(n)n.hidden=false}
    return s}).catch(function(){return{}});
  window.loadRecent=function(){
    return fetch('/api/conversations').then(function(r){return r.json()}).then(function(d){
      var box=document.getElementById('recent');box.innerHTML='';
      if(!d.conversations.length){box.innerHTML='<div class="empty">Aucune conversation</div>';return d}
      d.conversations.slice(0,8).forEach(function(c){
        var row=document.createElement('div');row.className='rc'+(c.id===d.current?' cur':'');
        var a=document.createElement('a');a.href='/chat?c='+c.id;a.textContent=c.title;a.title=c.title;
        var b=document.createElement('button');b.type='button';b.setAttribute('aria-label','Supprimer la conversation');b.innerHTML=ic('i-trash');
        b.addEventListener('click',function(){if(!confirm('Supprimer cette conversation ?'))return;
          window.api('/api/conversations/'+c.id,{method:'DELETE'}).then(function(){toast('Conversation supprimée','ok');
            if(location.pathname==='/chat'&&c.id===d.current)location.href='/chat?new=1';else window.loadRecent()}).catch(function(e){toast(e.message,'err')})});
        row.appendChild(a);row.appendChild(b);box.appendChild(row)});return d}).catch(function(){})};
  window.loadRecent();
})();
