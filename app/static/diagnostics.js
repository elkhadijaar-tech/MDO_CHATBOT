(function(){
  function el(t,c,x){var e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e}
  function load(){return api('/api/diagnostics').then(function(d){
    var ul=document.getElementById('checks');ul.innerHTML='';
    d.checks.forEach(function(c){var li=el('li');li.innerHTML='<svg class="ic '+(c.ok?'ok':'ko')+'"><use href="#'+(c.ok?'i-check':'i-x')+'"/></svg>';
      var d2=el('div');d2.appendChild(el('strong','',c.name));d2.appendChild(el('small','',c.detail));li.appendChild(d2);ul.appendChild(li)});
    var dl=document.getElementById('cfg');dl.innerHTML='';
    [['Fournisseur',d.config.provider],['Modèle',d.config.model],['Clé API configurée',d.config.api_key_set?'oui':'non'],['Modèle de secours',d.config.fallback_model||'aucun'],
     ['Mot de passe administrateur',d.config.admin_password_set?'défini':'non défini (accès limité à cet ordinateur)'],['Journal',d.config.log_file]].forEach(function(x){dl.appendChild(el('dt','',x[0]));dl.appendChild(el('dd','',x[1]))})
  }).catch(function(e){toast(e.message,'err')})}
  document.getElementById('llm-test').addEventListener('click',function(){var b=this;b.disabled=true;b.textContent='Test en cours…';
    api('/api/diagnostics/llm-test',{method:'POST'}).then(function(r){toast(r.ok?'Connexion IA vérifiée ('+r.ms+' ms)':'Échec : '+r.error,r.ok?'ok':'err');return load()})
      .catch(function(e){toast(e.message,'err')}).finally(function(){b.disabled=false;b.textContent='Tester la connexion IA'})});
  load();
})();
