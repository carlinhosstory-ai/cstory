function $(sel){return document.querySelector(sel)}
function $all(sel){return document.querySelectorAll(sel)}

const defaultState = {kills:0,deaths:0,scoreA:0,scoreB:0}
function load(){
  const raw = localStorage.getItem('cs_state')
  return raw?JSON.parse(raw):defaultState
}
function save(state){localStorage.setItem('cs_state',JSON.stringify(state))}

let state = load()
function render(){
  Object.keys(state).forEach(k=>{
    const el = $('#'+k)
    if(el) el.textContent = state[k]
  })
}

function change(target,delta){
  if(!(target in state)) state[target]=0
  state[target] = Math.max(0,(state[target]||0)+delta)
  save(state)
  render()
}

document.addEventListener('click',e=>{
  const btn = e.target.closest('button[data-action]')
  if(!btn) return
  const action = btn.getAttribute('data-action')
  const target = btn.getAttribute('data-target')
  if(action==='inc') change(target,1)
  if(action==='dec') change(target,-1)
  if(action==='reset'){ state[target]=0; save(state); render() }
})

// Simula atualização do servidor
$('#simulate')?.addEventListener('click',()=>{
  const players = Math.floor(Math.random()*32)
  $('#players').textContent = players
  const uptime = Math.floor(Math.random()*3600)
  $('#server-uptime').textContent = `Uptime: ${Math.floor(uptime/60)}m ${uptime%60}s`
})

render()
