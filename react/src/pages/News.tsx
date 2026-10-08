/*
  News - native React port of legacy news.html + assets/js/pages/news-html.js.

  Legacy behaviors found and preserved:
   1. 15 ESPN news sources (NHL, MLB, NBA, NCAAM, WNBA, MLS, EPL, LALIGA, LIGUE1, SERIEA, BUNDESLIGA, UFC, NFL, CFB, CFL),
      each fetched once on load from site.api.espn.com .../{sport}/{league}/news?limit=20 with cache: "no-store", all in parallel.
   2. A non-OK response or a failed fetch gives no articles for that league (failure is logged with console.warn).
   3. Article fields: league key, label, group, headline, description, first image url, source, published date, web link ("#" if none).
   4. Articles sorted newest first; articles without a date go last.
   5. Status bar: "Fetching news..." (loading, yellow dot) while loading; "N ARTICLES - UPDATED h:mm AM" (green) when done;
      "No articles loaded" (error, red) when nothing loaded; "Error loading news" (error, red) if the whole load throws.
   6. Filters: All, group (Football, Basketball, Soccer: "All Football" etc.), single league (NFL, CFB, CFL, NHL, MLB, NBA, NCAAM,
      WNBA, MLS, EPL, LALIGA, LIGUE1, SERIEA, BUNDESLIGA, UFC). Selecting a filter closes the open menu.
   7. Group buttons toggle their own submenu; only one menu is open at a time; clicking outside the groups or pressing Escape closes menus.
   8. Active highlighting: All; a group highlights its toggle and its "All X" item; a league highlights its pill (or submenu item)
      and the parent group's toggle.
   9. Search box (trimmed, case-insensitive) matches headline, description or league label; combines with the filter.
  10. Cards: image or placeholder with the league label, league tag, headline, description (only if present), source and date
      ("Mon D, YYYY - h:mm AM"), "READ" link opening in a new tab (rel noopener).
  11. "No articles found" shown when the filtered list is empty after loading (nothing shown before the first load finishes).
  12. Not present in legacy: URL params, localStorage, auto-refresh, POST, credentials (nav.js is loaded by SiteShell).
  Difference: ESPN text is rendered as React text (legacy escaped it into innerHTML) - same visible result.
*/
import { useEffect, useMemo, useState } from "react";
import "../../../app/frontend/src/assets/css/pages/news-html.css";

const MID = String.fromCharCode(0xb7);
const ARROW = String.fromCharCode(0x2192);

type Source = {
  key: string;
  label: string;
  group: string;
  sport: string;
  league: string;
};

type Article = {
  league: string;
  label: string;
  group: string;
  headline: string;
  desc: string;
  img: string;
  source: string;
  date: Date | null;
  url: string;
};

type FilterType = "all" | "group" | "league";

const SOURCES: Source[] = [
  { key: "NHL", label: "NHL", group: "hockey", sport: "hockey", league: "nhl" },
  { key: "MLB", label: "MLB", group: "baseball", sport: "baseball", league: "mlb" },
  { key: "NBA", label: "NBA", group: "basketball", sport: "basketball", league: "nba" },
  { key: "NCAAM", label: "College Basketball", group: "basketball", sport: "basketball", league: "mens-college-basketball" },
  { key: "WNBA", label: "WNBA", group: "basketball", sport: "basketball", league: "wnba" },
  { key: "MLS", label: "MLS", group: "soccer", sport: "soccer", league: "usa.1" },
  { key: "EPL", label: "EPL", group: "soccer", sport: "soccer", league: "eng.1" },
  { key: "LALIGA", label: "La Liga", group: "soccer", sport: "soccer", league: "esp.1" },
  { key: "LIGUE1", label: "Ligue 1", group: "soccer", sport: "soccer", league: "fra.1" },
  { key: "SERIEA", label: "Serie A", group: "soccer", sport: "soccer", league: "ita.1" },
  { key: "BUNDESLIGA", label: "Bundesliga", group: "soccer", sport: "soccer", league: "ger.1" },
  { key: "UFC", label: "UFC", group: "mma", sport: "mma", league: "ufc" },
  { key: "NFL", label: "NFL", group: "football", sport: "football", league: "nfl" },
  { key: "CFB", label: "College Football", group: "football", sport: "football", league: "college-football" },
  { key: "CFL", label: "CFL", group: "football", sport: "football", league: "cfl" },
];

const GROUPS: Record<string, string[]> = {
  football: ["NFL", "CFB", "CFL"],
  basketball: ["NBA", "NCAAM", "WNBA"],
  soccer: ["MLS", "EPL", "LALIGA", "LIGUE1", "SERIEA", "BUNDESLIGA"],
};

type MenuGroup = {
  name: string;
  label: string;
  items: { value: string; label: string }[];
};

