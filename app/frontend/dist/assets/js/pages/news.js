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

var allArticles = [];
var activeFilterType = "all";
var activeFilterValue = "all";
var searchQuery = "";

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
  document.getElementById("news-status").className = "status-bar " + (cls || "");
  document.getElementById("status-dot").className = "status-dot " + (dotCls || "");
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

  closeAllMenus();
  setActiveControls(type, value);
  render();
}

async function fetchLeagueNews(source) {
  var url = "https://site.api.espn.com/apis/site/v2/sports/" + source.sport + "/" + source.league + "/news?limit=20";

  try {
    var response = await fetch(url, { cache: "no-store" });

    if (!response.ok) return [];

    var data = await response.json();
    var articles = data.articles || [];

    return articles.map(function(article) {
      var webUrl = "#";

      if (article.links && article.links.web && article.links.web.href) {
        webUrl = article.links.web.href;
      }

      return {
        league: source.key,
        label: source.label,
        group: source.group,
        headline: article.headline || "",
        desc: article.description || "",
        img: article.images && article.images[0] ? article.images[0].url : "",
        source: article.source || "",
        date: article.published ? new Date(article.published) : null,
        url: webUrl
      };
    });
  } catch (error) {
    console.warn(source.key + " news failed:", error);
    return [];
  }
}

function fmtDate(date) {
  if (!date) return "";

  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric"
  }) + " · " + date.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit"
  });
}

function filterArticles() {
  var articles = allArticles.slice();

  if (activeFilterType === "league") {
    articles = articles.filter(function(article) {
      return article.league === activeFilterValue;
    });
  }

  if (activeFilterType === "group") {
    var allowed = GROUPS[activeFilterValue] || [];

    articles = articles.filter(function(article) {
      return allowed.indexOf(article.league) !== -1;
    });
  }

  if (searchQuery) {
    var query = searchQuery.toLowerCase();

    articles = articles.filter(function(article) {
      return String(article.headline || "").toLowerCase().indexOf(query) !== -1 ||
             String(article.desc || "").toLowerCase().indexOf(query) !== -1 ||
             String(article.label || "").toLowerCase().indexOf(query) !== -1;
    });
  }

  return articles;
}

function render() {
  var articles = filterArticles();
  var grid = document.getElementById("news-grid");
  var empty = document.getElementById("news-empty");

  grid.innerHTML = "";

  if (articles.length === 0) {
    empty.style.display = "";
    return;
  }

  empty.style.display = "none";

  articles.forEach(function(article) {
    var card = document.createElement("div");
    card.className = "news-card";

    var safeLeague = escapeHtml(article.league);
    var safeLabel = escapeHtml(article.label || sourceLabel(article.league));
    var safeHeadline = escapeHtml(article.headline);
    var safeDesc = escapeHtml(article.desc);
    var safeSource = escapeHtml(article.source || "");
    var safeDate = article.date ? escapeHtml(fmtDate(article.date)) : "";
    var safeUrl = escapeHtml(article.url || "#");
    var safeImg = escapeHtml(article.img || "");

    var imgHtml = safeImg
      ? '<div class="news-img-wrap"><img class="news-img" src="' + safeImg + '" loading="lazy" alt=""></div>'
      : '<div class="news-img-placeholder"><span>' + safeLabel + '</span></div>';

    card.innerHTML =
      imgHtml +
      '<div class="news-body">' +
        '<span class="news-league-tag tag-' + safeLeague + '">' + safeLabel + '</span>' +
        '<div class="news-headline">' + safeHeadline + '</div>' +
        (safeDesc ? '<div class="news-desc">' + safeDesc + '</div>' : '') +
        '<div class="news-footer">' +
          '<div class="news-meta">' + safeSource + (safeDate ? " · " + safeDate : "") + '</div>' +
          '<a class="news-link" href="' + safeUrl + '" target="_blank" rel="noopener">READ →</a>' +
        '</div>' +
      '</div>';

    grid.appendChild(card);
  });
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

document.getElementById("news-search").addEventListener("input", function(event) {
  searchQuery = event.target.value.trim();
  render();
});

async function loadAll() {
  setStatus("Fetching news...", "loading", "yellow");
  allArticles = [];

  try {
    var results = await Promise.all(SOURCES.map(function(source) {
      return fetchLeagueNews(source);
    }));

    results.forEach(function(articles) {
      allArticles = allArticles.concat(articles);
    });

    allArticles.sort(function(a, b) {
      if (!a.date && !b.date) return 0;
      if (!a.date) return 1;
      if (!b.date) return -1;

      return b.date - a.date;
    });

    render();

    if (allArticles.length === 0) {
      setStatus("No articles loaded", "error", "red");
    } else {
      var updatedTime = new Date().toLocaleTimeString("en-US", {
        hour: "numeric",
        minute: "2-digit"
      });
      setStatus(allArticles.length + " ARTICLES · UPDATED " + updatedTime, "", "green");
    }
  } catch (error) {
    console.error(error);
    setStatus("Error loading news", "error", "red");
    render();
  }
}

loadAll();
