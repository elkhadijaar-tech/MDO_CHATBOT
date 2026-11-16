(function(){
  var dlg=document.getElementById('dlg'),tbody=document.querySelector('#src-table tbody');
  function el(t,c,x){var e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e}
  function openDlg(title,bodyNode,buttons){document.getElementById('dlg-title').textContent=title;var b=document.getElementById('dlg-body');b.innerHTML='';b.appendChild(bodyNode);
    var f=document.getElementById('dlg-foot');f.innerHTML='';(buttons||[]).forEach(function(x){f.appendChild(x)});if(!dlg.open)dlg.showModal()}
  document.getElementById('dlg-close').addEventListener('click',function(){dlg.close()});
  function reportNode(r){var w=el('div');var dl=el('dl','dl');
    [['Statut',r.status],['Format',r.format],['Passages indexés',r.chunks_indexed],['Doublons ignorés',r.duplicates_skipped],['Vides ignorés',r.empty_skipped],['Taille (octets)',r.size_bytes]].forEach(function(x){
      if(x[1]===undefined||x[1]===null)return;dl.appendChild(el('dt','',x[0]));dl.appendChild(el('dd','',String(x[1])))});w.appendChild(dl);
    if(r.error)w.appendChild(el('p','err',r.error));if(r.warning)w.appendChild(el('p','note','⚠ '+r.warning));if(r.schema_changed)w.appendChild(el('p','note','⚠ Le schéma de la base a changé depuis le dernier import.'));
    var pre=el('pre','',JSON.stringify(r,null,2));pre.style.marginTop='12px';w.appendChild(pre);return w}
  function btn(label,cls,fn){var b=el('button','btn btn-sm '+cls,label);b.type='button';b.addEventListener('click',fn);return b}
  function load(){return api('/api/knowledge').then(function(d){
    var cards=document.getElementById('kb-cards');cards.innerHTML='';var dl=document.getElementById('kb-list');dl.innerHTML='';
    d.kbs.forEach(function(k){var c=el('article','card');c.appendChild(el('span','badge '+(k.builtin?'':'mute'),k.builtin?'Intégrée':'Importée'));
      c.appendChild(el('h4','',k.label));c.appendChild(el('p','',k.name+' · '+k.chunks+' passages'));cards.appendChild(c);var o=el('option');o.value=k.name;dl.appendChild(o)});
    tbody.innerHTML='';
    if(!d.sources.length){var tr=el('tr'),td=el('td','empty-state','Aucune source.');td.colSpan=8;tr.appendChild(td);tbody.appendChild(tr)}
    d.sources.forEach(function(s){var tr=el('tr');
      [s.name,s.kb,s.source_type||'—',s.chunk_count,s.duplicate_count].forEach(function(v){tr.appendChild(el('td','',String(v)))});
      var st=el('td');st.appendChild(el('span','badge '+(s.status==='indexed'?'ok':'err'),s.status==='indexed'?'Indexée':'Échec'));tr.appendChild(st);
      tr.appendChild(el('td','',(s.updated_at||'').slice(0,16)));
      var ac=el('td');
      ac.appendChild(btn('Rapport','btn-ghost',function(){api('/api/knowledge/sources/'+s.id+'/report').then(function(r){openDlg('Rapport d\'ingestion — '+s.name,reportNode(r.report),[btn('Fermer','btn-ghost',function(){dlg.close()})])}).catch(function(e){toast(e.message,'err')})}));
      ac.appendChild(document.createTextNode(' '));
      ac.appendChild(btn(s.builtin?'Recharger':'Réindexer','btn-ghost',function(){api('/api/knowledge/sources/'+s.id+'/reindex',{method:'POST'}).then(function(){toast('Source réindexée','ok');load()}).catch(function(e){toast(e.message,'err')})}));
      if(!s.builtin){ac.appendChild(document.createTextNode(' '));
        ac.appendChild(btn('Retirer','btn-ghost',function(){var p=el('p','','Retirer « '+s.name+' » de l\'index ? Le fichier original est conservé sur le disque.');
          openDlg('Confirmer le retrait',p,[btn('Annuler','btn-ghost',function(){dlg.close()}),btn('Retirer','btn-danger',function(){
            api('/api/knowledge/sources/'+s.id,{method:'DELETE'}).then(function(){dlg.close();toast('Source retirée','ok');load()}).catch(function(e){toast(e.message,'err')})})])}))}
      tr.appendChild(ac);tbody.appendChild(tr)})}).catch(function(e){toast(e.message,'err')})}
  document.getElementById('import-form').addEventListener('submit',function(e){e.preventDefault();
    var f=document.getElementById('f-file').files[0];if(!f)return;var fd=new FormData();fd.append('file',f);fd.append('kb',document.getElementById('f-kb').value);fd.append('label',document.getElementById('f-label').value);
    var b=document.getElementById('f-submit');b.disabled=true;b.textContent='Import en cours…';
    api('/api/knowledge/import',{method:'POST',body:fd}).then(function(r){toast('Import terminé : '+r.report.chunks_indexed+' passages','ok');
      openDlg('Rapport d\'ingestion — '+f.name,reportNode(r.report),[btn('Fermer','btn-ghost',function(){dlg.close()})]);document.getElementById('import-form').reset();document.getElementById('f-kb').value='documents';load()})
      .catch(function(e){toast(e.message,'err')}).finally(function(){b.disabled=false;b.innerHTML='<svg class="ic"><use href="#i-upload"/></svg>Importer et indexer'})});
  load();
})();
