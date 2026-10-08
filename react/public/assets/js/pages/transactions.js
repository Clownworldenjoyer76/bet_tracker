var SOURCES = [
  { key: "NHL",        label: "NHL",                group: "hockey",     sport: "hockey",     league: "nhl"                    },
  { key: "MLB",        label: "MLB",                group: "baseball",   sport: "baseball",   league: "mlb"                    },

  { key: "NBA",        label: "NBA",                group: "basketball", sport: "basketball", league: "nba"                    },
  { key: "NCAAM",      label: "College Basketball", group: "basketball", sport: "basketball", league: "mens-college-basketball" },
  { key: "WNBA",       label: "WNBA",               group: "basketball", sport: "basketball", league: "wnba"                   },

  { key: "MLS",        label: "MLS",                group: "soccer",     sport: "soccer",     league: "usa.1"                  },
  { key: "EPL",        label: "EPL",                group: "soccer",     sport: "soccer",     league: "eng.1"                  },
  { key: "LALIGA",     label: "La Liga",            group: "soccer",     sport: "soccer",     league: "esp.1"                  },
  { key: "LIGUE1",     label: "Ligue 1",            group: "soccer",     sport: "soccer",     league: "fra.1"                  },
  { key: "SERIEA",     label: "Serie A",            group: "soccer",     sport: "soccer",     league: "ita.1"                  },
  { key: "BUNDESLIGA", label: "Bundesliga",         group: "soccer",     sport: "soccer",     league: "ger.1"                  },

  { key: "UFC",        label: "UFC",                group: "mma",        sport: "mma",        league: "ufc"                    },

  { key: "NFL",        label: "NFL",                group: "football",   sport: "football",   league: "nfl"                    },
  { key: "CFB",        label: "College Football",   group: "football",   sport: "football",   league: "college-football"       },
  { key: "CFL",        label: "CFL",                group: "football",   sport: "football",   league: "cfl"                    }
];

var GROUPS = {
  football: ["NFL", "CFB", "CFL"],
  basketball: ["NBA", "NCAAM", "WNBA"],
  soccer: ["MLS", "EPL", "LALIGA", "LIGUE1", "SERIEA", "BUNDESLIGA"]
};

var PAGE_SIZE = 50;

var allTxns = [];
var activeFilterType = "all";
var activeFilterValue = "all";
var searchQuery = "";
var typeFilter = "all";
var periodFilter = "7";
var visibleLimit = PAGE_SIZE;

function escapeHtml(value) {
  return String(value || "").replace(/[&<>'"]/g, function(char) {
    return {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "'": "&#39;",
      '"': "&quot;"
    }[char];
  });
}

function setStatus(text, cls, dotCls) {
  document.getElementById("status-text").textContent = text;
  document.getElementById("txn-status").className = "status-bar " + (cls || "");
  document.getElementById("status-dot").className = "status-dot " + (dotCls || "");
}

function parseTxnDate(str) {
  if (!str) return null;

  var d = new Date(str);
  if (isNaN(d.getTime())) return null;

  return d;
}

function fmtDateHeading(str) {
  var d = parseTxnDate(str);
  if (!d) return "Unknown Date";

  return d.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric"
  });
}

function dateGroupKey(str) {
  var d = parseTxnDate(str);
  if (!d) return "unknown";

  return [
    d.getFullYear(),
    String(d.getMonth() + 1).padStart(2, "0"),
    String(d.getDate()).padStart(2, "0")
  ].join("-");
}

function transactionAgeDays(str) {
  var d = parseTxnDate(str);
  if (!d) return Number.POSITIVE_INFINITY;

  var now = new Date();

  var txnDay = new Date(
    d.getFullYear(),
    d.getMonth(),
    d.getDate()
  );

  var today = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate()
  );

  return Math.floor(
    (today.getTime() - txnDay.getTime()) /
    86400000
  );
}

function classifyTransaction(desc) {
  var text = String(desc || "").toLowerCase();
  var matches = [];

  function add(key, label, pattern) {
    if (pattern.test(text)) {
      matches.push({
        key: key,
        label: label
      });
    }
  }

  add("trade", "Trade", /\btraded\b|\btrade\b/);
  add("signed", "Signed", /\bsigned\b|\bsigns\b|\bsigning\b/);
  add(
    "il",
    "Injured List",
    /\binjured list\b|\bdisabled list\b|\bplaced\b[^.]*\bil\b|\b15-day il\b|\b10-day il\b|\b60-day il\b/
  );
  add(
    "released",
    "Released / DFA",
    /\bdesignated\b[^.]*\bassignment\b|\bdfa\b|\breleased\b/
  );
  add("reinstated", "Reinstated", /\breinstated\b|\bactivated\b/);
  add("recalled", "Recalled", /\brecalled\b/);
  add("optioned", "Optioned", /\boptioned\b|\bassigned\b|\bassignment\b/);
  add("claimed", "Claimed", /\bclaimed\b/);
  add("waived", "Waived", /\bwaived\b|\bwaivers\b/);

  if (!matches.length) {
    matches.push({
      key: "other",
      label: "Other"
    });
  }

  return matches;
}

