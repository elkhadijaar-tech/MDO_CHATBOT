(function(){
  var grid=document.getElementById('mod-grid'),search=document.getElementById('mod-search'),sem='';
  function load(){var p=new URLSearchParams();if(sem)p.set('semester',sem);if(search.value)p.set('q',search.value);
    fetch('/api/modules?'+p).then(function(r){return r.json()}).then(function(rows){
      grid.innerHTML='';if(!rows.length){grid.innerHTML='<div class="empty-state">Aucun module trouvé.</div>';return}
      rows.forEach(function(m){var c=document.createElement('article');c.className='card';
        c.innerHTML='<span class="tag"></span><h3 class="card-title" style="margin-top:8px"></h3><p></p><div class="card-actions"><a class="btn btn-sm btn-ghost">Poser une question</a></div>';
        c.querySelector('.tag').textContent='Semestre '+m.semester;c.querySelector('h3').textContent=m.name;
        var p=c.querySelector('p');if(m.professor)p.textContent=m.professor;else{var e=document.createElement('em');e.textContent='Professeur non indiqué dans la base';p.appendChild(e)}
        c.querySelector('a').href='/chat?q='+encodeURIComponent('Parle-moi du module '+m.name+' (S'+m.semester+')');grid.appendChild(c)})})}
  document.getElementById('sem-filter').addEventListener('click',function(e){if(e.target.tagName!=='BUTTON')return;
    [].forEach.call(this.children,function(b){b.classList.remove('on')});e.target.classList.add('on');sem=e.target.getAttribute('data-s');load()});
  var t;search.addEventListener('input',function(){clearTimeout(t);t=setTimeout(load,200)});load();
})();
