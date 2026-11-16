(function(){
  function el(t,c,x){var e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e}
  function empty(box,msg){box.innerHTML='';box.appendChild(el('div','empty-state',msg))}
  fetch('/api/conversations').then(function(r){return r.json()}).then(function(d){
    var box=document.getElementById('dash-convs');
    if(!d.conversations.length)return empty(box,'Aucune conversation pour le moment. Posez votre première question à l\'assistant.');
    box.innerHTML='';d.conversations.slice(0,6).forEach(function(c){var a=el('a','row');a.href='/chat?c='+c.id;
      a.appendChild(el('span','',c.title));a.appendChild(el('small','',c.messages+' messages'));box.appendChild(a)})});
  fetch('/api/kbs').then(function(r){return r.json()}).then(function(k){
    var box=document.getElementById('dash-kbs');if(!k.length)return empty(box,'Aucune base chargée.');box.innerHTML='';
    k.forEach(function(x){var r=el('div','row');var l=el('span','',x.label);r.appendChild(l);r.appendChild(el('small','',x.chunks+' passages'));box.appendChild(r)})});
  NexaStatus.then(function(s){
    var box=document.getElementById('dash-status');box.innerHTML='';
    function row(k,v,cls){var r=el('div','row');r.appendChild(el('span','',k));var b=el('span','badge '+(cls||'mute'),v);r.appendChild(b);box.appendChild(r)}
    row('Mode',s.mode==='ia'?'IA activée':'Démo (sans IA)',s.mode==='ia'?'ok':'warn');
    if(s.mode==='ia'){row('Fournisseur · modèle',s.provider+' · '+s.model,'mute');
      row('Connexion',s.connection_verified===true?'Vérifiée':(s.connection_verified===false?'Échec du test':'Non vérifiée'),s.connection_verified===true?'ok':'warn')}
    row('Recherche web',s.web_research?'Activée':'Non configurée','mute')});
})();
