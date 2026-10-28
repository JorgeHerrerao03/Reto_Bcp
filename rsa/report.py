"""Reporte HTML autocontenido (sin servidor ni CDN). El mismo archivo funciona:
- estático (doble clic / GitHub Pages): ranking, brief, grafo, matriz, what-if de pesos, búsqueda, traza;
- 'modo app' (python -m rsa app): además añadir fuentes con preview, deshacer, demos, Claude."""
from __future__ import annotations

import json
from types import SimpleNamespace

from .brief import recomendacion, render


def _slim(state):
    vs = []
    for v in state["versiones"]:
        by = {f["id"]: SimpleNamespace(**f) for f in v["fuentes"]}
        sig = []
        for s in v["signals"]:
            s = dict(s)
            s["recomendacion"] = recomendacion(s)
            s["brief_md"] = render(s, by)
            sig.append(s)
        d = {k: v[k] for k in ("v", "ts", "evento", "fuentes", "descartadas", "log", "diff")}
        d["signals"] = sig
        vs.append(d)
    return vs


def write(state, path):
    data = json.dumps(_slim(state), ensure_ascii=False).replace("</", "<\\/")
    path.write_text(HTML.replace("/*__DATA__*/null", data), encoding="utf-8")


HTML = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Revenue Signals</title>
<style>
:root{--bg:#f4f2ee;--panel:#fffdf9;--ink:#14213d;--mut:#5d6679;--line:#e3dfd6;--acc:#e8731a;--acc2:#0b5cad;
--hecho:#1f7a4d;--hip:#b7791f;--falt:#7a5cc7;--adv:#8a6d3b;--corr:#0b5cad;--ref:#c0392b;--res:#1f7a4d;--noise:#9aa1ad;
--chipbg:rgba(20,33,61,.06);--shadow:0 1px 0 rgba(20,33,61,.04),0 8px 24px -12px rgba(20,33,61,.18)}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0d1424;--panel:#141d31;--ink:#e9edf5;--mut:#9aa6bd;
--line:#25304a;--acc:#ff8a3d;--acc2:#5aa2ff;--hecho:#4cc38a;--hip:#e0a84a;--falt:#a68bff;--adv:#c9a56a;--corr:#5aa2ff;
--ref:#ff6b5e;--res:#4cc38a;--noise:#5c6680;--chipbg:rgba(255,255,255,.06);--shadow:0 8px 24px -12px rgba(0,0,0,.6)}}
:root[data-theme=dark]{--bg:#0d1424;--panel:#141d31;--ink:#e9edf5;--mut:#9aa6bd;--line:#25304a;--acc:#ff8a3d;--acc2:#5aa2ff;
--hecho:#4cc38a;--hip:#e0a84a;--falt:#a68bff;--adv:#c9a56a;--corr:#5aa2ff;--ref:#ff6b5e;--res:#4cc38a;--noise:#5c6680;
--chipbg:rgba(255,255,255,.06);--shadow:0 8px 24px -12px rgba(0,0,0,.6)}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 "Segoe UI",system-ui,-apple-system,sans-serif}
.mono{font-family:ui-monospace,"Cascadia Code",Consolas,monospace}
header{padding:18px 28px 14px;border-bottom:1px solid var(--line);display:flex;gap:20px;align-items:flex-end;flex-wrap:wrap}
h1{font-size:22px;margin:0;letter-spacing:-.02em}h1 b{color:var(--acc)}
.sub{color:var(--mut);font-size:12.5px}
.kpis{display:flex;gap:10px;margin-left:auto;flex-wrap:wrap}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:8px 14px;min-width:88px}
.kpi b{display:block;font-size:20px;font-variant-numeric:tabular-nums}.kpi span{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.06em}
.bar-actions{padding:10px 28px;display:flex;gap:8px;flex-wrap:wrap;border-bottom:1px solid var(--line);align-items:center}
.btn{border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:9px;padding:7px 13px;cursor:pointer;font:inherit;font-size:13px}
.btn:hover{border-color:var(--acc)}.btn.pri{background:var(--acc);border-color:var(--acc);color:#fff;font-weight:600}
.btn:disabled{opacity:.5;cursor:not-allowed}
.mode{margin-left:auto;font-size:12px;color:var(--mut)}.mode b{color:var(--hecho)}
.time{padding:12px 28px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;border-bottom:1px solid var(--line)}
.time .lbl{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--mut);margin-right:6px}
.vbtn{border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:999px;padding:6px 12px;cursor:pointer;font:inherit;font-size:12.5px}
.vbtn.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}.vbtn small{opacity:.7;margin-left:6px}
.wrap{display:grid;grid-template-columns:340px 1fr;gap:20px;padding:20px 28px 40px}
@media(max-width:900px){.wrap{grid-template-columns:1fr;padding:16px}header,.time,.bar-actions{padding-left:16px;padding-right:16px}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow)}
.sig{padding:14px 16px;cursor:pointer;margin-bottom:10px;transition:transform .15s,border-color .15s}
.sig:hover{transform:translateY(-1px)}.sig.on{border-color:var(--acc);outline:2px solid color-mix(in srgb,var(--acc) 30%,transparent)}
.sig .top{display:flex;align-items:baseline;gap:8px}.sid{font-weight:700;color:var(--acc)}
.sig h3{margin:2px 0 8px;font-size:14.5px;line-height:1.3}
.score{margin-left:auto;font-size:22px;font-weight:700;font-variant-numeric:tabular-nums}
.bar{height:6px;border-radius:3px;background:var(--chipbg);overflow:hidden;margin:6px 0 8px}.bar i{display:block;height:100%;background:linear-gradient(90deg,var(--acc2),var(--acc));transition:width .6s}
.delta{font-size:12px;font-weight:600;padding:1px 7px;border-radius:999px}.up{color:var(--res);background:color-mix(in srgb,var(--res) 14%,transparent)}
.dn{color:var(--ref);background:color-mix(in srgb,var(--ref) 14%,transparent)}
.counts{display:flex;gap:6px;flex-wrap:wrap}
.chip{font-size:11px;padding:2px 8px;border-radius:999px;background:var(--chipbg);color:var(--mut);white-space:nowrap}
.chip.t-hecho{color:var(--hecho)}.chip.t-hipotesis{color:var(--hip)}.chip.t-faltante{color:var(--falt)}.chip.t-advertencia{color:var(--adv)}
.chip.t-correccion{color:var(--corr)}.chip.t-refutada{color:var(--ref)}.chip.t-resuelta{color:var(--res)}
.noise{padding:14px 16px}.noise h4{margin:0 0 8px;font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--mut)}
.noise div{font-size:12.5px;color:var(--mut);padding:4px 0;border-top:1px dashed var(--line)}
.changes{padding:16px 18px;margin-bottom:16px;border-left:4px solid var(--acc)}
.changes h2{margin:0 0 8px;font-size:15px}.changes ul{margin:0;padding-left:18px}.changes li{margin:3px 0}
.tabs{display:flex;gap:4px;border-bottom:1px solid var(--line);padding:0 18px;overflow-x:auto}
.tab{padding:12px 14px;border:0;background:none;color:var(--mut);font:inherit;cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap}
.tab.on{color:var(--ink);border-color:var(--acc);font-weight:600}
.pane{padding:18px 22px}
.hd{display:flex;gap:16px;align-items:flex-start;flex-wrap:wrap}.hd h2{margin:0;font-size:20px;letter-spacing:-.01em}
.comp{display:flex;gap:14px;margin:12px 0 4px;flex-wrap:wrap}.comp div{font-size:12px;color:var(--mut)}.comp b{color:var(--ink);font-size:15px;margin-right:4px}
.rec{display:inline-block;margin-top:8px;padding:6px 12px;border-radius:8px;background:color-mix(in srgb,var(--acc) 12%,transparent);font-weight:600;font-size:13px}
.sec{margin-top:20px}.sec h3{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--mut);margin:0 0 8px}
.cl{display:grid;grid-template-columns:92px 1fr auto;gap:10px;align-items:start;padding:8px 0;border-top:1px solid var(--line)}
.cl.sup .tx{text-decoration:line-through;opacity:.55}.cl.nuevo{background:color-mix(in srgb,var(--acc) 8%,transparent);border-radius:6px}
.cite{color:var(--acc2);cursor:pointer;white-space:nowrap;border:0;background:none;font:inherit;font-size:12px;padding:0}
.cite:hover{text-decoration:underline}.trans{font-size:11px;font-weight:600;color:var(--ref)}
.no{background:color-mix(in srgb,var(--ref) 7%,var(--panel));border:1px solid color-mix(in srgb,var(--ref) 30%,var(--line));border-radius:12px;padding:12px 16px}
.no li{margin:4px 0}
.ai{background:color-mix(in srgb,var(--acc2) 7%,var(--panel));border:1px solid color-mix(in srgb,var(--acc2) 30%,var(--line));border-radius:12px;padding:12px 16px}
.tool{border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin:6px 0;font-size:12.5px}.tool code{font-size:12px}
.warn{color:var(--hip);font-size:12px;margin-top:6px}
table{border-collapse:collapse;width:100%;font-size:12.5px}td,th{border-top:1px solid var(--line);padding:7px 8px;text-align:left;vertical-align:top}
td{overflow-wrap:anywhere}th{color:var(--mut);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.06em}
svg text{fill:var(--ink);font-size:11px}svg .m{fill:var(--mut)}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--mut);margin-bottom:8px}.legend i{display:inline-block;width:18px;height:3px;vertical-align:middle;margin-right:5px}
.drawer{position:fixed;top:0;right:0;height:100%;width:min(460px,100%);background:var(--panel);border-left:1px solid var(--line);box-shadow:-20px 0 40px -20px rgba(0,0,0,.3);transform:translateX(105%);transition:transform .25s;z-index:20;overflow:auto;padding:22px}
.drawer.on{transform:none}.x{float:right;border:0;background:var(--chipbg);color:var(--ink);border-radius:8px;padding:4px 10px;cursor:pointer}
.drawer p{margin:6px 0;padding:6px 8px;border-radius:6px}.drawer p.hl{background:color-mix(in srgb,var(--acc) 18%,transparent)}
.flash{animation:fl 1.4s ease}@keyframes fl{0%{background:color-mix(in srgb,var(--acc) 30%,transparent)}100%{background:transparent}}
.modal{position:fixed;inset:0;background:rgba(10,15,30,.45);display:none;align-items:flex-start;justify-content:center;z-index:30;padding:40px 16px;overflow:auto}
.modal.on{display:flex}.modal .card{width:min(760px,100%);padding:22px}
.modal h2{margin:0 0 4px;font-size:18px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:12px 0}@media(max-width:700px){.grid{grid-template-columns:1fr 1fr}}
label{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.06em;display:block}
input,select,textarea{width:100%;font:inherit;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin-top:3px}
textarea{min-height:130px;resize:vertical}
.drop{border:2px dashed var(--line);border-radius:12px;padding:18px;text-align:center;color:var(--mut);cursor:pointer;margin-top:12px}
.drop.over{border-color:var(--acc);color:var(--acc)}
.row{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px;align-items:center}
.res{margin-top:16px;border-top:1px solid var(--line);padding-top:12px}
.hit{padding:8px 0;border-top:1px solid var(--line);font-size:13px}
.toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);background:var(--ink);color:var(--bg);padding:10px 16px;border-radius:10px;z-index:40;display:none;max-width:90%}
.slider{display:grid;grid-template-columns:110px 1fr 46px;gap:10px;align-items:center;margin:8px 0}
.slider input{padding:0}
@media print{.bar-actions,.time,.tabs,aside,.drawer,.modal,.toast{display:none!important}.wrap{display:block;padding:0}.card{box-shadow:none;border:0}body{background:#fff}}
</style></head><body>
<header><div><h1>Revenue <b>Signals</b> Agent</h1>
<div class="sub">Señales con potencial económico · hechos vs. hipótesis vs. faltantes · fuentes sintéticas</div></div>
<div class="kpis" id="kpis"></div></header>
<div class="bar-actions" id="actions"></div>
<div class="time" id="time"></div>
<div class="wrap"><aside id="list"></aside><main id="main"></main></div>
<div class="drawer" id="drawer"></div>
<div class="modal" id="m-add"><div class="card"><button class="x" data-close>✕</button><h2>Añadir fuente</h2>
<div class="sub">Arrastra un .md, .txt o .docx, o pega el texto. Si el archivo ya trae el encabezado estándar (**ID:**, **Fecha:**…) se respeta.</div>
<div class="drop" id="drop">Suelta aquí el archivo o haz clic para elegir<input type="file" id="file" accept=".md,.txt,.docx" hidden></div>
<div class="grid"><div><label>ID</label><input id="f-id"></div><div><label>Fecha</label><input id="f-fecha" type="date"></div>
<div><label>Tipo</label><select id="f-tipo"><option>Correo</option><option>Teams</option><option>Acta</option><option>Acta de reunión</option><option>Documento</option><option>Ficha técnica</option><option>Política comercial</option></select></div>
<div><label>Área</label><input id="f-area" placeholder="Operaciones"></div></div>
<label>Título</label><input id="f-titulo" placeholder="Se toma del archivo si lo omites">
<div style="margin-top:10px"><label>Texto</label><textarea id="f-texto" placeholder="Pega aquí el contenido…"></textarea></div>
<div class="row"><button class="btn" id="b-prev">Previsualizar impacto</button><button class="btn pri" id="b-inc" disabled>Incorporar</button>
<label style="text-transform:none;letter-spacing:0;font-size:13px;display:flex;gap:6px;align-items:center;margin-left:8px"><input type="checkbox" id="f-llm" style="width:auto;margin:0"> Segunda opinión de Claude</label>
<span class="sub" id="f-file"></span></div><div id="prev-res"></div></div></div>
<div class="modal" id="m-ask"><div class="card"><button class="x" data-close>✕</button><h2>Preguntar a las fuentes</h2>
<div class="sub">Búsqueda por relevancia sobre cada oración de la versión vigente. En la app, Claude puede redactar la respuesta citando solo esa evidencia.</div>
<div class="row"><input id="q" placeholder="¿El piloto de fechas de pago está en producción?" style="flex:1;margin:0"><button class="btn pri" id="b-ask">Buscar</button>
<label style="text-transform:none;letter-spacing:0;font-size:13px;display:flex;gap:6px;align-items:center" class="apponly"><input type="checkbox" id="q-llm" style="width:auto;margin:0"> con Claude</label></div><div id="ask-res"></div></div></div>
<div class="modal" id="m-cfg"><div class="card"><button class="x" data-close>✕</button><h2>Claude (opcional)</h2>
<div class="sub">La API key se guarda solo en el archivo <code>.env</code> de tu PC (excluido de git). Sin key, todo funciona en modo determinístico.</div>
<div class="grid" style="grid-template-columns:2fr 1fr"><div><label>ANTHROPIC_API_KEY</label><input id="c-key" type="password" placeholder="sk-ant-…"></div>
<div><label>Modelo</label><input id="c-model" placeholder="claude-haiku-5-5"></div></div>
<div class="row"><button class="btn pri" id="b-save">Guardar</button><button class="btn" id="b-test">Probar conexión</button><button class="btn" id="b-sum">Generar resúmenes de señales</button></div><div id="cfg-res" class="res sub"></div></div></div>
<div class="toast" id="toast"></div>
<script>
const V=/*__DATA__*/null, APP=!!window.RSA_APP;
const $=s=>document.querySelector(s), esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const ET={hecho:"Hecho",hipotesis:"Hipótesis",faltante:"Faltante",advertencia:"Advertencia",correccion:"Corrección",refutada:"Refutada",resuelta:"Resuelta"};
const ss=(k,d)=>{try{return JSON.parse(sessionStorage.getItem(k))??d}catch(e){return d}}, sset=(k,v)=>{try{sessionStorage.setItem(k,JSON.stringify(v))}catch(e){}};
let vi=V.length-1, sel=ss("rs-sel",null), tab=ss("rs-tab","brief"), W={impacto:.45,evidencia:.30,urgencia:.25}, ST=null;
try{const t=localStorage.getItem("rs-theme");if(t)document.documentElement.dataset.theme=t}catch(e){}
const st=c=>c.superada||c.tipo;
function toast(m,ms=3200){const t=$("#toast");t.textContent=m;t.style.display="block";clearTimeout(t._h);t._h=setTimeout(()=>t.style.display="none",ms)}
async function api(path,body){const r=await fetch(path,{method:body===undefined?"GET":"POST",headers:{"Content-Type":"application/json"},body:body===undefined?undefined:JSON.stringify(body)});
  const j=await r.json();if(!r.ok)throw new Error(j.error||r.status);return j}
function prevSig(id){return vi>0?V[vi-1].signals.find(s=>s.id===id):null}
function actions(){
  const a=APP?[["add","＋ Añadir fuente","pri"],["ask","Preguntar a las fuentes"],["undo","Deshacer última"],["d1","Demo: contradice"],["d2","Demo: confirma"],["d3","Demo: ruido"],["reset","Reiniciar"],["cfg","Claude ⚙"],["print","Imprimir / PDF"],["theme","Tema"]]
    :[["ask","Buscar en fuentes"],["print","Imprimir / PDF"],["theme","Tema"]];
  $("#actions").innerHTML=a.map(([k,n,c])=>`<button class="btn ${c||""}" data-a="${k}">${n}</button>`).join("")
   +`<span class="mode">${APP?`<b>●</b> App local${ST?` · Claude: ${ST.llm.configurada?"<b>conectado</b> ("+esc(ST.llm.modelo)+")":"no configurado"}`:""}`:"Versión publicada (solo lectura) · se regenera desde GitHub"}</span>`;
  document.querySelectorAll("[data-a]").forEach(b=>b.onclick=()=>act(b.dataset.a));
}
async function act(k){
  if(k==="theme"){const r=document.documentElement,d=matchMedia("(prefers-color-scheme: dark)").matches,n=(r.dataset.theme||(d?"dark":"light"))==="dark"?"light":"dark";r.dataset.theme=n;try{localStorage.setItem("rs-theme",n)}catch(e){}return}
  if(k==="print")return window.print();
  if(k==="ask"){$("#m-ask").classList.add("on");$("#q").focus();return}
  if(k==="add"){openAdd();return}
  if(k==="cfg"){$("#m-cfg").classList.add("on");$("#c-model").value=ST?.llm.modelo||"";$("#cfg-res").textContent=ST?.llm.configurada?"Key actual: "+ST.llm.key:"Sin key configurada.";return}
  const map={undo:["/api/deshacer",{}],reset:["/api/reset",{}],d1:["/api/demo",{caso:"contradice"}],d2:["/api/demo",{caso:"confirma"}],d3:["/api/demo",{caso:"ruido"}]};
  if(k==="reset"&&!confirm("¿Reiniciar a las 18 fuentes originales? Se pierden las incorporadas."))return;
  try{toast("Procesando…");const r=await api(...map[k]);if(r.cambios&&r.cambios[0])sset("rs-sel",r.cambios[0]);sset("rs-msg",r.explicacion||[r.retirada?`Retirada ${r.retirada}`:"Listo"]);location.reload()}catch(e){toast("⚠ "+e.message,6000)}
}
function render(){
  const v=V[vi]; if(!sel||!v.signals.find(s=>s.id===sel)) sel=v.signals[0]?.id; sset("rs-sel",sel); sset("rs-tab",tab);
  const nc=v.log.filter(l=>l.accion==="consulta_herramienta").length;
  $("#kpis").innerHTML=[["Fuentes",v.fuentes.length],["Señales",v.signals.length],["Ruido",v.descartadas.length],["Consultas tool",nc],["Versión","v"+v.v]]
   .map(([k,n])=>`<div class="kpi"><b>${n}</b><span>${k}</span></div>`).join("");
  $("#time").innerHTML=`<span class="lbl">Máquina del tiempo</span>`+V.map((x,i)=>`<button class="vbtn ${i===vi?"on":""}" data-v="${i}">v${x.v}<small>${esc(x.evento)}</small></button>`).join("");
  document.querySelectorAll("[data-v]").forEach(b=>b.onclick=()=>{vi=+b.dataset.v;render()});
  $("#list").innerHTML=v.signals.map((s,i)=>{const p=prevSig(s.id);const d=p?Math.round((s.score-p.score)*10)/10:null;
    const c=s.conteo;return `<div class="card sig ${s.id===sel?"on":""}" data-s="${s.id}">
    <div class="top"><span class="sid">#${i+1} · ${s.id}</span>${d?`<span class="delta ${d>0?"up":"dn"}">${d>0?"▲":"▼"} ${Math.abs(d)}</span>`:""}${p===undefined&&vi>0?`<span class="delta up">nueva</span>`:""}<span class="score">${s.score}</span></div>
    <h3>${esc(s.titulo)}</h3><div class="bar"><i style="width:${s.score}%"></i></div>
    <div class="counts">${["hecho","hipotesis","faltante","correccion"].filter(t=>c[t]).map(t=>`<span class="chip t-${t}">${c[t]} ${ET[t].toLowerCase()}</span>`).join("")}
    <span class="chip">madurez ${s.confianza}</span><span class="chip">${s.fuentes.length} fuentes</span></div></div>`}).join("")
   +`<div class="card noise"><h4>Descartadas como ruido</h4>${v.descartadas.map(d=>`<div><button class="cite" data-src="${d.fuente}">${d.fuente}</button> ${esc(d.motivo)}</div>`).join("")||"<div>—</div>"}</div>`;
  document.querySelectorAll("[data-s]").forEach(b=>b.onclick=()=>{sel=b.dataset.s;render()});
  const s=v.signals.find(x=>x.id===sel), d=v.diff; let h="";
  if(d&&d.explicacion.length)h+=`<div class="card changes"><h2>Qué cambió en v${v.v} y por qué</h2><div class="sub" style="margin-bottom:8px">${esc(v.evento)}</div><ul>${d.explicacion.map(l=>`<li>${cites(esc(l))}</li>`).join("")}</ul></div>`;
  h+=`<div class="card"><div class="tabs">${[["brief","Opportunity Brief"],["grafo","Grafo de evidencia"],["matriz","Matriz"],["pesos","¿Y si cambio los pesos?"],["traza","Traza"]].map(([k,n])=>`<button class="tab ${tab===k?"on":""}" data-t="${k}">${n}</button>`).join("")}</div><div class="pane">`;
  h+= !s?"<p>Sin señales.</p>":tab==="brief"?brief(s,d):tab==="grafo"?graph(v):tab==="matriz"?matrix(v):tab==="pesos"?weights(v):trace(v,s);
  $("#main").innerHTML=h+"</div></div>";
  document.querySelectorAll("[data-t]").forEach(b=>b.onclick=()=>{tab=b.dataset.t;render()});
  if(tab==="pesos")bindWeights(v);
  const dl=$("#dl-md");if(dl)dl.onclick=()=>{const b=new Blob([s.brief_md],{type:"text/markdown"});const a=document.createElement("a");a.href=URL.createObjectURL(b);a.download=`${s.id}_brief.md`;a.click()};
  bindCites();
}
function cites(h){return h.replace(/\[(F\d+(?:\.\d+)?)\]/g,(m,id)=>`<button class="cite" data-src="${id}">[${id}]</button>`)}
function bindCites(){document.querySelectorAll("[data-src]").forEach(b=>b.onclick=e=>{e.stopPropagation();openSrc(b.dataset.src)})}
function openSrc(id){const v=V[vi],[fid]=id.split("."),f=v.fuentes.find(x=>x.id===fid);if(!f)return;
  $("#drawer").innerHTML=`<button class="x" onclick="this.parentNode.classList.remove('on')">✕</button><div class="sub">${f.id} · ${f.fecha} · ${esc(f.tipo)} · ${esc(f.area)}${f.origen==="incorporada"?" · <b style='color:var(--acc)'>incorporada</b>":""}</div>
  <h2 style="margin:6px 0 14px;font-size:18px">${esc(f.titulo)}</h2>${f.sents.map(x=>`<p class="${x.sid===id?"hl":""}"><span class="mono sub">${x.sid}</span> ${esc(x.texto)}</p>`).join("")}<div class="sub mono" style="margin-top:14px">sha1 ${f.sha1}</div>`;
  $("#drawer").classList.add("on")}
function brief(s,d){
  const ch=d&&d.cambios[s.id]; const tr={}; (ch?.transiciones||[]).forEach(t=>tr[t.sid]=t); const nw=new Set((ch?.claims_nuevos||[]).map(c=>c.sid)); const C=s.componentes;
  let h=`<div class="hd"><div style="flex:1;min-width:260px"><div class="sub">${s.id} · ${s.areas.join(" · ")}</div><h2>${esc(s.titulo)}</h2>
  <div class="rec">${esc(s.recomendacion)}</div> <button class="btn" id="dl-md" style="margin-left:6px">⬇ Brief .md</button></div><div style="text-align:right"><div style="font-size:40px;font-weight:700;line-height:1">${s.score}</div><div class="sub">score / 100 · madurez ${s.confianza}</div></div></div>
  <div class="comp"><div><b>${C.impacto}</b>impacto ×${s.pesos.impacto}</div><div><b>${C.evidencia}</b>evidencia ×${s.pesos.evidencia}</div><div><b>${C.urgencia}</b>urgencia ×${s.pesos.urgencia}</div>${C.penalizacion?`<div><b style="color:var(--ref)">−${C.penalizacion}</b>refutaciones</div>`:""}</div>`;
  if(s.resumen_llm)h+=`<div class="sec ai"><h3 style="color:var(--acc2)">Resumen ejecutivo · Claude (citas validadas)</h3>${cites(esc(s.resumen_llm))}</div>`;
  if(s.no_afirmo.length)h+=`<div class="sec no"><h3 style="color:var(--ref)">Lo que NO afirmo</h3><ul style="margin:0;padding-left:18px">${s.no_afirmo.map(x=>`<li>${esc(x)}</li>`).join("")}</ul></div>`;
  for(const [t,n] of [["hecho","Hechos en fuentes"],["hipotesis","Hipótesis"],["faltante","Datos faltantes"],["advertencia","Advertencias"],["correccion","Correcciones"]]){const xs=s.claims.filter(c=>c.tipo===t);if(!xs.length)continue;
    h+=`<div class="sec"><h3>${n} (${xs.length})</h3>${xs.map(c=>`<div class="cl ${c.superada?"sup":""} ${nw.has(c.sid)?"nuevo flash":""}"><span class="chip t-${st(c)}">${ET[st(c)]}</span>
    <div><span class="tx">${esc(c.texto)}</span>${c.superada?` <span class="trans">→ ${c.superada} por ${cites("["+c.por+"]")}</span>`:""}${tr[c.sid]?` <span class="trans">(cambió en esta versión: ${ET[tr[c.sid].de]} → ${ET[tr[c.sid].a]})</span>`:""}</div>
    <button class="cite" data-src="${c.sid}">[${c.sid}]</button></div>`).join("")}</div>`}
  if(s.consultas.length)h+=`<div class="sec"><h3>Consulta a herramienta local</h3>${s.consultas.map(c=>`<div class="tool"><code class="mono">consultar_parametros.py ${c.args.map(a=>"'"+esc(a)+"'").join(" ")}</code><div>${cites(esc(c.lectura))}</div><div class="sub">${c.ms} ms · encontrado=${c.resultado.encontrado}</div></div>`).join("")}<div class="warn">⚠ ${esc(s.consultas[0].resultado.advertencia||"")}</div></div>`;
  if(s.proximos_pasos.length)h+=`<div class="sec"><h3>Próximos pasos (desde fuentes)</h3><ol style="margin:0;padding-left:18px">${s.proximos_pasos.map(p=>`<li>${esc(p.texto)} ${cites("["+p.sid+"]")}</li>`).join("")}</ol></div>`;
  return h}
function graph(v){
  const Wd=900,rowH=92,x0=210,top=58,rows=[...v.signals.map(s=>({s,ids:s.fuentes})),{s:null,ids:v.descartadas.map(d=>d.fuente)}];
  const H=rows.length*rowH+top,pos={};let svg="",bg="",ln="";
  rows.forEach((r,i)=>{const y=top+i*rowH,n=r.ids.length,step=Math.min(100,(Wd-x0-110)/Math.max(n,1));
    bg+=`<rect x="6" y="${y-22}" width="${Wd-12}" height="${rowH-12}" rx="12" fill="${r.s&&r.s.id===sel?"color-mix(in srgb,var(--acc) 8%,transparent)":"var(--chipbg)"}"/>`;
    svg+=`<text x="20" y="${y-2}" font-weight="700" style="fill:${r.s?"var(--acc)":"var(--mut)"}">${r.s?r.s.id+" · "+r.s.score:"Ruido"}</text><text class="m" x="20" y="${y+14}">${esc((r.s?r.s.titulo:"sin impacto económico").slice(0,30))}</text>`;
    r.ids.forEach((id,j)=>{const x=x0+j*step+20;pos[id]={x,y};const f=v.fuentes.find(z=>z.id===id);
      svg+=`<g data-src="${id}" style="cursor:pointer"><circle cx="${x}" cy="${y+4}" r="15" fill="${r.s?"var(--panel)":"var(--chipbg)"}" stroke="${!r.s?"var(--noise)":f.origen==="incorporada"?"var(--acc)":"var(--acc2)"}" stroke-width="${f.origen==="incorporada"?3:1.6}"/><text x="${x}" y="${y+8}" text-anchor="middle" font-weight="600">${id.slice(1)}</text><text class="m" x="${x}" y="${y+32}" text-anchor="middle" font-size="9.5">${f.fecha.slice(5)}</text></g>`;
      if(j>0){const p=pos[r.ids[j-1]];ln+=`<line x1="${p.x+15}" y1="${y+4}" x2="${x-15}" y2="${y+4}" stroke="var(--line)" stroke-width="2"/>`}});
    if(r.s&&r.s.consultas.length){const x=Wd-80;svg+=`<rect x="${x-12}" y="${y-8}" width="24" height="24" transform="rotate(45 ${x} ${y+4})" fill="none" stroke="var(--hip)" stroke-width="2"/><text x="${x+22}" y="${y+8}" style="fill:var(--hip)">tool ×${r.s.consultas.length}</text>`}});
  const E={};v.signals.forEach(s=>s.contradicciones.forEach(c=>{const k=c.de.split(".")[0]+">"+c.a.split(".")[0];(E[k]=E[k]||{de:c.de.split(".")[0],a:c.a.split(".")[0],rels:[]}).rels.push(c.de+" "+c.relacion+" "+c.a)}));
  Object.values(E).forEach(e=>{const a=pos[e.de],b=pos[e.a];if(!a||!b)return;const rf=e.rels.some(r=>r.includes("refuta")),col=rf?"var(--ref)":"var(--res)",mx=(a.x+b.x)/2,my=a.y-22-Math.min(26,Math.abs(a.x-b.x)*.06);
    svg+=`<path d="M${a.x} ${a.y-11} Q${mx} ${my} ${b.x} ${b.y-11}" fill="none" stroke="${col}" stroke-width="2" ${rf?"":'stroke-dasharray="4 3"'} marker-end="url(#ar)"><title>${e.rels.join("; ")}</title></path>`});
  return `<div class="legend"><span><i style="background:var(--ref)"></i>refuta</span><span><i style="background:var(--res)"></i>resuelve faltante</span><span><i style="background:var(--acc)"></i>fuente incorporada</span><span>◇ consulta a herramienta</span><span>clic en un nodo = ver fuente</span></div>
  <div style="overflow-x:auto"><svg viewBox="0 0 ${Wd} ${H}" width="100%" style="min-width:640px"><defs><marker id="ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="var(--mut)"/></marker></defs>${bg}${ln}${svg}</svg></div>`}
function matrix(v){
  const Wd=640,H=420,m=56,lo=.3,X=e=>m+(Math.max(e,lo)-lo)/(1-lo)*(Wd-2*m),Y=i=>H-m-(Math.max(i,lo)-lo)/(1-lo)*(H-2*m);
  let g=`<line x1="${X(.5)}" y1="${m-10}" x2="${X(.5)}" y2="${H-m}" stroke="var(--line)" stroke-dasharray="4 4"/><line x1="${m}" y1="${Y(.5)}" x2="${Wd-m+10}" y2="${Y(.5)}" stroke="var(--line)" stroke-dasharray="4 4"/>
  <line x1="${m}" y1="${H-m}" x2="${Wd-m+10}" y2="${H-m}" stroke="var(--mut)"/><line x1="${m}" y1="${m-10}" x2="${m}" y2="${H-m}" stroke="var(--mut)"/>
  <text class="m" x="${Wd/2}" y="${H-16}" text-anchor="middle">Evidencia →</text><text class="m" x="16" y="${H/2}" transform="rotate(-90 16 ${H/2})" text-anchor="middle">Impacto →</text>
  ${[["Investigar evidencia",m+8,m-16,"start"],["Actuar / validar ya",Wd-m,m-16,"end"],["Monitorear",m+8,H-m-8,"start"],["Bien documentado, menor impacto",Wd-m,H-m-8,"end"]].map(([t,x,y,a])=>`<text class="m" x="${x}" y="${y}" text-anchor="${a}" font-size="11" opacity=".85">${t}</text>`).join("")}
  <text class="m" x="${m}" y="${H-m+16}" text-anchor="middle" font-size="10">0.3</text><text class="m" x="${Wd-m}" y="${H-m+16}" text-anchor="middle" font-size="10">1.0</text>`;
  v.signals.forEach(s=>{const c=s.componentes,r=10+c.urgencia*18,on=s.id===sel;
    g+=`<g data-s2="${s.id}" style="cursor:pointer"><circle cx="${X(c.evidencia)}" cy="${Y(c.impacto)}" r="${r}" fill="color-mix(in srgb,var(--acc) ${on?55:28}%,transparent)" stroke="var(--acc)" stroke-width="${on?2.5:1}"/><text x="${X(c.evidencia)}" y="${Y(c.impacto)+4}" text-anchor="middle" font-weight="700">${s.id}</text><text class="m" x="${X(c.evidencia)+r+6}" y="${Y(c.impacto)+4}">${s.score}</text></g>`});
  setTimeout(()=>document.querySelectorAll("[data-s2]").forEach(b=>b.onclick=()=>{sel=b.dataset.s2;tab="brief";render()}),0);
  return `<div class="sub" style="margin-bottom:8px">Tamaño de burbuja = urgencia · clic = abrir brief</div><svg viewBox="0 0 ${Wd} ${H}" width="100%" style="max-width:${Wd}px">${g}</svg>`}
function rescore(v){return v.signals.map(s=>{const c=s.componentes;return {s,sc:Math.max(0,100*(W.impacto*c.impacto+W.evidencia*c.evidencia+W.urgencia*c.urgencia)-(c.penalizacion||0))}}).sort((a,b)=>b.sc-a.sc)}
function weights(v){
  return `<div class="sub">Mueve los pesos (se normalizan a 100%) y mira cómo se re-ordena el ranking. Útil para discutir supuestos de negocio con el comité.</div>
  ${["impacto","evidencia","urgencia"].map(k=>`<div class="slider"><label style="margin:0">${k}</label><input type="range" min="0" max="100" value="${Math.round(W[k]*100)}" data-w="${k}"><b id="wv-${k}">${Math.round(W[k]*100)}%</b></div>`).join("")}
  <button class="btn" id="w-reset">Restaurar 45 / 30 / 25</button><div id="w-out" class="sec"></div>`}
function bindWeights(v){
  const orig=v.signals.map(s=>s.id);
  const draw=()=>{$("#w-out").innerHTML=`<table><tr><th>#</th><th>Señal</th><th>Score original</th><th>Score con estos pesos</th><th>Cambio de puesto</th></tr>${rescore(v).map((x,i)=>{const d=orig.indexOf(x.s.id)-i;
    return `<tr><td>${i+1}</td><td><b>${x.s.id}</b> ${esc(x.s.titulo)}</td><td>${x.s.score}</td><td><b>${x.sc.toFixed(1)}</b></td><td>${d?`<span class="delta ${d>0?"up":"dn"}">${d>0?"▲":"▼"} ${Math.abs(d)}</span>`:"="}</td></tr>`}).join("")}</table>`};
  document.querySelectorAll("[data-w]").forEach(r=>r.oninput=()=>{const raw={};document.querySelectorAll("[data-w]").forEach(x=>raw[x.dataset.w]=+x.value);const t=Object.values(raw).reduce((a,b)=>a+b,0)||1;
    for(const k in raw){W[k]=raw[k]/t;$("#wv-"+k).textContent=Math.round(W[k]*100)+"%"}draw()});
  $("#w-reset").onclick=()=>{W={impacto:.45,evidencia:.30,urgencia:.25};render()};draw()}
function trace(v,s){
  const rows=v.log.filter(e=>!e.senal||e.senal===s.titulo);
  return `<div class="sub" style="margin-bottom:10px">Registro observable de acciones (no razonamiento interno) · señal ${s.id}</div><table><tr><th>#</th><th>Acción</th><th>Detalle</th></tr>${rows.map((e,i)=>{let d;
   if(e.accion==="consulta_herramienta")d=`<code class="mono">${e.args.map(esc).join(" · ")}</code><br>${esc(e.motivo)} · ${e.ms} ms<br><span class="sub mono">${esc(JSON.stringify(e.resultado.registros))}</span>`;
   else if(e.accion==="agrupar_fuentes")d=`grupo: ${s.fuentes.join(", ")}`;
   else if(e.accion==="ingestar")d=`${e.n_fuentes} fuentes (sha1 por archivo)`;
   else d=esc(JSON.stringify(Object.fromEntries(Object.entries(e).filter(([k])=>!["accion","senal"].includes(k)))));
   return `<tr><td>${i+1}</td><td><b>${esc(e.accion)}</b></td><td>${d}</td></tr>`}).join("")}</table>
   <div class="sec"><h3>Aspectos no resueltos</h3><ul>${s.claims.filter(c=>c.tipo==="faltante"&&!c.superada).map(c=>`<li>${esc(c.texto)} ${cites("["+c.sid+"]")}</li>`).join("")}</ul></div>`}
// ---------- búsqueda (cliente; en app puede sumar Claude) ----------
function localSearch(q){const toks=q.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g,"").match(/[a-z_]{4,}/g)||[];const v=V[vi];
  const sig={};v.signals.forEach(s=>s.fuentes.forEach(f=>sig[f]=s.id));const stt={};v.signals.forEach(s=>s.claims.forEach(c=>stt[c.sid]=st(c)));
  return v.fuentes.flatMap(f=>f.sents.map(x=>{const t=(x.texto+" "+f.titulo).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g,"");
    const sc=toks.reduce((a,k)=>a+(t.includes(k.slice(0,Math.max(4,k.length-2)))?1:0),0)*(stt[x.sid]==="correccion"?1.35:1);return {sid:x.sid,texto:x.texto,fecha:f.fecha,senal:sig[f.id]||null,estado:stt[x.sid]||null,score:sc}}))
   .filter(h=>h.score>0).sort((a,b)=>b.score-a.score).slice(0,8)}