const MENU_GROUPS: Record<string, MenuGroup> = {
  football: {
    name: "football",
    label: "Football",
    items: [
      { value: "NFL", label: "NFL" },
      { value: "CFB", label: "College Football" },
      { value: "CFL", label: "CFL" },
    ],
  },
  basketball: {
    name: "basketball",
    label: "Basketball",
    items: [
      { value: "NBA", label: "NBA" },
      { value: "NCAAM", label: "College Basketball" },
      { value: "WNBA", label: "WNBA" },
    ],
  },
  soccer: {
    name: "soccer",
    label: "Soccer",
    items: [
      { value: "MLS", label: "MLS" },
      { value: "EPL", label: "EPL" },
      { value: "LALIGA", label: "La Liga" },
      { value: "LIGUE1", label: "Ligue 1" },
      { value: "SERIEA", label: "Serie A" },
      { value: "BUNDESLIGA", label: "Bundesliga" },
    ],
  },
};

function sourceLabel(key: string) {
  const found = SOURCES.find((source) => source.key === key);
  return found ? found.label : key;
}

function sourceGroup(key: string) {
  const found = SOURCES.find((source) => source.key === key);
  return found ? found.group : "";
}

async function fetchLeagueNews(source: Source, signal: AbortSignal): Promise<Article[]> {
  const url =
    "https://site.api.espn.com/apis/site/v2/sports/" +
    source.sport +
    "/" +
    source.league +
    "/news?limit=20";

  try {
    const response = await fetch(url, { cache: "no-store", signal });

    if (!response.ok) return [];

    const data = await response.json();
    const articles: any[] = data.articles || [];

    return articles.map((article) => {
      let webUrl = "#";

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
        url: webUrl,
      };
    });
  } catch (error) {
    if (signal.aborted) return [];
    console.warn(source.key + " news failed:", error);
    return [];
  }
}

function fmtDate(date: Date | null) {
  if (!date) return "";

  return (
    date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    }) +
    " " +
    MID +
    " " +
    date.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
    })
  );
}

function filterArticles(
  allArticles: Article[],
  type: FilterType,
  value: string,
  search: string
) {
  let articles = allArticles.slice();

  if (type === "league") {
    articles = articles.filter((article) => article.league === value);
  }

  if (type === "group") {
    const allowed = GROUPS[value] || [];

    articles = articles.filter((article) => allowed.indexOf(article.league) !== -1);
  }

  if (search) {
    const query = search.toLowerCase();

    articles = articles.filter(
      (article) =>
        String(article.headline || "").toLowerCase().indexOf(query) !== -1 ||
        String(article.desc || "").toLowerCase().indexOf(query) !== -1 ||
        String(article.label || "").toLowerCase().indexOf(query) !== -1
    );
  }

  return articles;
}

function pillClass(base: string, active: boolean) {
  return base + (active ? " active" : "");
}

