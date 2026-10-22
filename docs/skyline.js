/* Contribution Skyline v2: independent Canvas 2D implementation.
   Math and animation behavior based on independently studied public reference.
   Only synthetic sample data is embedded; GitHub activity requires contributions.json.
*/
'use strict';
const SAMPLE_START = '2016-11-06';
const SAMPLE_COUNTS = [0,5,0,1,2,5,9,1,19,24,19,31,32,33,4,24,8,3,2,31,0,0,11,15,23,0,9,0,2,4,10,2,1,0,0,0,8,2,5,0,2,0,0,0,2,0,4,2,0,0,2,0,0,0,0,0,4,9,0,0,9,2,5,4,7,1,4,3,0,2,0,2,4,2,3,3,0,1,0,1,4,0,0,0,3,2,3,2,1,0,0,0,3,2,7,4,4,0,2,4,1,2,0,0,0,0,0,1,4,0,7,22,0,0,4,3,3,0,1,0,2,3,3,3,0,0,0,0,3,0,2,0,0,2,0,0,0,0,0,1,1,8,0,7,19,4,0,0,11,5,3,24,3,6,3,6,9,1,2,15,0,0,2,12,11,4,9,4,32,6,1,17,31,9,3,3,8,8,7,2,3,1,1,21,1,7,10,4,1,0,12,3,2,8,3,4,2,0,8,7,0,3,0,0,15,3,8,4,0,0,0,4,6,0,4,0,0,0,0,2,4,0,11,13,0,3,4,0,0,7,13,3,0,8,3,15,8,9,4,1,7,3,8,3,4,0,20,22,4,19,9,2,15,31,8,4,5,2,9,15,15,54,5,13,24,1,4,6,3,0,4,22,5,2,1,27,32,5,1,4,1,6,12,0,12,5,2,3,13,14,10,0,2,3,0,3,7,1,1,4,0,0,0,2,3,2,1,5,3,0,0,1,0,2,0,3,0,0,0,0,2,0,0,0,4,0,2,8,0,0,0,2,0,2,7,0,1,3,4,0,3,3,0,5,0,0,0,9,0,0,1,4,3,1,0,1,0,1,9,3,0,0,18,0,0,0,1,4];
const SAMPLE_LEVELS = '02011221344444142114002340201121100021101000101100100000120021112111010111110101100011111000112110111100000110240011101011110000101001000001120241003214111221130013312142134211222111141221103112111022010031210001201000011033011002310213221121211044142134211123341341121014211441111230321133301101211100011111100101010000100010120001012011101101000200111101012100300011';
const PALETTES = {
  github: {light:['#ebedf0','#c6e48b','#7bc96f','#239a3b','#196127'],dark:['#242424','#0e4429','#006d32','#26a641','#39d353']},
  halloween: {light:['#f0eded','#ffee4a','#ffc501','#fe9600','#03001c'],dark:['#25212a','#ffee4a','#ffc501','#fe9600','#c97200']},
  ocean: {light:['#e9f2f5','#b8ecfa','#72c5e6','#2591c3','#15567f'],dark:['#182b34','#194b67','#277da5','#31aed4','#7de1f6']},
  ember: {light:['#f1ebe9','#ffd0a1','#ff9c5b','#de5c3a','#822c37'],dark:['#2d2225','#783d3d','#ba4b3b','#eb8149','#ffc078']},
  grape: {light:['#eeebf3','#dac8ef','#ae8cdf','#7a57bc','#472a76'],dark:['#292333','#4b2e7c','#7850b8','#b38bea','#e1ccff']},
  mono: {light:['#ebedf0','#d3d6dc','#a5aeb6','#687580','#24292f'],dark:['#23262c','#474e58','#687482','#a1b0c0','#e2e8f0']}
};
const $ = id=>document.getElementById(id);
const DAY=86400000, clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
const lerp=(a,b,t)=>a+(b-a)*t;
const easeInOutCubic=t=>{t=clamp(t,0,1);return t<.5?4*t*t*t:1-(-2*t+2)**3/2;};
const easeOutCubic=t=>1-(1-clamp(t,0,1))**3;
const smoothstep=(a,b,x)=>{const t=clamp((x-a)/(b-a),0,1);return t*t*(3-2*t);};
const barHeight=(count,max,scale=1)=>count>0&&max>0?.4+Math.pow(count/max,.85)*7.2*scale:.2;
const riseAt=(t,week,weeks,day)=>{
  const delay=(weeks>1?week/(weeks-1):0)*.36+(day/6)*.06;
  return easeOutCubic((t-delay)/(1-.42));
};
const ymd=d=>d.toISOString().slice(0,10);
const dateUTC=s=>new Date(s+'T00:00:00Z');
const plusDays=(d,offset)=>new Date(d.getTime()+offset*DAY);
const fmtNum=n=>new Intl.NumberFormat('en-US').format(n);
const fmtDate=s=>s?dateUTC(s).toLocaleDateString('en-US',{month:'short',day:'numeric',timeZone:'UTC'}):'—';
const fmtFull=s=>s?dateUTC(s).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'}):'—';
function parseHex(hex){return [parseInt(hex.slice(1,3),16),parseInt(hex.slice(3,5),16),parseInt(hex.slice(5,7),16)];}
function faceColor(hex,mult){let rgb=parseHex(hex);return `rgb(${rgb.map(c=>Math.round(c*mult)).join(',')})`;}
function lighten(hex,mult=.15){const rgb=parseHex(hex);return `rgb(${rgb.map(c=>Math.round(c+(255-c)*mult)).join(',')})`;}
function pointInPoly(x,y,poly){
  let inside=false;
  for(let i=0,j=poly.length-1;i<poly.length;j=i++){
    const a=poly[i],b=poly[j];
    if((a[1]>y)!==(b[1]>y) && x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])inside=!inside;
  }
  return inside;
}
function formatSample(){
  let s=dateUTC(SAMPLE_START);
  return SAMPLE_COUNTS.map((count,i)=>({date:ymd(plusDays(s,i)),count,previewLevel:Number(SAMPLE_LEVELS[i])}));
}
function normalizeDays(raw){
  const validDate=s=>typeof s==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&Number.isFinite(Date.parse(s+'T00:00:00Z'))&&ymd(dateUTC(s))===s;
  const counts=new Map(), levels=new Map();
  for(const item of raw||[]){
    if(!validDate(item?.date))continue;
    const n=Number(item.count);
    if(!Number.isFinite(n)||n<0)continue;
    counts.set(item.date,(counts.get(item.date)||0)+Math.floor(n));
    if(Number.isInteger(item.level)&&item.level>=0&&item.level<=4)
      levels.set(item.date,Math.max(levels.get(item.date)||0,item.level));
  }
  const inputDates=(raw||[]).map(x=>x?.date).filter(validDate).sort();
  const end=inputDates.at(-1)||ymd(new Date()), start=inputDates[0]||ymd(plusDays(dateUTC(end),-364));
  const to=dateUTC(end), from=new Date(Math.max(dateUTC(start).getTime(),to.getTime()-370*DAY));
  let days=[];
  for(let d=from;d<=to&&days.length<371;d=plusDays(d,1)){
    const date=ymd(d), day={date,count:counts.get(date)||0};
    if(levels.has(date))day.level=levels.get(date);
    days.push(day);
  }
  return days;
}
function validatePayload(data){
  if(!data||typeof data.isDemo!=='boolean'||(!data.isDemo&&data.username?.toLowerCase()!=='trynabe'))throw Error('Unverified contribution account');
  if(typeof data.generatedAt!=='string'||!Number.isFinite(Date.parse(data.generatedAt)))throw Error('Missing update timestamp');
  if(!Array.isArray(data.days)||!data.days.length)throw Error('Empty contribution calendar');
  for(const d of data.days){
    if(typeof d?.date!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(d.date)||!Number.isFinite(Date.parse(d.date+'T00:00:00Z'))||ymd(dateUTC(d.date))!==d.date||!Number.isSafeInteger(d.count)||d.count<0)throw Error('Invalid contribution day');
    if(d.level!=null&&(!Number.isInteger(d.level)||d.level<0||d.level>4))throw Error('Invalid GitHub activity level');
  }
  const dates=data.days.map(d=>d.date).sort();
  if((dateUTC(dates.at(-1))-dateUTC(dates[0]))/DAY>=371)throw Error('Contribution range is too long');
  const days=normalizeDays(data.days);
  if(data.stats?.total!==days.reduce((sum,d)=>sum+d.count,0))throw Error('Contribution totals do not agree');
  return {...data,days};
}
function activityLevels(days){
  const nonzero=days.map(d=>d.count).filter(n=>n>0).sort((a,b)=>a-b);
  const busy=nonzero.length?nonzero[Math.floor((nonzero.length-1)*.95)]:1;
  return days.map(d=>({ ...d, level: d.previewLevel!=null?clamp(d.previewLevel,0,4):Number.isInteger(d.level)&&d.level>=0&&d.level<=4?d.level:d.count===0?0:clamp(Math.ceil(4*d.count/Math.max(1,busy)),1,4) }));
}
function computeStats(days){
  const total=days.reduce((a,d)=>a+d.count,0);
  let busiest={count:0,date:null},longest=0,longFrom=null,longTo=null,run=0,runStart=null;
  days.forEach(d=>{if(d.count>busiest.count)busiest=d;
    if(d.count>0){if(run===0)runStart=d.date;run++;if(run>longest){longest=run;longFrom=runStart;longTo=d.date;}}
    else run=0;
  });
  const dmap=new Map(days.map(d=>[d.date,d.count]));
  let last=days.at(-1)?.date||ymd(new Date());
  if(!dmap.get(last))last=ymd(plusDays(dateUTC(last),-1));
  let cur=0, back=dateUTC(last);
  while(dmap.get(ymd(back))>0){cur++;back=plusDays(back,-1);}
  return {total,busiest,longest,longFrom,longTo,current:cur,currentFrom:cur?ymd(plusDays(dateUTC(last),-cur+1)):null,currentTo:cur?last:null,start:days[0]?.date,end:days.at(-1)?.date,maxCount:Math.max(0,...days.map(d=>d.count))};
}

