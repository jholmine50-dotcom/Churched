(function(){
  var btns=document.querySelectorAll('.mode-opt');
  function setMode(m){
    document.body.classList.toggle('mode-base',m==='base');
    document.body.classList.toggle('mode-full',m==='full');
    btns.forEach(function(b){b.classList.toggle('active',b.dataset.mode===m)});
  }
  btns.forEach(function(b){b.onclick=function(){setMode(b.dataset.mode)}});
  setMode('base');
})();

;
const MUSICS={
  original:{label:"Original",tracks:{"Backing_Vocals":"x","Drums":"x","Bass":"x","Keyboard":"x","Percussion":"x","Strings":"x","Synth":"x","FX":"x","Brass":"x","Woodwinds":"x"}},
  oceans:{label:"Agnus Dei",tracks:{"Drums":"x","Bass":"x","Keyboard":"x","Percussion":"x","Strings":"x","Synth":"x","FX":"x","Brass":"x","Woodwinds":"x"}},
  forte:{label:"Oração Forte",tracks:{
"Drums":"x",
"Bass":"x",
"Keyboard":"x",
"Percussion":"x",
"Strings":"x",
"Synth":"x",
"FX":"x",
"Brass":"x",
"Woodwinds":"x"
}},
};
let currentSet="original";
let srcMap={...MUSICS[currentSet].tracks};
let N=Object.keys(srcMap);

const PROFILE={
  Backing_Vocals:{min:0.00,max:0.30,curve:0.95}, Drums:{min:0.00,max:0.58,curve:1.25},
  Bass:{min:0.00,max:0.66,curve:1.02}, Keyboard:{min:0.30,max:0.78,curve:0.78},
  Percussion:{min:0.02,max:0.46,curve:1.05}, Strings:{min:0.00,max:0.96,curve:1.45},
  Synth:{min:0.00,max:0.82,curve:1.65}, FX:{min:0.00,max:0.38,curve:1.75},
  Brass:{min:0.00,max:0.24,curve:2.05}, Woodwinds:{min:0.02,max:0.18,curve:1.75}
};
const GATED=new Set(['Bass','Strings','Synth']);
const ROLE_LABELS={Backing_Vocals:'vocais',Drums:'bateria',Bass:'baixo',Keyboard:'teclas',Percussion:'percussão',Strings:'cordas',Synth:'sintetizador',FX:'efeitos',Brass:'metais',Woodwinds:'sopros'};

const INTENTS=[
  {at:0,name:"SUAVE",desc:"espaçoso e discreto"}, {at:25,name:"REFLEXIVO",desc:"íntimo e contemplativo"},
  {at:50,name:"PRESENTE",desc:"fundo sustentando a fala"}, {at:72,name:"TENSÃO",desc:"construindo expectativa"},
  {at:100,name:"CLÍMAX",desc:"máxima expressão"}
];
let ctx=null,master=null,media={},gains={},filters={},sends={},sources={},started=false,fxDelay=null,fxFeedback=null,fxReverb=null,fxSendBus=null,stopTimer=null;
let masterLevel=.24,ducked=false,duckLevel=.28;
let expression=50,loop=false,totalDuration=0,raf=0,metadataReady=0,stoppingTail=false,stoppedPosition=0;
const objectUrls={};

function byId(id){return document.getElementById(id)}
const status=byId('status'),scene=byId('scene'),sceneDesc=byId('sceneDesc'),num=byId('num'),exprPct=byId('exprPct');
const fader=byId('fader');
const duckBtn=byId('duckBtn'),masterFader=byId('masterFader'),masterNum=byId('masterNum');
const timeline=byId('timeline'),elapsed=byId('elapsed'),total=byId('total'),remaining=byId('remaining'),timelineState=byId('timelineState'),loopBtn=byId('loopBtn'),grid=byId('grid');
const pill=byId('pill'),trackList=byId('trackList'),tracksHint=byId('tracksHint');
const musicLabel=byId('musicLabel'),dockCount=byId('dockCount');

