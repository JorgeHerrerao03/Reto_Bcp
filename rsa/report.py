"""Reporte HTML autocontenido. El mismo archivo funciona:
- estático (doble clic / GitHub Pages): señales, brief, evidencia, análisis, búsqueda, traza;
- 'modo app' (python -m rsa app): además añadir fuentes con preview, deshacer, demos y Claude.
Estilo: paleta corporativa azul/naranja inspirada en banca peruana; sin logos ni imágenes de terceros."""
from __future__ import annotations

import base64
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


BRAND_TXT = '<div>Revenue Signals<small>Prototipo · reto técnico · datos sintéticos</small></div>'


def _brand():
    """Logo opcional SOLO local: marca/logo.png (excluido de git, no se publica en GitHub Pages)."""
    from .engine import AGENT_DIR
    f = AGENT_DIR / "marca" / "logo.png"
    if f.exists():
        b64 = base64.b64encode(f.read_bytes()).decode()
        return (f'<div class="brand"><span class="logo"><img src="data:image/png;base64,{b64}" alt="Logo"></span>'
                f'<span class="sep"></span>{BRAND_TXT}</div>')
    return f'<div class="brand"><i></i>{BRAND_TXT}</div>'


def write(state, path):
    data = json.dumps(_slim(state), ensure_ascii=False).replace("</", "<\\/")
    path.write_text(HTML.replace("/*__DATA__*/null", data).replace("<!--BRAND-->", _brand()), encoding="utf-8")


