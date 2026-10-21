/* SSI in Five Minutes — data-aligned interactive illustration. */
(() => {
  'use strict';
  const CHANNELS = ['Blue','Green','Red','NIR','SWIR1','SWIR2'];
  const IDS = ['#3277C8','#27986F','#DA5A58','#8062B5','#D59A3F','#A45B45'];
  const POS = '#B5462F', NEG = '#2F6F73';
  const LOCATIONS = [{row:9,col:11},{row:5,col:5},{row:7,col:11}]; // zero-based, verified from sample_0163
  const slides = Array.from(document.querySelectorAll('.stage > .slide'));
  const stage = document.getElementById('stage');
  let current = 0, selectedLocation = 0, selectedBand = 5, orderIndex = null;
  let result = null;
  let customLocation = null, viewFocus = 'where';
  const includedOrders = new Set();
  let activeOrder = null, restoreStep = 0, playbackTimer = null;
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
    if(current===3&&next!==3)stopPlayback();
    current=next;
    slides.forEach((s,k)=>{s.classList.toggle('active',k===current);s.classList.toggle('visible',k===current);if(k!==current)s.classList.remove('drawer-open')});
    document.querySelectorAll('.road button').forEach(b=>b.classList.toggle('on',Number(b.dataset.go)===current+1));
    $('progress').style.width=`${(current+1)/slides.length*100}%`;
    $('pageCount').textContent=`${current+1} / ${slides.length}`;
    $('prevSlide').disabled=current===0;
    $('nextSlide').disabled=current===slides.length-1;
    try { history.replaceState(null,'',location.pathname+location.search+`#${current+1}`); } catch (_) { /* file or sandboxed preview */ }
    if(result){if(current===2)renderLocal();if(current===3)renderOrders();if(current===4)renderJoint();if(current===5){renderSpectral();renderMatrix()}}
  }
  function toggleDetails(){slides[current].classList.toggle('drawer-open')}
  function showHelp(){ $('helpPanel').classList.toggle('show') }
  function dismiss(){slides[current].classList.remove('drawer-open');$('helpPanel').classList.remove('show')}
  function registerControls(){
    $('prevSlide').onclick=()=>showSlide(current-1);$('nextSlide').onclick=()=>showSlide(current+1);
    $('helpToggle').onclick=showHelp;$('closeHelp').onclick=()=> $('helpPanel').classList.remove('show');
    document.querySelectorAll('[data-details]').forEach(b=>b.addEventListener('click',toggleDetails));

    const photo=$('photoInteractive');
    const pointerCell=(event)=>{
      const rect=photo.getBoundingClientRect(),n=result?.grid||16;
      return {
        col:Math.max(0,Math.min(n-1,Math.floor((event.clientX-rect.left)/rect.width*n))),
        row:Math.max(0,Math.min(n-1,Math.floor((event.clientY-rect.top)/rect.height*n))),
      };
    };
    photo.addEventListener('click',event=>{
      if(!result)return;
      const {row,col}=pointerCell(event),previous=currentCell();
      if(row!==previous.row||col!==previous.col)selectImageCell(row,col);
    });
    photo.addEventListener('keydown',e=>{
      const delta={ArrowLeft:[0,-1],ArrowRight:[0,1],ArrowUp:[-1,0],ArrowDown:[1,0]}[e.key];
      if(!delta||!result)return;
      e.preventDefault();e.stopPropagation();
      const loc=currentCell();
      selectImageCell(Math.max(0,Math.min(result.grid-1,loc.row+delta[0])),Math.max(0,Math.min(result.grid-1,loc.col+delta[1])));
    });
    $('playOrder').onclick=startPlayback;
    document.querySelectorAll('.axis-toggle').forEach(button=>button.addEventListener('click',()=>{
      viewFocus=button.dataset.focus;renderMatrix();
    }));
    const img=photo.querySelector('img');
    if(!img.complete)img.addEventListener('load',()=>{if(result)renderLocal()});
    document.addEventListener('keydown',e=>{if(e.altKey||e.ctrlKey||e.metaKey)return;
      if(['ArrowRight',' ','PageDown'].includes(e.key)){e.preventDefault();showSlide(current+1)}
      else if(['ArrowLeft','PageUp'].includes(e.key)){e.preventDefault();showSlide(current-1)}
      else if(e.key==='Home')showSlide(0);else if(e.key==='End')showSlide(slides.length-1);
      else if(/^[1-7]$/.test(e.key))showSlide(Number(e.key)-1);
      else if(e.key.toLowerCase()==='d')toggleDetails();
      else if(e.key==='?'||e.key.toLowerCase()==='h')showHelp();else if(e.key==='Escape')dismiss();
    });
    window.addEventListener('wheel',e=>{if(slides[current].classList.contains('drawer-open'))return;const now=Date.now();if(Math.abs(e.deltaY)>40 && now-lastWheel>800){lastWheel=now;showSlide(current+Math.sign(e.deltaY))}},{passive:true});
    window.addEventListener('touchstart',e=>{touchX=e.touches[0].clientX},{passive:true});
    window.addEventListener('touchend',e=>{if(touchX===null)return;const d=e.changedTouches[0].clientX-touchX;if(Math.abs(d)>75)showSlide(current+(d<0?1:-1));touchX=null},{passive:true});
  }

  function currentCell(){return customLocation || LOCATIONS[selectedLocation]}
  function rowAt(){const {row,col}=currentCell();return result.attribution[row][col]}
  function cellIndex(){const {row,col}=currentCell();return row*result.grid+col}
  function selectImageCell(row,col){
    const match=LOCATIONS.findIndex(c=>c.row===row&&c.col===col);
    selectedLocation=match>=0?match:-1;
    customLocation=match>=0?null:{row,col};
    stopPlayback();
    includedOrders.clear();orderIndex=null;refreshLocation();
  }
  function refreshLocation(){
    if(!result)return;
    renderLocal();renderOrders();renderJoint();renderMatrix();
  }
  function drawObservedZoom(){
    const canvas=$('observedZoom'),img=$('photoInteractive').querySelector('img');
    if(!canvas||!img.complete||!img.naturalWidth)return;
    const ctx=canvas.getContext('2d'),loc=currentCell(),cw=img.naturalWidth/result.grid,ch=img.naturalHeight/result.grid;
    ctx.clearRect(0,0,canvas.width,canvas.height);
    ctx.imageSmoothingEnabled=false;
    ctx.drawImage(img,loc.col*cw,loc.row*ch,cw,ch,0,0,canvas.width,canvas.height);
  }
  // The observed full-image score is fixed. The recorded SSI tensor gives
  // f(x) - f(x with this cell masked) by the within-cell Shapley identity.
  function renderLocal(){
    if(!result)return;
    const pos=currentCell();
    const observed=result.full_value;
    const contrast=sum(result.attribution[pos.row][pos.col]);
    const masked=observed-contrast;
    $('maskedScore').textContent=masked.toFixed(4);
    $('fullScore').textContent=observed.toFixed(4);
    $('contrastScore').textContent=displaySigned(contrast,4);
    $('locationIndex').textContent=`g · row ${pos.row+1}, col ${pos.col+1}`;
    const el=$('cellMark');
    el.style.left=`${pos.col/result.grid*100}%`;
    el.style.top=`${pos.row/result.grid*100}%`;
    el.style.width=`${100/result.grid}%`;
    el.style.height=`${100/result.grid}%`;
    drawObservedZoom();
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

  function buildIllustratedGame(){
    const target=rowAt(), paths=seededOrders(cellIndex()),n=6,k=paths.length;
    const weights=Array.from({length:n},()=>Array(n).fill(0));
    for(const order of paths){
      const previous=[];
      for(const c of order){for(const j of previous)weights[c][j]+=1/k;previous.push(c)}
    }
    const size=Math.min(.006,Math.max(...target.map(Math.abs))*.14);
    const pair=Array.from({length:n},()=>Array(n).fill(0));
    for(let i=0;i<n;i++)for(let j=i+1;j<n;j++)
      pair[i][j]=pair[j][i]=size*(.68*Math.sin((i+1)*1.71+(j+1)*2.39)+.32*Math.cos((j-i)*2.19));
    const solo=target.map((v,c)=>v-pair[c].reduce((s,z,j)=>s+weights[c][j]*z,0));
    const base=result.full_value-sum(target);
    const score=(bits)=>{
      let value=base;
      for(let i=0;i<n;i++)if(bits&(1<<i)){
        value+=solo[i];
        for(let j=0;j<i;j++)if(bits&(1<<j))value+=pair[i][j];
      }
      return value;
    };
    const effects=paths.map(order=>{
      let bits=0;const row=Array(n).fill(0);
      for(const c of order){const before=score(bits);bits|=(1<<c);row[c]=score(bits)-before}
      return row;
    });
    for(let c=0;c<n;c++)
      if(Math.abs(effects.reduce((s,r)=>s+r[c],0)/k-target[c])>1e-10)
        throw Error('Shapley average mismatch');
    if(Math.abs(score(63)-result.full_value)>1e-10)throw Error('Endpoint mismatch');
    return {paths,effects,target,base,score};
  }
  function stopPlayback(){
    if(playbackTimer!==null){clearTimeout(playbackTimer);playbackTimer=null}
    activeOrder=null;
    restoreStep=0;
  }
  function startPlayback(){
    if(!result||orderIndex===null||activeOrder!==null)return;
    stopPlayback();
    const target=orderIndex;
    // Remove only the selected order before replay. Previously completed orders stay intact.
    includedOrders.delete(target);
    activeOrder=target;
    restoreStep=0;
    renderOrders();
    const advance=()=>{
      if(current!==3||activeOrder!==target){stopPlayback();renderOrders();return}
      restoreStep++;
      if(restoreStep>=6){
        includedOrders.add(target);
        activeOrder=null;
        playbackTimer=null;
        restoreStep=6;
        renderOrders();
        return;
      }
      renderOrders();
      playbackTimer=setTimeout(advance,390);
    };
    playbackTimer=setTimeout(advance,390);
  }
  function renderOrders(){
    if(!result)return;
    const game=buildIllustratedGame();
    const focus=orderIndex;
    const active=activeOrder!==null;
    const focusIsIncluded=focus!==null&&includedOrders.has(focus);
    const focusSteps=active&&focus===activeOrder?restoreStep:focusIsIncluded?6:0;
    const complete=includedOrders.size===5&&!active;
    $('orderNumber').textContent=focus===null?'— / 05':
      String(focus+1).padStart(2,'0')+' / 05';
    $('orderPills').innerHTML=game.paths.map((_,p)=>
      '<button type="button" data-order="'+p+'" class="live-order-dot '+
      (includedOrders.has(p)?'finished selected ':'')+
      (p===focus?'active ':'')+
      '" aria-label="Order '+(p+1)+(includedOrders.has(p)?', included':'')+
      (p===focus?', selected':'')+'" aria-pressed="'+(p===focus)+'"'+
      (active?' disabled':'')+'>'+String(p+1).padStart(2,'0')+'</button>'
    ).join('');
    $('orderPills').querySelectorAll('button').forEach(button=>button.onclick=()=>{
      if(active)return;
      const p=Number(button.dataset.order);
      // An included, already-focused order can be removed with another click.
      if(p===orderIndex&&includedOrders.has(p)){
        includedOrders.delete(p);
        restoreStep=0;
      } else {
        orderIndex=p;
        restoreStep=includedOrders.has(p)?6:0;
      }
      renderOrders();
    });
    $('channelSequence').innerHTML=focus===null?
      '<div class="live-empty-sequence">Select an order above</div>':
      game.paths[focus].map((c,i)=>
        '<div class="live-path-band '+(i<focusSteps?'restored ':'')+
        (i===focusSteps-1&&active?'current':'')+
        '" style="--id:'+IDS[c]+'"><i class="live-path-icon"></i>'+
        '<span>'+CHANNELS[c]+'</span></div>'
      ).join('');
    $('stepProgress').textContent=active
      ?includedOrders.size+' / 5 orders added · '+restoreStep+' / 6 channels'
      :includedOrders.size+' / 5 orders added';
    const restoredBand=active&&restoreStep>0?
      game.paths[activeOrder][restoreStep-1]:null;
    $('restorationPhase').textContent=active?
      (restoredBand===null?'Order '+(activeOrder+1)+' ready':
       CHANNELS[restoredBand]+' restored'):
      complete?'Five orders combined':focus===null?'Choose any order':
      focusIsIncluded?'Order '+(focus+1)+' included':'Order '+(focus+1)+' ready';
    const shown=active?restoreStep:focusIsIncluded?6:0;
    if(focus===null||shown===0){
      $('demoScoreBefore').textContent='—';
      $('demoScore').textContent='—';
      $('demoDeltaLabel').textContent='ORDER CONTRIBUTION';
      $('demoDelta').textContent='—';
      $('demoDelta').className='';
    } else {
      const sequence=game.paths[focus],bits=sequence.slice(0,shown)
        .reduce((mask,c)=>mask|(1<<c),0);
      const score=game.score(bits);
      const before=active&&restoredBand!==null?
        game.score(bits&~(1<<restoredBand)):game.base;
      const delta=active&&restoredBand!==null?
        game.effects[focus][restoredBand]/game.paths.length:
        (result.full_value-game.base)/game.paths.length;
      $('demoScoreBefore').textContent=before.toFixed(4);
      $('demoScore').textContent=score.toFixed(4);
      $('demoDeltaLabel').textContent=active&&restoredBand!==null?
        'Δ '+CHANNELS[restoredBand].toUpperCase()+' ÷ 5':'ORDER CONTRIBUTION';
      $('demoDelta').textContent=displaySigned(delta,4);
      $('demoDelta').className=delta>=0?'positive':'negative';
    }
    const grid=Array.from({length:6},()=>Array(5).fill(null));
    for(let p=0;p<5;p++){
      const steps=includedOrders.has(p)?6:p===activeOrder?restoreStep:0;
      for(let i=0;i<steps;i++){
        const channel=game.paths[p][i];
        grid[channel][p]=game.effects[p][channel]/5;
      }
    }
    const scale=Math.max(.082,...game.target.map(Math.abs));
    $('localBars').innerHTML=grid.map((samples,c)=>{
      const values=samples.filter(v=>v!==null);
      const total=sum(values);
      const cells=samples.map((v,p)=>
        '<span class="live-effect-slot '+(v===null?'pending':v>=0?'positive':'negative')+
        (p===activeOrder&&c===restoredBand?' new':'')+
        '"'+(v===null?'':' data-value="'+v+'"')+'>'+
        (v===null?'·':displaySigned(v,4))+'</span>'
      ).join('');
      const width=Math.min(46,Math.abs(total)/scale*46),left=total>=0?50:50-width;
      return '<div class="live-effect-row '+(c===restoredBand?'highlight ':'')+
        (complete?'final':'')+'" style="--id:'+IDS[c]+'" data-total="'+total+'">'+
        '<span class="live-effect-name">'+CHANNELS[c]+'</span>'+
        '<div class="live-effect-slots">'+cells+'</div>'+
        '<div class="live-effect-mean">'+
        '<div class="live-mean-rail"><i class="live-effect-line" style="left:'+left+
        '%;width:'+width+'%;background:'+(total<0?NEG:POS)+'"></i></div>'+
        '<output>'+displaySigned(total,4)+'</output></div></div>';
    }).join('');
    $('demoFooter').textContent=active?
      (restoredBand===null?'Restoring Order '+(activeOrder+1):
      CHANNELS[restoredBand]+' added to the running sum'):
      complete?'All five orders combined · Φ(g,c)':
      includedOrders.size+' of 5 orders included · choose one order and press Play';
    $('demoFooter').classList.toggle('done',complete);
    const button=$('playOrder');
    button.disabled=focus===null||active;
    button.textContent=active?'Playing Order '+(activeOrder+1)+'…':
      focus===null?'▶  Select an order':
      focusIsIncluded?'↻  Replay Order '+(focus+1):
      '▶  Play Order '+(focus+1);
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
    const cell=currentCell();ctx.strokeStyle='#F5E8C5';ctx.lineWidth=3;ctx.strokeRect(cell.col*size+1,cell.row*size+1,size-2,size-2);
  }
  function renderJoint(){if(!result)return;
    $('jointMaps').innerHTML=CHANNELS.map((name,i)=>`<button class="joint-card ${selectedBand===i?'selected':''}" data-band="${i}" aria-label="Inspect ${name}" style="--ch:${IDS[i]}"><span class="identity">${name}</span><canvas></canvas><span class="joint-value"><span>Σ over g</span><strong>${displaySigned(result.spectral[i])}</strong></span></button>`).join('');
    $('jointMaps').querySelectorAll('.joint-card').forEach(card=>{const i=Number(card.dataset.band);drawMap(card.querySelector('canvas'),i);card.addEventListener('click',()=>{selectedBand=i;renderJoint()})});
    $('selectedBandTotal').textContent=`${CHANNELS[selectedBand]} · ${displaySigned(result.spectral[selectedBand])}`;
  }

  function renderMatrix(){
    if(!result)return;
    const outer=$('viewsGrid');if(outer)outer.dataset.focus=viewFocus;
    document.querySelectorAll('.axis-toggle').forEach(b=>{
      const on=b.dataset.focus===viewFocus;
      b.setAttribute('aria-pressed',String(on));b.classList.toggle('active',on);
    });
    const keys=$('matrixBandKeys');
    if(keys)keys.innerHTML=CHANNELS.map((n,i)=>`<i style="--id:${IDS[i]}" title="${n}"></i>`).join('');
    const canvas=$('matrixCanvas');if(!canvas)return;
    const ctx=canvas.getContext('2d'),g=result.grid,n=result.channels.length;
    const cellWidth=canvas.width/n,cellHeight=canvas.height/(g*g),max=.07535534570403755;
    const base=[247,243,235],pos=[190,79,57],neg=[45,112,120];
    for(let row=0;row<g;row++)for(let col=0;col<g;col++)for(let band=0;band<n;band++){
      const v=result.attribution[row][col][band];
      const mix=Math.pow(Math.min(1,Math.abs(v)/max),.60)*.94;
      const target=v>=0?pos:neg;
      ctx.fillStyle=`rgb(${base.map((x,i)=>Math.round(x*(1-mix)+target[i]*mix)).join(',')})`;
      ctx.fillRect(band*cellWidth,(row*g+col)*cellHeight,cellWidth+.3,cellHeight+.2);
    }
    ctx.strokeStyle='#D8D0C1';ctx.lineWidth=1.25;
    for(let i=1;i<n;i++){ctx.beginPath();ctx.moveTo(i*cellWidth+.5,0);ctx.lineTo(i*cellWidth+.5,canvas.height);ctx.stroke()}
    if(viewFocus==='where'){
      const idx=cellIndex();ctx.fillStyle='#C8A870';ctx.fillRect(0,idx*cellHeight-1,canvas.width,3.5);
    }else{
      ctx.strokeStyle='#9C7C43';ctx.lineWidth=4;
      ctx.strokeRect(selectedBand*cellWidth+2,2,cellWidth-4,canvas.height-4);
    }
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
      result=d;renderLocal();renderOrders();renderJoint();renderSpectral();renderMatrix();
    }catch(err){console.error(err);$('status').textContent='Authentic SSI data could not be loaded. Please serve this folder over HTTP. '+err.message;$('status').classList.add('show');}
  }
  stageScale();window.addEventListener('resize',stageScale);
  buildRoads();registerControls();
  const start=Number(location.hash.slice(1));showSlide(Number.isInteger(start)&&start>=1&&start<=slides.length?start-1:0);
  loadData();
})();