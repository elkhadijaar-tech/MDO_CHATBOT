(function(){
  var grid=document.getElementById('course-grid'),all=[],q=document.getElementById('c-search');
  function split(t){var m=/^(.*?)\s*\((.*)\)\s*$/.exec(t);return m?{main:m[1],sub:m[2]}:{main:t,sub:''}}
  function link(label,cls,text,n,title){var a=document.createElement('a');a.className='btn btn-sm '+cls;a.textContent=label;
    a.href='/chat?mode=cours&q='+encodeURIComponent(text+' du module '+n+' : '+title);return a}
  function render(){var f=q.value.trim().toLowerCase();grid.innerHTML='';
    var rows=all.filter(function(c){return!f||c.title.toLowerCase().indexOf(f)>=0});
    if(!rows.length){grid.innerHTML='<div class="empty-state">Aucun module trouvé.</div>';return}
    rows.forEach(function(c){var t=split(c.title),card=document.createElement('article');card.className='card';
      card.innerHTML='<span class="tag"></span><h3 class="card-title" style="margin-top:8px"></h3><p></p><div class="card-actions"></div>';
      card.querySelector('.tag').textContent='Module '+c.no;card.querySelector('h3').textContent=t.main;card.querySelector('p').textContent=t.sub;
      var ac=card.querySelector('.card-actions');
      ac.appendChild(link('Expliquer','btn-primary','Explique-moi les notions clés',c.no,c.title));
      ac.appendChild(link('Résumé','btn-ghost','Fais un résumé',c.no,c.title));
      ac.appendChild(link('QCM','btn-ghost',"Génère un QCM d'entraînement",c.no,c.title));
      grid.appendChild(card)})}
  q.addEventListener('input',render);
  fetch('/api/courses').then(function(r){return r.json()}).then(function(d){all=d;render()});
})();