export default function News() {
  const [allArticles, setAllArticles] = useState<Article[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [statusText, setStatusText] = useState("Loading...");
  const [statusClass, setStatusClass] = useState("");
  const [dotClass, setDotClass] = useState("yellow");
  const [filterType, setFilterType] = useState<FilterType>("all");
  const [filterValue, setFilterValue] = useState("all");
  const [search, setSearch] = useState("");
  const [openGroup, setOpenGroup] = useState<string | null>(null);

  // Load all league news once (legacy loadAll()).
  useEffect(() => {
    const controller = new AbortController();

    const loadAll = async () => {
      setStatusText("Fetching news...");
      setStatusClass("loading");
      setDotClass("yellow");

      try {
        const results = await Promise.all(
          SOURCES.map((source) => fetchLeagueNews(source, controller.signal))
        );

        if (controller.signal.aborted) return;

        let articles: Article[] = [];

        results.forEach((list) => {
          articles = articles.concat(list);
        });

        articles.sort((a, b) => {
          if (!a.date && !b.date) return 0;
          if (!a.date) return 1;
          if (!b.date) return -1;

          return b.date.getTime() - a.date.getTime();
        });

        setAllArticles(articles);
        setLoaded(true);

        if (articles.length === 0) {
          setStatusText("No articles loaded");
          setStatusClass("error");
          setDotClass("red");
        } else {
          const updatedTime = new Date().toLocaleTimeString("en-US", {
            hour: "numeric",
            minute: "2-digit",
          });

          setStatusText(articles.length + " ARTICLES " + MID + " UPDATED " + updatedTime);
          setStatusClass("");
          setDotClass("green");
        }
      } catch (error) {
        if (controller.signal.aborted) return;

        console.error(error);
        setStatusText("Error loading news");
        setStatusClass("error");
        setDotClass("red");
        setLoaded(true);
      }
    };

    loadAll();

    return () => controller.abort();
  }, []);

  // Close menus on outside click or Escape.
  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      const target = event.target;

      if (!(target instanceof Element) || !target.closest(".control-group")) {
        setOpenGroup(null);
      }
    };

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpenGroup(null);
    };

    document.addEventListener("click", onClick);
    document.addEventListener("keydown", onKey);

    return () => {
      document.removeEventListener("click", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  const articles = useMemo(
    () => filterArticles(allArticles, filterType, filterValue, search),
    [allArticles, filterType, filterValue, search]
  );

  const applyFilter = (type: FilterType, value: string) => {
    setFilterType(type);
    setFilterValue(value);
    setOpenGroup(null);
  };

  const activeLeagueGroup = filterType === "league" ? sourceGroup(filterValue) : "";

  const isGroupActive = (name: string) =>
    (filterType === "group" && filterValue === name) || activeLeagueGroup === name;

  const leaguePill = (value: string, label: string) => (
    <button
      type="button"
      className={pillClass("league-pill", filterType === "league" && filterValue === value)}
      onClick={(event) => {
        event.stopPropagation();
        applyFilter("league", value);
      }}
    >
      {label}
    </button>
  );

  const groupControl = (group: MenuGroup) => (
    <div
      className={"control-group" + (openGroup === group.name ? " open" : "")}
      key={group.name}
    >
      <button
        type="button"
        className={pillClass("group-pill", isGroupActive(group.name))}
        onClick={(event) => {
          event.stopPropagation();
          setOpenGroup(openGroup === group.name ? null : group.name);
        }}
      >
        {group.label}
      </button>

      <div className="submenu">
        <button
          type="button"
          className={pillClass(
            "submenu-pill",
            filterType === "group" && filterValue === group.name
          )}
          onClick={(event) => {
            event.stopPropagation();
            applyFilter("group", group.name);
          }}
        >
          All {group.label}
        </button>

        {group.items.map((item) => (
          <button
            type="button"
            key={item.value}
            className={pillClass(
              "submenu-pill",
              filterType === "league" && filterValue === item.value
            )}
            onClick={(event) => {
              event.stopPropagation();
              applyFilter("league", item.value);
            }}
          >
            {item.label}
          </button>
        ))}
      </div>
    </div>
  );

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">News</div>
          <div className="page-subtitle">
            {["All", "Football", "NHL", "MLB", "Basketball", "Soccer", "UFC"].join(
              " " + MID + " "
            )}
          </div>
        </div>
      </div>

      <div className="controls" id="league-controls">
        <button
          type="button"
          className={pillClass("league-pill", filterType === "all")}
          onClick={(event) => {
            event.stopPropagation();
            applyFilter("all", "all");
          }}
        >
          All
        </button>

        {groupControl(MENU_GROUPS.football)}

        {leaguePill("NHL", "NHL")}
        {leaguePill("MLB", "MLB")}

        {groupControl(MENU_GROUPS.basketball)}
        {groupControl(MENU_GROUPS.soccer)}

        {leaguePill("UFC", "UFC")}

        <input
          type="text"
          className="search-box"
          id="news-search"
          placeholder="Search headlines..."
          value={search}
          onChange={(event) => setSearch(event.target.value.trim())}
        />
      </div>

      <div className={"status-bar" + (statusClass ? " " + statusClass : "")} id="news-status">
        <span className={"status-dot " + dotClass} id="status-dot" />
        <span id="status-text">{statusText}</span>
      </div>

      <div className="main">
        <div className="news-grid" id="news-grid">
          {loaded
            ? articles.map((article, index) => (
                <div className="news-card" key={article.league + "-" + index}>
                  {article.img ? (
                    <div className="news-img-wrap">
                      <img className="news-img" src={article.img} loading="lazy" alt="" />
                    </div>
                  ) : (
                    <div className="news-img-placeholder">
                      <span>{article.label || sourceLabel(article.league)}</span>
                    </div>
                  )}

                  <div className="news-body">
                    <span className={"news-league-tag tag-" + article.league}>
                      {article.label || sourceLabel(article.league)}
                    </span>
                    <div className="news-headline">{article.headline}</div>
                    {article.desc ? <div className="news-desc">{article.desc}</div> : null}
                    <div className="news-footer">
                      <div className="news-meta">
                        {article.source || ""}
                        {article.date ? " " + MID + " " + fmtDate(article.date) : ""}
                      </div>
                      <a
                        className="news-link"
                        href={article.url || "#"}
                        target="_blank"
                        rel="noopener"
                      >
                        READ {ARROW}
                      </a>
                    </div>
                  </div>
                </div>
              ))
            : null}
        </div>

        <div
          className="empty-state"
          id="news-empty"
          style={{ display: loaded && articles.length === 0 ? "" : "none" }}
        >
          No articles found
        </div>
      </div>
    </>
  );
}