HTML = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Revenue Signals</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Nunito+Sans:opsz,wght@6..12,400;6..12,600;6..12,700;6..12,800&display=swap" rel="stylesheet">
<style>
:root{--blue:#002a8d;--blue2:#0039c6;--orange:#ff7800;--orange2:#e86c00;--bg:#f4f6fb;--panel:#fff;--ink:#0b1b4a;--mut:#5b6787;
--line:#e3e8f2;--soft:#eef2fb;--hecho:#0f8a5f;--hip:#c27a00;--falt:#6b4fd8;--adv:#8a6d3b;--corr:#0039c6;--ref:#d4351c;--res:#0f8a5f;
--shadow:0 1px 2px rgba(0,42,141,.06),0 6px 20px -10px rgba(0,42,141,.18);--hdr:#002a8d;--hdrink:#fff;--bt:#002a8d}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0a1130;--panel:#111a3f;--ink:#eef2ff;--mut:#a3aed0;--line:#223063;
--soft:#16224f;--hecho:#3fd19a;--hip:#ffb547;--falt:#a993ff;--adv:#d0b07a;--corr:#7aa2ff;--ref:#ff7a66;--res:#3fd19a;--hdr:#061a5e;--shadow:0 8px 24px -12px rgba(0,0,0,.6);--bt:#a9c1ff;--blue2:#7aa2ff}}
:root[data-theme=dark]{--bg:#0a1130;--panel:#111a3f;--ink:#eef2ff;--mut:#a3aed0;--line:#223063;--soft:#16224f;--hecho:#3fd19a;--hip:#ffb547;
--falt:#a993ff;--adv:#d0b07a;--corr:#7aa2ff;--ref:#ff7a66;--res:#3fd19a;--hdr:#061a5e;--shadow:0 8px 24px -12px rgba(0,0,0,.6);--bt:#a9c1ff;--blue2:#7aa2ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 "Nunito Sans","Segoe UI",system-ui,sans-serif}
button{font:inherit}.mono{font-family:ui-monospace,Consolas,monospace;font-size:.88em}
.sub{color:var(--mut);font-size:13px}
/* header */
.hdr{background:var(--hdr);color:var(--hdrink)}
.hdr .in{max-width:1320px;margin:0 auto;padding:14px 24px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:10px;font-weight:800;font-size:19px;letter-spacing:-.01em}
.brand i{width:12px;height:12px;border-radius:50%;background:var(--orange);display:inline-block}
.brand .logo{background:#fff;border-radius:10px;padding:6px 10px;display:flex}.brand .logo img{height:26px;display:block}.brand .sep{width:1px;height:30px;background:rgba(255,255,255,.35)}
.brand small{display:block;font-weight:600;font-size:12px;opacity:.75;letter-spacing:0}
.hdr .acts{margin-left:auto;display:flex;gap:8px;align-items:center;position:relative}
.btn{border:1.5px solid var(--line);background:var(--panel);color:var(--ink);border-radius:999px;padding:8px 16px;cursor:pointer;font-weight:700;font-size:14px}
.btn:hover{border-color:var(--blue2)}.btn:disabled{opacity:.45;cursor:not-allowed}
.btn.pri{background:var(--orange);border-color:var(--orange);color:#fff}.btn.pri:hover{background:var(--orange2)}
.btn.ghost{background:transparent;border-color:rgba(255,255,255,.45);color:#fff}.btn.ghost:hover{border-color:#fff}
.btn.sm{padding:6px 12px;font-size:13px}
.menu{position:absolute;right:0;top:46px;background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);min-width:230px;padding:6px;display:none;z-index:25}
.menu.on{display:block}.menu button{display:block;width:100%;text-align:left;border:0;background:none;padding:9px 12px;border-radius:9px;cursor:pointer;color:var(--ink);font-weight:600}
.menu button:hover{background:var(--soft)}.menu hr{border:0;border-top:1px solid var(--line);margin:6px 0}
/* subbar */
.subbar{background:var(--panel);border-bottom:1px solid var(--line)}
.subbar .in{max-width:1320px;margin:0 auto;padding:10px 24px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.ver{display:flex;align-items:center;gap:6px}.ver label{font-weight:700;font-size:13px;color:var(--mut)}
.ver select{font:inherit;font-weight:700;color:var(--ink);background:var(--soft);border:1px solid var(--line);border-radius:999px;padding:6px 12px;max-width:420px}
.arrow{width:32px;height:32px;border-radius:50%;border:1px solid var(--line);background:var(--panel);color:var(--ink);cursor:pointer}
.stats{margin-left:auto;display:flex;gap:18px;flex-wrap:wrap;font-size:13px;color:var(--mut)}.stats b{color:var(--ink);font-size:15px;margin-right:4px}
.badge{font-size:12px;font-weight:700;padding:3px 10px;border-radius:999px;background:var(--soft);color:var(--blue2)}
/* layout */
.wrap{max-width:1320px;margin:0 auto;display:grid;grid-template-columns:330px 1fr;gap:20px;padding:20px 24px 48px}
@media(max-width:920px){.wrap{grid-template-columns:1fr;padding:16px}.hdr .in,.subbar .in{padding-left:16px;padding-right:16px}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow)}
.h-list{font-size:12px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);margin:2px 4px 10px}
.sig{padding:14px 16px;margin-bottom:10px;cursor:pointer;border-left:4px solid transparent;transition:border-color .15s,transform .15s}
.sig:hover{transform:translateY(-1px)}.sig.on{border-left-color:var(--orange)}
.sig .r{display:flex;gap:10px;align-items:flex-start}
.rank{flex:none;width:26px;height:26px;border-radius:50%;background:var(--soft);color:var(--blue2);font-weight:800;font-size:13px;display:grid;place-items:center}
.sig.on .rank{background:var(--blue);color:#fff}
.sig h3{margin:0;font-size:15px;line-height:1.3;font-weight:700;flex:1}
.sc{font-size:22px;font-weight:800;color:var(--bt);line-height:1}.sig.on .sc{color:var(--orange)}
.bar{height:5px;border-radius:3px;background:var(--soft);margin:10px 0 8px;overflow:hidden}.bar i{display:block;height:100%;background:var(--blue2);border-radius:3px}
.sig.on .bar i{background:var(--orange)}
.meta{display:flex;justify-content:space-between;flex-wrap:wrap;gap:2px 8px;font-size:12.5px;color:var(--mut)}
.delta{font-size:12px;font-weight:800;padding:1px 8px;border-radius:999px;margin-left:6px}.up{color:var(--res);background:color-mix(in srgb,var(--res) 12%,transparent)}.dn{color:var(--ref);background:color-mix(in srgb,var(--ref) 12%,transparent)}
details.noise{padding:12px 16px}details.noise summary{cursor:pointer;font-weight:700;font-size:14px}
details.noise div{font-size:13px;color:var(--mut);padding:6px 0;border-top:1px dashed var(--line)}
/* main */
.changes{padding:14px 18px;margin-bottom:16px;border-left:4px solid var(--orange)}
.changes summary{cursor:pointer;font-weight:800}.changes ul{margin:10px 0 0;padding-left:18px}.changes li{margin:4px 0;font-size:14px}
.seg{display:inline-flex;background:var(--soft);border-radius:999px;padding:4px;gap:2px;margin:16px 20px 0;flex-wrap:wrap}
.seg button{border:0;background:none;padding:8px 16px;border-radius:999px;cursor:pointer;color:var(--mut);font-weight:700;font-size:14px}
.seg button.on{background:var(--panel);color:var(--bt);box-shadow:0 1px 3px rgba(0,42,141,.15)}
.pane{padding:20px 24px 26px}
.top{display:flex;gap:16px;align-items:flex-start;flex-wrap:wrap}.top h2{margin:2px 0 8px;font-size:23px;line-height:1.2;letter-spacing:-.01em}
.big{font-size:46px;font-weight:800;line-height:1;color:var(--bt);text-align:right}
.pill{display:inline-block;padding:5px 12px;border-radius:999px;font-weight:700;font-size:13px;background:color-mix(in srgb,var(--orange) 14%,transparent);color:var(--orange2)}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:16px 0}@media(max-width:600px){.tiles{grid-template-columns:1fr}}
.tile{background:var(--soft);border-radius:12px;padding:10px 14px}.tile b{font-size:20px;color:var(--bt)}.tile span{display:block;font-size:12px;color:var(--mut);font-weight:700;text-transform:uppercase;letter-spacing:.05em}
.tile .tb{height:4px;background:var(--line);border-radius:2px;margin-top:6px}.tile .tb i{display:block;height:100%;background:var(--blue2);border-radius:2px}
.callout{border-radius:14px;padding:14px 18px;margin:14px 0}.callout h4{margin:0 0 6px;font-size:13px;font-weight:800;letter-spacing:.05em;text-transform:uppercase}
.callout ul{margin:0;padding-left:18px}.callout li{margin:3px 0}
.no{background:color-mix(in srgb,var(--ref) 7%,var(--panel));border:1px solid color-mix(in srgb,var(--ref) 25%,var(--line))}.no h4{color:var(--ref)}
.ai{background:color-mix(in srgb,var(--blue2) 7%,var(--panel));border:1px solid color-mix(in srgb,var(--blue2) 25%,var(--line))}.ai h4{color:var(--blue2)}
details.grp{border-top:1px solid var(--line);padding:4px 0}details.grp>summary{cursor:pointer;list-style:none;padding:12px 0;font-weight:800;display:flex;align-items:center;gap:8px}
details.grp>summary::-webkit-details-marker{display:none}details.grp>summary:before{content:"›";display:inline-block;transition:transform .15s;color:var(--mut);font-size:18px;width:12px}
details.grp[open]>summary:before{transform:rotate(90deg)}
.cnt{font-size:12px;font-weight:800;padding:1px 9px;border-radius:999px;background:var(--soft);color:var(--mut)}
.cl{display:grid;grid-template-columns:1fr auto;gap:12px;padding:8px 0 8px 20px;font-size:14.5px}
.cl.sup .tx{text-decoration:line-through;opacity:.55}.cl.nuevo{background:color-mix(in srgb,var(--orange) 8%,transparent);border-radius:8px}
.tag{font-size:11.5px;font-weight:800;padding:1px 8px;border-radius:999px;background:var(--soft);margin-right:6px}
.t-hecho{color:var(--hecho)}.t-hipotesis{color:var(--hip)}.t-faltante{color:var(--falt)}.t-advertencia{color:var(--adv)}.t-correccion{color:var(--corr)}.t-refutada{color:var(--ref)}.t-resuelta{color:var(--res)}
.cite{color:var(--blue2);cursor:pointer;white-space:nowrap;border:0;background:none;font-weight:700;font-size:12.5px;padding:0}.cite:hover{text-decoration:underline}
.trans{font-size:12px;font-weight:700;color:var(--ref)}
.tool{border:1px solid var(--line);border-radius:12px;padding:10px 14px;margin:8px 0 0 20px;font-size:13.5px}
.warn{color:var(--hip);font-size:13px;margin:8px 0 0 20px}
ol.steps{margin:0;padding-left:40px}ol.steps li{margin:5px 0;font-size:14.5px}
table{border-collapse:collapse;width:100%;font-size:13.5px}td,th{border-top:1px solid var(--line);padding:8px;text-align:left;vertical-align:top}
td{overflow-wrap:anywhere}th{color:var(--mut);font-weight:800;font-size:12px;text-transform:uppercase;letter-spacing:.05em}
svg text{fill:var(--ink);font-size:11px;font-family:"Nunito Sans",sans-serif}svg .m{fill:var(--mut)}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:var(--mut);margin-bottom:10px}.legend i{display:inline-block;width:18px;height:3px;vertical-align:middle;margin-right:5px;border-radius:2px}
h3.sect{font-size:16px;margin:26px 0 6px}
.slider{display:grid;grid-template-columns:100px 1fr 50px;gap:12px;align-items:center;margin:8px 0}.slider span{font-weight:700;text-transform:capitalize}
input[type=range]{accent-color:var(--orange)}
/* drawer, modal */
.drawer{position:fixed;top:0;right:0;height:100%;width:min(460px,100%);background:var(--panel);border-left:1px solid var(--line);box-shadow:-20px 0 40px -20px rgba(0,0,0,.3);transform:translateX(105%);transition:transform .25s;z-index:20;overflow:auto;padding:24px}
.drawer.on{transform:none}.x{float:right;border:0;background:var(--soft);color:var(--ink);border-radius:999px;width:32px;height:32px;cursor:pointer}
.drawer p{margin:6px 0;padding:8px 10px;border-radius:8px}.drawer p.hl{background:color-mix(in srgb,var(--orange) 16%,transparent)}
.flash{animation:fl 1.4s ease}@keyframes fl{0%{background:color-mix(in srgb,var(--orange) 28%,transparent)}100%{background:transparent}}
.modal{position:fixed;inset:0;background:rgba(0,20,70,.45);display:none;align-items:flex-start;justify-content:center;z-index:30;padding:40px 16px;overflow:auto}
.modal.on{display:flex}.modal .card{width:min(720px,100%);padding:24px 26px}.modal h2{margin:0 0 4px;font-size:21px;color:var(--bt)}
.step{display:flex;gap:10px;align-items:center;margin:18px 0 8px;font-weight:800}.step b{width:24px;height:24px;border-radius:50%;background:var(--blue);color:#fff;display:grid;place-items:center;font-size:12.5px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}@media(max-width:700px){.grid{grid-template-columns:1fr 1fr}}
label.f{font-size:12px;color:var(--mut);font-weight:700;display:block}
input,select,textarea{width:100%;font:inherit;font-size:14px;color:var(--ink);background:var(--panel);border:1.5px solid var(--line);border-radius:10px;padding:9px 11px;margin-top:4px}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--blue2)}
textarea{min-height:120px;resize:vertical}
.drop{border:2px dashed var(--line);border-radius:14px;padding:20px;text-align:center;color:var(--mut);cursor:pointer;font-weight:700}
.drop.over,.drop:hover{border-color:var(--orange);color:var(--orange2)}
.or{text-align:center;color:var(--mut);font-size:13px;margin:10px 0}
.row{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px;align-items:center}
.chk{display:flex;gap:6px;align-items:center;font-size:14px;font-weight:600;color:var(--mut)}.chk input{width:auto;margin:0}
.res{margin-top:16px;border-top:1px solid var(--line);padding-top:14px}
.hit{padding:9px 0;border-top:1px solid var(--line);font-size:14px}
.toast{position:fixed;bottom:20px;right:20px;max-width:min(420px,calc(100% - 40px));font-size:13.5px;background:var(--blue);color:#fff;padding:12px 18px;border-radius:12px;z-index:40;display:none;font-weight:600;box-shadow:var(--shadow)}
.foot{max-width:1320px;margin:0 auto;padding:0 24px 30px;color:var(--mut);font-size:12.5px}
@media print{.hdr .acts,.subbar,aside,.seg,.drawer,.modal,.toast,.foot{display:none!important}.wrap{display:block;padding:0}.card{box-shadow:none;border:0}body{background:#fff}details{display:block}}
</style></head><body>
<div class="hdr"><div class="in"><!--BRAND-->
<div class="acts" id="acts"></div></div></div>
<div class="subbar"><div class="in">
<div class="ver"><label for="vsel">Versión</label><button class="arrow" id="vprev" title="Anterior (←)">‹</button><select id="vsel"></select><button class="arrow" id="vnext" title="Siguiente (→)">›</button></div>
<span id="mode" class="badge"></span><div class="stats" id="stats"></div></div></div>
<div class="wrap"><aside id="list"></aside><main id="main"></main></div>
<div class="foot">Prototipo de candidato sobre fuentes ficticias del reto. No representa datos ni sistemas reales.</div>
<div class="drawer" id="drawer"></div>
<div class="modal" id="m-add"><div class="card"><button class="x" data-close>✕</button><h2>Añadir fuente</h2>
<div class="sub">Sube un archivo o pega el texto. Antes de guardar verás qué cambiaría.</div>
<div class="step"><b>1</b>Contenido</div>
<div class="drop" id="drop">📄 Arrastra aquí un .md, .txt o .docx — o haz clic para elegir<input type="file" id="file" accept=".md,.txt,.docx" hidden></div>
<div class="or">o pega el texto</div><textarea id="f-texto" placeholder="Ej.: Tecnología aclara que la captura revisada correspondía al entorno de certificación…"></textarea>
<div class="sub" id="f-file" style="margin-top:6px"></div>
<div class="step"><b>2</b>Datos de la fuente <span class="sub" style="font-weight:600">(si el archivo ya trae encabezado, se respeta)</span></div>
<div class="grid"><div><label class="f">ID</label><input id="f-id"></div><div><label class="f">Fecha</label><input id="f-fecha" type="date"></div>
<div><label class="f">Tipo</label><select id="f-tipo"><option>Correo</option><option>Teams</option><option>Acta</option><option>Acta de reunión</option><option>Documento</option><option>Ficha técnica</option><option>Política comercial</option></select></div>
<div><label class="f">Área</label><input id="f-area" placeholder="Operaciones"></div></div>
<div style="margin-top:10px"><label class="f">Título</label><input id="f-titulo" placeholder="Opcional: se toma del archivo"></div>
<div class="step"><b>3</b>Revisar y guardar</div>
<div class="row" style="margin-top:4px"><button class="btn" id="b-prev">Previsualizar impacto</button><button class="btn pri" id="b-inc" disabled>Incorporar</button>
<label class="chk"><input type="checkbox" id="f-llm"> Segunda opinión de Claude</label></div><div id="prev-res"></div></div></div>
<div class="modal" id="m-ask"><div class="card"><button class="x" data-close>✕</button><h2>Preguntar a las fuentes</h2>
<div class="sub">Busca en cada oración de la versión vigente. En la app, Claude puede redactar la respuesta citando solo esa evidencia.</div>
<div class="row"><input id="q" placeholder="¿El piloto de fechas de pago está en producción?" style="flex:1;margin:0"><button class="btn pri" id="b-ask">Buscar</button>
<label class="chk apponly"><input type="checkbox" id="q-llm"> con Claude</label></div><div id="ask-res"></div></div></div>
<div class="modal" id="m-cfg"><div class="card"><button class="x" data-close>✕</button><h2>Conectar Claude (opcional)</h2>
<div class="sub">La API key se guarda solo en el archivo <span class="mono">.env</span> de tu PC (excluido de git). Sin key todo funciona en modo determinístico.</div>
<div class="grid" style="grid-template-columns:2fr 1fr;margin-top:14px"><div><label class="f">ANTHROPIC_API_KEY</label><input id="c-key" type="password" placeholder="sk-ant-…"></div>
<div><label class="f">Modelo</label><input id="c-model" placeholder="claude-haiku-5-5"></div></div>
<div class="row"><button class="btn pri" id="b-save">Guardar</button><button class="btn" id="b-test">Probar conexión</button><button class="btn" id="b-sum">Generar resúmenes</button></div><div id="cfg-res" class="res sub"></div></div></div>
<div class="toast" id="toast"></div>
<script>
const V=/*__DATA__*/null, APP=!!window.RSA_APP;
const $=s=>document.querySelector(s), esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const ET={hecho:"Hecho",hipotesis:"Hipótesis",faltante:"Faltante",advertencia:"Advertencia",correccion:"Corrección",refutada:"Refutada",resuelta:"Resuelta"};
const ss=(k,d)=>{try{return JSON.parse(sessionStorage.getItem(k))??d}catch(e){return d}}, sset=(k,v)=>{try{sessionStorage.setItem(k,JSON.stringify(v))}catch(e){}};
let vi=V.length-1, sel=ss("rs-sel",null), tab=ss("rs-tab","resumen"), W={impacto:.45,evidencia:.30,urgencia:.25}, ST=null;
if(!["resumen","evidencia","analisis","traza"].includes(tab))tab="resumen";
try{const t=localStorage.getItem("rs-theme");if(t)document.documentElement.dataset.theme=t}catch(e){}
const st=c=>c.superada||c.tipo;
const short=r=>r.startsWith("Investigar con prioridad")?"Prioridad alta":r.startsWith("Investigar")?"Investigar":"Monitorear";
function toast(m,ms=3500){const t=$("#toast");t.textContent=m;t.style.display="block";clearTimeout(t._h);t._h=setTimeout(()=>t.style.display="none",ms)}
async function api(path,body){const r=await fetch(path,{method:body===undefined?"GET":"POST",headers:{"Content-Type":"application/json"},body:body===undefined?undefined:JSON.stringify(body)});
  const j=await r.json();if(!r.ok)throw new Error(j.error||r.status);return j}
function prevSig(id){return vi>0?V[vi-1].signals.find(s=>s.id===id):null}
// ---------- header ----------
function header(){
  const menu=APP?[["undo","↶ Deshacer última fuente"],["-"],["d1","Demo · fuente que contradice"],["d2","Demo · fuente que confirma"],["d3","Demo · fuente de ruido"],["-"],["cfg","Conectar Claude"],["print","Imprimir / PDF"],["theme","Cambiar tema"],["-"],["reset","Reiniciar a las 18 fuentes"]]
    :[["print","Imprimir / PDF"],["theme","Cambiar tema"]];
  $("#acts").innerHTML=`<button class="btn ghost" data-a="ask">${APP?"Preguntar":"Buscar"}</button>${APP?`<button class="btn pri" data-a="add">＋ Añadir fuente</button>`:""}
   <button class="btn ghost" id="more" aria-label="Más opciones">⋯</button><div class="menu" id="menu">${menu.map(([k,n])=>k==="-"?"<hr>":`<button data-a="${k}">${n}</button>`).join("")}</div>`;
  $("#more").onclick=e=>{e.stopPropagation();$("#menu").classList.toggle("on")};
  document.querySelectorAll("[data-a]").forEach(b=>b.onclick=()=>{$("#menu").classList.remove("on");act(b.dataset.a)});
  $("#mode").textContent=APP?(ST?.llm.configurada?"App local · Claude conectado":"App local"):"Solo lectura";
}
document.addEventListener("click",()=>$("#menu")?.classList.remove("on"));
async function act(k){
  if(k==="theme"){const r=document.documentElement,d=matchMedia("(prefers-color-scheme: dark)").matches,n=(r.dataset.theme||(d?"dark":"light"))==="dark"?"light":"dark";r.dataset.theme=n;try{localStorage.setItem("rs-theme",n)}catch(e){}return}
  if(k==="print")return window.print();
  if(k==="ask"){$("#m-ask").classList.add("on");$("#q").focus();return}
  if(k==="add")return openAdd();
  if(k==="cfg"){$("#m-cfg").classList.add("on");$("#c-model").value=ST?.llm.modelo||"";$("#cfg-res").textContent=ST?.llm.configurada?"Key actual: "+ST.llm.key:"Sin key configurada.";return}
  const map={undo:["/api/deshacer",{}],reset:["/api/reset",{}],d1:["/api/demo",{caso:"contradice"}],d2:["/api/demo",{caso:"confirma"}],d3:["/api/demo",{caso:"ruido"}]};
  if(k==="reset"&&!confirm("¿Reiniciar a las 18 fuentes originales? Se retiran las fuentes incorporadas."))return;
  try{toast("Procesando…");const r=await api(...map[k]);if(r.cambios&&r.cambios[0])sset("rs-sel",r.cambios[0]);sset("rs-msg",r.explicacion||[r.retirada?`Retirada ${r.retirada}`:"Listo"]);location.reload()}catch(e){toast("⚠ "+e.message,6000)}
}
// ---------- render ----------
function render(){
  const v=V[vi]; if(!sel||!v.signals.find(s=>s.id===sel)) sel=v.signals[0]?.id; sset("rs-sel",sel); sset("rs-tab",tab);
  $("#vsel").innerHTML=V.map((x,i)=>`<option value="${i}" ${i===vi?"selected":""}>v${x.v} · ${esc(x.evento)}</option>`).join("");
  $("#vprev").disabled=vi===0;$("#vnext").disabled=vi===V.length-1;
  const nc=v.log.filter(l=>l.accion==="consulta_herramienta").length;
  $("#stats").innerHTML=[[v.fuentes.length,"fuentes"],[v.signals.length,"señales"],[v.descartadas.length,"descartadas"],[nc,"consultas a la herramienta"]].map(([n,k])=>`<span><b>${n}</b>${k}</span>`).join("");
  $("#list").innerHTML=`<div class="h-list">Señales priorizadas</div>`+v.signals.map((s,i)=>{const p=prevSig(s.id);const d=p?Math.round((s.score-p.score)*10)/10:null;const c=s.conteo;
    return `<div class="card sig ${s.id===sel?"on":""}" data-s="${s.id}"><div class="r"><span class="rank">${i+1}</span><h3>${esc(s.titulo)}</h3><span class="sc">${s.score}</span></div>
    <div class="bar"><i style="width:${s.score}%"></i></div>
    <div class="meta"><span>${short(s.recomendacion)}${d?`<span class="delta ${d>0?"up":"dn"}">${d>0?"▲":"▼"}${Math.abs(d)}</span>`:""}${p===undefined&&vi>0?`<span class="delta up">nueva</span>`:""}</span><span>${c.hecho||0} hechos · ${(c.hipotesis||0)} hip. · ${c.faltante||0} faltan</span></div></div>`}).join("")
   +`<details class="card noise"><summary>Descartadas como ruido (${v.descartadas.length})</summary>${v.descartadas.map(d=>`<div><button class="cite" data-src="${d.fuente}">${d.fuente}</button> ${esc(d.motivo)}</div>`).join("")||"<div>—</div>"}</details>`;
  document.querySelectorAll("[data-s]").forEach(b=>b.onclick=()=>{sel=b.dataset.s;render()});
  const s=v.signals.find(x=>x.id===sel), d=v.diff; let h="";
  if(d&&d.explicacion.length)h+=`<details class="card changes" open><summary>Qué cambió en v${v.v} · ${esc(v.evento)}</summary><ul>${d.explicacion.map(l=>`<li>${cites(esc(l))}</li>`).join("")}</ul></details>`;
  h+=`<div class="card"><div class="seg">${[["resumen","Resumen"],["evidencia","Evidencia"],["analisis","Análisis"],["traza","Traza"]].map(([k,n])=>`<button class="${tab===k?"on":""}" data-t="${k}">${n}</button>`).join("")}</div><div class="pane">`;
  h+=!s?"<p>Sin señales.</p>":tab==="resumen"?brief(s,d):tab==="evidencia"?graph(v):tab==="analisis"?matrix(v)+weights(v):trace(v,s);
  $("#main").innerHTML=h+"</div></div>";
  document.querySelectorAll("[data-t]").forEach(b=>b.onclick=()=>{tab=b.dataset.t;render()});
  if(tab==="analisis"){bindWeights(v);document.querySelectorAll("[data-s2]").forEach(b=>b.onclick=()=>{sel=b.dataset.s2;tab="resumen";render()})}
  const dl=$("#dl-md");if(dl)dl.onclick=()=>{const b=new Blob([s.brief_md],{type:"text/markdown"});const a=document.createElement("a");a.href=URL.createObjectURL(b);a.download=`${s.id}_brief.md`;a.click()};
  bindCites();
}
$("#vsel").onchange=e=>{vi=+e.target.value;render()};$("#vprev").onclick=()=>{if(vi>0){vi--;render()}};$("#vnext").onclick=()=>{if(vi<V.length-1){vi++;render()}};
function cites(h){return h.replace(/\[(F\d+(?:\.\d+)?)\]/g,(m,id)=>`<button class="cite" data-src="${id}">[${id}]</button>`)}
function bindCites(){document.querySelectorAll("[data-src]").forEach(b=>b.onclick=e=>{e.stopPropagation();openSrc(b.dataset.src)})}
function openSrc(id){const v=V[vi],[fid]=id.split("."),f=v.fuentes.find(x=>x.id===fid);if(!f)return;
  $("#drawer").innerHTML=`<button class="x" onclick="this.parentNode.classList.remove('on')">✕</button><div class="sub">${f.id} · ${f.fecha} · ${esc(f.tipo)} · ${esc(f.area)}${f.origen==="incorporada"?" · <b style='color:var(--orange2)'>incorporada</b>":""}</div>
  <h2 style="margin:8px 0 14px;font-size:20px;color:var(--bt)">${esc(f.titulo)}</h2>${f.sents.map(x=>`<p class="${x.sid===id?"hl":""}"><span class="mono sub">${x.sid}</span> ${esc(x.texto)}</p>`).join("")}<div class="sub mono" style="margin-top:14px">sha1 ${f.sha1}</div>`;
  $("#drawer").classList.add("on")}
function brief(s,d){
  const ch=d&&d.cambios[s.id]; const tr={}; (ch?.transiciones||[]).forEach(t=>tr[t.sid]=t); const nw=new Set((ch?.claims_nuevos||[]).map(c=>c.sid)); const C=s.componentes;
  let h=`<div class="top"><div style="flex:1;min-width:260px"><div class="sub">${s.id} · ${s.areas.join(" · ")}</div><h2>${esc(s.titulo)}</h2><span class="pill">${esc(s.recomendacion)}</span></div>
  <div><div class="big">${s.score}</div><div class="sub" style="text-align:right">de 100 · madurez ${s.confianza}</div><div style="text-align:right;margin-top:8px"><button class="btn sm" id="dl-md">⬇ Descargar brief</button></div></div></div>
  <div class="tiles">${[["impacto","Impacto"],["evidencia","Evidencia"],["urgencia","Urgencia"]].map(([k,n])=>`<div class="tile"><span>${n} · peso ${Math.round(s.pesos[k]*100)}%</span><b>${C[k]}</b><div class="tb"><i style="width:${C[k]*100}%"></i></div></div>`).join("")}</div>
  ${C.penalizacion?`<div class="sub" style="margin:-6px 0 8px">Penalización por evidencia refutada: <b style="color:var(--ref)">−${C.penalizacion}</b></div>`:""}`;
  if(s.resumen_llm)h+=`<div class="callout ai"><h4>Resumen ejecutivo · Claude (citas validadas)</h4>${cites(esc(s.resumen_llm))}</div>`;
  if(s.no_afirmo.length)h+=`<div class="callout no"><h4>Lo que NO afirmo</h4><ul>${s.no_afirmo.map(x=>`<li>${esc(x)}</li>`).join("")}</ul></div>`;
  for(const [t,n,open] of [["hecho","Hechos confirmados",1],["hipotesis","Hipótesis",1],["faltante","Datos faltantes",0],["correccion","Correcciones",1],["advertencia","Advertencias",0]]){const xs=s.claims.filter(c=>c.tipo===t);if(!xs.length)continue;
    h+=`<details class="grp" ${open||xs.some(c=>nw.has(c.sid)||c.superada)?"open":""}><summary>${n}<span class="cnt">${xs.length}</span></summary>${xs.map(c=>`<div class="cl ${c.superada?"sup":""} ${nw.has(c.sid)?"nuevo flash":""}">
    <div>${c.superada?`<span class="tag t-${st(c)}">${ET[st(c)]}</span>`:""}<span class="tx">${esc(c.texto)}</span>${c.superada?` <span class="trans">por ${cites("["+c.por+"]")}</span>`:""}${tr[c.sid]?` <span class="trans">(cambió: ${ET[tr[c.sid].de]} → ${ET[tr[c.sid].a]})</span>`:""}</div>
    <button class="cite" data-src="${c.sid}">[${c.sid}]</button></div>`).join("")}</details>`}
  if(s.consultas.length)h+=`<details class="grp" open><summary>Consulta a la herramienta<span class="cnt">${s.consultas.length}</span></summary>${s.consultas.map(c=>`<div class="tool"><span class="mono">consultar_parametros.py ${c.args.map(a=>"'"+esc(a)+"'").join(" ")}</span><div>${cites(esc(c.lectura))}</div></div>`).join("")}<div class="warn">⚠ ${esc(s.consultas[0].resultado.advertencia||"")}</div></details>`;
  if(s.proximos_pasos.length)h+=`<details class="grp" open><summary>Próximos pasos<span class="cnt">${s.proximos_pasos.length}</span></summary><ol class="steps">${s.proximos_pasos.map(p=>`<li>${esc(p.texto)} ${cites("["+p.sid+"]")}</li>`).join("")}</ol></details>`;
  return h}
function graph(v){
  const Wd=900,rowH=92,x0=210,top=58,rows=[...v.signals.map(s=>({s,ids:s.fuentes})),{s:null,ids:v.descartadas.map(d=>d.fuente)}];
  const H=rows.length*rowH+top,pos={};let svg="",bg="",ln="";
  rows.forEach((r,i)=>{const y=top+i*rowH,n=r.ids.length,step=Math.min(100,(Wd-x0-110)/Math.max(n,1));
    bg+=`<rect x="6" y="${y-22}" width="${Wd-12}" height="${rowH-12}" rx="14" fill="${r.s&&r.s.id===sel?"color-mix(in srgb,var(--orange) 9%,transparent)":"var(--soft)"}"/>`;
    svg+=`<text x="22" y="${y-1}" font-weight="800" style="fill:${r.s?"var(--blue2)":"var(--mut)"}">${r.s?r.s.id+" · "+r.s.score:"Ruido"}</text><text class="m" x="22" y="${y+15}">${esc((r.s?r.s.titulo:"sin impacto económico").slice(0,30))}</text>`;
    r.ids.forEach((id,j)=>{const x=x0+j*step+20;pos[id]={x,y};const f=v.fuentes.find(z=>z.id===id);
      svg+=`<g data-src="${id}" style="cursor:pointer"><circle cx="${x}" cy="${y+4}" r="15" fill="var(--panel)" stroke="${!r.s?"var(--mut)":f.origen==="incorporada"?"var(--orange)":"var(--blue2)"}" stroke-width="${f.origen==="incorporada"?3:1.8}"/><text x="${x}" y="${y+8}" text-anchor="middle" font-weight="800">${id.slice(1)}</text><text class="m" x="${x}" y="${y+32}" text-anchor="middle" font-size="9.5">${f.fecha.slice(5)}</text></g>`;
      if(j>0){const p=pos[r.ids[j-1]];ln+=`<line x1="${p.x+15}" y1="${y+4}" x2="${x-15}" y2="${y+4}" stroke="var(--line)" stroke-width="2"/>`}});
    if(r.s&&r.s.consultas.length){const x=Wd-80;svg+=`<rect x="${x-11}" y="${y-7}" width="22" height="22" rx="3" transform="rotate(45 ${x} ${y+4})" fill="none" stroke="var(--orange)" stroke-width="2"/><text x="${x+22}" y="${y+8}" style="fill:var(--orange2)" font-weight="700">tool ×${r.s.consultas.length}</text>`}});
  const E={};v.signals.forEach(s=>s.contradicciones.forEach(c=>{const k=c.de.split(".")[0]+">"+c.a.split(".")[0];(E[k]=E[k]||{de:c.de.split(".")[0],a:c.a.split(".")[0],rels:[]}).rels.push(c.de+" "+c.relacion+" "+c.a)}));
  Object.values(E).forEach(e=>{const a=pos[e.de],b=pos[e.a];if(!a||!b)return;const rf=e.rels.some(r=>r.includes("refuta")),col=rf?"var(--ref)":"var(--res)",mx=(a.x+b.x)/2,my=a.y-22-Math.min(26,Math.abs(a.x-b.x)*.06);
    svg+=`<path d="M${a.x} ${a.y-11} Q${mx} ${my} ${b.x} ${b.y-11}" fill="none" stroke="${col}" stroke-width="2" ${rf?"":'stroke-dasharray="4 3"'} marker-end="url(#ar)"><title>${e.rels.join("; ")}</title></path>`});
  return `<div class="legend"><span><i style="background:var(--ref)"></i>refuta</span><span><i style="background:var(--res)"></i>resuelve un faltante</span><span><i style="background:var(--orange)"></i>fuente incorporada</span><span>◇ consulta a herramienta</span><span>Clic en un círculo = ver la fuente</span></div>
  <div style="overflow-x:auto"><svg viewBox="0 0 ${Wd} ${H}" width="100%" style="min-width:640px"><defs><marker id="ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="var(--mut)"/></marker></defs>${bg}${ln}${svg}</svg></div>`}
function matrix(v){
  const Wd=640,H=400,m=56,lo=.3,X=e=>m+(Math.max(e,lo)-lo)/(1-lo)*(Wd-2*m),Y=i=>H-m-(Math.max(i,lo)-lo)/(1-lo)*(H-2*m);
  let g=`<rect x="${X(.65)}" y="${m-10}" width="${Wd-m+10-X(.65)}" height="${Y(.65)-m+10}" rx="10" fill="color-mix(in srgb,var(--orange) 7%,transparent)"/>
  <line x1="${m}" y1="${H-m}" x2="${Wd-m+10}" y2="${H-m}" stroke="var(--mut)"/><line x1="${m}" y1="${m-10}" x2="${m}" y2="${H-m}" stroke="var(--mut)"/>
  <text class="m" x="${Wd/2}" y="${H-16}" text-anchor="middle" font-weight="700">Evidencia →</text><text class="m" x="16" y="${H/2}" transform="rotate(-90 16 ${H/2})" text-anchor="middle" font-weight="700">Impacto →</text>
  <text x="${Wd-m}" y="${m+6}" text-anchor="end" style="fill:var(--orange2)" font-weight="800">Actuar / validar ya</text>
  <text class="m" x="${m+8}" y="${m+6}">Investigar evidencia</text><text class="m" x="${m+8}" y="${H-m-8}">Monitorear</text>`;
  v.signals.forEach(s=>{const c=s.componentes,r=10+c.urgencia*16,on=s.id===sel;
    g+=`<g data-s2="${s.id}" style="cursor:pointer"><circle cx="${X(c.evidencia)}" cy="${Y(c.impacto)}" r="${r}" fill="${on?"var(--orange)":"var(--blue2)"}" fill-opacity="${on?.85:.7}"/><text x="${X(c.evidencia)}" y="${Y(c.impacto)+4}" text-anchor="middle" font-weight="800" style="fill:#fff">${s.id}</text><text class="m" x="${X(c.evidencia)+r+6}" y="${Y(c.impacto)+4}" font-weight="700">${s.score}</text></g>`});
  return `<h3 class="sect" style="margin-top:0">Matriz impacto × evidencia</h3><div class="sub" style="margin-bottom:8px">Tamaño = urgencia. Clic en una burbuja para abrir su resumen.</div><svg viewBox="0 0 ${Wd} ${H}" width="100%" style="max-width:${Wd}px">${g}</svg>`}
function rescore(v){return v.signals.map(s=>{const c=s.componentes;return {s,sc:Math.max(0,100*(W.impacto*c.impacto+W.evidencia*c.evidencia+W.urgencia*c.urgencia)-(c.penalizacion||0))}}).sort((a,b)=>b.sc-a.sc)}
function weights(v){
  return `<h3 class="sect">¿Y si cambio los pesos?</h3><div class="sub">Los pesos son supuestos de negocio. Muévelos (se normalizan a 100%) y mira cómo cambia el ranking.</div>
  ${["impacto","evidencia","urgencia"].map(k=>`<div class="slider"><span>${k}</span><input type="range" min="0" max="100" value="${Math.round(W[k]*100)}" data-w="${k}"><b id="wv-${k}">${Math.round(W[k]*100)}%</b></div>`).join("")}
  <button class="btn sm" id="w-reset">Restaurar 45 / 30 / 25</button><div id="w-out" style="margin-top:12px"></div>`}
function bindWeights(v){
  const orig=v.signals.map(s=>s.id);
  const draw=()=>{$("#w-out").innerHTML=`<table><tr><th>#</th><th>Señal</th><th>Original</th><th>Con estos pesos</th><th>Puesto</th></tr>${rescore(v).map((x,i)=>{const d=orig.indexOf(x.s.id)-i;
    return `<tr><td>${i+1}</td><td><b>${x.s.id}</b> ${esc(x.s.titulo)}</td><td>${x.s.score}</td><td><b>${x.sc.toFixed(1)}</b></td><td>${d?`<span class="delta ${d>0?"up":"dn"}">${d>0?"▲":"▼"}${Math.abs(d)}</span>`:"="}</td></tr>`}).join("")}</table>`};
  document.querySelectorAll("[data-w]").forEach(r=>r.oninput=()=>{const raw={};document.querySelectorAll("[data-w]").forEach(x=>raw[x.dataset.w]=+x.value);const t=Object.values(raw).reduce((a,b)=>a+b,0)||1;
    for(const k in raw){W[k]=raw[k]/t;$("#wv-"+k).textContent=Math.round(W[k]*100)+"%"}draw()});
  $("#w-reset").onclick=()=>{W={impacto:.45,evidencia:.30,urgencia:.25};render()};draw()}
function trace(v,s){
  const rows=v.log.filter(e=>!e.senal||e.senal===s.titulo);
  return `<div class="sub" style="margin-bottom:10px">Registro observable de acciones de la señal ${s.id} (no es razonamiento interno del modelo).</div><table><tr><th>#</th><th>Acción</th><th>Detalle</th></tr>${rows.map((e,i)=>{let d;
   if(e.accion==="consulta_herramienta")d=`<span class="mono">${e.args.map(esc).join(" · ")}</span><br>${esc(e.motivo)} · ${e.ms} ms<br><span class="sub mono">${esc(JSON.stringify(e.resultado.registros))}</span>`;
   else if(e.accion==="agrupar_fuentes")d=`grupo: ${s.fuentes.join(", ")}`;
   else if(e.accion==="ingestar")d=`${e.n_fuentes} fuentes (sha1 por archivo)`;
   else d=esc(JSON.stringify(Object.fromEntries(Object.entries(e).filter(([k])=>!["accion","senal"].includes(k)))));
   return `<tr><td>${i+1}</td><td><b>${esc(e.accion)}</b></td><td>${d}</td></tr>`}).join("")}</table>
   <h3 class="sect">Aspectos no resueltos</h3><ul>${s.claims.filter(c=>c.tipo==="faltante"&&!c.superada).map(c=>`<li>${esc(c.texto)} ${cites("["+c.sid+"]")}</li>`).join("")}</ul>`}
// ---------- búsqueda ----------
function localSearch(q){const toks=q.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g,"").match(/[a-z_]{4,}/g)||[];const v=V[vi];
  const sig={};v.signals.forEach(s=>s.fuentes.forEach(f=>sig[f]=s.id));const stt={};v.signals.forEach(s=>s.claims.forEach(c=>stt[c.sid]=st(c)));
  return v.fuentes.flatMap(f=>f.sents.map(x=>{const t=(x.texto+" "+f.titulo).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g,"");
    const sc=toks.reduce((a,k)=>a+(t.includes(k.slice(0,Math.max(4,k.length-2)))?1:0),0)*(stt[x.sid]==="correccion"?1.35:1);return {sid:x.sid,texto:x.texto,senal:sig[f.id]||null,estado:stt[x.sid]||null,score:sc}}))
   .filter(h=>h.score>0).sort((a,b)=>b.score-a.score).slice(0,8)}
async function ask(){const q=$("#q").value.trim();if(!q)return;$("#ask-res").innerHTML='<div class="res sub">Buscando…</div>';
  let r;try{r=APP?await api("/api/preguntar",{q,llm:$("#q-llm").checked}):{hits:localSearch(q)}}catch(e){$("#ask-res").innerHTML=`<div class="res">⚠ ${esc(e.message)}</div>`;return}
  let h='<div class="res">';
  if(r.llm)h+=r.llm.error?`<div class="warn" style="margin-left:0">Claude: ${esc(r.llm.error)}</div>`:`<div class="callout ai"><h4>Claude · ${r.llm.aceptada?"citas validadas":"⚠ citas no validadas"} · USD ${r.llm.costo_usd}</h4>${cites(esc(r.llm.respuesta))}</div>`;
  h+=(r.hits.length?r.hits.map(x=>`<div class="hit"><button class="cite" data-src="${x.sid}">[${x.sid}]</button> ${x.estado?`<span class="tag t-${x.estado}">${ET[x.estado]}</span>`:""}${x.senal?`<span class="tag">${x.senal}</span>`:""}${esc(x.texto)}</div>`).join(""):"<div class='sub'>Sin coincidencias.</div>")+"</div>";
  $("#ask-res").innerHTML=h;bindCites()}
// ---------- añadir fuente ----------
let FILE=null, PREV=null;
function openAdd(){FILE=null;PREV=null;["f-titulo","f-area","f-texto"].forEach(i=>$("#"+i).value="");$("#f-file").textContent="";$("#prev-res").innerHTML="";$("#b-inc").disabled=true;
  $("#f-id").value=ST?.next_id||"";$("#f-fecha").value=new Date().toISOString().slice(0,10);$("#f-llm").disabled=!ST?.llm.configurada;$("#m-add").classList.add("on")}
function readFile(f){const r=new FileReader();r.onload=()=>{FILE={filename:f.name,b64:r.result.split(",")[1]};$("#f-file").textContent="📄 "+f.name+" cargado";
  if(/\.(md|txt)$/i.test(f.name)){$("#f-texto").value=new TextDecoder().decode(Uint8Array.from(atob(FILE.b64),c=>c.charCodeAt(0)));FILE=null}
  PREV=null;$("#b-inc").disabled=true};r.readAsDataURL(f)}
function payload(){const meta={id:$("#f-id").value,fecha:$("#f-fecha").value,tipo:$("#f-tipo").value,area:$("#f-area").value,titulo:$("#f-titulo").value};
  return FILE?{...FILE,meta}:{texto:$("#f-texto").value,filename:"",meta}}
async function preview(){$("#prev-res").innerHTML='<div class="res sub">Analizando impacto…</div>';
  try{PREV=await api("/api/preview",{...payload(),llm:$("#f-llm").checked})}catch(e){$("#prev-res").innerHTML=`<div class="res">⚠ ${esc(e.message)}</div>`;PREV=null;$("#b-inc").disabled=true;return}
  const p=PREV,f=p.fuente;let h=`<div class="res"><b>${f.id}</b> · ${f.fecha} · ${esc(f.tipo)} · ${esc(f.area)} · ${esc(f.titulo)}`;
  h+=p.descartada?`<div class="callout no" style="margin:10px 0"><h4>Se descartaría como ruido</h4>${esc(p.descartada.motivo)}</div>`:"";
  h+=`<h3 class="sect" style="margin-top:14px">Qué cambiaría</h3><ul>${(p.diff?.explicacion||[]).map(l=>`<li>${esc(l)}</li>`).join("")||"<li>Sin cambios materiales</li>"}</ul>`;
  if(p.clasificacion.length)h+=`<h3 class="sect">Cómo se clasificó cada oración</h3>${p.clasificacion.map(c=>`<div class="hit"><span class="tag t-${c.tipo}">${ET[c.tipo]}</span><span class="mono sub">${c.sid}</span> ${esc(c.texto)}</div>`).join("")}`;
  if(p.revision_llm)h+=`<div class="callout ai"><h4>Segunda opinión · Claude</h4>${p.revision_llm.relaciones.map(r=>`<div class="hit"><b>${esc(r.nuevo)}</b> ${esc(r.relacion)} <b>${esc(r.existente)}</b> — ${esc(r.motivo)}</div>`).join("")||"<div class='sub'>Sin relaciones claras.</div>"}${p.revision_llm.riesgo?`<div class="warn" style="margin-left:0">Riesgo de sobreafirmación: ${esc(p.revision_llm.riesgo)}</div>`:""}<div class="sub">USD ${p.revision_llm.costo_usd} · ${p.revision_llm.ms} ms</div></div>`;
  $("#prev-res").innerHTML=h+"</div>";$("#b-inc").disabled=false}
async function incorporate(){if(!PREV)return;$("#b-inc").disabled=true;try{const r=await api("/api/incorporar",{markdown:PREV.markdown});sset("rs-msg",r.explicacion);if(r.cambios&&r.cambios[0])sset("rs-sel",r.cambios[0]);sset("rs-tab","resumen");location.reload()}catch(e){toast("⚠ "+e.message,6000);$("#b-inc").disabled=false}}
// ---------- Claude ----------
async function cfgSave(){try{const r=await api("/api/config",{key:$("#c-key").value||undefined,model:$("#c-model").value||undefined});ST.llm=r;$("#c-key").value="";$("#cfg-res").textContent="Guardado. Key: "+(r.key||"—")+" · modelo "+r.modelo;header()}catch(e){$("#cfg-res").textContent="⚠ "+e.message}}
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
(async()=>{if(APP){try{ST=await api("/api/status")}catch(e){}}header();render();
  const msg=ss("rs-msg",null);if(msg){sset("rs-msg",null);toast(msg.join(" · ").slice(0,260),6500)}})();
</script></body></html>"""
