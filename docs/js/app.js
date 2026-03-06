(() => {

const dateInput = document.getElementById("p-date");
const statusEl = document.getElementById("status");
const gamesEl = document.getElementById("games");
const modal = document.getElementById("modal");
const modalContent = document.getElementById("modal-content");

if (!dateInput || !statusEl || !gamesEl) return;
if (!window.REPO_CONFIG) {
  statusEl.textContent = "Missing config.";
  return;
}

init();

function init(){

  dateInput.value = new Date().toLocaleDateString("en-CA");

  dateInput.addEventListener("change",loadPage);

  modal.addEventListener("click",e=>{
    if(e.target===modal) modal.classList.remove("open");
  });

  loadPage();

}

async function loadPage(){

  const date = (dateInput.value || "").replaceAll("-","_");

  statusEl.textContent = "Loading...";
  gamesEl.innerHTML = "";

  const leagues = REPO_CONFIG.leagues;

  let totalPicks = 0;

  for(const league of leagues){

    const cfg = REPO_CONFIG[league];

    const column=document.createElement("div");
    column.className="league-column";

    const header=document.createElement("div");
    header.className="league-header";
    header.textContent=league;

    column.appendChild(header);

    try{

      const selectRows=await fetchMultiple(cfg.selectFiles(date));
      const predRows=await fetchCSV(cfg.predFile(date));
      const bookRows=await fetchCSV(cfg.bookFile(date));

      const predMap=buildGameMap(predRows);
      const bookMap=buildGameMap(bookRows);

      const merged=selectRows.map(sel=>{
        const key=makeKey(sel);
        return {...sel,...(predMap[key]||{}),...(bookMap[key]||{}),__key:key};
      });

      const grouped={};

      merged.forEach(r=>{
        if(!grouped[r.__key]) grouped[r.__key]=[];
        grouped[r.__key].push(r);
      });

      const keys=Object.keys(grouped).sort((a,b)=>{
        return parseTime(grouped[a][0].game_time)-parseTime(grouped[b][0].game_time);
      });

      keys.forEach(key=>{

        const picks=grouped[key];
        const r=picks[0];

        picks.forEach(p=>{

          const card=document.createElement("div");
          card.className="pick-card";

          const betText = buildBetText(p,r,cfg);
          const edge = extractEdge(p);

          card.innerHTML=`
            <div class="pick-time">${r.game_time||"-"}</div>
            <div class="pick-matchup">${r.away_team||"-"} @ ${r.home_team||"-"}</div>
            <div class="pick-bet">${betText}</div>
            <div class="pick-edge">${edgeIcon(edge)}</div>
          `;

          card.addEventListener("click",()=>{
            openModal(buildModalHtml(r,picks,cfg));
          });

          column.appendChild(card);

          totalPicks++;

        });

      });

    }catch(e){
      console.error("League load failed:", league, e);
    }

    gamesEl.appendChild(column);

  }

  statusEl.textContent = totalPicks + " picks found";

}

function buildBetText(p,r,cfg){

  const market = p.market_type || "";
  const side = p.bet_side || "";
  const line = p.line || "";
  const odds = p.take_odds || "";

  if(cfg.isHockey){

    if(market==="total"){

      if(side==="under") return `Under ${line} ${odds}`.trim();
      if(side==="over") return `Over ${line} ${odds}`.trim();

    }

    if(market==="puck_line"){

      if(side==="away") return `${r.away_team} ${formatSpread(line)} ${odds}`.trim();
      if(side==="home") return `${r.home_team} ${formatSpread(line)} ${odds}`.trim();

    }

    if(market==="moneyline"){

      if(side==="away") return `${r.away_team} ${odds}`.trim();
      if(side==="home") return `${r.home_team} ${odds}`.trim();

    }

  }

  if(p.take_bet){
    return `${p.take_bet} ${line} ${odds}`.trim();
  }

  return `${side} ${line}`.trim();

}

function formatSpread(line){

  if(line==="1.5") return "+1.5";
  if(line==="-1.5") return "-1.5";

  const num=parseFloat(line);
  if(isNaN(num)) return line;

  if(num>0) return "+"+num;

  return num.toString();

}

function parseTime(t){

  if(!t) return 0;

  const m=t.match(/(\d+):(\d+)\s*(AM|PM)/i);

  if(!m) return 0;

  let h=parseInt(m[1]);
  const min=parseInt(m[2]);
  const p=m[3].toUpperCase();

  if(p==="PM"&&h!==12)h+=12;
  if(p==="AM"&&h===12)h=0;

  return h*60+min;

}

async function fetchMultiple(paths){

  let rows=[];

  for(const p of paths){

    const r=await fetch(p);

    if(!r.ok) continue;

    const txt=await r.text();

    rows=rows.concat(parseCSV(txt));

  }

  return rows;

}

async function fetchCSV(path){

  const r=await fetch(path);

  if(!r.ok) return [];

  const txt=await r.text();

  return parseCSV(txt);

}

function parseCSV(text){

  const lines=text.trim().split(/\r?\n/);

  if(lines.length<2) return [];

  const headers=lines[0].split(",").map(h=>h.trim());

  return lines.slice(1).map(line=>{
    const values=line.split(",");
    let obj={};
    headers.forEach((h,i)=>obj[h]=(values[i]??""));
    return obj;
  });

}

function buildGameMap(rows){

  let map={};

  rows.forEach(r=>{
    const key=makeKey(r);
    map[key]=r;
  });

  return map;

}

function makeKey(r){

  const gameDate=(r.game_date||"").trim();
  const homeTeam=(r.home_team||"").trim();
  const awayTeam=(r.away_team||"").trim();

  return gameDate+"|"+homeTeam+"|"+awayTeam;

}

function extractEdge(p){

  if(p.take_bet_edge_pct) return parseFloat(p.take_bet_edge_pct);

  if(p.home_edge_decimal) return parseFloat(p.home_edge_decimal);
  if(p.away_edge_decimal) return parseFloat(p.away_edge_decimal);
  if(p.over_edge_decimal) return parseFloat(p.over_edge_decimal);
  if(p.under_edge_decimal) return parseFloat(p.under_edge_decimal);

  return 0;

}

function edgeIcon(edge){

  if(edge>=0.08) return "🟢⬆";
  if(edge>=0.04) return "🟡⬆";

  return "";

}

function openModal(html){

  modalContent.innerHTML = html;
  modal.classList.add("open");

}

function buildModalHtml(r,picks,cfg){

  const isHockey = !!cfg.isHockey;

  const projAway=isHockey?r.away_projected_goals:r.away_projected_points;
  const projHome=isHockey?r.home_projected_goals:r.home_projected_points;
  const projTotal=isHockey?r.total_projected_goals:r.total_projected_points;

  const spreadAway=isHockey?r.away_puck_line:r.away_spread;
  const spreadHome=isHockey?r.home_puck_line:r.home_spread;

  const spreadAwayOdds=isHockey?r.away_dk_puck_line_american:r.away_dk_spread_american;
  const spreadHomeOdds=isHockey?r.home_dk_puck_line_american:r.home_dk_spread_american;

  return `
  <h2>${r.away_team} @ ${r.home_team}</h2>

  <div class="game-proj">
  Proj: ${projAway||"-"} - ${projHome||"-"} (Total: ${projTotal||"-"})
  </div>

  <div class="game-book">
  ML: ${r.away_dk_moneyline_american||"-"} / ${r.home_dk_moneyline_american||"-"}<br>
  Line: ${spreadAway||"-"} (${spreadAwayOdds||"-"}) / ${spreadHome||"-"} (${spreadHomeOdds||"-"})<br>
  Total: ${r.total||"-"} (O ${r.dk_total_over_american||"-"} / U ${r.dk_total_under_american||"-"})
  </div>
  `;

}

})();