async function ask(){const q=$("#q").value.trim();if(!q)return;$("#ask-res").innerHTML='<div class="res sub">Buscando…</div>';
  let r;try{r=APP?await api("/api/preguntar",{q,llm:$("#q-llm").checked}):{hits:localSearch(q)}}catch(e){$("#ask-res").innerHTML=`<div class="res">⚠ ${esc(e.message)}</div>`;return}
  let h='<div class="res">';
  if(r.llm){h+=r.llm.error?`<div class="warn">Claude: ${esc(r.llm.error)}</div>`:`<div class="ai"><h3 style="margin:0 0 6px;font-size:12px;color:var(--acc2)">CLAUDE · ${r.llm.aceptada?"citas validadas":"⚠ citas no validadas"} · USD ${r.llm.costo_usd}</h3>${cites(esc(r.llm.respuesta))}</div>`}
  h+=(r.hits.length?r.hits.map(x=>`<div class="hit"><button class="cite" data-src="${x.sid}">[${x.sid}]</button> <span class="chip t-${x.estado||""}">${x.estado?ET[x.estado]:"—"}</span> <span class="chip">${x.senal||"sin señal"}</span> ${esc(x.texto)}</div>`).join(""):"<div class='sub'>Sin coincidencias.</div>")+"</div>";
  $("#ask-res").innerHTML=h;bindCites()}