function say(t,b=false){status.textContent=t;status.style.color=b?'#ff9f9f':'#a9e3b5'}
function clamp(x,a=0,b=1){return Math.max(a,Math.min(b,x))}
function smootherstep(x){x=clamp(x);return x*x*x*(x*(x*6-15)+10)}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function formatTime(sec){
  if(!isFinite(sec)||sec<0) sec=0;
  sec=Math.round(sec);
  const h=Math.floor(sec/3600),m=Math.floor((sec%3600)/60),s=sec%60;
  return (h>0?String(h).padStart(2,'0')+':':'')+String(m).padStart(2,'0')+':'+String(s).padStart(2,'0');
}
function expressionGain(v,n){
  const p=PROFILE[n]||{min:0,max:.4,curve:1};
  const x=v/100;
  let y;
  if(x<.16) y=(x/.16)*0.08;
  else {const t=(x-.16)/.84;y=.08+.92*smootherstep(Math.pow(t,p.curve));}
  return p.min+(p.max-p.min)*y;
}
function calc(){
  const g={};
  N.forEach(n=>{
    if(GATED.has(n)){
      if(expression<=50){g[n]=0;return;}
      const x=smootherstep((expression-50)/50);
      const p=PROFILE[n]||{max:.7,curve:1};
      g[n]=clamp(p.max*Math.pow(x,p.curve),0,.98);
      return;
    }
    g[n]=clamp(expressionGain(expression,n),0,.98);
  });
  N.forEach(n=>{if(muted.has(n))g[n]=0});
  return g;
}
function label(v){let out=INTENTS[0];for(const item of INTENTS)if(v>=item.at)out=item;return out}
function applyMix(immediate=false){
  const g=calc(),now=ctx?.currentTime||0,transition=immediate?.02:.10;
  N.forEach(n=>{
    if(gains[n]) gains[n].gain.setTargetAtTime(g[n],now,transition);
  });
  const tag=label(expression);
  scene.textContent=tag.name;sceneDesc.textContent=tag.desc;num.textContent=expression;exprPct.textContent=expression+'%';
  render(g);
}
function render(g){grid.innerHTML=N.map(n=>{const pct=Math.round((g[n]||0)*100);return `<div class="item"><div class="row"><b>${esc(n.replace('_',' '))}</b><span>${pct}%</span></div><div class="meter"><div class="fill" style="width:${Math.min(100,Math.round((g[n]||0)*110))}%"></div></div></div>`}).join('')}
function setDuck(on){
  ducked=on;const target=on?duckLevel:1;
  if(master) master.gain.setTargetAtTime(masterLevel*target,ctx.currentTime,.10);
  duckBtn.classList.toggle('active',on);duckBtn.textContent=on?'🎤 FALA — MÚSICA ABAIXADA':'🎤 FALA';say(on?'Música abaixada. Intensidade preservada.':'Música voltou ao nível atual.');
}
function setMaster(v){masterLevel=v/100;if(master)master.gain.setTargetAtTime(masterLevel*(ducked?duckLevel:1),ctx.currentTime,.06);masterNum.textContent=v+'%'}
function updateDuration(){
  const ds=N.map(n=>media[n]?.duration).filter(d=>isFinite(d)&&d>0);
  if(!ds.length)return;
  totalDuration=Math.max(...ds);
  timeline.max=String(totalDuration);timeline.disabled=false;total.textContent=formatTime(totalDuration);timelineState.textContent=(loop?'LOOP ATIVO':'SEM LOOP')+' • '+formatTime(totalDuration)+' de música';
}
function currentPosition(){
  if(stoppingTail)return stoppedPosition;
  const ts=N.map(n=>media[n]?.currentTime||0);
  return Math.min(totalDuration||Infinity,ts.length?Math.max(...ts):0);
}
function updateTimeline(){
  const pos=currentPosition();
  elapsed.textContent=formatTime(pos);total.textContent=formatTime(totalDuration);remaining.textContent='RESTAM '+formatTime(Math.max(0,totalDuration-pos));
  if(document.activeElement!==timeline)timeline.value=pos;
  if(started){
    if(pos>=totalDuration-0.08 && totalDuration>0){
      if(loop){
        N.forEach(n=>{if(media[n])safeSeek(media[n],0)});
        N.forEach(n=>media[n]?.play().catch(()=>{}));
      }else{
        started=false;setDuck(false);say('Fim da música.');
      }
    }
  }
  raf=requestAnimationFrame(updateTimeline);
}
function ensureTicker(){if(!raf)raf=requestAnimationFrame(updateTimeline)}
function makeReverb(){
  const len=Math.floor(ctx.sampleRate*3.8);
  const impulse=ctx.createBuffer(2,len,ctx.sampleRate);
  for(let ch=0;ch<2;ch++){
    const data=impulse.getChannelData(ch);
    for(let i=0;i<len;i++){
      const t=i/len;
      data[i]=(Math.random()*2-1)*Math.pow(1-t,2.35)*0.72;
    }
  }
  const conv=ctx.createConvolver();conv.buffer=impulse;return conv;
}
function setupFX(){
  fxSendBus=ctx.createGain();fxSendBus.gain.value=1;
  fxDelay=ctx.createDelay(1.0);fxDelay.delayTime.value=.28;
  fxFeedback=ctx.createGain();fxFeedback.gain.value=.52;
  fxReverb=makeReverb();
  fxSendBus.connect(fxDelay);fxDelay.connect(fxFeedback);fxFeedback.connect(fxDelay);
  fxDelay.connect(fxReverb);fxSendBus.connect(fxReverb);fxReverb.connect(master);
}
function ensureCtx(){
  if(ctx)return;
  ctx=new (window.AudioContext||window.webkitAudioContext)();master=ctx.createGain();master.gain.value=masterLevel;master.connect(ctx.destination);
  setupFX();
}
function teardownMedia(){
  N.forEach(n=>{
    try{media[n]?.pause()}catch(e){}
    [gains[n],filters[n],sends[n],sources[n]].forEach(node=>{try{if(node)node.disconnect()}catch(e){}});
    if(media[n]){try{media[n].src=''}catch(e){}}
    delete media[n];delete gains[n];delete filters[n];delete sends[n];delete sources[n];
  });
  Object.keys(objectUrls).forEach(k=>{try{URL.revokeObjectURL(objectUrls[k])}catch(e){};delete objectUrls[k]});
}
const blobCache={};
function resolveSrc(dataUrl){
  if(!dataUrl)return dataUrl;
  if(!dataUrl.startsWith('data:'))return dataUrl;
  if(blobCache[dataUrl])return blobCache[dataUrl];
  try{
    const comma=dataUrl.indexOf(',');
    const head=dataUrl.slice(0,comma);
    const b64=dataUrl.slice(comma+1);
    const bin=atob(b64);
    const bytes=new Uint8Array(bin.length);
    for(let i=0;i<bin.length;i++)bytes[i]=bin.charCodeAt(i);
    const mime=(head.match(/data:([^;]+)/)||[])[1]||'audio/mpeg';
    const url=URL.createObjectURL(new Blob([bytes],{type:mime}));
    blobCache[dataUrl]=url;
    return url;
  }catch(e){return dataUrl}
}
function playIfValid(a){
  if(!a)return Promise.resolve();
  if(a.loop)return a.play().catch(()=>{});
  const d=a.duration;
  if(isFinite(d)&&d>0&&a.currentTime>=d-0.08){
    // no fim: não chama play() (isso rebobinaria do 0)
    return Promise.resolve();
  }
  return a.play().catch(()=>{});
}
function safeSeek(a,t){
  if(!a)return;
  const d=a.duration;
  if(!isFinite(d)||d<=0){try{a.currentTime=t}catch(e){}return}
  let x=t;
  if(a.loop||d<8){x=((t%d)+d)%d}
  else if(x>d-0.05)x=Math.max(0,d-0.05);
  try{a.currentTime=x}catch(e){}
}
function buildAudio(name){
  if(media[name]||!srcMap[name])return;
  const a=new Audio();
  a.preload='auto';
  a.loop=false;
  a.crossOrigin='anonymous';
  a.src=resolveSrc(srcMap[name]);
  a.addEventListener('loadedmetadata',()=>{if(isFinite(a.duration)&&a.duration>0&&a.duration<8)a.loop=true;metadataReady++;updateDuration();});
  a.addEventListener('canplay',()=>{}, {once:true});
  a.addEventListener('error',()=>{
    if(!a._retried){
      a._retried=true;
      const s=srcMap[name];
      a.src='';
      setTimeout(()=>{if(media[name]===a){a.src=resolveSrc(s);a.load&&a.load()}},150);
      say('Recarregando '+name+'…',false);
    }else{
      say('Falha na track '+name+' — pressione TOCAR de novo.',true);
    }
  });
  const src=ctx.createMediaElementSource(a);
  const filter=ctx.createBiquadFilter();filter.type='lowpass';filter.frequency.value=14000;filter.Q.value=.45;
  const gn=ctx.createGain();gn.gain.value=0;
  const send=ctx.createGain();send.gain.value=.028;
  src.connect(filter);filter.connect(gn).connect(master);filter.connect(send).connect(fxSendBus);
  media[name]=a;gains[name]=gn;filters[name]=filter;sends[name]=send;sources[name]=src;
}
function setup(){
  ensureCtx();
  armAudioRecovery();
  N.forEach(buildAudio);
  applyMix(true);ensureTicker();
}
function switchMusic(id){
  if(!MUSICS[id]||id===currentSet)return;
  if(stopTimer){clearTimeout(stopTimer);stopTimer=null}
  stoppingTail=false;started=false;stoppedPosition=0;
  if(ctx){try{N.forEach(n=>media[n]?.pause())}catch(e){}}
  setDuck(false);
  teardownMedia();
  muted.clear();
  currentSet=id;
  srcMap={...MUSICS[id].tracks};
  N=Object.keys(srcMap);
  totalDuration=0;metadataReady=0;
  timeline.max='0';timeline.value='0';timeline.disabled=true;
  elapsed.textContent='0:00';total.textContent='0:00';remaining.textContent='RESTAM 0:00';
  if(ctx){N.forEach(buildAudio);applyMix(true)}
  else{render(calc())}
  renderTrackList();
  musicLabel.textContent=MUSICS[id].label;
  document.querySelectorAll('.music-opt').forEach(b=>b.classList.toggle('active',b.dataset.set===id));
  timelineState.textContent=(loop?'LOOP ATIVO':'SEM LOOP')+' • '+MUSICS[id].label;
  say('Música: '+MUSICS[id].label+'. Clique em TOCAR.');
}
function armAudioRecovery(){
  const kick=()=>{
    if(ctx&&ctx.state!=='running'){ctx.resume().then(()=>{
      if(started)N.forEach(n=>{const a=media[n];if(a&&a.paused)playIfValid(a)});
    }).catch(()=>{})}
  };
  ['pointerdown','keydown','touchstart'].forEach(ev=>window.addEventListener(ev,kick,{passive:true}));
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)kick()});
  if(ctx)ctx.onstatechange=()=>{if(ctx.state==='suspended'&&started)setTimeout(kick,50)};
}

