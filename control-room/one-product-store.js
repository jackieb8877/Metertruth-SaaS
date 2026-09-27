'use strict';
const menuBtn=document.querySelector('#menuBtn');
const navLinks=document.querySelector('#navLinks');
menuBtn.addEventListener('click',()=>{
  const open=menuBtn.getAttribute('aria-expanded')!=='true';
  menuBtn.setAttribute('aria-expanded',String(open));
  navLinks.classList.toggle('open',open);
});
navLinks.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{
  menuBtn.setAttribute('aria-expanded','false');
  navLinks.classList.remove('open');
}));

const motion=matchMedia('(prefers-reduced-motion: reduce)');
const object=document.querySelector('#calibrationObject');
const rotateBtn=document.querySelector('#rotateBtn');
const resetBtn=document.querySelector('#resetBtn');
const viewer=document.querySelector('#viewer');
let angle=-28,tilt=-18,auto=false,drag=false,lastX=0,raf=0,visible=false,last=0;

function draw(){
  object.style.transform='rotateX('+tilt+'deg) rotateY('+angle+'deg)';
}
function frame(t){
  if(!auto||!visible||document.hidden||motion.matches){
    cancelAnimationFrame(raf);
    return;
  }
  if(t-last>40){
    angle+=Math.min((t-last)/1000,.08)*22;
    last=t;
    draw();
  }
  raf=requestAnimationFrame(frame);
}
function sync(){
  cancelAnimationFrame(raf);
  rotateBtn.textContent=auto?'Pausar giro':'Iniciar giro';
  rotateBtn.setAttribute('aria-pressed',String(auto));
  draw();
  if(auto&&visible&&!document.hidden&&!motion.matches){
    last=performance.now();
    raf=requestAnimationFrame(frame);
  }
}
rotateBtn.addEventListener('click',()=>{
  auto=!auto;
  sync();
});
resetBtn.addEventListener('click',()=>{
  auto=false;
  angle=-28;
  tilt=-18;
  sync();
});
object.addEventListener('pointerdown',e=>{
  drag=true;
  auto=false;
  lastX=e.clientX;
  object.setPointerCapture(e.pointerId);
  sync();
});
object.addEventListener('pointermove',e=>{
  if(!drag)return;
  angle+=(e.clientX-lastX)*.6;
  lastX=e.clientX;
  draw();
});
object.addEventListener('pointerup',()=>{drag=false});
object.addEventListener('pointercancel',()=>{drag=false});
object.addEventListener('keydown',e=>{
  if(!['ArrowLeft','ArrowRight','Home'].includes(e.key))return;
  e.preventDefault();
  auto=false;
  if(e.key==='Home'){
    angle=-28;
    tilt=-18;
  }else{
    angle+=e.key==='ArrowRight'?12:-12;
  }
  sync();
});
new IntersectionObserver(([e])=>{
  visible=e.isIntersecting;
  sync();
},{threshold:.05}).observe(viewer);
document.addEventListener('visibilitychange',sync);
motion.addEventListener('change',()=>{
  if(motion.matches)auto=false;
  sync();
});
sync();