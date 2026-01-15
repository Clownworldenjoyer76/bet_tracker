function loadCSV(url, renderFn) {
  fetch(url)
    .then(res => {
      if (!res.ok) throw new Error("Failed to load CSV");
      return res.text();
    })
    .then(text => {
      const rows = parseCSV(text);
      renderFn(rows);
    })
    .catch(err => {
      console.error(err);
      alert("Could not load data.");
    });
}

function parseCSV(text) {
  const lines = text.trim().split("\n");
  const headers = lines[0].split(",");
  return lines.slice(1).map(line => {
    const values = line.split(",");
    const obj = {};
    headers.forEach((h, i) => {
      obj[h.trim()] = values[i]?.trim();
    });
    return obj;
  });
}

function renderNCAAB(rows) {
  const tbody = document.querySelector("#bets-table tbody");
  tbody.innerHTML = "";

  rows.forEach(row => {
    const tr = document.createElement("tr");

    tr.innerHTML = `
      <td>${row.date}</td>
      <td>${row.time}</td>
      <td>${row.team}</td>
      <td>${row.opponent}</td>
      <td>${row.win_probability}</td>
      <td>${row.acceptable_american_odds}</td>
      <td>${row.units_to_bet}</td>
    `;

    if (parseFloat(row.units_to_bet) > 1.0) {
      tr.classList.add("highlight");
    }

    tbody.appendChild(tr);
  });
}
