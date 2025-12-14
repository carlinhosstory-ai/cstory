const lat = -25.0905;
const lon = -50.1638;
const timezone = 'America/Sao_Paulo';
const apiBase = 'https://api.open-meteo.com/v1/forecast';
const updateInterval = 2 * 60 * 1000; // 2 minutes

function el(id){return document.getElementById(id)}

async function fetchWeather(){
  const url = `${apiBase}?latitude=${lat}&longitude=${lon}&current_weather=true&hourly=relativehumidity_2m,apparent_temperature&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=${encodeURIComponent(timezone)}`;
  const res = await fetch(url);
  if(!res.ok) throw new Error('Erro na API');
  return res.json();
}

function weatherCodeToText(code){
  const map = {
    0: 'Céu limpo',1:'Principalmente limpo',2:'Parcialmente nublado',3:'Nublado',
    45:'Nevoeiro',48:'Depósito de neblina',51:'Chuvisco leve',53:'Chuvisco',55:'Chuvisco forte',
    61:'Chuva fraca',63:'Chuva',65:'Chuva forte',71:'Neve fraca',73:'Neve',75:'Neve forte',
    80:'Aguaceiros',81:'Aguaceiros fortes',82:'Aguaceiros muito fortes',95:'Tempestade',
  };
  return map[code]||'—';
}

function weatherCodeToIconName(code){
  // retorna o nome do ícone SVG correspondente
  const map = {
    0: 'sun',1:'partly_cloudy',2:'partly_cloudy',3:'cloudy',
    45:'fog',48:'fog',51:'drizzle',53:'drizzle',55:'drizzle',
    61:'rain',63:'rain',65:'storm',71:'snow',73:'snow',75:'snow',
    80:'rain',81:'rain',82:'storm',95:'storm'
  };
  return map[code]||'unknown';
}

function iconNameToPath(name){
  return `icons/${name}.svg`;
}

function render(data){
  const cur = data.current_weather;
  el('temp').textContent = `${Math.round(cur.temperature)} °C`;
  el('weather').textContent = weatherCodeToText(cur.weathercode);
  const iconEl = el('icon');
  if(iconEl){
    const name = weatherCodeToIconName(cur.weathercode);
    iconEl.src = iconNameToPath(name);
    iconEl.alt = weatherCodeToText(cur.weathercode);
  }
  el('wind').textContent = `Vento: ${cur.windspeed} m/s`;

  // humidity & feels from hourly (approx nearest hour)
  const hourIdx = data.hourly.time.indexOf(cur.time);
  if(hourIdx>=0){
    el('humidity').textContent = data.hourly.relativehumidity_2m[hourIdx] + '%';
    el('feels').textContent = Math.round(data.hourly.apparent_temperature[hourIdx]) + ' °C';
  }

  // daily cards
  const cards = el('cards'); cards.innerHTML='';
  const days = data.daily.time;
  for(let i=0;i<days.length;i++){
    const d = document.createElement('div'); d.className='day';
    const date = new Date(days[i]);
    const name = date.toLocaleDateString('pt-BR',{weekday:'short',day:'numeric',month:'short'});
    const dayIconName = weatherCodeToIconName(data.daily.weathercode[i]);
    const dayIconPath = iconNameToPath(dayIconName);
    d.innerHTML = `<h4>${name}</h4><div class="day-icon"><img src="${dayIconPath}" alt="${weatherCodeToText(data.daily.weathercode[i])}"></div><p>Máx: ${Math.round(data.daily.temperature_2m_max[i])} °C</p><p>Min: ${Math.round(data.daily.temperature_2m_min[i])} °C</p>`;
    cards.appendChild(d);
  }

  el('updated').textContent = 'Última atualização: ' + new Date().toLocaleTimeString('pt-BR');
}

async function update(){
  try{
    el('updated').textContent = 'Atualizando...';
    const data = await fetchWeather();
    render(data);
  }catch(err){
    el('updated').textContent = 'Erro ao atualizar';
    console.error(err);
  }
}

update();
setInterval(update, updateInterval);

// Theme toggle: salva preferência em localStorage
function applyTheme(theme){
  if(theme==='light') document.body.classList.add('light'); else document.body.classList.remove('light');
}

const savedTheme = localStorage.getItem('theme') || 'dark';
applyTheme(savedTheme);
const themeBtn = el('theme-toggle');
if(themeBtn){
  themeBtn.addEventListener('click', ()=>{
    const next = document.body.classList.contains('light') ? 'dark' : 'light';
    applyTheme(next);
    localStorage.setItem('theme', next);
  });
}
