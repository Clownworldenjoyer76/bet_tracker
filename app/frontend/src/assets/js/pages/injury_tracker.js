(function() {
  "use strict";

  var RAW_DOCS =
    "https://raw.githubusercontent.com/" +
    "Clownworldenjoyer76/bet_tracker/main/docs/";

  var PAGE_SIZE = 50;

  /*
    These are intentionally always available on this page.
    They are not tied to the offseason toggles used by
    Games Today / Live Scores / Final Scores.
  */
  var LEAGUES = [
    {
      key: "NHL",
      label: "NHL",
      group: "hockey",
      sport: "hockey",
      league: "nhl"
    },
    {
      key: "MLB",
      label: "MLB",
      group: "baseball",
      sport: "baseball",
      league: "mlb"
    },

    {
      key: "NBA",
      label: "NBA",
      group: "basketball",
      sport: "basketball",
      league: "nba"
    },
    {
      key: "NCAAM",
      label: "College Basketball",
      group: "basketball",
      sport: "basketball",
      league: "mens-college-basketball"
    },
    {
      key: "WNBA",
      label: "WNBA",
      group: "basketball",
      sport: "basketball",
      league: "wnba"
    },

    {
      key: "MLS",
      label: "MLS",
      group: "soccer",
      sport: "soccer",
      league: "usa.1"
    },
    {
      key: "EPL",
      label: "EPL",
      group: "soccer",
      sport: "soccer",
      league: "eng.1"
    },
    {
      key: "LALIGA",
      label: "La Liga",
      group: "soccer",
      sport: "soccer",
      league: "esp.1"
    },
    {
      key: "LIGUE1",
      label: "Ligue 1",
      group: "soccer",
      sport: "soccer",
      league: "fra.1"
    },
    {
      key: "SERIEA",
      label: "Serie A",
      group: "soccer",
      sport: "soccer",
      league: "ita.1"
    },
    {
      key: "BUNDESLIGA",
      label: "Bundesliga",
      group: "soccer",
      sport: "soccer",
      league: "ger.1"
    },

    {
      key: "UFC",
      label: "UFC",
      group: "mma",
      sport: "mma",
      league: "ufc"
    },

    {
      key: "NFL",
      label: "NFL",
      group: "football",
      sport: "football",
      league: "nfl"
    },
    {
      key: "CFB",
      label: "College Football",
      group: "football",
      sport: "football",
      league: "college-football"
    },
    {
      key: "CFL",
      label: "CFL",
      group: "football",
      sport: "football",
      league: "cfl"
    }
  ];

  var GROUPS = {
    football: [
      "NFL",
      "CFB",
      "CFL"
    ],

    basketball: [
      "NBA",
      "NCAAM",
      "WNBA"
    ],

    soccer: [
      "MLS",
      "EPL",
      "LALIGA",
      "LIGUE1",
      "SERIEA",
      "BUNDESLIGA"
    ]
  };

  var leagueByKey = {};

  LEAGUES.forEach(function(cfg) {
    leagueByKey[cfg.key] = cfg;
  });

  var allInjuries = [];
  var todayPicks = [];

  /*
    These track the picked-team verification pass.

    League-wide ESPN injury feeds are still loaded first.
    Afterward we resolve the exact teams from today's picked games
    and query their team-specific ESPN injury endpoints.
  */
  var pickedTeamsResolved = 0;
  var pickedTeamInjuriesAdded = 0;

  var activeFilterType = "all";
  var activeFilterValue = "all";

  var searchQuery = "";
  var statusMode = "impact";
  var visibleLimit = PAGE_SIZE;

  function $(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(
      value === null || value === undefined
        ? ""
        : value
    ).replace(
      /[&<>'"]/g,
      function(char) {
        return {
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          "'": "&#39;",
          '"': "&quot;"
        }[char];
      }
    );
  }

  function padTwo(n) {
    return n < 10
      ? "0" + n
      : String(n);
  }

  function todayUnderscore() {
    var d = new Date();

    return (
      d.getFullYear() +
      "_" +
      padTwo(d.getMonth() + 1) +
      "_" +
      padTwo(d.getDate())
    );
  }

  function todayDash() {
    return todayUnderscore().replace(/_/g, "-");
  }

  function normalizeDate(value) {
    return String(value || "")
      .trim()
      .replace(/-/g, "_");
  }

  function normalizeLeague(value) {
    var league = String(value || "")
      .trim()
      .toUpperCase();

    if (league === "NCAAB") {
      return "NCAAM";
    }

    if (league === "COLLEGE-BASKETBALL") {
      return "NCAAM";
    }

    if (league === "COLLEGE BASKETBALL") {
      return "NCAAM";
    }

    if (league === "COLLEGE FOOTBALL") {
      return "CFB";
    }

    return league;
  }

  /*
    Match ESPN team names against pipeline team names.

    Parenthetical disambiguators are removed so forms such as:
    Miami (FL) Hurricanes
    can match a pipeline form without "(FL)".
  */
  function normalizeTeam(value) {
    var text = String(value || "");

    /*
      Unicode normalization is critical here.

      Examples:
      San José State -> San Jose State
      Köln           -> Koln
    */
    if (typeof text.normalize === "function") {
      text = text
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "");
    }

    return text
      .toLowerCase()
      .replace(/\([^)]*\)/g, " ")
      .replace(/&/g, "and")
      .replace(/['’`]/g, "")
      .replace(/[^a-z0-9]+/g, "");
  }

  function sameTeam(a, b) {
    var left = normalizeTeam(a);
    var right = normalizeTeam(b);

    if (!left || !right) {
      return false;
    }

    if (left === right) {
      return true;
    }

    var minLen = Math.min(
      left.length,
      right.length
    );

    /*
      Allows:
      Eastern Michigan
      Eastern Michigan Eagles

      San Jose State
      San Jose State Spartans
    */
    if (
      minLen >= 7 &&
      (
        left.indexOf(right) !== -1 ||
        right.indexOf(left) !== -1
      )
    ) {
      return true;
    }

    return false;
  }

  function sourceLabel(key) {
    return leagueByKey[key]
      ? leagueByKey[key].label
      : key;
  }

  function sourceGroup(key) {
    return leagueByKey[key]
      ? leagueByKey[key].group
      : "";
  }

  function setStatus(text, cls, dotCls) {
    $("status-text").textContent = text || "";

    $("inj-status").className =
      "status-bar " + (cls || "");

    $("status-dot").className =
      "status-dot " + (dotCls || "");
  }

  /* ── CSV parser ───────────────────────────────────────────────────────── */

  function cleanCSVCell(value) {
    var s = String(
      value === null || value === undefined
        ? ""
        : value
    ).trim();

    if (
      s.length >= 2 &&
      s.charAt(0) === '"' &&
      s.charAt(s.length - 1) === '"'
    ) {
      s = s.slice(1, -1);
    }

    return s
      .replace(/""/g, '"')
      .trim();
  }

  function parseCSVLine(line) {
    var out = [];
    var cur = "";
    var inQuotes = false;

    for (
      var i = 0;
      i < line.length;
      i++
    ) {
      var ch = line.charAt(i);

      if (ch === '"') {
        if (
          inQuotes &&
          line.charAt(i + 1) === '"'
        ) {
          cur += '"';
          i++;
        } else {
          inQuotes = !inQuotes;
        }

        continue;
      }

      if (
        ch === "," &&
        !inQuotes
      ) {
        out.push(cur);
        cur = "";
        continue;
      }

      cur += ch;
    }

    out.push(cur);

    return out;
  }

  function parseCSV(text) {
    var raw = String(text || "")
      .replace(/^\uFEFF/, "")
      .trim();

    if (!raw) {
      return [];
    }

    var lines = raw
      .split(/\r?\n/)
      .filter(function(line) {
        return line.trim() !== "";
      });

    if (lines.length < 2) {
      return [];
    }

    var headers = parseCSVLine(
      lines[0]
    ).map(cleanCSVCell);

    return lines
      .slice(1)
      .map(function(line) {
        var vals = parseCSVLine(
          line
        ).map(cleanCSVCell);

        var obj = {};

        headers.forEach(
          function(header, i) {
            obj[header] =
              vals[i] === undefined
                ? ""
                : vals[i];
          }
        );

        return obj;
      });
  }

  async function fetchCSV(path) {
    if (!path) {
      return {
        ok: false,
        rows: []
      };
    }

    var url =
      path.indexOf("win/") === 0
        ? RAW_DOCS + path
        : path;

    try {
      var response = await fetch(
        url,
        {
          cache: "no-store"
        }
      );

      if (!response.ok) {
        return {
          ok: false,
          rows: []
        };
      }

      return {
        ok: true,
        rows: parseCSV(
          await response.text()
        ),
        source: path
      };
    } catch (error) {
      return {
        ok: false,
        rows: []
      };
    }
  }

  async function fetchFirstCSV(paths) {
    var list = Array.isArray(paths)
      ? paths.filter(Boolean)
      : [];

    for (
      var i = 0;
      i < list.length;
      i++
    ) {
      var result = await fetchCSV(
        list[i]
      );

      if (result.ok) {
        return result;
      }
    }

    return {
      ok: false,
      rows: []
    };
  }

  function resolveSelectPaths(cfg, date) {
    if (
      !cfg ||
      !cfg.selectFiles
    ) {
      return [];
    }

    try {
      var value =
        typeof cfg.selectFiles === "function"
          ? cfg.selectFiles(date)
          : cfg.selectFiles;

      if (Array.isArray(value)) {
        return value.filter(Boolean);
      }

      return value
        ? [value]
        : [];
    } catch (error) {
      return [];
    }
  }

  function rowMatchesLeague(
    row,
    cfg,
    leagueKey
  ) {
    if (!cfg) {
      return false;
    }

    if (cfg.leagueColumn) {
      return (
        normalizeLeague(
          row[cfg.leagueColumn]
        ) === leagueKey
      );
    }

    if (cfg.marketColumn) {
      return (
        normalizeLeague(
          row[cfg.marketColumn]
        ) === leagueKey
      );
    }

    var rowLeague =
      normalizeLeague(
        row.league
      );

    return (
      !rowLeague ||
      rowLeague === leagueKey
    );
  }

  /* ── Today's picks ────────────────────────────────────────────────────── */

  function genericPickText(row) {
    var market = String(
      row.market_type ||
      row.market ||
      "Pick"
    )
      .replace(/_/g, " ")
      .toUpperCase();

    var side = String(
      row.bet_side ||
      row.side ||
      ""
    ).toLowerCase();

    var label = side;

    if (side === "home") {
      label = row.home_team || "Home";
    }

    if (side === "away") {
      label = row.away_team || "Away";
    }

    if (side === "over") {
      label = "Over";
    }

    if (side === "under") {
      label = "Under";
    }

    if (side === "draw") {
      label = "Draw";
    }

    var line =
      row.bet_line ||
      row.line ||
      "";

    var odds =
      row.bet_odds_american ||
      row.dk_odds_american ||
      row.take_odds ||
      row.odds ||
      "";

    var lineText =
      line !== ""
        ? " " + line
        : "";

    var oddsText =
      odds !== ""
        ? " (" + odds + ")"
        : "";

    return (
      market +
      " · " +
      label +
      lineText +
      oddsText
    ).trim();
  }

  function pickText(row, cfg) {
    if (
      cfg &&
      typeof cfg.buildBetText === "function"
    ) {
      try {
        var built =
          cfg.buildBetText(
            row,
            row
          );

        if (built) {
          return built;
        }
      } catch (error) {}
    }

    return genericPickText(row);
  }

  async function loadTodayPicks() {
    var repoConfig =
      window.REPO_CONFIG || {};

    var date =
      todayUnderscore();

    var keys =
      Object.keys(leagueByKey);

    var results =
      await Promise.all(
        keys.map(
          async function(key) {
            var cfg =
              repoConfig[key];

            if (
              !cfg ||
              !cfg.selectFiles
            ) {
              return [];
            }

            var paths =
              resolveSelectPaths(
                cfg,
                date
              );

            if (!paths.length) {
              return [];
            }

            var result =
              await fetchFirstCSV(
                paths
              );

            if (!result.ok) {
              return [];
            }

            var normalize =
              typeof cfg.normalizeRow === "function"
                ? function(row) {
                    return cfg.normalizeRow(row);
                  }
                : function(row) {
                    return row;
                  };

            var rows = [];

            result.rows.forEach(
              function(rawRow) {
                var normalized;

                try {
                  normalized =
                    normalize(rawRow);
                } catch (error) {
                  normalized =
                    rawRow;
                }

                var expanded =
                  [normalized];

                if (
                  typeof cfg.expandRows === "function"
                ) {
                  try {
                    expanded =
                      cfg.expandRows(
                        normalized
                      ) || [];
                  } catch (error) {
                    expanded = [];
                  }
                }

                expanded.forEach(
                  function(row) {
                    if (
                      !rowMatchesLeague(
                        row,
                        cfg,
                        key
                      )
                    ) {
                      return;
                    }

                    var rowDate =
                      normalizeDate(
                        row.game_date ||
                        row.match_date
                      );

                    if (
                      rowDate &&
                      rowDate !== date
                    ) {
                      return;
                    }

                    rows.push({
                      league: key,

                      leagueLabel:
                        cfg.displayName ||
                        sourceLabel(key),

                      home_team:
                        row.home_team || "",

                      away_team:
                        row.away_team || "",

                      game_time:
                        row.game_time ||
                        row.match_time ||
                        row.edt_time ||
                        "",

                      market_type:
                        row.market_type ||
                        row.market ||
                        "",

                      bet_side:
                        row.bet_side ||
                        row.side ||
                        "",

                      line:
                        row.bet_line ||
                        row.line ||
                        "",

                      text:
                        pickText(
                          row,
                          cfg
                        )
                    });
                  }
                );
              }
            );

            return rows;
          }
        )
      );

    todayPicks = [];

    results.forEach(
      function(rows) {
        todayPicks =
          todayPicks.concat(rows);
      }
    );
  }

  /* ── ESPN injuries ────────────────────────────────────────────────────── */

  async function fetchLeagueInjuries(cfg) {
    var url =
      "https://site.api.espn.com/" +
      "apis/site/v2/sports/" +
      cfg.sport +
      "/" +
      cfg.league +
      "/injuries";

    try {
      var response =
        await fetch(
          url,
          {
            cache: "no-store"
          }
        );

      if (!response.ok) {
        return [];
      }

      var data =
        await response.json();

      var teamGroups =
        data.injuries || [];

      var rows = [];

      teamGroups.forEach(
        function(group) {
          var teamObject =
            group.team || {};

          var teamName =
            group.displayName ||
            teamObject.displayName ||
            teamObject.name ||
            "Unknown";

          var injuries =
            group.injuries || [];

          injuries.forEach(
            function(injury) {
              var athlete =
                injury.athlete || {};

              var position =
                athlete.position &&
                athlete.position.abbreviation
                  ? athlete.position.abbreviation
                  : "-";

              var injuryType =
                injury.details &&
                injury.details.type
                  ? injury.details.type
                  : "-";

              rows.push({
                league: cfg.key,
                leagueLabel: cfg.label,
                group: cfg.group,

                player:
                  athlete.displayName ||
                  "Unknown",

                position:
                  position,

                team:
                  teamName,

                status:
                  injury.status ||
                  "Unknown",

                injury:
                  injuryType
              });
            }
          );
        }
      );

      return rows;
    } catch (error) {
      console.warn(
        cfg.key +
        " injuries failed:",
        error
      );

      return [];
    }
  }

  async function loadAllInjuries() {
    var results =
      await Promise.all(
        LEAGUES.map(
          fetchLeagueInjuries
        )
      );

    allInjuries = [];

    results.forEach(
      function(rows) {
        allInjuries =
          allInjuries.concat(rows);
      }
    );
  }

  /* ── Picked-team injury verification ─────────────────────────────────── */

  async function fetchJson(url) {
    try {
      var response = await fetch(
        url,
        {
          cache: "no-store"
        }
      );

      if (!response.ok) {
        return null;
      }

      return await response.json();
    } catch (error) {
      return null;
    }
  }

  function espnDateCompact() {
    return todayUnderscore()
      .replace(/_/g, "");
  }

  function scoreboardUrl(cfg) {
    return (
      "https://site.api.espn.com/" +
      "apis/site/v2/sports/" +
      cfg.sport +
      "/" +
      cfg.league +
      "/scoreboard?dates=" +
      espnDateCompact()
    );
  }

  function teamInjuryUrl(cfg, teamId) {
    return (
      "https://site.api.espn.com/" +
      "apis/site/v2/sports/" +
      cfg.sport +
      "/" +
      cfg.league +
      "/teams/" +
      encodeURIComponent(teamId) +
      "/injuries"
    );
  }

  function competitorNames(competitor) {
    var team =
      competitor && competitor.team
        ? competitor.team
        : {};

    return [
      team.displayName,
      team.shortDisplayName,
      team.name,
      team.location,
      team.nickname,
      team.abbreviation
    ].filter(Boolean);
  }

  function competitorMatchesTeam(
    competitor,
    pipelineTeamName
  ) {
    var names =
      competitorNames(competitor);

    return names.some(
      function(name) {
        return sameTeam(
          name,
          pipelineTeamName
        );
      }
    );
  }

  function uniquePickedTeamsForLeague(
    leagueKey
  ) {
    var found = {};

    todayPicks
      .filter(
        function(pick) {
          return (
            pick.league ===
            leagueKey
          );
        }
      )
      .forEach(
        function(pick) {
          [
            pick.away_team,
            pick.home_team
          ].forEach(
            function(teamName) {
              if (!teamName) {
                return;
              }

              var key =
                normalizeTeam(
                  teamName
                );

              if (!key) {
                return;
              }

              found[key] =
                teamName;
            }
          );
        }
      );

    return Object.keys(
      found
    ).map(
      function(key) {
        return found[key];
      }
    );
  }

  async function resolvePickedTeamTargets() {
    var targets = [];
    var targetKeys = {};

    var leaguesWithPicks = [];

    todayPicks.forEach(
      function(pick) {
        if (
          leaguesWithPicks.indexOf(
            pick.league
          ) === -1
        ) {
          leaguesWithPicks.push(
            pick.league
          );
        }
      }
    );

    for (
      var i = 0;
      i < leaguesWithPicks.length;
      i++
    ) {
      var leagueKey =
        leaguesWithPicks[i];

      var cfg =
        leagueByKey[
          leagueKey
        ];

      /*
        Team injury reports only make sense
        for team sports.
      */
      if (
        !cfg ||
        cfg.sport === "mma"
      ) {
        continue;
      }

      var scoreboard =
        await fetchJson(
          scoreboardUrl(cfg)
        );

      if (
        !scoreboard ||
        !Array.isArray(
          scoreboard.events
        )
      ) {
        continue;
      }

      var competitors = [];

      scoreboard.events.forEach(
        function(event) {
          var competition =
            event.competitions &&
            event.competitions[0]
              ? event.competitions[0]
              : null;

          if (
            !competition ||
            !Array.isArray(
              competition.competitors
            )
          ) {
            return;
          }

          competition.competitors.forEach(
            function(competitor) {
              competitors.push(
                competitor
              );
            }
          );
        }
      );

      var pickedTeams =
        uniquePickedTeamsForLeague(
          leagueKey
        );

      pickedTeams.forEach(
        function(pipelineTeamName) {
          var competitor =
            competitors.find(
              function(item) {
                return competitorMatchesTeam(
                  item,
                  pipelineTeamName
                );
              }
            );

          if (
            !competitor ||
            !competitor.team ||
            !competitor.team.id
          ) {
            console.warn(
              "[injuries] Could not resolve picked team:",
              leagueKey,
              pipelineTeamName
            );

            return;
          }

          var targetKey =
            leagueKey +
            "|" +
            competitor.team.id;

          if (
            targetKeys[
              targetKey
            ]
          ) {
            return;
          }

          targetKeys[
            targetKey
          ] = true;

          targets.push({
            leagueKey:
              leagueKey,

            cfg:
              cfg,

            teamId:
              String(
                competitor.team.id
              ),

            pipelineTeamName:
              pipelineTeamName,

            espnTeamName:
              competitor.team.displayName ||
              competitor.team.shortDisplayName ||
              competitor.team.name ||
              pipelineTeamName
          });
        }
      );
    }

    return targets;
  }

  function normalizeTeamInjuryEntry(
    injury,
    target
  ) {
    var athlete =
      injury &&
      injury.athlete
        ? injury.athlete
        : {};

    var position =
      athlete.position &&
      athlete.position.abbreviation
        ? athlete.position.abbreviation
        : "-";

    var injuryType =
      injury &&
      injury.details &&
      injury.details.type
        ? injury.details.type
        : "-";

    return {
      league:
        target.leagueKey,

      leagueLabel:
        target.cfg.label,

      group:
        target.cfg.group,

      player:
        athlete.displayName ||
        athlete.fullName ||
        athlete.name ||
        "Unknown",

      position:
        position,

      /*
        Use the pipeline team name here deliberately.

        That means the fallback record is guaranteed to
        match the exact team name used by today's Picks page.
      */
      team:
        target.pipelineTeamName,

      status:
        injury.status ||
        injury.type ||
        "Unknown",

      injury:
        injuryType,

      verifiedPickedTeam:
        true
    };
  }

  async function fetchPickedTeamInjuries(
    target
  ) {
    var data =
      await fetchJson(
        teamInjuryUrl(
          target.cfg,
          target.teamId
        )
      );

    if (!data) {
      return [];
    }

    var raw = [];

    /*
      ESPN has returned both shapes historically:

      injuries: [ injury, injury, ... ]

      and

      injuries: [
        {
          injuries: [ injury, injury, ... ]
        }
      ]

      Handle both.
    */
    if (
      Array.isArray(
        data.injuries
      )
    ) {
      data.injuries.forEach(
        function(item) {
          if (
            item &&
            Array.isArray(
              item.injuries
            )
          ) {
            raw =
              raw.concat(
                item.injuries
              );
          } else if (item) {
            raw.push(item);
          }
        }
      );
    }

    if (
      !raw.length &&
      Array.isArray(
        data.items
      )
    ) {
      raw =
        data.items.filter(
          Boolean
        );
    }

    return raw.map(
      function(injury) {
        return normalizeTeamInjuryEntry(
          injury,
          target
        );
      }
    );
  }

  function injuryDedupKey(row) {
    return [
      row.league,
      normalizeTeam(
        row.team
      ),
      String(
        row.player || ""
      )
        .trim()
        .toLowerCase(),
      String(
        row.status || ""
      )
        .trim()
        .toLowerCase(),
      String(
        row.injury || ""
      )
        .trim()
        .toLowerCase()
    ].join("|");
  }

  async function augmentPickedTeamInjuries() {
    pickedTeamsResolved = 0;
    pickedTeamInjuriesAdded = 0;

    var targets =
      await resolvePickedTeamTargets();

    pickedTeamsResolved =
      targets.length;

    if (!targets.length) {
      return;
    }

    var results =
      await Promise.all(
        targets.map(
          fetchPickedTeamInjuries
        )
      );

    var existing = {};

    allInjuries.forEach(
      function(row) {
        existing[
          injuryDedupKey(row)
        ] = true;
      }
    );

    results.forEach(
      function(rows) {
        rows.forEach(
          function(row) {
            var key =
              injuryDedupKey(
                row
              );

            if (
              existing[key]
            ) {
              return;
            }

            existing[key] = true;

            allInjuries.push(
              row
            );

            pickedTeamInjuriesAdded++;
          }
        );
      }
    );

    console.info(
      "[injuries] Picked teams resolved:",
      pickedTeamsResolved,
      "team-specific injuries added:",
      pickedTeamInjuriesAdded
    );
  }

  /* ── Injury status helpers ────────────────────────────────────────────── */

  function statusKey(value) {
    return String(value || "")
      .trim()
      .toLowerCase();
  }

  function isOut(row) {
    return (
      statusKey(row.status) === "out"
    );
  }

  function isQuestionable(row) {
    var key =
      statusKey(row.status);

    return (
      key === "questionable" ||
      key === "doubtful"
    );
  }

  function isDayToDay(row) {
    return (
      statusKey(row.status) ===
      "day-to-day"
    );
  }

  function isPrimaryImpact(row) {
    return (
      isOut(row) ||
      isQuestionable(row) ||
      isDayToDay(row)
    );
  }

  function matchesStatusFilter(row) {
    if (statusMode === "all") {
      return true;
    }

    if (statusMode === "out") {
      return isOut(row);
    }

    if (statusMode === "questionable") {
      return isQuestionable(row);
    }

    if (statusMode === "dtd") {
      return isDayToDay(row);
    }

    /*
      Default general browser:
      OUT + DOUBTFUL + QUESTIONABLE.
    */
    return (
      isOut(row) ||
      isQuestionable(row)
    );
  }

  function statusRank(value) {
    var key =
      statusKey(value);

    if (key === "out") {
      return 0;
    }

    if (key === "doubtful") {
      return 1;
    }

    if (key === "questionable") {
      return 2;
    }

    if (key === "day-to-day") {
      return 3;
    }

    if (key === "probable") {
      return 4;
    }

    return 5;
  }

  function statusClass(value) {
    var key =
      statusKey(value);

    if (key === "out") {
      return "s-out";
    }

    if (key === "doubtful") {
      return "s-doubtful";
    }

    if (key === "questionable") {
      return "s-questionable";
    }

    if (key === "day-to-day") {
      return "s-day-to-day";
    }

    if (key === "probable") {
      return "s-probable";
    }

    return "s-other";
  }

  /* ── League filter controls ───────────────────────────────────────────── */

  function closeAllMenus() {
    document
      .querySelectorAll(
        ".control-group"
      )
      .forEach(
        function(group) {
          group.classList.remove(
            "open"
          );
        }
      );
  }

  function setActiveControls(
    type,
    value
  ) {
    document
      .querySelectorAll(
        ".league-pill, " +
        ".group-pill, " +
        ".submenu-pill"
      )
      .forEach(
        function(button) {
          button.classList.remove(
            "active"
          );
        }
      );

    if (type === "all") {
      var allButton =
        document.querySelector(
          '[data-filter-type="all"]' +
          '[data-filter-value="all"]'
        );

      if (allButton) {
        allButton.classList.add(
          "active"
        );
      }

      return;
    }

    if (type === "group") {
      var groupButton =
        document.querySelector(
          '[data-group-toggle="' +
          value +
          '"]'
        );

      var groupSubButton =
        document.querySelector(
          '.submenu-pill' +
          '[data-filter-type="group"]' +
          '[data-filter-value="' +
          value +
          '"]'
        );

      if (groupButton) {
        groupButton.classList.add(
          "active"
        );
      }

      if (groupSubButton) {
        groupSubButton.classList.add(
          "active"
        );
      }

      return;
    }

    if (type === "league") {
      var directButton =
        document.querySelector(
          '.league-pill' +
          '[data-filter-type="league"]' +
          '[data-filter-value="' +
          value +
          '"]'
        );

      var childButton =
        document.querySelector(
          '.submenu-pill' +
          '[data-filter-type="league"]' +
          '[data-filter-value="' +
          value +
          '"]'
        );

      var group =
        sourceGroup(value);

      if (directButton) {
        directButton.classList.add(
          "active"
        );
      }

      if (childButton) {
        childButton.classList.add(
          "active"
        );
      }

      if (group) {
        var parentButton =
          document.querySelector(
            '[data-group-toggle="' +
            group +
            '"]'
          );

        if (parentButton) {
          parentButton.classList.add(
            "active"
          );
        }
      }
    }
  }

  function applyLeagueFilter(
    type,
    value
  ) {
    activeFilterType = type;
    activeFilterValue = value;

    visibleLimit = PAGE_SIZE;

    closeAllMenus();

    setActiveControls(
      type,
      value
    );

    renderBrowser();
  }

  /* ── General injury browser ───────────────────────────────────────────── */

  function filteredBrowserRows() {
    var rows =
      allInjuries.slice();

    if (
      activeFilterType ===
      "league"
    ) {
      rows =
        rows.filter(
          function(row) {
            return (
              row.league ===
              activeFilterValue
            );
          }
        );
    }

    if (
      activeFilterType ===
      "group"
    ) {
      var allowed =
        GROUPS[
          activeFilterValue
        ] || [];

      rows =
        rows.filter(
          function(row) {
            return (
              allowed.indexOf(
                row.league
              ) !== -1
            );
          }
        );
    }

    rows =
      rows.filter(
        matchesStatusFilter
      );

    if (searchQuery) {
      var query =
        searchQuery.toLowerCase();

      rows =
        rows.filter(
          function(row) {
            return (
              String(
                row.player || ""
              )
                .toLowerCase()
                .indexOf(query) !== -1 ||

              String(
                row.team || ""
              )
                .toLowerCase()
                .indexOf(query) !== -1 ||

              String(
                row.injury || ""
              )
                .toLowerCase()
                .indexOf(query) !== -1 ||

              String(
                row.leagueLabel || ""
              )
                .toLowerCase()
                .indexOf(query) !== -1
            );
          }
        );
    }

    rows.sort(
      function(a, b) {
        var statusDiff =
          statusRank(a.status) -
          statusRank(b.status);

        if (statusDiff !== 0) {
          return statusDiff;
        }

        var leagueDiff =
          String(
            a.leagueLabel || ""
          ).localeCompare(
            String(
              b.leagueLabel || ""
            )
          );

        if (leagueDiff !== 0) {
          return leagueDiff;
        }

        var teamDiff =
          String(
            a.team || ""
          ).localeCompare(
            String(
              b.team || ""
            )
          );

        if (teamDiff !== 0) {
          return teamDiff;
        }

        return String(
          a.player || ""
        ).localeCompare(
          String(
            b.player || ""
          )
        );
      }
    );

    return rows;
  }

  function renderBrowser() {
    var rows =
      filteredBrowserRows();

    var shown =
      rows.slice(
        0,
        visibleLimit
      );

    var tbody =
      $("inj-tbody");

    var empty =
      $("inj-empty");

    var loadMore =
      $("load-more");

    tbody.innerHTML = "";

    shown.forEach(
      function(row) {
        var tr =
          document.createElement(
            "tr"
          );

        tr.innerHTML =
          '<td class="td-league">' +
            escapeHtml(
              row.leagueLabel
            ) +
          '</td>' +

          '<td class="td-team">' +
            escapeHtml(
              row.team
            ) +
          '</td>' +

          '<td class="td-player">' +
            escapeHtml(
              row.player
            ) +
          '</td>' +

          '<td class="td-pos">' +
            escapeHtml(
              row.position
            ) +
          '</td>' +

          '<td>' +
            '<span class="status-badge ' +
              statusClass(
                row.status
              ) +
            '">' +
              escapeHtml(
                row.status
              ) +
            '</span>' +
          '</td>' +

          '<td class="td-injury">' +
            escapeHtml(
              row.injury
            ) +
          '</td>';

        tbody.appendChild(tr);
      }
    );

    empty.style.display =
      rows.length
        ? "none"
        : "";

    $("result-count").textContent =
      "Showing " +
      Math.min(
        shown.length,
        rows.length
      ) +
      " of " +
      rows.length +
      " matching injuries";

    loadMore.style.display =
      rows.length > visibleLimit
        ? "block"
        : "none";
  }

  /* ── Picks impact matching ────────────────────────────────────────────── */

  function gameKey(pick) {
    return [
      pick.league,
      normalizeTeam(
        pick.away_team
      ),
      normalizeTeam(
        pick.home_team
      )
    ].join("|");
  }

  function buildImpactGroups() {
    var groups = {};

    todayPicks.forEach(
      function(pick) {
        if (
          !pick.home_team &&
          !pick.away_team
        ) {
          return;
        }

        var key =
          gameKey(pick);

        if (!groups[key]) {
          groups[key] = {
            league:
              pick.league,

            leagueLabel:
              pick.leagueLabel ||
              sourceLabel(
                pick.league
              ),

            home_team:
              pick.home_team,

            away_team:
              pick.away_team,

            game_time:
              pick.game_time,

            picks: [],

            homeInjuries: [],
            awayInjuries: []
          };
        }

        groups[key].picks.push(
          pick
        );
      }
    );

    Object.keys(groups).forEach(
      function(key) {
        var group =
          groups[key];

        group.homeInjuries =
          allInjuries.filter(
            function(row) {
              return (
                row.league ===
                  group.league &&

                sameTeam(
                  row.team,
                  group.home_team
                ) &&

                isPrimaryImpact(
                  row
                )
              );
            }
          );

        group.awayInjuries =
          allInjuries.filter(
            function(row) {
              return (
                row.league ===
                  group.league &&

                sameTeam(
                  row.team,
                  group.away_team
                ) &&

                isPrimaryImpact(
                  row
                )
              );
            }
          );
      }
    );

    return Object
      .keys(groups)
      .map(
        function(key) {
          return groups[key];
        }
      )
      .filter(
        function(group) {
          return (
            group.homeInjuries.length ||
            group.awayInjuries.length
          );
        }
      );
  }

  function renderImpactInjuryRows(
    rows
  ) {
    return rows
      .slice()
      .sort(
        function(a, b) {
          return (
            statusRank(a.status) -
            statusRank(b.status)
          );
        }
      )
      .map(
        function(row) {
          return (
            '<div class="impact-injury-row">' +

              '<span class="status-badge ' +
                statusClass(
                  row.status
                ) +
              '">' +
                escapeHtml(
                  row.status
                ) +
              '</span>' +

              '<span class="impact-player">' +
                escapeHtml(
                  row.player
                ) +
              '</span>' +

              '<span>' +
                escapeHtml(
                  row.position
                ) +
              '</span>' +

              '<span class="impact-injury-type">' +
                escapeHtml(
                  row.injury
                ) +
              '</span>' +

            '</div>'
          );
        }
      )
      .join("");
  }

  function renderImpact() {
    var groups =
      buildImpactGroups();

    var grid =
      $("impact-grid");

    var empty =
      $("impact-empty");

    grid.innerHTML = "";

    var affectedTeams = {};
    var pickedImpactRows = [];

    groups.forEach(
      function(group) {

        if (
          group.awayInjuries.length
        ) {
          affectedTeams[
            group.league +
            "|" +
            normalizeTeam(
              group.away_team
            )
          ] = true;

          pickedImpactRows =
            pickedImpactRows.concat(
              group.awayInjuries
            );
        }

        if (
          group.homeInjuries.length
        ) {
          affectedTeams[
            group.league +
            "|" +
            normalizeTeam(
              group.home_team
            )
          ] = true;

          pickedImpactRows =
            pickedImpactRows.concat(
              group.homeInjuries
            );
        }
      }
    );

    /*
      Deduplicate the same injury if multiple picks exist
      on the same game.
    */
    var uniqueImpact = {};

    pickedImpactRows.forEach(
      function(row) {
        var key = [
          row.league,
          normalizeTeam(
            row.team
          ),
          String(
            row.player || ""
          ).toLowerCase(),
          statusKey(
            row.status
          ),
          String(
            row.injury || ""
          ).toLowerCase()
        ].join("|");

        uniqueImpact[key] = row;
      }
    );

    var uniqueRows =
      Object
        .keys(uniqueImpact)
        .map(
          function(key) {
            return uniqueImpact[key];
          }
        );

    $("sum-picks").textContent =
      todayPicks.length;

    $("sum-teams").textContent =
      Object.keys(
        affectedTeams
      ).length;

    $("sum-out").textContent =
      uniqueRows.filter(
        isOut
      ).length;

    $("sum-questionable").textContent =
      uniqueRows.filter(
        isQuestionable
      ).length;

    if (!todayPicks.length) {
      empty.textContent =
        "No current picks were loaded for " +
        todayDash() +
        ".";

      empty.style.display = "";

      return;
    }

    if (!groups.length) {
      empty.textContent =
        "No reported impact injuries were matched " +
        "to teams in today's picked games.";

      empty.style.display = "";

      return;
    }

    empty.style.display = "none";

    groups.forEach(
      function(group) {
        var card =
          document.createElement(
            "article"
          );

        card.className =
          "impact-card";

        var pickHTML =
          group.picks
            .map(
              function(pick) {
                return (
                  '<span class="pick-chip">' +
                    escapeHtml(
                      pick.text ||
                      "Pick"
                    ) +
                  '</span>'
                );
              }
            )
            .join("");

        var teamHTML = "";

        if (
          group.awayInjuries.length
        ) {
          teamHTML +=
            '<div class="impact-team">' +

              '<div class="impact-team-name">' +
                escapeHtml(
                  group.away_team
                ) +
              '</div>' +

              renderImpactInjuryRows(
                group.awayInjuries
              ) +

            '</div>';
        }

        if (
          group.homeInjuries.length
        ) {
          teamHTML +=
            '<div class="impact-team">' +

              '<div class="impact-team-name">' +
                escapeHtml(
                  group.home_team
                ) +
              '</div>' +

              renderImpactInjuryRows(
                group.homeInjuries
              ) +

            '</div>';
        }

        card.innerHTML =
          '<div class="impact-card-top">' +

            '<div class="impact-matchup">' +
              escapeHtml(
                group.away_team ||
                "Away"
              ) +
              ' @ ' +
              escapeHtml(
                group.home_team ||
                "Home"
              ) +
            '</div>' +

            '<div class="impact-league">' +
              escapeHtml(
                group.leagueLabel
              ) +
              (
                group.game_time
                  ? " · " +
                    escapeHtml(
                      group.game_time
                    )
                  : ""
              ) +
            '</div>' +

          '</div>' +

          '<div class="impact-picks">' +
            pickHTML +
          '</div>' +

          teamHTML;

        grid.appendChild(card);
      }
    );
  }

  /* ── Event binding ────────────────────────────────────────────────────── */

  function bindControls() {

    document
      .querySelectorAll(
        "[data-group-toggle]"
      )
      .forEach(
        function(button) {
          button.addEventListener(
            "click",
            function(event) {
              event.stopPropagation();

              var groupName =
                button.dataset.groupToggle;

              var group =
                document.querySelector(
                  '.control-group' +
                  '[data-group="' +
                  groupName +
                  '"]'
                );

              var wasOpen =
                group &&
                group.classList.contains(
                  "open"
                );

              closeAllMenus();

              if (
                group &&
                !wasOpen
              ) {
                group.classList.add(
                  "open"
                );
              }
            }
          );
        }
      );

    document
      .querySelectorAll(
        "[data-filter-type]"
      )
      .forEach(
        function(button) {
          button.addEventListener(
            "click",
            function(event) {
              event.stopPropagation();

              applyLeagueFilter(
                button.dataset.filterType,
                button.dataset.filterValue
              );
            }
          );
        }
      );

    document.addEventListener(
      "click",
      function(event) {
        if (
          !event.target.closest(
            ".control-group"
          )
        ) {
          closeAllMenus();
        }
      }
    );

    document.addEventListener(
      "keydown",
      function(event) {
        if (
          event.key ===
          "Escape"
        ) {
          closeAllMenus();
        }
      }
    );

    $("inj-search")
      .addEventListener(
        "input",
        function(event) {
          searchQuery =
            event.target.value.trim();

          visibleLimit =
            PAGE_SIZE;

          renderBrowser();
        }
      );

    $("status-filter")
      .addEventListener(
        "change",
        function(event) {
          statusMode =
            event.target.value;

          visibleLimit =
            PAGE_SIZE;

          renderBrowser();
        }
      );

    $("load-more")
      .addEventListener(
        "click",
        function() {
          visibleLimit +=
            PAGE_SIZE;

          renderBrowser();
        }
      );
  }

  /* ── Init ─────────────────────────────────────────────────────────────── */

  async function init() {
    bindControls();

    setStatus(
      "Loading injury feeds and today's picks...",
      "loading",
      "yellow"
    );

    await Promise.all([
      loadTodayPicks(),
      loadAllInjuries()
    ]);

    /*
      The league-wide feed can omit injuries that exist
      on an individual team's ESPN report.

      Resolve every team in today's picked games against
      today's ESPN scoreboard, then query those teams
      individually before calculating the priority section.
    */
    await augmentPickedTeamInjuries();

    renderImpact();
    renderBrowser();

    setStatus(
      allInjuries.length +
      " injuries loaded · " +
      todayPicks.length +
      " current picks cross-referenced · " +
      pickedTeamsResolved +
      " picked teams verified · " +
      pickedTeamInjuriesAdded +
      " fallback injuries added · " +
      todayDash(),
      "",
      "green"
    );
  }

  if (
    document.readyState ===
    "loading"
  ) {
    document.addEventListener(
      "DOMContentLoaded",
      init
    );
  } else {
    init();
  }

})();
