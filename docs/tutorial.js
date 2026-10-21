/* SSI in Five Minutes — measured data only. No invented model scores. */
(() => {
  'use strict';
  const CHANNELS = ['Blue','Green','Red','NIR','SWIR1','SWIR2'];
  const IDS = ['#3277C8','#27986F','#DA5A58','#8062B5','#D59A3F','#A45B45'];
  const POS = '#B5462F', NEG = '#2F6F73';
  const LOCATIONS = [{row:9,col:11},{row:5,col:5},{row:7,col:11}]; // zero-based, verified from sample_0163
  const slides = Array.from(document.querySelectorAll('.stage > .slide'));
  const stage = document.getElementById('stage');
  let current = 0, selectedLocation = 0, selectedBand = 5, orderIndex = 0;
  let restored = false, result = null;
  let lastWheel = 0, touchX = null;
  const $ = (id) => document.getElementById(id);
  const displaySigned = (x,n=4) => (x>=0?'+':'−')+Math.abs(x).toFixed(n);
  const sum = a => a.reduce((s,v)=>s+v,0);

  function stageScale(){
    const k = Math.min(window.innerWidth/1920,window.innerHeight/1080);
    stage.style.transform = `scale(${k})`;
    stage.style.left = `${(window.innerWidth-1920*k)/2}px`;
    stage.style.top = `${(window.innerHeight-1080*k)/2}px`;
  }
  function buildRoads(){
    const entries = [{n:1,t:'Problem'},{n:2,t:'Local game'},{n:3,t:'Shapley'},{n:4,t:'Joint'},{n:5,t:'Two views'}];
    document.querySelectorAll('.road').forEach(nav=>{
      nav.innerHTML=entries.map(({n,t})=>`<button data-go="${n+1}">${t}</button>`).join('');
    });
    document.querySelectorAll('[data-go]').forEach(b=>b.addEventListener('click',()=>showSlide(Number(b.dataset.go)-1)));
  }
  function showSlide(i){
    const next=Math.max(0,Math.min(slides.length-1,i));
    current=next;
    slides.forEach((s,k)=>{s.classList.toggle('active',k===current);s.classList.toggle('visible',k===current);if(k!==current)s.classList.remove('drawer-open')});
    document.querySelectorAll('.road button').forEach(b=>b.classList.toggle('on',Number(b.dataset.go)===current+1));
    $('progress').style.width=`${(current+1)/slides.length*100}%`;
    $('pageCount').textContent=`${current+1} / ${slides.length}`;
    $('prevSlide').disabled=current===0;
    $('nextSlide').disabled=current===slides.length-1;
    $('notesPanel').classList.remove('show');
    try { history.replaceState(null,'',location.pathname+location.search+`#${current+1}`); } catch (_) { /* file or sandboxed preview */ }
    if(result){if(current===2)renderLocal();if(current===3)renderOrders();if(current===4)renderJoint();if(current===5)renderSpectral()}
  }
  function toggleDetails(){slides[current].classList.toggle('drawer-open')}
  function showNotes(){const panel=$('notesPanel');const open=!panel.classList.contains('show');panel.classList.toggle('show',open);if(open){const notes=slides[current].querySelector('.notes');$('notesContent').innerHTML=notes?notes.outerHTML:'<p>No notes for this slide.</p>'}}
  function showHelp(){ $('helpPanel').classList.toggle('show') }
  function dismiss(){slides[current].classList.remove('drawer-open');$('notesPanel').classList.remove('show');$('helpPanel').classList.remove('show')}
  function registerControls(){
    $('prevSlide').onclick=()=>showSlide(current-1);$('nextSlide').onclick=()=>showSlide(current+1);
    $('notesToggle').onclick=showNotes;$('helpToggle').onclick=showHelp;$('closeNotes').onclick=()=> $('notesPanel').classList.remove('show');$('closeHelp').onclick=()=> $('helpPanel').classList.remove('show');
    document.querySelectorAll('[data-details]').forEach(b=>b.addEventListener('click',toggleDetails));
    document.querySelectorAll('.loc-btn').forEach(b=>b.addEventListener('click',()=>{selectedLocation=Number(b.dataset.location);orderIndex=0;renderLocal();renderOrders();renderJoint()}));
    $('maskBtn').onclick=()=>{restored=false;renderLocal()};$('restoreBtn').onclick=()=>{restored=true;renderLocal()};
    $('previousOrder').onclick=()=>{orderIndex=(orderIndex+4)%5;renderOrders()};$('nextOrder').onclick=()=>{orderIndex=(orderIndex+1)%5;renderOrders()};
    document.addEventListener('keydown',e=>{if(e.altKey||e.ctrlKey||e.metaKey)return;
      if(['ArrowRight',' ','PageDown'].includes(e.key)){e.preventDefault();showSlide(current+1)}
      else if(['ArrowLeft','PageUp'].includes(e.key)){e.preventDefault();showSlide(current-1)}
      else if(e.key==='Home')showSlide(0);else if(e.key==='End')showSlide(slides.length-1);
      else if(/^[1-7]$/.test(e.key))showSlide(Number(e.key)-1);
      else if(e.key.toLowerCase()==='n')showNotes();else if(e.key.toLowerCase()==='d')toggleDetails();
      else if(e.key==='?'||e.key.toLowerCase()==='h')showHelp();else if(e.key==='Escape')dismiss();
    });
    window.addEventListener('wheel',e=>{if($('notesPanel').classList.contains('show')||slides[current].classList.contains('drawer-open'))return;const now=Date.now();if(Math.abs(e.deltaY)>40 && now-lastWheel>800){lastWheel=now;showSlide(current+Math.sign(e.deltaY))}},{passive:true});
    window.addEventListener('touchstart',e=>{touchX=e.touches[0].clientX},{passive:true});
    window.addEventListener('touchend',e=>{if(touchX===null)return;const d=e.changedTouches[0].clientX-touchX;if(Math.abs(d)>75)showSlide(current+(d<0?1:-1));touchX=null},{passive:true});
  }
  function rowAt(){const {row,col}=LOCATIONS[selectedLocation];return result.attribution[row][col]}
  function cellIndex(){const {row,col}=LOCATIONS[selectedLocation];return row*result.grid+col}
  function renderLocal(){if(!result)return;const data=rowAt(),total=sum(data),pos=LOCATIONS[selectedLocation];
    $('maskedScore').textContent=(result.full_value-total).toFixed(4);$('fullScore').textContent=result.full_value.toFixed(4);$('contrastScore').textContent=displaySigned(total,4);
    document.querySelectorAll('.loc-btn').forEach(b=>b.classList.toggle('selected',Number(b.dataset.location)===selectedLocation));
    for(const id of ['maskPatch','cellMark']){const el=$(id);el.style.left=`${pos.col/result.grid*100}%`;el.style.top=`${pos.row/result.grid*100}%`;el.style.width=`${100/result.grid}%`;el.style.height=`${100/result.grid}%`;}
    $('maskPatch').style.opacity=restored?'0':'1';
    $('maskBtn').setAttribute('aria-pressed',String(!restored));$('restoreBtn').setAttribute('aria-pressed',String(restored));
  }
  // The exact original xorshift32 and Fisher–Yates sampler from docs/playground/compute-runtime.js.
  function seededOrders(target){
    let x=(0^0x9e3779b9)>>>0;const rng=()=>{x^=x<<13;x^=x>>>17;x^=x<<5;return(x>>>0)/4294967296};
    let orders=[];
    for(let g=0;g<=target;g++){
      const curr=[];
      for(let p=0;p<result.permutations;p++){
        const order=[0,1,2,3,4,5];
        for(let k=5;k>0;k--){const j=Math.floor(rng()*(k+1));[order[k],order[j]]=[order[j],order[k]]}
        curr.push(order);
      }
      if(g===target)orders=curr;
    }
    return orders;
  }
  function renderOrders(){if(!result)return;
    const orders=seededOrders(cellIndex());const ord=orders[orderIndex];$('orderNumber').textContent=`0${orderIndex+1} / 05`;
    $('channelSequence').innerHTML=ord.map((b,i)=>`${i?'<span class="sep">→</span>':''}<div class="band-unit"><i class="band-square" style="--id:${IDS[b]}"></i><label>${CHANNELS[b]}</label></div>`).join('');
    const data=rowAt();const m=Math.max(.08,...data.map(x=>Math.abs(x)));
    $('localBars').innerHTML=data.map((v,i)=>{
      const wid=Math.max(1.5,Math.abs(v)/m*50);
      const start=v>=0?50:(50-wid);
      return `<div class="signed-row"><label style="--id:${IDS[i]}">${CHANNELS[i]}</label><div class="signed-track"><i class="bar ${v<0?'neg':''}" style="left:${start}%;width:${wid}%"></i></div><output>${displaySigned(v)}</output></div>`;
    }).join('');
  }
  function drawMap(canvas,band){
    const ctx=canvas.getContext('2d');if(!ctx)return;
    const g=result.grid,dim=320,size=dim/g,values=result.attribution;
    canvas.width=dim;canvas.height=dim;
    const max=.07535534570403755;
    ctx.clearRect(0,0,dim,dim);
    for(let y=0;y<g;y++)for(let x=0;x<g;x++){
      const v=values[y][x][band],alpha=Math.pow(Math.min(1,Math.abs(v)/max),.62)*.86;
      ctx.fillStyle=v>=0?`rgba(224,115,90,${alpha})`:`rgba(88,169,171,${alpha})`;
      ctx.fillRect(x*size,y*size,size,size);
    }
    const cell=LOCATIONS[selectedLocation];ctx.strokeStyle='#F5E8C5';ctx.lineWidth=3;ctx.strokeRect(cell.col*size+1,cell.row*size+1,size-2,size-2);
  }
  function renderJoint(){if(!result)return;
    $('jointMaps').innerHTML=CHANNELS.map((name,i)=>`<button class="joint-card ${selectedBand===i?'selected':''}" data-band="${i}" aria-label="Inspect ${name}" style="--ch:${IDS[i]}"><span class="identity">${name}</span><canvas></canvas><span class="joint-value"><span>Σ over g</span><strong>${displaySigned(result.spectral[i])}</strong></span></button>`).join('');
    $('jointMaps').querySelectorAll('.joint-card').forEach(card=>{const i=Number(card.dataset.band);drawMap(card.querySelector('canvas'),i);card.addEventListener('click',()=>{selectedBand=i;renderJoint()})});
    $('selectedBandTotal').textContent=`${CHANNELS[selectedBand]} · ${displaySigned(result.spectral[selectedBand])}`;
  }
  function renderSpectral(){if(!result)return;const svg=$('spectralPlot');const center=348,scale=285/.8;
    const lines=[`<line x1="${center}" y1="16" x2="${center}" y2="460" stroke="#9B978E" stroke-width="1.5"/>`];
    for(let i=0;i<6;i++){const y=33+i*73,v=result.spectral[i],w=Math.abs(v)*scale;
      lines.push(`<rect x="${v>=0?center:center-w}" y="${y}" height="38" width="${w}" fill="${v>=0?POS:NEG}"/>`);
      lines.push(`<rect x="24" y="${y+4}" width="9" height="31" fill="${IDS[i]}"/>`);
      lines.push(`<text x="47" y="${y+29}" fill="#1A2030" font-size="21">${CHANNELS[i]}</text>`);
      lines.push(`<text x="${v>=0?center+w+10:center-w-10}" text-anchor="${v>=0?'start':'end'}" y="${y+29}" fill="#1A2030" font-size="19">${displaySigned(v,3)}</text>`);
    }
    svg.innerHTML=lines.join('');
  }
  async function loadData(){
    try{
      const response=await fetch('./assets/ssi-tour/result.json',{cache:'no-store'});if(!response.ok)throw new Error(`HTTP ${response.status}`);
      const d=await response.json();
      if(d.grid!==16||d.permutations!==5||d.seed!==0||d.baseline!=='mean'||d.attribution.length!==16||d.channels.join('|')!==CHANNELS.join('|'))throw new Error('Unexpected SSI data or settings');
      const spec=CHANNELS.map((_,i)=>d.attribution.flatMap(row=>row.map(cell=>cell[i])).reduce((a,b)=>a+b,0));
      if(spec.some((x,i)=>Math.abs(x-d.spectral[i])>1e-10))throw new Error('Tensor/spectral aggregation mismatch');
      result=d;renderLocal();renderOrders();renderJoint();renderSpectral();
    }catch(err){console.error(err);$('status').textContent='Authentic SSI data could not be loaded. Please serve this folder over HTTP. '+err.message;$('status').classList.add('show');}
  }
  stageScale();window.addEventListener('resize',stageScale);
  buildRoads();registerControls();
  const start=Number(location.hash.slice(1));showSlide(Number.isInteger(start)&&start>=1&&start<=slides.length?start-1:0);
  loadData();
})();