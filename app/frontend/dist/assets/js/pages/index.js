    function padTwo(n) {
      return n < 10 ? "0" + n : String(n);
    }

    function todayFileDate() {
      var d = new Date();
      return d.getFullYear() + "_" + padTwo(d.getMonth() + 1) + "_" + padTwo(d.getDate());
    }

    function normalizeFileDate(value) {
      return String(value || "").trim().replaceAll("-", "_");
    }

    function dateFromFileDate(value) {
      var parts = normalizeFileDate(value).split("_").map(function(v) {
        return parseInt(v, 10);
      });

      if (parts.length !== 3 || parts.some(function(v) { return isNaN(v); })) {
        return null;
      }

      return new Date(parts[0], parts[1] - 1, parts[2]);
    }

    function fileDateFromDate(d) {
      return d.getFullYear() + "_" + padTwo(d.getMonth() + 1) + "_" + padTwo(d.getDate());
    }

    function buildDateList(startDate, endDate) {
      var start = dateFromFileDate(startDate);
      var end = dateFromFileDate(endDate || todayFileDate());
      var dates = [];

      if (!start || !end || start > end) return dates;

      var current = new Date(start.getTime());

      while (current <= end) {
        dates.push(fileDateFromDate(current));
        current.setDate(current.getDate() + 1);
      }

      return dates;
    }

    function fetchSourceUrl(url, label, warnOnFail) {
      return fetch(url)
        .then(function(response) {
          if (!response.ok) {
            throw new Error(label + " " + response.status);
          }
          return response.text();
        })
        .then(function(text) {
          return parseCSV(text);
        })
        .catch(function(error) {
          if (warnOnFail) {
            console.warn("Failed to load " + label + ":", error);
          }
          return [];
        });
    }

    function resolveSourceUrls(source) {
      if (Array.isArray(source.urls)) {
        return Promise.resolve(source.urls);
      }

      if (source.url) {
        return Promise.resolve([source.url]);
      }

      if (source.indexUrl) {
        return fetch(source.indexUrl)
          .then(function(response) {
            if (!response.ok) {
              throw new Error(source.label + " index " + response.status);
            }
            return response.json();
          })
          .then(function(items) {
            if (!Array.isArray(items)) return [];

            if (typeof source.indexItemToUrl === "function") {
              return items
                .map(function(item) {
                  return source.indexItemToUrl(item);
                })
                .filter(function(url) {
                  return !!url;
                });
            }

            return [];
          })
          .catch(function(error) {
            console.warn("Failed to load " + source.label + " index:", error);
            return [];
          });
      }

      if (typeof source.datePattern === "function") {
        return Promise.resolve(
          buildDateList(source.startDate, source.endDate).map(function(date) {
            return source.datePattern(date);
          })
        );
      }

      return Promise.resolve([]);
    }

    function loadSource(source) {
      return resolveSourceUrls(source).then(function(urls) {
        if (!urls.length) {
          return {
            label: source.label,
            rows: []
          };
        }

        var warnOnFail = !source.datePattern;

        return Promise.all(
          urls.map(function(url) {
            return fetchSourceUrl(url, source.label, warnOnFail);
          })
        ).then(function(groups) {
          return {
            label: source.label,
            rows: groups.reduce(function(all, rows) {
              return all.concat(rows);
            }, [])
          };
        });
      });
    }

    function prepareSourceRow(row, sourceLabel) {
      if (sourceLabel === "MLB_LINEUPS") {
        var lineupRow = Object.assign({}, row);
        lineupRow.league = "MLB_LINEUPS";
        return lineupRow;
      }

      if (sourceLabel === "UFC") {
        var bet = String(row.bet || "").toLowerCase().trim();
        var fighterIndex = bet === "fighter_1" ? 1 : bet === "fighter_2" ? 2 : 0;

        if (!fighterIndex) return row;

        var ufcRow = Object.assign({}, row);
        var fighter = fighterIndex === 1 ? row.fighter_1 : row.fighter_2;

        ufcRow.sport = "mma";
        ufcRow.league = "UFC";
        ufcRow.game_date = row.match_date;
        ufcRow.matchup = [row.fighter_1, row.fighter_2].filter(Boolean).join(" vs ");
        ufcRow.market_type = "moneyline";
        ufcRow.bet_side = fighter;
        ufcRow.take_bet = fighter;
        ufcRow.dk_odds_american = fighterIndex === 1 ? row.moneyline_f1 : row.moneyline_f2;
        ufcRow.model_prob = fighterIndex === 1 ? row.model_prob_f1 : row.model_prob_f2;
        ufcRow.ev = fighterIndex === 1 ? row.ev_f1 : row.ev_f2;
        ufcRow.kelly = fighterIndex === 1 ? row.kelly_f1 : row.kelly_f2;
        ufcRow.edge = fighterIndex === 1 ? row.edge_f1 : row.edge_f2;
        ufcRow.bet_result = fighterIndex === 1 ? row.result_fighter_1 : row.result_fighter_2;

        return ufcRow;
      }

      return row;
    }

    function setStatus(text, state) {
      document.getElementById("status-text").textContent = text;
      document.getElementById("status-dot").className =
        "status-dot" + (state ? " " + state : "");
    }

    function setValueClass(element, className) {
      element.classList.remove("val-green", "val-red", "val-yellow", "val-blue");
      if (className) {
        element.classList.add(className);
      }
    }

    function winRateClass(rate) {
      if (rate >= 0.55) return "val-green";
      if (rate < 0.45) return "val-red";
      return "val-yellow";
    }

    function formatProfit(value) {
      var n = parseFloat(value);
      if (isNaN(n)) return "N/A";
      return (n > 0 ? "+" : "") + n.toFixed(2) + "u";
    }

    function cleanDate(value) {
      return String(value || "").trim().replaceAll("_", "-");
    }

    function formatDateLong(value) {
      var clean = cleanDate(value);
      var parts = clean.split("-");

      if (parts.length !== 3) return clean || "Unknown Date";

      var year = parseInt(parts[0], 10);
      var month = parseInt(parts[1], 10);
      var day = parseInt(parts[2], 10);

      if (
        isNaN(year) ||
        isNaN(month) ||
        isNaN(day) ||
        month < 1 ||
        month > 12
      ) {
        return clean || "Unknown Date";
      }

      var monthNames = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December"
      ];

      return monthNames[month - 1] + " " + day + ", " + year;
    }

    function renderSummary(graded) {
      var wins = graded.filter(function(row) {
        return row.result === "win";
      }).length;

      var losses = graded.filter(function(row) {
        return row.result === "loss";
      }).length;

      var pushes = graded.filter(function(row) {
        return row.result === "push";
      }).length;

      var decisions = wins + losses;
      var winRate = decisions ? wins / decisions : null;

      var probabilityRows = graded.filter(function(row) {
        return row.model_prob !== null;
      });

      var avgProbability = probabilityRows.length
        ? probabilityRows.reduce(function(sum, row) {
            return sum + row.model_prob;
          }, 0) / probabilityRows.length
        : null;

      var profitRows = graded.filter(function(row) {
        return row.profit_unit !== null;
      });

      var totalProfit = profitRows.reduce(function(sum, row) {
        return sum + row.profit_unit;
      }, 0);

      var completedEl = document.getElementById("summary-completed");
      var recordEl = document.getElementById("summary-record");
      var winRateEl = document.getElementById("summary-win-rate");
      var modelProbEl = document.getElementById("summary-model-prob");
      var profitEl = document.getElementById("summary-profit");

      completedEl.textContent = graded.length.toLocaleString();
      recordEl.textContent = wins + "-" + losses + "-" + pushes;
      winRateEl.textContent = winRate === null ? "N/A" : (winRate * 100).toFixed(1) + "%";
      modelProbEl.textContent = avgProbability === null
        ? "N/A"
        : (avgProbability * 100).toFixed(1) + "%";
      profitEl.textContent = profitRows.length ? formatProfit(totalProfit) : "N/A";

      setValueClass(
        recordEl,
        winRate === null ? "" : winRateClass(winRate)
      );

      setValueClass(
        winRateEl,
        winRate === null ? "" : winRateClass(winRate)
      );

      setValueClass(modelProbEl, "val-blue");

      setValueClass(
        profitEl,
        profitRows.length
          ? (totalProfit >= 0 ? "val-green" : "val-red")
          : ""
      );
    }

    function buildDateGroups(graded) {
      var groups = {};

      graded.forEach(function(row) {
        var key = cleanDate(row.game_date);

        if (!key) return;

        if (!groups[key]) {
          groups[key] = [];
        }

        groups[key].push(row);
      });

      return Object.keys(groups)
        .sort(function(a, b) {
          return b.localeCompare(a);
        })
        .slice(0, 30)
        .map(function(date) {
          return {
            date: date,
            rows: groups[date]
          };
        });
    }

    function renderHistory(graded) {
      var grid = document.getElementById("history-grid");
      var groups = buildDateGroups(graded);

      if (!groups.length) {
        grid.innerHTML =
          '<div class="empty-state">No completed bet history available</div>';
        return;
      }

      grid.innerHTML = groups.map(function(group) {
        var rows = group.rows;

        var wins = rows.filter(function(row) {
          return row.result === "win";
        }).length;

        var losses = rows.filter(function(row) {
          return row.result === "loss";
        }).length;

        var pushes = rows.filter(function(row) {
          return row.result === "push";
        }).length;

        var decisions = wins + losses;
        var rate = decisions ? wins / decisions : null;

        var profitRows = rows.filter(function(row) {
          return row.profit_unit !== null;
        });

        var profit = profitRows.reduce(function(sum, row) {
          return sum + row.profit_unit;
        }, 0);

        var rateText = rate === null
          ? "N/A"
          : (rate * 100).toFixed(1) + "%";

        var rateClass = rate === null
          ? ""
          : winRateClass(rate);

        var profitText = profitRows.length
          ? formatProfit(profit)
          : "N/A";

        var profitClass = profitRows.length
          ? (profit >= 0 ? "val-green" : "val-red")
          : "";

        var recordClass = rate === null
          ? ""
          : winRateClass(rate);

        return (
          '<article class="day-card">' +
            '<div class="date-label">Date</div>' +
            '<div class="date-value">' + formatDateLong(group.date) + '</div>' +
            '<div class="day-stats">' +
              '<div class="day-stat">' +
                '<div class="day-stat-label">Bets For That Day</div>' +
                '<div class="day-stat-value">' + rows.length.toLocaleString() + '</div>' +
              '</div>' +
              '<div class="day-stat">' +
                '<div class="day-stat-label">W-L-P Record</div>' +
                '<div class="day-stat-value ' + recordClass + '">' +
                  wins + '-' + losses + '-' + pushes +
                '</div>' +
              '</div>' +
              '<div class="day-stat">' +
                '<div class="day-stat-label">Win Rate</div>' +
                '<div class="day-stat-value ' + rateClass + '">' +
                  rateText +
                '</div>' +
              '</div>' +
              '<div class="day-stat">' +
                '<div class="day-stat-label">Profit / Loss</div>' +
                '<div class="day-stat-value ' + profitClass + '">' +
                  profitText +
                '</div>' +
              '</div>' +
            '</div>' +
          '</article>'
        );
      }).join("");
    }

    function loadHomepage() {
      var activeSources = SOURCES.filter(function(source) {
        return source.enabled !== false;
      });

      if (!activeSources.length) {
        renderSummary([]);
        renderHistory([]);
        setStatus("No completed-bet sources are enabled.", "red");
        return;
      }

      setStatus("Loading completed bets from all enabled sports and markets...", "");

      Promise.all(
        activeSources.map(function(source) {
          return loadSource(source);
        })
      )
        .then(function(results) {
          var allRows = [];

          results.forEach(function(result) {
            result.rows.forEach(function(row) {
              var prepared = prepareSourceRow(row, result.label);
              allRows.push(normalizeRow(prepared, result.label));
            });
          });

          var graded = allRows.filter(function(row) {
            return row.result === "win" ||
              row.result === "loss" ||
              row.result === "push";
          });

          renderSummary(graded);
          renderHistory(graded);

          setStatus(
            graded.length.toLocaleString() +
            " completed bets loaded across all enabled sports and markets.",
            "green"
          );
        })
        .catch(function(error) {
          console.error("Homepage load failed:", error);
          renderSummary([]);
          renderHistory([]);
          setStatus("Completed bet history failed to load.", "red");
        });
    }

    loadHomepage();
  