// ---------- añadir fuente (app) ----------
let FILE=null, PREV=null;
function openAdd(){FILE=null;PREV=null;["f-titulo","f-area","f-texto"].forEach(i=>$("#"+i).value="");$("#f-file").textContent="";$("#prev-res").innerHTML="";$("#b-inc").disabled=true;
  $("#f-id").value=ST?.next_id||"";$("#f-fecha").value=new Date().toISOString().slice(0,10);$("#f-llm").disabled=!ST?.llm.configurada;$("#m-add").classList.add("on")}
function readFile(f){const r=new FileReader();r.onload=()=>{FILE={filename:f.name,b64:r.result.split(",")[1]};$("#f-file").textContent="📄 "+f.name;
  if(/\.(md|txt)$/i.test(f.name)){const t=new TextDecoder().decode(Uint8Array.from(atob(FILE.b64),c=>c.charCodeAt(0)));$("#f-texto").value=t;FILE=null}
  PREV=null;$("#b-inc").disabled=true};r.readAsDataURL(f)}
function payload(){const meta={id:$("#f-id").value,fecha:$("#f-fecha").value,tipo:$("#f-tipo").value,area:$("#f-area").value,titulo:$("#f-titulo").value};
  return FILE?{...FILE,meta}:{texto:$("#f-texto").value,filename:"",meta}}