async function playAll(){
  armAudioRecovery();
  try{
    if(!ctx)setup(); else N.forEach(buildAudio);
    if(ctx.state==='suspended'){await ctx.resume()}
    if(ctx.state!=='running'){await ctx.resume()}
    if(stopTimer){clearTimeout(stopTimer);stopTimer=null;}
    const now=ctx.currentTime;
    if(fxSendBus)fxSendBus.gain.cancelScheduledValues(now),fxSendBus.gain.setTargetAtTime(1,now,.03);
    const pos=stoppedPosition>0?stoppedPosition:currentPosition();
    const atEnd=totalDuration>0 && pos>=totalDuration-0.15;
    if(!started && (pos===0 || atEnd))N.forEach(n=>{if(media[n])safeSeek(media[n],atEnd?0:pos)});
    stoppingTail=false;
    N.forEach(n=>{if(media[n])safeSeek(media[n],pos)});
    const results=await Promise.allSettled(N.map(async n=>{
      const a=media[n];
      if(!a)return;
      try{await playIfValid(a)}
      catch(err){
        await new Promise(r=>setTimeout(r,80));
        try{await playIfValid(a)}
        catch(e2){console.warn('track falhou',n,e2);throw e2}
      }
    }));
    const failed=results.filter(r=>r.status==='rejected').length;
    const anyOk=results.some(r=>r.status==='fulfilled');
    if(!anyOk){
      say('Navegador bloqueou o áudio — clique em TOCAR novamente.',true);
      if(ctx.state!=='running'){try{await ctx.resume()}catch(e){}}
      return;
    }
    started=true;
    stoppedPosition=0;
    applyMix(true);
    say(failed?('Tocando ('+failed+' track(s) com falha — dê TOCAR de novo para reanexar).'):'Tocando — '+MUSICS[currentSet].label+'. A intensidade responde em tempo real.');
  }catch(e){
    say('Erro ao tocar: '+e.message+'. Clique em TOCAR novamente.',true);
    console.error(e);
    try{if(ctx&&ctx.state!=='running')await ctx.resume()}catch(_){}
  }
}function stopAll(){
  if(!ctx){say('STOP. Nada está tocando.');return}
  if(stopTimer)clearTimeout(stopTimer);
  const pos=currentPosition();
  const safePos=Number.isFinite(pos)?pos:0;
  const now=ctx.currentTime;
  stoppedPosition=safePos;stoppingTail=true;
  started=false;setDuck(false);
  if(fxSendBus){
    fxSendBus.gain.cancelScheduledValues(now);
    fxSendBus.gain.setValueAtTime(1.25,now);
    fxSendBus.gain.setTargetAtTime(1.55,now+.03,.045);
    fxSendBus.gain.setTargetAtTime(0,now+.16,1.25);
  }
  if(fxDelay){fxDelay.delayTime.cancelScheduledValues(now);fxDelay.delayTime.setTargetAtTime(.30,now,.03)}
  if(fxFeedback){fxFeedback.gain.cancelScheduledValues(now);fxFeedback.gain.setValueAtTime(.58,now);fxFeedback.gain.setTargetAtTime(.38,now+.55,.80)}
  N.forEach(n=>{
    if(gains[n]){
      const current=gains[n].gain.value || 0;
      gains[n].gain.cancelScheduledValues(now);
      gains[n].gain.setValueAtTime(current,now);
      gains[n].gain.setTargetAtTime(current*.92,now+.03,.03);
      if(sends[n]){
        sends[n].gain.cancelScheduledValues(now);
        sends[n].gain.setTargetAtTime(.34,now,.035);
        sends[n].gain.setTargetAtTime(0,now+.34,.60);
      }
      gains[n].gain.setTargetAtTime(0,now+.10,.08);
    }
  });
  stopTimer=setTimeout(()=>{
    N.forEach(n=>{if(media[n]){media[n].pause();safeSeek(media[n],safePos)}});
    if(fxSendBus)fxSendBus.gain.setValueAtTime(0,ctx.currentTime);
    N.forEach(n=>{if(sends[n])sends[n].gain.setValueAtTime(.028,ctx.currentTime)});
    stoppingTail=false;
    stopTimer=null;
    say('STOP. Cauda concluída • posição em '+formatTime(safePos)+'.');
  },2600);
  say('STOP • deixando a última batida virar uma cauda de delay + reverb…');
}
function fadeOut(){
  if(!ctx||!started)return;
  const now=ctx.currentTime;master.gain.cancelScheduledValues(now);master.gain.setTargetAtTime(0,now,.30);say('Fade out...');
  setTimeout(()=>{N.forEach(n=>media[n]?.pause());if(fxSendBus)fxSendBus.gain.setTargetAtTime(0,ctx.currentTime,.08);master.gain.cancelScheduledValues(ctx.currentTime);master.gain.setTargetAtTime(masterLevel*(ducked?duckLevel:1),ctx.currentTime,.06);started=false;say('Fade out concluído.')},1100);
}
function toggleLoop(){
  loop=!loop;loopBtn.classList.toggle('active',loop);loopBtn.textContent=loop?'↻ LOOP: ON':'↻ LOOP: OFF';timelineState.textContent=(loop?'LOOP ATIVO':'SEM LOOP')+(totalDuration?' • '+formatTime(totalDuration)+' de música':' • '+MUSICS[currentSet].label);
  say(loop?'Loop ativado.':'Loop desativado.');
}
function seekTo(v){const p=clamp(Number(v),0,totalDuration||0);N.forEach(n=>{if(media[n])safeSeek(media[n],p)});updateTimeline()}