function sourceLabel(key) {
  var found = SOURCES.find(function(source) {
    return source.key === key;
  });

  return found ? found.label : key;
}

function sourceGroup(key) {
  var found = SOURCES.find(function(source) {
    return source.key === key;
  });

  return found ? found.group : "";
}

function closeAllMenus() {
  document.querySelectorAll(".control-group").forEach(function(group) {
    group.classList.remove("open");
  });
}

function setActiveControls(type, value) {
  document.querySelectorAll(".league-pill, .group-pill, .submenu-pill").forEach(function(button) {
    button.classList.remove("active");
  });

  if (type === "all") {
    var allButton = document.querySelector('[data-filter-type="all"][data-filter-value="all"]');
    if (allButton) allButton.classList.add("active");
    return;
  }

  if (type === "group") {
    var groupButton = document.querySelector('[data-group-toggle="' + value + '"]');
    var groupSubButton = document.querySelector('.submenu-pill[data-filter-type="group"][data-filter-value="' + value + '"]');

    if (groupButton) groupButton.classList.add("active");
    if (groupSubButton) groupSubButton.classList.add("active");
    return;
  }

  if (type === "league") {
    var directButton = document.querySelector('.league-pill[data-filter-type="league"][data-filter-value="' + value + '"]');
    var childButton = document.querySelector('.submenu-pill[data-filter-type="league"][data-filter-value="' + value + '"]');
    var group = sourceGroup(value);

    if (directButton) directButton.classList.add("active");
    if (childButton) childButton.classList.add("active");

    if (group) {
      var parentButton = document.querySelector('[data-group-toggle="' + group + '"]');
      if (parentButton) parentButton.classList.add("active");
    }
  }
}

function applyFilter(type, value) {
  activeFilterType = type;
  activeFilterValue = value;
  visibleLimit = PAGE_SIZE;

  closeAllMenus();
  setActiveControls(type, value);
  render();
}

function matchesPeriod(row) {
  if (periodFilter === "all") {
    return true;
  }

  var ageDays = transactionAgeDays(row.date);

  if (!Number.isFinite(ageDays) || ageDays < 0) {
    return false;
  }

  if (periodFilter === "today") {
    return ageDays === 0;
  }

  var days = parseInt(periodFilter, 10);

  if (!Number.isFinite(days)) {
    return true;
  }

  return ageDays <= (days - 1);
}

function filteredTransactions() {
  var rows = allTxns.slice();

  if (activeFilterType === "league") {
    rows = rows.filter(function(row) {
      return row.league === activeFilterValue;
    });
  }

  if (activeFilterType === "group") {
    var allowed = GROUPS[activeFilterValue] || [];

    rows = rows.filter(function(row) {
      return allowed.indexOf(row.league) !== -1;
    });
  }

  if (typeFilter !== "all") {
    rows = rows.filter(function(row) {
      return (row.types || []).some(function(type) {
        return type.key === typeFilter;
      });
    });
  }

  rows = rows.filter(matchesPeriod);

  if (searchQuery) {
    var q = searchQuery.toLowerCase();

    rows = rows.filter(function(row) {
      return String(row.team || "").toLowerCase().indexOf(q) !== -1 ||
             String(row.teamName || "").toLowerCase().indexOf(q) !== -1 ||
             String(row.desc || "").toLowerCase().indexOf(q) !== -1 ||
             String(row.label || "").toLowerCase().indexOf(q) !== -1 ||
             (row.types || []).some(function(type) {
               return String(type.label || "").toLowerCase().indexOf(q) !== -1;
             });
    });
  }

  rows.sort(function(a, b) {
    var at = a.date ? new Date(a.date).getTime() : 0;
    var bt = b.date ? new Date(b.date).getTime() : 0;
    return bt - at;
  });

  return rows;
}

