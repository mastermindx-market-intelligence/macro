/* Recording DOM double for controller/source-boundary tests. Not layout or browser proof. */
class Element {
 constructor(tag,doc){this.tagName=tag.toUpperCase();this.ownerDocument=doc;this.attrs={};this.children=[];this.parentElement=null;this._text='';this.listeners={};this.style={};this.hidden=false;this.value='';this.open=false;this.scrollTop=0;this.focusCount=0;
 this.dataset=new Proxy({}, {get:(_,k)=>this.getAttribute('data-'+k.replace(/[A-Z]/g,c=>'-'+c.toLowerCase()))||undefined,set:(_,k,v)=>{this.setAttribute('data-'+k.replace(/[A-Z]/g,c=>'-'+c.toLowerCase()),v);return true;}});
 this.classList={contains:c=>this.className.split(/\s+/).includes(c),add:(...xs)=>this.className=[...new Set([...this.className.split(/\s+/).filter(Boolean),...xs])].join(' '),remove:(...xs)=>this.className=this.className.split(/\s+/).filter(c=>!xs.includes(c)).join(' ')};
 }
 get className(){return this.attrs.class||'';}set className(v){this.attrs.class=v;}
 get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}set textContent(v){this._text=String(v);this.children=[];}
 get childNodes(){return this.children;}get firstChild(){return this.children[0]||null;}
 get isConnected(){return this===this.ownerDocument.documentElement||!!this.parentElement&&this.parentElement.isConnected;}
 get previousElementSibling(){if(!this.parentElement)return null;const x=this.parentElement.children;return x[x.indexOf(this)-1]||null;}
 get namespaceURI(){return 'http://www.w3.org/2000/svg';}
 set href(v){this.setAttribute('href',v);}get href(){return this.getAttribute('href');}
 set target(v){this.setAttribute('target',v);}get target(){return this.getAttribute('target')||'';}
 set rel(v){this.setAttribute('rel',v);}get rel(){return this.getAttribute('rel')||'';}
 setAttribute(k,v){this.attrs[k]=String(v);}getAttribute(k){return Object.hasOwn(this.attrs,k)?this.attrs[k]:null;}
 hasAttribute(k){return Object.hasOwn(this.attrs,k);}removeAttribute(k){delete this.attrs[k];}
 appendChild(n){n.remove();this.children.push(n);n.parentElement=this;return n;}
 insertBefore(n,b){n.remove();let i=b?this.children.indexOf(b):-1;this.children.splice(i<0?this.children.length:i,0,n);n.parentElement=this;return n;}
 replaceChildren(...ns){for(const c of this.children)c.parentElement=null;this.children=[];this._text='';ns.forEach(n=>this.appendChild(n));}
 remove(){if(this.parentElement){const a=this.parentElement.children;a.splice(a.indexOf(this),1);this.parentElement=null;}}
 contains(n){return n===this||this.children.some(c=>c.contains(n));}
 cloneNode(deep){const n=new Element(this.tagName,this.ownerDocument);n.attrs={...this.attrs};n._text=this._text;n.hidden=this.hidden;if(deep)this.children.forEach(c=>n.appendChild(c.cloneNode(true)));return n;}
 matches(selector){return selector.split(',').some(s=>{
  s=s.trim();const tag=s.match(/^[\w-]+/);if(tag&&tag[0].toUpperCase()!==this.tagName)return false;
  for(const [,c]of s.matchAll(/\.([\w-]+)/g))if(!this.classList.contains(c))return false;
  for(const [,k,,v]of s.matchAll(/\[([\w-]+)(=(['"]?)([^\]'"]+)\3)?\]/g)){/* parsed below */}
  const attrs=[...s.matchAll(/\[([\w-]+)(?:=['"]?([^\]'"]*)['"]?)?\]/g)];
  for(const a of attrs)if(!this.hasAttribute(a[1])||(a[2]!==undefined&&this.getAttribute(a[1])!==a[2]))return false;
  if(s.includes('[open]')&&!this.open)return false;
  return true;
 });}
 querySelectorAll(selector){const out=[];for(let s of selector.split(',')){s=s.trim();const direct=s.startsWith(':scope > ');if(direct)s=s.slice(9).trim();const visit=n=>{for(const c of n.children){if(c.matches(s)&&!out.includes(c))out.push(c);if(!direct)visit(c);}};visit(this);}return out;}
 querySelector(s){return this.querySelectorAll(s)[0]||null;}
 closest(s){for(let n=this;n;n=n.parentElement)if(n.matches(s))return n;return null;}
 addEventListener(k,f){(this.listeners[k] ||= []).push(f);}
 fire(k,props={}){const e={target:this,prevented:false,preventDefault(){this.prevented=true;},...props};(this.listeners[k]||[]).forEach(f=>f(e));return e;}
 focus(options){this.ownerDocument.activeElement=this;this.focusCount++;this.focusOptions=options;}
 showModal(){this.open=true;this.setAttribute('open','');}
 close(){this.open=false;this.removeAttribute('open');this.fire('close');}
 getClientRects(){return this.hidden||(this.tagName==='DIALOG'&&!this.open)?[]:[{}];}
}
function createPage({path='/macro.html',phone=false,supported=true}={}){
 const d={baseURI:'https://www.mastermind-x.com'+path,listeners:{},activeElement:null};
 d.documentElement=new Element('html',d);d.body=new Element('body',d);d.documentElement.appendChild(d.body);
 d.createElement=t=>new Element(t,d);d.createElementNS=(_,t)=>new Element(t,d);d.querySelectorAll=s=>d.documentElement.querySelectorAll(s);d.querySelector=s=>d.querySelectorAll(s)[0]||null;
 d.addEventListener=(k,f)=>(d.listeners[k] ||= []).push(f);d.fire=k=>(d.listeners[k]||[]).forEach(f=>f());
 d.defaultView={document:d,location:{pathname:path},matchMedia:()=>({matches:phone})};
 const nav=d.createElement('nav');nav.className='site-nav';d.body.appendChild(nav);const root=d.createElement('div');root.className='nav-links';nav.appendChild(root);const controls=d.createElement('div');controls.className='nav-ctrls';nav.appendChild(controls);
 const host=d.createElement('div');host.setAttribute('data-mmx-all-tools','');d.body.appendChild(host);
 const add=(parent,tag,key)=>{const n=d.createElement(tag);if(key)n.setAttribute(key,'');parent.appendChild(n);return n;};
 const trigger=add(host,'button','data-tools-open');trigger.hidden=true;const dialog=add(host,'dialog');if(!supported)dialog.showModal=undefined;
 const title=add(dialog,'h2','data-tools-title'),query=add(dialog,'input','data-tools-query'),close=add(dialog,'button','data-tools-close'),clear=add(dialog,'button','data-tools-clear'),categories=add(dialog,'nav','data-tools-categories'),list=add(dialog,'div','data-tools-results'),status=add(dialog,'div','data-tools-status'),count=add(dialog,'span','data-tools-count'),all=add(dialog,'button','data-tools-all');
 function anchor({href='macro.html',en='Market Dashboard',zh='市场看板',description='Read the market.',group='United States',groupZh='美国',target='',badge='',hidden=false}={}){
  let dd=root.children.find(x=>x.group===group);if(!dd){dd=add(root,'div');dd.className='nav-dd';dd.group=group;const trig=add(dd,'a');trig.className='nav-link';const a=add(trig,'span');a.className='l-en';a.textContent=group;const b=add(trig,'span');b.className='l-zh';b.textContent=groupZh;}
  const menu=dd.querySelector('.nav-dd-menu')||add(dd,'div');menu.className='nav-dd-menu';const a=add(menu,'a');a.href=href;a.target=target;a.hidden=hidden;
  const tx=add(a,'span');tx.className='nm-t';const e=add(tx,'span');e.className='l-en';e.textContent=en;const c=add(tx,'span');c.className='l-zh';c.textContent=zh;
  if(badge){const b=add(tx,'span');b.className='nm-tier';b.textContent=badge;}
  const de=add(a,'span');de.className='d';const den=add(de,'span');den.className='l-en';den.textContent=description;
  return a;
 }
 return {d,nav,root,controls,host,trigger,dialog,title,query,close,clear,categories,list,status,count,all,anchor};
}
module.exports={Element,createPage};
