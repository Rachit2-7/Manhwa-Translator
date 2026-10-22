const $=s=>document.querySelector(s);
let pages=[],cur=-1,showOrig=false,ctl=null;
const MAXW=1000,SLICE=1500;
document.fonts.load('700 20px "Comic Neue"').catch(()=>{});
fetch("/api/health").then(r=>r.json()).then(h=>{$("#status").textContent=h.api_key_configured?"Backend ready (model "+h.model+")":"Backend is up, but ANTHROPIC_API_KEY is not set."}).catch(()=>{$("#status").innerHTML='<span class="err">Cannot reach the backend. Start it with <code>make run</code>.</span>'});
const drop=$("#drop"),fi=$("#file");
drop.onclick=()=>fi.click();
fi.onchange=()=>addFiles(fi.files);
["dragover","dragenter"].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.add("on")}));
["dragleave","drop"].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.remove("on")}));
drop.addEventListener("drop",ev=>addFiles(ev.dataTransfer.files));
async function addFiles(fl){
  const arr=[...fl].filter(f=>f.type.startsWith("image/")).sort((a,b)=>a.name.localeCompare(b.name,undefined,{numeric:true}));
  for(const f of arr){
    const bmp=await createImageBitmap(f);
    const sc=Math.min(1,MAXW/bmp.width),c=document.createElement("canvas");
    c.width=Math.round(bmp.width*sc);c.height=Math.round(bmp.height*sc);
    c.getContext("2d").drawImage(bmp,0,0,c.width,c.height);
    pages.push({name:f.name,src:c,regions:[],done:false,thumb:c.toDataURL("image/jpeg",.3)});
  }
  if(cur<0&&pages.length)cur=0;
  fi.value="";renderList();show();
}
function renderList(){
  const el=$("#pages");el.innerHTML="";
  if(!pages.length){el.innerHTML='<div class="msg">No pages yet.</div>';}
  pages.forEach((p,i)=>{
    const d=document.createElement("div");d.className="pg"+(i===cur?" sel":"");
    const im=document.createElement("img");im.src=p.thumb;
    const t=document.createElement("div");t.textContent=p.name;
    const s=document.createElement("small");s.textContent=p.done?p.regions.length+" lines translated":p.err?"failed":"waiting";t.appendChild(s);
    d.append(im,t);d.onclick=()=>{cur=i;renderList();show()};el.appendChild(d);
  });
  $("#go").disabled=!pages.length;
  const any=pages.some(p=>p.done);$("#dl").disabled=!any;$("#dlall").disabled=!any;
}
function show(){
  const st=$("#stage");st.innerHTML="";
  if(cur<0){st.innerHTML='<div class="empty">Your translated page appears here.</div>';$("#regs").innerHTML="";return}
  const p=pages[cur],c=document.createElement("canvas");
  paint(p,c,!showOrig);st.appendChild(c);p.view=c;
  const box=$("#regs");box.innerHTML="";
  p.regions.forEach((r,i)=>{
    const d=document.createElement("div");d.className="reg";
    const h=document.createElement("div");h.className="hd";
    const cb=document.createElement("input");cb.type="checkbox";cb.checked=r.on;
    cb.onchange=()=>{r.on=cb.checked;paint(p,p.view,!showOrig)};
    const ty=document.createElement("span");ty.textContent=r.type;h.append(cb,ty);
    const ko=document.createElement("div");ko.className="ko";ko.textContent=r.korean;
    const ta=document.createElement("textarea");ta.rows=2;ta.value=r.english;
    ta.oninput=()=>{r.english=ta.value;paint(p,p.view,!showOrig)};
    d.append(h,ko,ta);box.appendChild(d);
  });
}
$("#tg").onclick=()=>{showOrig=!showOrig;$("#tg").textContent=showOrig?"Show translation":"Show original";show()};
function bgOf(ctx,x,y,w,h){
  const pts=[],W=ctx.canvas.width,H=ctx.canvas.height,cl=(v,m)=>Math.max(0,Math.min(m-1,Math.round(v)));
  for(let i=0;i<=6;i++){const t=i/6;
    pts.push([x+w*t,y],[x+w*t,y+h],[x,y+h*t],[x+w,y+h*t]);}
  let r=0,g=0,b=0;
  pts.forEach(([px,py])=>{const d=ctx.getImageData(cl(px,W),cl(py,H),1,1).data;r+=d[0];g+=d[1];b+=d[2]});
  const n=pts.length;return[r/n,g/n,b/n].map(Math.round);
}
function wrap(ctx,text,maxW){
  const out=[];
  text.split("\n").forEach(par=>{
    let line="";
    par.split(/\s+/).filter(Boolean).forEach(w=>{
      const t=line?line+" "+w:w;
      if(ctx.measureText(t).width>maxW&&line){out.push(line);line=w}else line=t;
    });
    out.push(line);
  });
  return out;
}
function paint(p,c,translated){
  c.width=p.src.width;c.height=p.src.height;
  const ctx=c.getContext("2d",{willReadFrequently:true});
  ctx.drawImage(p.src,0,0);
  if(!translated)return;
  const base=p.src.getContext("2d",{willReadFrequently:true});
  p.regions.forEach(r=>{
    if(!r.on||!r.english)return;
    let [x,y,w,h]=r.box;const pad=Math.max(3,Math.min(w,h)*.06);
    x=Math.max(0,x-pad);y=Math.max(0,y-pad);w=Math.min(c.width-x,w+pad*2);h=Math.min(c.height-y,h+pad*2);
    const [R,G,B]=bgOf(base,x,y,w,h),lum=(.299*R+.587*G+.114*B);
    ctx.fillStyle=`rgb(${R},${G},${B})`;
    ctx.beginPath();ctx.roundRect(x,y,w,h,Math.min(w,h)*.25);ctx.fill();
    ctx.fillStyle=lum>140?"#111":"#fff";ctx.textAlign="center";ctx.textBaseline="middle";
    const iw=w*.88,ih=h*.86;let fs=Math.min(40,ih*.6),lines;
    for(;fs>=8;fs-=1){
      ctx.font=`700 ${fs}px "Comic Neue","Comic Sans MS",sans-serif`;
      lines=wrap(ctx,r.english,iw);
      if(lines.length*fs*1.15<=ih&&lines.every(l=>ctx.measureText(l).width<=iw))break;
    }
    const lh=fs*1.15,y0=y+h/2-(lines.length-1)*lh/2;
    lines.forEach((l,i)=>ctx.fillText(l,x+w/2,y0+i*lh));
  });
}
function blobOf(c,q){return new Promise(r=>c.toBlob(r,"image/jpeg",q||.88))}
async function translatePage(p,i,n){
  p.regions=[];p.err=false;
  const fd=new FormData();
  fd.append("image",await blobOf(p.src),p.name);fd.append("style",$("#tone").value);
  fd.append("glossary",$("#gloss").value.trim());fd.append("include_sfx",$("#sfx").checked);
  const res=await fetch("/api/translate",{method:"POST",body:fd,signal:ctl.signal});
  const j=await res.json().catch(()=>({}));
  if(!res.ok)throw{code:res.status,message:j.detail||("HTTP "+res.status)};
  const W=p.src.width,H=p.src.height;
  p.regions=j.regions.map(r=>({box:[r.box[0]*W,r.box[1]*H,r.box[2]*W,r.box[3]*H],korean:r.korean,english:r.english,type:r.type,on:true}));
  p.done=true;$("#bar").style.width=((i+1)/n*100)+"%";
}
$("#go").onclick=async()=>{
  if(!pages.length)return;
  ctl=new AbortController();$("#go").disabled=true;$("#stop").hidden=false;showOrig=false;$("#tg").textContent="Show original";
  const todo=pages.filter(p=>!p.done);let i=0;
  for(const p of todo){
    $("#status").textContent=`Reading and translating ${p.name} (${i+1} of ${todo.length})… this can take a minute.`;
    try{await translatePage(p,i,todo.length)}
    catch(e){
      p.err=true;
      if(e&&e.code===503){$("#status").innerHTML='<span class="err">'+esc(e.message)+'</span>';break}
      if(ctl.signal.aborted){$("#status").textContent="Stopped.";break}
      $("#status").innerHTML='<span class="err">'+esc((e&&e.message)||"Translation failed")+" ("+esc((e&&e.code)||"error")+")</span>";
      if(e&&e.code===429)break;
    }
    i++;renderList();if(pages[cur]===p)show();
  }
  if(!$("#status").querySelector(".err")&&!ctl.signal.aborted)$("#status").textContent="Done. Review the detected text on the right and fix anything you like.";
  $("#stop").hidden=true;$("#go").disabled=false;$("#bar").style.width="100%";renderList();show();
};
$("#stop").onclick=()=>ctl&&ctl.abort();
function esc(s){return String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]))}
async function save(p,name){
  const c=document.createElement("canvas");paint(p,c,true);
  const blob=await new Promise(r=>c.toBlob(r,"image/png"));
  const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),4000);
}
const base=p=>p.name.replace(/\.[^.]+$/,"")+"_en.png";
$("#dl").onclick=()=>{if(cur>=0)save(pages[cur],base(pages[cur]))};
$("#dlall").onclick=async()=>{for(const p of pages.filter(p=>p.done))await save(p,base(p))};