function render() {
  var rows = filteredTransactions();
  var shown = rows.slice(0, visibleLimit);

  var feed = document.getElementById("txn-feed");
  var empty = document.getElementById("txn-empty");
  var loadMore = document.getElementById("load-more");
  var resultCount = document.getElementById("result-count");

  feed.innerHTML = "";

  resultCount.textContent =
    "Showing " +
    Math.min(shown.length, rows.length) +
    " of " +
    rows.length +
    " matching transactions";

  if (rows.length === 0) {
    empty.style.display = "";
    loadMore.style.display = "none";
    return;
  }

  empty.style.display = "none";

  var currentGroupKey = "";
  var currentGroup = null;
  var currentRows = null;
  var groupCounts = {};

  shown.forEach(function(t) {
    var groupKey = dateGroupKey(t.date);

    if (!groupCounts[groupKey]) {
      groupCounts[groupKey] = 0;
    }

    groupCounts[groupKey]++;
  });

  shown.forEach(function(t) {
    var groupKey = dateGroupKey(t.date);

    if (groupKey !== currentGroupKey) {
      currentGroupKey = groupKey;

      currentGroup = document.createElement("section");
      currentGroup.className = "txn-date-group";

      var heading = document.createElement("div");
      heading.className = "txn-date-heading";
      heading.innerHTML =
        '<span>' + escapeHtml(fmtDateHeading(t.date)) + '</span>' +
        '<span class="txn-date-count">' +
          groupCounts[groupKey] +
          ' shown' +
        '</span>';

      currentRows = document.createElement("div");

      currentGroup.appendChild(heading);
      currentGroup.appendChild(currentRows);
      feed.appendChild(currentGroup);
    }

    var row = document.createElement("div");
    row.className = "txn-row";

    var teamTitle = t.teamName || t.team || "";

    row.innerHTML =
      '<div class="txn-league league-' + escapeHtml(t.league) + '">' +
        escapeHtml(t.label || sourceLabel(t.league)) +
      '</div>' +

      '<div class="txn-team" title="' + escapeHtml(teamTitle) + '">' +
        escapeHtml(t.team || "—") +
      '</div>' +

      '<div class="txn-types">' +
        (t.types || []).map(function(type) {
          return (
            '<span class="txn-type type-' + escapeHtml(type.key) + '">' +
              escapeHtml(type.label) +
            '</span>'
          );
        }).join("") +
      '</div>' +

      '<div class="txn-desc">' +
        escapeHtml(t.desc || "—") +
      '</div>';

    currentRows.appendChild(row);
  });

  loadMore.style.display =
    rows.length > visibleLimit
      ? "block"
      : "none";
}

async function fetchLeagueTransactions(source) {
  var url = "https://site.api.espn.com/apis/site/v2/sports/" +
    source.sport + "/" +
    source.league +
    "/transactions";

  try {
    var response = await fetch(url, { cache: "no-store" });

    if (!response.ok) return [];

    var data = await response.json();
    var txns = data.transactions || [];

    return txns.map(function(t) {
      var classifications = classifyTransaction(t.description || "");

      return {
        league: source.key,
        label: source.label,
        group: source.group,
        date: t.date || "",
        team: t.team ? (t.team.abbreviation || t.team.displayName || "") : "",
        teamName: t.team ? (t.team.displayName || t.team.name || t.team.abbreviation || "") : "",
        desc: t.description || "",
        types: classifications
      };
    });
  } catch (error) {
    console.warn(source.key + " transactions failed:", error);
    return [];
  }
}

async function loadAll() {
  setStatus("Fetching transactions...", "loading", "yellow");
  allTxns = [];

  try {
    var results = await Promise.all(SOURCES.map(function(source) {
      return fetchLeagueTransactions(source);
    }));

    results.forEach(function(rows) {
      allTxns = allTxns.concat(rows);
    });

    render();

    if (allTxns.length === 0) {
      setStatus("No transactions loaded", "", "");
    } else {
      var updatedTime = new Date().toLocaleTimeString("en-US", {
        hour: "numeric",
        minute: "2-digit"
      });

      setStatus(
        allTxns.length +
        " TRANSACTIONS LOADED · UPDATED " +
        updatedTime,
        "",
        "green"
      );
    }
  } catch (error) {
    console.error(error);
    setStatus("Error loading transactions", "error", "red");
    render();
  }
}

document.querySelectorAll("[data-group-toggle]").forEach(function(button) {
  button.addEventListener("click", function(event) {
    event.stopPropagation();

    var groupName = button.dataset.groupToggle;
    var group = document.querySelector('.control-group[data-group="' + groupName + '"]');
    var wasOpen = group && group.classList.contains("open");

    closeAllMenus();

    if (group && !wasOpen) {
      group.classList.add("open");
    }
  });
});

document.querySelectorAll("[data-filter-type]").forEach(function(button) {
  button.addEventListener("click", function(event) {
    event.stopPropagation();

    applyFilter(button.dataset.filterType, button.dataset.filterValue);
  });
});

document.addEventListener("click", function(event) {
  if (!event.target.closest(".control-group")) {
    closeAllMenus();
  }
});

document.addEventListener("keydown", function(event) {
  if (event.key === "Escape") {
    closeAllMenus();
  }
});

document.getElementById("txn-search").addEventListener("input", function(event) {
  searchQuery = event.target.value.trim();
  visibleLimit = PAGE_SIZE;
  render();
});

document.getElementById("type-filter").addEventListener("change", function(event) {
  typeFilter = event.target.value;
  visibleLimit = PAGE_SIZE;
  render();
});

document.getElementById("period-filter").addEventListener("change", function(event) {
  periodFilter = event.target.value;
  visibleLimit = PAGE_SIZE;
  render();
});

document.getElementById("load-more").addEventListener("click", function() {
  visibleLimit += PAGE_SIZE;
  render();
});

loadAll();