function matchProfile(name){
  const n=name.toLowerCase();
  if(/bass|baixo|sub\b/.test(n)) return {min:0,max:0.66,curve:1.02,gated:true,role:'baixo'};
  if(/string|corda|orch/.test(n)) return {min:0,max:0.96,curve:1.45,gated:true,role:'cordas'};
  if(/synth|sint|(^|[^a-z])pad([^a-z]|$)/.test(n)) return {min:0,max:0.82,curve:1.65,gated:true,role:'sintetizador'};
  if(/drum|bateria|kick|snare|hat\b|(^|[^a-z])tom([^a-z]|$)/.test(n)) return {min:0,max:0.58,curve:1.25,gated:false,role:'bateria'};
  if(/perc|shaker|tambor|conga|bongo/.test(n)) return {min:0.02,max:0.46,curve:1.05,gated:false,role:'percussão'};
  if(/vocal|voz|coro|choir|sing/.test(n)) return {min:0,max:0.30,curve:0.95,gated:false,role:'vocais'};
  if(/key|piano|organ|tecl|rhodes/.test(n)) return {min:0.30,max:0.78,curve:0.78,gated:false,role:'teclas'};
  if(/brass|tromp|trombon|horn|metais|sax/.test(n)) return {min:0,max:0.24,curve:2.05,gated:false,role:'metais'};
  if(/wood|flauta|flute|clarin|oboe|sopr/.test(n)) return {min:0.02,max:0.18,curve:1.75,gated:false,role:'sopros'};
  if(/\bfx\b|efeit|riser|impact|whoosh/.test(n)) return {min:0,max:0.38,curve:1.75,gated:false,role:'efeitos'};
  if(/lead|melod|theme/.test(n)) return {min:0,max:0.72,curve:1.15,gated:false,role:'melodia'};
  if(/guitar|violao|violão|ukulele|banjo/.test(n)) return {min:0,max:0.60,curve:1.10,gated:false,role:'guitarra'};
  return {min:0,max:0.70,curve:1.00,gated:false,role:'camada'};
}
function roleOf(name){
  if(ROLE_LABELS[name])return ROLE_LABELS[name];
  if(PROFILE[name]&&PROFILE[name].role)return PROFILE[name].role;
  return matchProfile(name).role||'camada';
}
function uniqueName(base){
  let name=base||'Faixa',c=2;
  while(srcMap[name])name=base+' ('+(c++)+')';
  return name;
}
function updatePill(){
  pill.textContent='OFFLINE • '+N.length+' FAIXA'+(N.length===1?'':'S');
  dockCount.textContent=String(N.length);
  tracksHint.textContent=N.length+' na mixagem • ✕ remove';
}
function renderTrackList(){
  trackList.innerHTML=N.map(function(n){
    var isAdded=!!objectUrls[n];
    var m=muted.has(n);
    return '<div class="track-item'+(m?' is-muted':'')+'">'+
      '<div class="t-main">'+
        '<div class="t-name" title="'+esc(n)+'">'+esc(n)+'</div>'+
        '<div class="t-role">'+esc(roleOf(n))+(GATED.has(n)?' â€¢ gate 50%':'')+'</div>'+
      '</div>'+
      '<span class="t-badge'+(isAdded?' added':'')+'">'+(isAdded?'EXTRA':esc(MUSICS[currentSet].label.slice(0,10).toUpperCase()))+'</span>'+
      '<button class="mute-btn'+(m?' muted':'')+'" data-mute="'+esc(n)+'" title="'+(m?'Desmutar faixa':'Mutar faixa')+'">'+(m?'MUTADO':'SOM')+'</button>'+
      '</div>';
  }).join('');
  updatePill();
}
const muted=new Set();
function toggleMute(name){
  if(muted.has(name)){muted.delete(name);say('Som ligado: '+name);}
  else{muted.add(name);say('Mudo: '+name);}
  applyMix(false);
  renderTrackList();
}
function isMuted(name){return muted.has(name)}
byId('play').onclick=playAll;byId('stop').onclick=stopAll;byId('fadeBtn').onclick=fadeOut;duckBtn.onclick=()=>setDuck(!ducked);loopBtn.onclick=toggleLoop;
fader.addEventListener('input',()=>{expression=+fader.value;applyMix(false)});
masterFader.addEventListener('input',()=>setMaster(+masterFader.value));
timeline.addEventListener('input',()=>seekTo(timeline.value));
fader.addEventListener('dblclick',()=>{fader.value=50;expression=50;applyMix(false);say('Intensidade voltou para 50%.')});
document.querySelectorAll('.music-opt').forEach(btn=>{btn.onclick=()=>switchMusic(btn.dataset.set)});

trackList.addEventListener('click',e=>{
  const btn=e.target.closest('[data-mute]');
  if(btn)toggleMute(btn.getAttribute('data-mute'));
});
window.addEventListener('keydown',e=>{
  if(e.target.tagName==='INPUT')return;
  if(e.code==='Space'){e.preventDefault();started?setDuck(!ducked):playAll()}
  if(e.key==='ArrowUp')fader.value=Math.min(100,+fader.value+3),expression=+fader.value,applyMix(false);
  if(e.key==='ArrowDown')fader.value=Math.max(0,+fader.value-3),expression=+fader.value,applyMix(false);
  if(e.key==='f'||e.key==='F')fadeOut();
});
render(calc());renderTrackList();ensureTicker();

;
