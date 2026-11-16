/* Rendu Markdown minimal et sûr (DOM + textContent uniquement : aucun HTML n'est interprété). */
(function(){
  var INLINE=/(`[^`\n]+`)|(\*\*[^*\n]+\*\*)|(\[[^\]\n]+\]\(https?:\/\/[^)\s]+\))|(https?:\/\/[^\s<]+|www\.[^\s<]+|[\w.+-]+@[\w-]+\.[\w.]+)|(\*[^*\s][^*\n]*\*)|((?<![\w])_[^_\s][^_\n]*_(?![\w]))/g;
  function safeHref(u){u=u.replace(/[.,;:)]+$/,'');if(/^https?:\/\//i.test(u))return u;if(/^www\./i.test(u))return 'https://'+u;if(/^[\w.+-]+@[\w-]+\.[\w.]+$/.test(u))return 'mailto:'+u;return null}
  function link(parent,text,href){var a=document.createElement('a');a.textContent=text;a.href=href;a.target='_blank';a.rel='noopener noreferrer';parent.appendChild(a)}
  function inline(text,parent){
    var last=0,m;INLINE.lastIndex=0;
    while((m=INLINE.exec(text))){
      if(m.index>last)parent.appendChild(document.createTextNode(text.slice(last,m.index)));
      var tok=m[0],el;
      if(m[1]){el=document.createElement('code');el.textContent=tok.slice(1,-1);parent.appendChild(el)}
      else if(m[2]){el=document.createElement('strong');inline(tok.slice(2,-2),el);parent.appendChild(el)}
      else if(m[3]){var mm=/^\[([^\]]+)\]\((.+)\)$/.exec(tok);link(parent,mm[1],mm[2])}
      else if(m[4]){var raw=tok.replace(/[.,;:)]+$/,''),h=safeHref(raw);if(h){link(parent,raw,h);last=m.index+raw.length;INLINE.lastIndex=last;continue}parent.appendChild(document.createTextNode(tok))}
      else if(m[5]||m[6]){el=document.createElement('em');inline(tok.slice(1,-1),el);parent.appendChild(el)}
      last=m.index+tok.length;INLINE.lastIndex=last;
    }
    if(last<text.length)parent.appendChild(document.createTextNode(text.slice(last)));
  }
  function cells(line){return line.trim().replace(/^\|/,'').replace(/\|$/,'').split('|').map(function(c){return c.trim()})}
  function render(src){
    var frag=document.createDocumentFragment(),lines=String(src).replace(/\r/g,'').split('\n'),i=0;
    function special(l){return /^\s*```/.test(l)||/^\s*\|/.test(l)||/^#{1,4}\s/.test(l)||/^\s*([-*•]|\d+[.)])\s+/.test(l)||/^\s*>/.test(l)}
    while(i<lines.length){
      var l=lines[i];
      if(!l.trim()){i++;continue}
      if(/^\s*```/.test(l)){var code=[];i++;while(i<lines.length&&!/^\s*```/.test(lines[i])){code.push(lines[i]);i++}i++;
        var pre=document.createElement('pre'),c=document.createElement('code');c.textContent=code.join('\n');pre.appendChild(c);pre.tabIndex=0;frag.appendChild(pre);continue}
      if(/^\s*\|/.test(l)){var rows=[];while(i<lines.length&&/^\s*\|/.test(lines[i])){rows.push(lines[i]);i++}
        var hasSep=rows.length>1&&/^\s*\|?\s*:?-{2,}/.test(rows[1]);
        var wrap=document.createElement('div');wrap.className='tbl-wrap';var tb=document.createElement('table');
        var head=hasSep?cells(rows[0]):null,body=rows.slice(hasSep?2:0);
        if(head){var th=document.createElement('thead'),tr=document.createElement('tr');head.forEach(function(h){var e=document.createElement('th');inline(h,e);tr.appendChild(e)});th.appendChild(tr);tb.appendChild(th)}
        var tbd=document.createElement('tbody');body.forEach(function(r){var tr=document.createElement('tr');cells(r).forEach(function(cv){var e=document.createElement('td');inline(cv,e);tr.appendChild(e)});tbd.appendChild(tr)});
        tb.appendChild(tbd);wrap.appendChild(tb);frag.appendChild(wrap);continue}
      var hm=/^(#{1,4})\s+(.*)/.exec(l);
      if(hm){var h=document.createElement('h'+Math.min(hm[1].length+1,4));inline(hm[2],h);frag.appendChild(h);i++;continue}
      if(/^\s*([-*•]|\d+[.)])\s+/.test(l)){var ordered=/^\s*\d+[.)]/.test(l),list=document.createElement(ordered?'ol':'ul');
        while(i<lines.length&&/^\s*([-*•]|\d+[.)])\s+/.test(lines[i])){var li=document.createElement('li');inline(lines[i].replace(/^\s*([-*•]|\d+[.)])\s+/,''),li);list.appendChild(li);i++}
        frag.appendChild(list);continue}
      if(/^\s*>/.test(l)){var q=[];while(i<lines.length&&/^\s*>/.test(lines[i])){q.push(lines[i].replace(/^\s*>\s?/,''));i++}
        var bq=document.createElement('blockquote');inline(q.join(' '),bq);frag.appendChild(bq);continue}
      var para=[];while(i<lines.length&&lines[i].trim()&&!special(lines[i])){para.push(lines[i]);i++}
      if(!para.length){para.push(lines[i]);i++}
      var p=document.createElement('p');para.forEach(function(t,k){if(k)p.appendChild(document.createElement('br'));inline(t,p)});frag.appendChild(p);
    }
    return frag;
  }
  window.NexaMD={render:render};
})();
