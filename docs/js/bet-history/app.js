var allRows = [];
var activeLeague = 'all';
var activeMarket = 'all';
var activeResult = 'all';

function setStatus(text, dotCls) {
  document.getElementById('status-text').textContent = text;
  document.getElementById('status-dot').className = 'status-dot ' + (dotCls || '');
}

function loadAll() {
  var activeSources = SOURCES.filter(function(src) {
    return src.enabled !== false;
  });

  if (!activeSources.length) {
    allRows = [];
    setStatus('No leagues are currently enabled.', 'red');
    render();
    return;
  }

  setStatus(
    'Fetching data from GitHub: ' + activeSources.map(function(s) {
      return s.label;
    }).join(', ') + '...',
    'yellow'
  );

  document.getElementById('history-main').innerHTML = '';

  var promises = activeSources.map(function(src) {
    return fetch(src.url)
      .then(function(res) {
        if (!res.ok) throw new Error(src.label + ' ' + res.status);
        return res.text();
      })
      .then(function(text) {
        return {
          label: src.label,
          rows: parseCSV(text)
        };
      })
      .catch(function(err) {
        console.warn('Failed to load ' + src.label + ':', err);

        return {
          label: src.label,
          rows: []
        };
      });
  });

  Promise.all(promises).then(function(results) {
    allRows = [];

    results.forEach(function(result) {
      result.rows.forEach(function(row) {
        allRows.push(normalizeRow(row, result.label));
      });
    });

    var graded = allRows.filter(function(r) {
      return r.result === 'win' || r.result === 'loss' || r.result === 'push';
    }).length;

    setStatus(
      allRows.length + ' bets loaded · ' + graded + ' graded · active: ' +
      activeSources.map(function(s) {
        return s.label;
      }).join(', '),
      'green'
    );

    render();
  });
}

function filteredRows() {
  return allRows.filter(function(r) {
    if (activeLeague !== 'all' && r.league !== activeLeague) return false;
    if (activeMarket !== 'all' && r.market !== activeMarket) return false;
    if (activeResult !== 'all' && r.result !== activeResult) return false;

    return true;
  });
}

document.querySelectorAll('.league-pill').forEach(function(pill) {
  pill.addEventListener('click', function() {
    document.querySelectorAll('.league-pill').forEach(function(p) {
      p.classList.remove('active');
    });

    pill.classList.add('active');
    activeLeague = pill.dataset.league;

    if (allRows.length) render();
  });
});

document.querySelectorAll('.market-pill').forEach(function(pill) {
  pill.addEventListener('click', function() {
    document.querySelectorAll('.market-pill').forEach(function(p) {
      p.classList.remove('active');
    });

    pill.classList.add('active');
    activeMarket = pill.dataset.market;

    if (allRows.length) render();
  });
});

document.querySelectorAll('.result-pill').forEach(function(pill) {
  pill.addEventListener('click', function() {
    document.querySelectorAll('.result-pill').forEach(function(p) {
      p.classList.remove('active');
    });

    pill.classList.add('active');
    activeResult = pill.dataset.result;

    if (allRows.length) render();
  });
});

loadAll();