async function preview(){$("#prev-res").innerHTML='<div class="res sub">Analizando impacto…</div>';
  try{PREV=await api("/api/preview",{...payload(),llm:$("#f-llm").checked})}catch(e){$("#prev-res").innerHTML=`<div class="res">⚠ ${esc(e.message)}</div>`;PREV=null;$("#b-inc").disabled=true;return}
  const p=PREV,f=p.fuente;let h=`<div class="res"><b>${f.id}</b> · ${f.fecha} · ${esc(f.tipo)} · ${esc(f.area)} · ${esc(f.titulo)}`;
  h+=p.descartada?`<div class="warn" style="font-size:13px">Se descartaría como ruido: ${esc(p.descartada.motivo)}</div>`:"";
  h+=`<div class="sec"><h3>Qué cambiaría</h3><ul>${(p.diff?.explicacion||[]).map(l=>`<li>${esc(l)}</li>`).join("")||"<li>Sin cambios materiales</li>"}</ul></div>`;
  if(p.clasificacion.length)h+=`<div class="sec"><h3>Cómo clasifiqué cada oración</h3>${p.clasificacion.map(c=>`<div class="hit"><span class="chip t-${c.tipo}">${ET[c.tipo]}</span> <span class="mono sub">${c.sid}</span> ${esc(c.texto)}</div>`).join("")}</div>`;
  if(p.revision_llm)h+=`<div class="sec ai"><h3 style="color:var(--acc2)">Segunda opinión · Claude (solo relaciones con IDs válidos)</h3>${p.revision_llm.relaciones.map(r=>`<div class="hit"><b>${esc(r.nuevo)}</b> ${esc(r.relacion)} <b>${esc(r.existente)}</b> — ${esc(r.motivo)}</div>`).join("")||"<div class='sub'>Sin relaciones claras.</div>"}${p.revision_llm.riesgo?`<div class="warn">Riesgo de sobreafirmación: ${esc(p.revision_llm.riesgo)}</div>`:""}<div class="sub">USD ${p.revision_llm.costo_usd} · ${p.revision_llm.ms} ms</div></div>`;
  $("#prev-res").innerHTML=h+"</div>";$("#b-inc").disabled=false}
