(function(){
  var box=document.getElementById('messages'),form=document.getElementById('chat-form'),input=document.getElementById('input'),
      langSel=document.getElementById('lang'),modeSel=document.getElementById('mode'),sendBtn=document.getElementById('send'),
      welcome=document.getElementById('welcome'),thread=null,busy=false,lastUser='';
  var MODE_LABEL={ia:'IA',demo:'Mode démo · extrait de la base',regle:'Règle de la base',calcul:'Calcul programmé (formules du cours)',demo_secours:'IA indisponible · extrait de la base'};
  var KB_LABEL={onboarding:'Administratif ESTC',cours:'Cours'};
  function ic(id){return '<svg class="ic"><use href="#'+id+'"/></svg>'}
  ['lang','mode'].forEach(function(k){var el=document.getElementById(k);try{var v=localStorage.getItem('nexa-'+k);if(v)el.value=v}catch(e){}
    el.addEventListener('change',function(){try{localStorage.setItem('nexa-'+k,el.value)}catch(e){}})});
  function ensureThread(){if(welcome){welcome.remove();welcome=null}if(!thread){thread=document.createElement('div');thread.className='thread';box.appendChild(thread)}return thread}
  function scroll(){box.scrollTop=box.scrollHeight}
  function badge(text,cls){var b=document.createElement('span');b.className='badge '+(cls||'');b.textContent=text;return b}
  function iconBtn(id,label,fn){var b=document.createElement('button');b.type='button';b.className='btn-icon';b.title=label;b.setAttribute('aria-label',label);b.innerHTML=ic(id);b.addEventListener('click',fn);return b}
  function copy(text){var done=function(){toast('Copié dans le presse-papiers','ok')};
    if(navigator.clipboard&&window.isSecureContext)navigator.clipboard.writeText(text).then(done,function(){toast('Copie impossible','err')});
    else{var t=document.createElement('textarea');t.value=text;document.body.appendChild(t);t.select();try{document.execCommand('copy');done()}catch(e){toast('Copie impossible','err')}t.remove()}}
  function userMsg(text){
    var m=document.createElement('div');m.className='msg user';var main=document.createElement('div');main.className='msg-main';
    var b=document.createElement('div');b.className='bubble-user';b.setAttribute('dir','auto');b.textContent=text;
    var a=document.createElement('div');a.className='actions';
    a.appendChild(iconBtn('i-edit','Modifier la question',function(){input.value=text;input.focus();resize()}));
    a.appendChild(iconBtn('i-copy','Copier',function(){copy(text)}));
    main.appendChild(b);main.appendChild(a);m.appendChild(main);ensureThread().appendChild(m);scroll();return m}
  function botMsg(d){
    var m=document.createElement('div');m.className='msg bot';
    var av=document.createElement('div');av.className='avatar';av.innerHTML='<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M9 23V9l14 14V9" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    var main=document.createElement('div');main.className='msg-main';
    var body=document.createElement('div');body.className='md';body.setAttribute('dir','auto');body.appendChild(NexaMD.render(d.content));main.appendChild(body);
    var meta=document.createElement('div');meta.className='meta';
    if(d.mode&&MODE_LABEL[d.mode])meta.appendChild(badge(d.mode==='ia'&&d.model?'IA · '+d.model:MODE_LABEL[d.mode],d.mode==='ia'?'ok':(d.mode==='demo_secours'?'warn':'mute')));
    if(d.kb)meta.appendChild(badge(KB_LABEL[d.kb]||d.kb));
    var det=d.source_details||[];
    if(det.length){var allOk=det.every(function(s){return/^VERIFIED/.test(s.verification||'')});
      meta.appendChild(allOk?badge('Base vérifiée','ok'):badge('Contenu à vérifier','warn'))}
    if(meta.childNodes.length)main.appendChild(meta);
    if(d.sources&&d.sources.length){var dt=document.createElement('details');dt.className='src-box';
      var sm=document.createElement('summary');sm.textContent='Sources ('+d.sources.length+')';dt.appendChild(sm);
      var ul=document.createElement('ul');d.sources.forEach(function(s,i){var li=document.createElement('li');var x=det[i];
        li.textContent=s+(x&&x.location&&x.location!==s?' — '+x.location:'');ul.appendChild(li)});dt.appendChild(ul);main.appendChild(dt)}
    var a=document.createElement('div');a.className='actions';
    a.appendChild(iconBtn('i-copy','Copier la réponse',function(){copy(d.content)}));
    var regen=iconBtn('i-refresh','Régénérer',function(){if(lastUser)send(lastUser)});a.appendChild(regen);
    var up=iconBtn('i-up','Réponse utile',function(){fb(1)}),down=iconBtn('i-down','Réponse à améliorer',function(){fb(-1)});
    function mark(v){up.classList.toggle('on',v===1);down.classList.toggle('on',v===-1)}
    function fb(v){if(!d.id)return;var cur=up.classList.contains('on')?1:(down.classList.contains('on')?-1:0);var nv=cur===v?0:v;
      api('/api/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message_id:d.id,value:nv})})
        .then(function(){mark(nv);toast(nv?'Merci pour votre retour':'Retour retiré','ok')}).catch(function(e){toast(e.message,'err')})}
    mark(d.feedback);if(d.id){a.appendChild(up);a.appendChild(down)}
    main.appendChild(a);m.appendChild(av);m.appendChild(main);return m}
  function setLast(){var all=thread?thread.querySelectorAll('.msg.bot'):[];[].forEach.call(all,function(x){x.classList.remove('last')});if(all.length)all[all.length-1].classList.add('last')}
  function typing(){var m=document.createElement('div');m.className='msg bot';m.innerHTML='<div class="avatar"><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M9 23V9l14 14V9" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg></div><div class="msg-main"><div class="typing" role="status" aria-label="L\'assistant écrit"><i></i><i></i><i></i></div></div>';ensureThread().appendChild(m);scroll();return m}
  function send(text){
    text=(text||'').trim();if(!text||busy)return;busy=true;sendBtn.disabled=true;lastUser=text;
    userMsg(text);input.value='';resize();var wait=typing();
    api('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,lang:langSel.value,mode:modeSel.value})})
      .then(function(r){wait.replaceWith(botMsg({id:r.message_id,content:r.answer,mode:r.mode,model:r.model,kb:r.kb,sources:r.sources,source_details:r.source_details}));setLast();scroll();window.loadRecent()})
      .catch(function(e){wait.replaceWith(botMsg({content:'**Erreur :** '+e.message}));setLast()})
      .finally(function(){busy=false;sendBtn.disabled=false;input.focus()})}
  function resize(){input.style.height='auto';input.style.height=Math.min(input.scrollHeight,200)+'px'}
  input.addEventListener('input',resize);
  input.addEventListener('keydown',function(e){if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();form.requestSubmit()}});
  form.addEventListener('submit',function(e){e.preventDefault();send(input.value)});
  document.getElementById('chips').addEventListener('click',function(e){if(e.target.tagName==='BUTTON')send(e.target.textContent)});
  function loadHistory(){return fetch('/api/history').then(function(r){return r.json()}).then(function(h){
    h.forEach(function(m){if(m.role==='user'){userMsg(m.content);lastUser=m.content}else botMsg&&ensureThread().appendChild(botMsg({id:m.id,content:m.content,mode:m.mode,model:m.model,kb:m.kb,sources:m.sources,feedback:m.feedback}))});
    setLast();scroll()})}
  var p=new URLSearchParams(location.search),pre=Promise.resolve();
  if(p.get('new'))pre=api('/api/reset',{method:'POST'});
  else if(p.get('c'))pre=api('/api/conversations/'+encodeURIComponent(p.get('c'))+'/open',{method:'POST'}).catch(function(e){toast(e.message,'err')});
  if(p.get('mode')&&['auto','cours','admin'].indexOf(p.get('mode'))>=0)modeSel.value=p.get('mode');
  pre.then(loadHistory).then(function(){var q=p.get('q');if(q)send(q);if(p.toString())history.replaceState(null,'','/chat');window.loadRecent()});
  input.focus();
})();