class Skyline {
  constructor(){
    this.canvas=$('skyline-canvas');this.shell=$('scene-shell');this.ctx=this.canvas.getContext('2d');
    this.tip=$('tooltip'); this.cells=[];this.drawOrder=[];this.hitPolys=[];
    this.viewTarget=new URLSearchParams(location.search).get('view')==='2d'?0:1;
    this.t=0;this.yawOffset=0;this.yawGoal=0;this.elevOffset=0;this.elevGoal=0;
    this.currentPalette='github';this.dark=document.documentElement.dataset.theme!=='light';this.focusedIndex=-1;this.hoverIndex=-1;this.pinnedIndex=-1;this.legendFilter=null;
    document.documentElement.dataset.theme=this.dark?'dark':'light';
    this.drag=null;this.dirty=true;this.raf=0;this.lastTime=0;this.width=900;this.canvasHeight=151;
    this.reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
    if(this.reduced)this.t=this.viewTarget;
    this.attachHandlers();
    this.observer=new ResizeObserver(()=>this.invalidate());this.observer.observe(this.shell);
    if(this.viewTarget && !this.reduced && 'IntersectionObserver' in window){
      this.viewTarget=0;
      this.entranceObs=new IntersectionObserver(entries=>{
        if(entries.some(e=>e.isIntersecting)){this.entranceObs.disconnect();this.viewTarget=1;this.setButtons();this.invalidate();}
      },{threshold:.35});this.entranceObs.observe(this.canvas);
    }
    this.setButtons();this.invalidate();
  }
  setData(raw,isDemo){
    this.days=activityLevels(isDemo?raw:normalizeDays(raw));
    if(!this.days.length)throw Error('No contribution days');
    this.hoverIndex=this.pinnedIndex=this.focusedIndex=-1;
    this.stats=computeStats(this.days);
    const begin=dateUTC(this.days[0].date);
    this.firstSunday=plusDays(begin,-begin.getUTCDay());
    const end=dateUTC(this.days.at(-1).date);
    this.weeks=Math.floor((end-this.firstSunday)/(7*DAY))+1;
    this.cells=[];this.cellsByDate=new Map();
    this.days.forEach((day,i)=>{
      const dt=dateUTC(day.date),w=Math.floor((dt-this.firstSunday)/(7*DAY)),dow=dt.getUTCDay();
      const cell={...day,week:w,dow,index:i};this.cells.push(cell);this.cellsByDate.set(day.date,cell);
    });
    $('sample-tag').hidden=!isDemo;
    $('card-title').innerHTML=`<strong>${fmtNum(this.stats.total)}</strong> contributions in the last year${isDemo?'':' · @trynabe'}`;
    $('total').textContent=fmtNum(this.stats.total);
    $('period').textContent=`${fmtFull(this.stats.start)} – ${fmtFull(this.stats.end)}`;
    $('busiest').textContent=fmtNum(this.stats.busiest.count);
    $('busiest-date').textContent=fmtDate(this.stats.busiest.date);
    $('longest').textContent=this.stats.longest;
    $('longest-range').textContent=this.stats.longest?`${fmtDate(this.stats.longFrom)} – ${fmtDate(this.stats.longTo)}`:'—';
    $('current').textContent=this.stats.current;
    $('current-range').textContent=this.stats.current?`${fmtDate(this.stats.currentFrom)} – ${fmtDate(this.stats.currentTo)}`:'—';
    this.drawLegend();this.invalidate();
  }
  attachHandlers(){
    $('grid-btn').addEventListener('click',()=>this.setView(0));
    $('skyline-btn').addEventListener('click',()=>this.setView(1));
    $('palette').addEventListener('change',e=>{this.currentPalette=e.target.value;this.drawLegend();this.invalidate();});
    $('dark-btn').addEventListener('click',()=>{this.dark=!this.dark;document.documentElement.dataset.theme=this.dark?'dark':'light';this.drawLegend();this.invalidate();});
    this.canvas.addEventListener('pointerdown',e=>{
      const p=this.localPoint(e);
      this.drag={startX:p.x,startY:p.y,lastX:p.x,lastY:p.y,moved:false};
      this.canvas.setPointerCapture(e.pointerId);
    });
    this.canvas.addEventListener('pointermove',e=>{
      const p=this.localPoint(e);
      if(this.drag){
        const dx=p.x-this.drag.lastX,dy=p.y-this.drag.lastY;
        if(Math.hypot(p.x-this.drag.startX,p.y-this.drag.startY)>4)this.drag.moved=true;
        if(this.drag.moved && this.t>.1){
          this.yawGoal=clamp(this.yawGoal+dx*.006,(8-45)*Math.PI/180,(82-45)*Math.PI/180);
          this.elevGoal=clamp(this.elevGoal+dy*.004,(18-34)*Math.PI/180,(62-34)*Math.PI/180);
          this.canvas.classList.add('dragging');this.hoverIndex=-1;this.invalidate();
        }
        this.drag.lastX=p.x;this.drag.lastY=p.y;
      } else {
        const i=this.pick(p.x,p.y);
        if(i!==this.hoverIndex){this.hoverIndex=i;this.invalidate();}
      }
    });
    const finish=e=>{
      if(!this.drag)return;
      const p=this.localPoint(e),moved=this.drag.moved;
      this.drag=null;this.canvas.classList.remove('dragging');
      if(!moved){const picked=this.pick(p.x,p.y);
        this.pinnedIndex=picked===this.pinnedIndex?-1:picked;
        this.focusedIndex=this.pinnedIndex;this.speak(this.focusedIndex);
      }
      this.invalidate();
    };
    this.canvas.addEventListener('pointerup',finish);
    this.canvas.addEventListener('pointercancel',()=>{this.drag=null;this.canvas.classList.remove('dragging');this.invalidate();});
    this.canvas.addEventListener('pointerleave',()=>{if(!this.drag){this.hoverIndex=-1;this.invalidate();}});
    this.canvas.addEventListener('dblclick',()=>{this.yawGoal=0;this.elevGoal=0;this.invalidate();});
    this.canvas.addEventListener('keydown',e=>{
      if(!this.cells.length)return;
      const steps={ArrowUp:-1,ArrowDown:1,ArrowLeft:-7,ArrowRight:7};
      if(steps[e.key]!=null||e.key==='Home'||e.key==='End')this.hoverIndex=this.pinnedIndex=-1;
      if(steps[e.key]!=null){e.preventDefault();this.focusedIndex=clamp((this.focusedIndex<0?this.cells.length-1:this.focusedIndex)+steps[e.key],0,this.cells.length-1);this.speak(this.focusedIndex);this.invalidate();}
      else if(e.key==='Home'){e.preventDefault();this.focusedIndex=0;this.speak(this.focusedIndex);this.invalidate();}
      else if(e.key==='End'){e.preventDefault();this.focusedIndex=this.cells.length-1;this.speak(this.focusedIndex);this.invalidate();}
      else if(e.key==='Escape'){e.preventDefault();this.focusedIndex=-1;this.hoverIndex=-1;this.pinnedIndex=-1;this.invalidate();}
      else if(e.key==='Enter'||e.key===' '){e.preventDefault();this.pinnedIndex=this.focusedIndex;this.speak(this.pinnedIndex);this.invalidate();}
    });
  }
  speak(index){const c=this.cells[index];if(c)$('live').textContent=`${fmtFull(c.date)}: ${fmtNum(c.count)} contributions`;}
  setView(target){this.viewTarget=target;if(this.reduced)this.t=target;this.setButtons();this.invalidate();}
  setButtons(){
    for(const [id,val] of [['grid-btn',0],['skyline-btn',1]]){
      $(id).classList.toggle('active',this.viewTarget===val);$(id).setAttribute('aria-pressed',String(this.viewTarget===val));
    }
    this.canvas.classList.toggle('orbit',this.viewTarget===1);
    $('help').textContent=this.viewTarget===1?'Drag to orbit · double-click to reset':'Hover a day for details · arrow keys to explore';
  }
  colors(){return PALETTES[this.currentPalette][this.dark?'dark':'light'];}
  drawLegend(){
    const target=$('legend');target.innerHTML='';
    this.colors().forEach((color,level)=>{
      const sw=document.createElement('button');sw.style.background=color;sw.setAttribute('aria-label',`Highlight activity level ${level}`);
      sw.setAttribute('aria-pressed',String(this.legendFilter===level));sw.title=`Activity level ${level}`;
      sw.addEventListener('click',()=>{this.legendFilter=this.legendFilter===level?null:level;this.drawLegend();this.invalidate();});target.appendChild(sw);
    });
  }
  invalidate(){if(!this.raf)this.raf=requestAnimationFrame(time=>this.render(time));}
  localPoint(e){const r=this.canvas.getBoundingClientRect();return {x:e.clientX-r.left,y:e.clientY-r.top};}
  pick(x,y){for(let i=this.hitPolys.length-1;i>=0;i--){const hit=this.hitPolys[i];if(hit.faces.some(poly=>pointInPoly(x,y,poly)))return hit.index;}return -1;}
  projectRaw(x,y,z,yaw,elev){
    return [x*Math.cos(yaw)-y*Math.sin(yaw),
      (x*Math.sin(yaw)+y*Math.cos(yaw))*Math.sin(elev)-z*Math.cos(elev)];
  }
  sceneBounds(t,yaw,elev,full=false){
    const eased=easeInOutCubic(t),half=lerp(.78,.9,eased)/2;
    let minx=Infinity,maxx=-Infinity,miny=Infinity,maxy=-Infinity;
    const include=(x,y,z)=>{
      const [sx,sy]=this.projectRaw(x,y,z,yaw,elev);
      minx=Math.min(minx,sx);maxx=Math.max(maxx,sx);miny=Math.min(miny,sy);maxy=Math.max(maxy,sy);
    };
    for(const cell of this.cells){
      const z=barHeight(cell.count,this.stats.maxCount)*(full?eased:riseAt(t,cell.week,this.weeks,cell.dow));
      for(const x of [cell.week-half,cell.week+half])for(const y of [cell.dow-half,cell.dow+half]){
        include(x,y,0);include(x,y,z);
      }
    }
    include(-.5,6.5+1.5*eased,0);include(this.weeks-.5,6.5+1.5*eased,0);
    return {minx,maxx,miny,maxy};
  }
  buildCamera(width,height,t){
    const eased=easeInOutCubic(t),yaw=eased*(Math.PI/4+this.yawOffset),elev=Math.PI/2+(34*Math.PI/180+this.elevOffset-Math.PI/2)*eased;
    // `elev` correctly moves 90° -> 34°, with user orbit offset only in 3D.
    const {minx,maxx,miny,maxy}=this.sceneBounds(t,yaw,elev);
    const pad=lerp(2,20,eased),gutter=width<520?0:32;
    const left=pad+gutter*(1-eased),top=pad+20*(1-eased);
    const availableWidth=width-left-pad,availableHeight=height-top-pad;
    const scale=Math.min(availableWidth/(maxx-minx),availableHeight/(maxy-miny));
    const ox=left+(availableWidth-(maxx-minx)*scale)/2-minx*scale;
    const oy=top+(availableHeight-(maxy-miny)*scale)/2-miny*scale;
    return {yaw,elev,scale,ox,oy,t,eased,project:(x,y,z)=>{const [a,b]=this.projectRaw(x,y,z,yaw,elev);return [ox+a*scale,oy+b*scale];}};
  }
  drawQuad(points,color,stroke){
    const c=this.ctx;c.beginPath();c.moveTo(points[0][0],points[0][1]);for(let i=1;i<points.length;i++)c.lineTo(points[i][0],points[i][1]);c.closePath();c.fillStyle=color;c.fill();
    if(stroke){c.lineWidth=stroke==='selected'?1.8:0.28;c.strokeStyle=stroke==='selected'?(this.dark?'#e6edf3':'#111827'):(this.dark?'#0b1019':'#ffffff66');c.stroke();}
  }
  render(time){
    this.raf=0;
    const dt=this.lastTime?Math.min(.05,(time-this.lastTime)/1000):.016;this.lastTime=time;
    const dtProgress=dt/1.3;
    if(Math.abs(this.t-this.viewTarget)>0.00001){this.t=Math.abs(this.t-this.viewTarget)<dtProgress?this.viewTarget:this.t+Math.sign(this.viewTarget-this.t)*dtProgress;}
    if(this.reduced)this.t=this.viewTarget;
    const follow=1-Math.exp(-13*dt);
    const dy=this.yawGoal-this.yawOffset,de=this.elevGoal-this.elevOffset;
    if(this.reduced){this.yawOffset=this.yawGoal;this.elevOffset=this.elevGoal;}
    else {
      if(Math.abs(dy)>.00004)this.yawOffset+=dy*follow;else this.yawOffset=this.yawGoal;
      if(Math.abs(de)>.00004)this.elevOffset+=de*follow;else this.elevOffset=this.elevGoal;
    }
    const t=this.t,eff=easeInOutCubic(t);
    const width=this.shell.getBoundingClientRect().width;
    if(width<1||!this.cells.length)return;
    const flat=this.sceneBounds(0,0,Math.PI/2,true),raised=this.sceneBounds(1,Math.PI/4,34*Math.PI/180,true);
    const height2d=24+(flat.maxy-flat.miny)/(flat.maxx-flat.minx)*(width-(width<520?0:32)-4);
    const natural3d=40+(raised.maxy-raised.miny)/(raised.maxx-raised.minx)*(width-40);
    const height3d=Math.max(Math.min(natural3d,width*.72,620),Math.min(natural3d,240));
    const height=lerp(height2d,height3d,eff);this.shell.style.height=height.toFixed(1)+'px';
    const layout=$('scene-layout'),desktop=width>=560,corners=desktop&&eff>.5;
    layout.classList.toggle('corner-layout',corners);
    layout.style.setProperty('--big-size',Math.round(clamp(width*.058,30,56))+'px');
    layout.style.setProperty('--row-factor',String(desktop?1-smoothstep(.05,.5,eff):1));
    layout.style.setProperty('--stats-opacity',String(desktop?(corners?smoothstep(.5,.95,eff):1-smoothstep(.05,.45,eff)):1));
    const dpr=Math.min(window.devicePixelRatio||1,2);
    if(this.canvas.width!==Math.round(width*dpr)||this.canvas.height!==Math.round(height*dpr)){
      this.canvas.width=Math.round(width*dpr);this.canvas.height=Math.round(height*dpr);
    }
    const ctx=this.ctx;ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,width,height);
    const cam=this.buildCamera(width,height,t);
    const activityColors=this.colors();
    const depth=cell=>(cell.week+.5)*Math.sin(cam.yaw)+(cell.dow+.5)*Math.cos(cam.yaw);
    const cells=this.cells.slice().sort((a,b)=>depth(a)-depth(b));
    this.hitPolys=[];
    const tooltipIndex=this.hoverIndex>=0?this.hoverIndex:this.pinnedIndex>=0?this.pinnedIndex:this.focusedIndex;
    let selectedAnchor=null;
    for(const cell of cells){
      const {week:w,dow,level,count,index}=cell;
      const z0=0;let z=riseAt(t,w,this.weeks,dow)*barHeight(count,this.stats.maxCount);
      const selected=index===(this.hoverIndex>=0?this.hoverIndex:this.pinnedIndex>=0?this.pinnedIndex:this.focusedIndex);
      if(selected)z+=.7*eff;
      const d=lerp(.78,.9,eff)/2;
      const x0=w-d,x1=w+d,y0=dow-d,y1=dow+d;
      const B0=cam.project(x0,y0,z0),B1=cam.project(x1,y0,z0),B2=cam.project(x1,y1,z0),B3=cam.project(x0,y1,z0);
      const T0=cam.project(x0,y0,z),T1=cam.project(x1,y0,z),T2=cam.project(x1,y1,z),T3=cam.project(x0,y1,z);
      const c=selected?lighten(activityColors[level],.2):activityColors[level];
      ctx.globalAlpha=(this.legendFilter!=null&&level!==this.legendFilter)?0.22:1;
      // Same tile is drawn in 2D and 3D; the side faces emerge with the bar height.
      const sy=[B3,B2,T2,T3],sx=[B1,B2,T2,T1],top=[T0,T1,T2,T3];
      if(t>.002){this.drawQuad(sy,faceColor(activityColors[level],.84));this.drawQuad(sx,faceColor(activityColors[level],.68));}
      if(t<.005){const x=T0[0],y=T0[1],tileW=T1[0]-T0[0],tileH=T3[1]-T0[1];
        ctx.beginPath();ctx.roundRect(x,y,tileW,tileH,Math.min(2.8,tileW*.22));ctx.fillStyle=c;ctx.fill();
        if(selected){ctx.strokeStyle=this.dark?'#fff':'#111';ctx.lineWidth=1.4;ctx.stroke();}
      } else this.drawQuad(top,c,selected?'selected':'soft');
      ctx.globalAlpha=1;
      this.hitPolys.push({index,faces:[top,sy,sx]});
      const anchor={x:(T0[0]+T1[0]+T2[0]+T3[0])/4,y:Math.min(T0[1],T1[1],T2[1],T3[1])-4};
      if(index===tooltipIndex)selectedAnchor=anchor;
    }
    // 2D grid labels fade during the continuous camera tilt, never replace the canvas.
    const labelAlpha=1-clamp(eff*3,0,1);
    const months=[];let previousMonth=-1;
    for(let week=0;week<this.weeks;week++){
      const date=plusDays(this.firstSunday,week*7),month=date.getUTCMonth();
      if(month!==previousMonth)months.push({week,label:date.toLocaleDateString('en-US',{month:'short',timeZone:'UTC'})});
      previousMonth=month;
    }
    if(months.length>1&&months[1].week-months[0].week<3)months.shift();
    ctx.font='10px Arial,Helvetica,sans-serif';ctx.fillStyle=this.dark?'#919191':'#737373';
    if(labelAlpha>.002){
      ctx.globalAlpha=labelAlpha;
      const labels=[['Mon',1],['Wed',3],['Fri',5]];
      ctx.textAlign='right';ctx.textBaseline='middle';
      for(const [name,dow] of labels){const [x,y]=cam.project(-.5,dow,0);if(width>=520)ctx.fillText(name,x-6,y);}
      ctx.textAlign='left';ctx.textBaseline='bottom';let edge=-Infinity;
      for(const month of months){
        const [x,y]=cam.project(month.week-.39,-.7,0),labelWidth=ctx.measureText(month.label).width;
        if(x>=edge&&x+labelWidth<=width){ctx.fillText(month.label,x,y-3);edge=x+labelWidth+6;}
      }
      ctx.globalAlpha=1;
    }
    const frontAlpha=smoothstep(.62,1,eff);
    if(frontAlpha>.002){
      ctx.globalAlpha=frontAlpha;ctx.textAlign='left';ctx.textBaseline='top';let edge=-Infinity;
      for(const month of months){
        const [x,y]=cam.project(month.week,6.8,0),labelWidth=ctx.measureText(month.label).width;
        if(x>=edge&&x+labelWidth<=width){ctx.fillText(month.label,x,y+2);edge=x+labelWidth+10;}
      }
      ctx.globalAlpha=1;
    }
    const selectedCell=this.cells[tooltipIndex];
    if(selectedCell){
      const anchor=selectedAnchor;
      if(anchor){this.tip.textContent=`${fmtNum(selectedCell.count)} contributions · ${fmtFull(selectedCell.date)}`;
        const half=Math.min(this.tip.offsetWidth/2,width/2-4);
        this.tip.style.left=clamp(anchor.x,half+4,width-half-4)+'px';
        this.tip.style.top=Math.max(this.tip.offsetHeight*1.15+4,anchor.y)+'px';this.tip.classList.add('show');
      }
    }else this.tip.classList.remove('show');
    if(this.t!==this.viewTarget||this.yawOffset!==this.yawGoal||this.elevOffset!==this.elevGoal)this.invalidate();
  }
}
window.addEventListener('DOMContentLoaded',async()=>{
  const graph=new Skyline();
  window.__skyline=graph; // For local testing and debugging only.
  const status=$('data-status'), demo=new URLSearchParams(location.search).get('demo')==='1';
  const controls=[...document.querySelectorAll('.toolbar button,.toolbar select')];
  controls.forEach(control=>control.disabled=true);
  document.documentElement.dataset.dataState='loading';
  $('sample-tag').hidden=true;
  let loaded=false, refreshing=false, lastDays='';
  async function refresh(){
    if(refreshing)return;
    refreshing=true;
    try{
      const response=await fetch('./contributions.json',{cache:'no-store',signal:AbortSignal.timeout(12000)});
      if(!response.ok)throw Error('Contribution data is not available yet');
      const data=validatePayload(await response.json());
      const signature=JSON.stringify(data.days);
      if(signature!==lastDays){graph.setData(data.days,data.isDemo);lastDays=signature;}
      const scope=data.coverage?.includesAnonymizedPrivate?'public and anonymized private contributions':'GitHub contribution calendar';
      status.textContent=data.isDemo?'SAMPLE DATA · appearance preview only · not trynabe activity':`@${data.username} · ${scope} · updated ${new Date(data.generatedAt).toLocaleString('en-GB',{timeZone:'UTC',dateStyle:'medium',timeStyle:'short'})} UTC`;
      loaded=true;
      document.documentElement.dataset.dataState='ready';controls.forEach(control=>control.disabled=false);
      $('empty-state').hidden=true;
    }catch{
      if(loaded){status.textContent='Showing the last successful contribution update · retrying automatically';return;}
      document.documentElement.dataset.dataState='error';
      $('card-title').textContent='Contribution Skyline';
      status.textContent='Contribution data unavailable · retrying automatically';
      $('empty-state').hidden=false;
    }finally{refreshing=false;}
  }
  if(demo){
    graph.setData(formatSample(),true);
    status.textContent='SAMPLE DATA · appearance preview only · not trynabe activity';
    document.documentElement.dataset.dataState='ready';controls.forEach(control=>control.disabled=false);
    $('empty-state').hidden=true;
  }else{
    await refresh();
    setInterval(()=>{if(!document.hidden)void refresh();},60000);
    window.addEventListener('focus',()=>void refresh());
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)void refresh();});
  }
});