async function incorporate(){if(!PREV)return;$("#b-inc").disabled=true;try{const r=await api("/api/incorporar",{markdown:PREV.markdown});sset("rs-msg",r.explicacion);if(r.cambios&&r.cambios[0])sset("rs-sel",r.cambios[0]);sset("rs-tab","brief");location.reload()}catch(e){toast("⚠ "+e.message,6000);$("#b-inc").disabled=false}}
// ---------- Claude config (app) ----------
async function cfgSave(){try{const r=await api("/api/config",{key:$("#c-key").value||undefined,model:$("#c-model").value||undefined});ST.llm=r;$("#c-key").value="";$("#cfg-res").textContent="Guardado. Key: "+(r.key||"—")+" · modelo "+r.modelo;actions()}catch(e){$("#cfg-res").textContent="⚠ "+e.message}}
async function cfgTest(){$("#cfg-res").textContent="Probando…";try{const r=await api("/api/llm/test",{});$("#cfg-res").textContent=`✅ Conectado · ${r.modelo} · ${r.ms} ms · USD ${r.costo_usd}`}catch(e){$("#cfg-res").textContent="⚠ "+e.message}}
async function cfgSum(){$("#cfg-res").textContent="Generando resúmenes (1 llamada por señal)…";try{const r=await api("/api/llm/resumenes",{});sset("rs-msg",[`Resúmenes de Claude aceptados: ${r.aceptados}/${r.total}`]);location.reload()}catch(e){$("#cfg-res").textContent="⚠ "+e.message}}
// ---------- init ----------
document.querySelectorAll("[data-close]").forEach(b=>b.onclick=()=>b.closest(".modal").classList.remove("on"));
document.querySelectorAll(".modal").forEach(m=>m.onclick=e=>{if(e.target===m)m.classList.remove("on")});
$("#b-ask").onclick=ask;$("#q").onkeydown=e=>{if(e.key==="Enter")ask()};
if(!APP)document.querySelectorAll(".apponly").forEach(e=>e.style.display="none");
$("#drop").onclick=()=>$("#file").click();$("#file").onchange=e=>e.target.files[0]&&readFile(e.target.files[0]);
["dragover","dragenter"].forEach(ev=>$("#drop").addEventListener(ev,e=>{e.preventDefault();$("#drop").classList.add("over")}));
["dragleave","drop"].forEach(ev=>$("#drop").addEventListener(ev,e=>{e.preventDefault();$("#drop").classList.remove("over")}));
$("#drop").addEventListener("drop",e=>e.dataTransfer.files[0]&&readFile(e.dataTransfer.files[0]));
["f-texto","f-id","f-fecha","f-tipo","f-area","f-titulo"].forEach(i=>$("#"+i).addEventListener("input",()=>{PREV=null;$("#b-inc").disabled=true}));
$("#b-prev").onclick=preview;$("#b-inc").onclick=incorporate;$("#b-save").onclick=cfgSave;$("#b-test").onclick=cfgTest;$("#b-sum").onclick=cfgSum;
document.addEventListener("keydown",e=>{if(e.key==="Escape"){$("#drawer").classList.remove("on");document.querySelectorAll(".modal").forEach(m=>m.classList.remove("on"))}
  if(e.target.matches("input,textarea,select"))return;
  if(e.key==="ArrowLeft"&&vi>0){vi--;render()}if(e.key==="ArrowRight"&&vi<V.length-1){vi++;render()}});
(async()=>{if(APP){try{ST=await api("/api/status")}catch(e){}}actions();render();
  const msg=ss("rs-msg",null);if(msg){sset("rs-msg",null);toast(msg.join(" · ").slice(0,260),6500)}})();
</script></body></html>"""
