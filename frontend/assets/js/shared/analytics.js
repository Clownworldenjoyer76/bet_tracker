/* SportsModelHub browser analytics â€” PostHog */
(function (t, e) {
  var o, n, p, r;
  if (e.__SV) return;

  window.posthog = e;
  e._i = [];

  e.init = function (i, s, a) {
    function g(t, e) {
      var o = e.split(".");
      if (o.length === 2) {
        t = t[o[0]];
        e = o[1];
      }
      t[e] = function () {
        t.push([e].concat(Array.prototype.slice.call(arguments, 0)));
      };
    }

    p = t.createElement("script");
    p.type = "text/javascript";
    p.crossOrigin = "anonymous";
    p.async = true;
    p.src = s.api_host.replace(".i.posthog.com", "-assets.i.posthog.com") + "/static/array.js";

    r = t.getElementsByTagName("script")[0];
    r.parentNode.insertBefore(p, r);

    var u = e;
    if (a !== undefined) {
      u = e[a] = [];
    } else {
      a = "posthog";
    }

    u.people = u.people || [];
    u.toString = function (t) {
      var e = "posthog";
      if (a !== "posthog") e += "." + a;
      if (!t) e += " (stub)";
      return e;
    };

    u.people.toString = function () {
      return u.toString(1) + ".people (stub)";
    };

    o = "init capture register register_once register_for_session unregister unregister_for_session getFeatureFlag getFeatureFlagPayload isFeatureEnabled reloadFeatureFlags updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures on onFeatureFlags onSessionId getSurveys getActiveMatchingSurveys renderSurvey canRenderSurvey getNextSurveyStep identify setPersonProperties group resetGroups setPersonPropertiesForFlags resetPersonPropertiesForFlags setGroupPropertiesForFlags resetGroupPropertiesForFlags reset get_distinct_id getGroups get_session_id get_session_replay_url alias set_config startSessionRecording stopSessionRecording sessionRecordingStarted captureException loadToolbar get_property getSessionProperty createPersonProfile opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing clear_opt_in_out_capturing debug".split(" ");

    for (n = 0; n < o.length; n++) {
      g(u, o[n]);
    }

    e._i.push([i, s, a]);
  };

  e.__SV = 1;
})(document, window.posthog || []);

posthog.init('phc_r8rHehNywABoAFEGt5vTx8iTpoTY6hiFoyygPrMF6WE4', {
  api_host: 'https://us.i.posthog.com',
  defaults: '2026-05-30',
  person_profiles: 'identified_only',
  autocapture: true,
  capture_pageview: true,
  capture_pageleave: true,
  disable_session_recording: true
});

/* SMH_INTERNAL_USER_MARKER_START */
(() => {
  const STORAGE_KEY = "smh_internal_user";
  const url = new URL(window.location.href);
  const requested = url.searchParams.get("smh_internal");

  if (requested === "1") {
    localStorage.setItem(STORAGE_KEY, "1");
    url.searchParams.delete("smh_internal");
    history.replaceState({}, "", url.pathname + url.search + url.hash);
  } else if (requested === "0") {
    localStorage.removeItem(STORAGE_KEY);
    url.searchParams.delete("smh_internal");
    history.replaceState({}, "", url.pathname + url.search + url.hash);
  }

  const isInternal = localStorage.getItem(STORAGE_KEY) === "1";

  if (
    isInternal &&
    window.posthog &&
    typeof window.posthog.setPersonProperties === "function"
  ) {
    window.posthog.setPersonProperties({
      $internal_or_test_user: true
    });
  } else if (
    requested === "0" &&
    window.posthog &&
    typeof window.posthog.setPersonProperties === "function"
  ) {
    window.posthog.setPersonProperties({
      $internal_or_test_user: false
    });
  }

  window.SMHInternalUser = {
    enabled: isInternal,
    enable() {
      localStorage.setItem(STORAGE_KEY, "1");
      if (
        window.posthog &&
        typeof window.posthog.setPersonProperties === "function"
      ) {
        window.posthog.setPersonProperties({
          $internal_or_test_user: true
        });
      }
    },
    disable() {
      localStorage.removeItem(STORAGE_KEY);
      if (
        window.posthog &&
        typeof window.posthog.setPersonProperties === "function"
      ) {
        window.posthog.setPersonProperties({
          $internal_or_test_user: false
        });
      }
    }
  };
})();
/* SMH_INTERNAL_USER_MARKER_END */

/* SMH_SESSION_REPLAY_START */
(() => {
  const INTERNAL_STORAGE_KEY = "smh_internal_user";
  const replayPages = new Set([
    "the_picks",
    "games_today",
    "kelly_calculator",
    "prop_engine",
    "props_nfl"
  ]);

  const page = (location.pathname.split("/").pop() || "index.html")
    .replace(/\.html$/i, "") || "index";

  const isInternal = localStorage.getItem(INTERNAL_STORAGE_KEY) === "1";
  const shouldRecord = replayPages.has(page) && !isInternal;

  if (
    shouldRecord &&
    window.posthog &&
    typeof window.posthog.startSessionRecording === "function"
  ) {
    window.posthog.startSessionRecording();
  } else if (
    window.posthog &&
    typeof window.posthog.stopSessionRecording === "function"
  ) {
    window.posthog.stopSessionRecording();
  }

  window.SMHSessionReplay = {
    eligible: replayPages.has(page),
    internal: isInternal,
    recordingRequested: shouldRecord
  };
})();
/* SMH_SESSION_REPLAY_END */

/* SMH_PRODUCT_ANALYTICS_START */
(() => {
  const VERSION = "1.0.0";

  const LEAGUE_SPORT = {
    NFL: "football",
    CFB: "football",
    CFL: "football",
    NHL: "hockey",
    MLB: "baseball",
    MLB_LINEUPS: "baseball",
    NBA: "basketball",
    WNBA: "basketball",
    NCAAM: "basketball",
    NCAAB: "basketball",
    UFC: "mma",
    SOCCER: "soccer",
    EPL: "soccer",
    MLS: "soccer",
    LIGUE1: "soccer",
    LALIGA: "soccer",
    SERIEA: "soccer",
    BUNDESLIGA: "soccer"
  };

  function pageName() {
    const file = (location.pathname.split("/").pop() || "index.html")
      .replace(/\.html$/i, "");
    return file || "index";
  }

  function normalizeLeague(value) {
    const league = String(value || "").trim();
    if (!league) return undefined;
    if (league.toLowerCase() === "all") return "all";
    return league.toUpperCase();
  }

  function inferSport(league) {
    const key = normalizeLeague(league);
    return key ? LEAGUE_SPORT[key] : undefined;
  }

  function deviceType() {
    const width = window.innerWidth || document.documentElement.clientWidth || 0;
    if (width < 768) return "mobile";
    if (width < 1024) return "tablet";
    return "desktop";
  }

  function selectedDate() {
    const input =
      document.getElementById("p-date") ||
      document.getElementById("gt-date") ||
      document.getElementById("date-picker");

    const value = input && input.value ? String(input.value) : "";
    return value ? value.replaceAll("_", "-") : undefined;
  }

  function normalizedFraction(value) {
    if (value === null || value === undefined || value === "") return undefined;
    let number = Number(value);
    if (!Number.isFinite(number)) return undefined;

    if (Math.abs(number) > 1 && Math.abs(number) <= 100) {
      number /= 100;
    }

    return number;
  }

  function probabilityBand(value) {
    const p = normalizedFraction(value);
    if (p === undefined || p < 0 || p > 1) return undefined;
    if (p < 0.45) return "<45%";
    if (p < 0.55) return "45-55%";
    if (p < 0.65) return "55-65%";
    if (p < 0.75) return "65-75%";
    return "75%+";
  }

  function confidenceTier(value) {
    const edge = normalizedFraction(value);
    if (edge === undefined) return undefined;
    if (edge >= 0.15) return "5_very_high";
    if (edge >= 0.10) return "4_high";
    if (edge >= 0.07) return "3_strong";
    if (edge >= 0.04) return "2_moderate";
    if (edge > 0) return "1_low";
    return "0_none";
  }

  function compact(properties) {
    return Object.fromEntries(
      Object.entries(properties).filter(([, value]) =>
        value !== undefined &&
        value !== null &&
        value !== ""
      )
    );
  }

  function capture(eventName, properties = {}) {
    if (!window.posthog || typeof window.posthog.capture !== "function") {
      window.__smhAnalyticsQueue = window.__smhAnalyticsQueue || [];
      window.__smhAnalyticsQueue.push([eventName, properties]);
      return;
    }

    const props = {
      page: pageName(),
      device_type: deviceType(),
      ...properties
    };

    if (!props.selected_date) {
      props.selected_date = selectedDate();
    } else {
      props.selected_date = String(props.selected_date).replaceAll("_", "-");
    }

    props.league = normalizeLeague(props.league);

    if (!props.sport && props.league) {
      props.sport = inferSport(props.league);
    }

    if (Object.prototype.hasOwnProperty.call(props, "model_probability")) {
      props.model_probability = normalizedFraction(props.model_probability);
      props.model_probability_band = probabilityBand(props.model_probability);
    }

    if (Object.prototype.hasOwnProperty.call(props, "edge")) {
      props.edge = normalizedFraction(props.edge);
      props.confidence_tier = confidenceTier(props.edge);
    }

    window.posthog.capture(eventName, compact(props));
  }

  function activeLeague() {
    const active = document.querySelector(
      "#league-controls .league-pill.active, " +
      "#league-filters .filter-pill.active, " +
      "#gt-filters .filter-pill.active, " +
      ".league-pill.active[data-sport][data-league]"
    );

    if (!active) return undefined;

    return normalizeLeague(
      active.dataset.leagueSub ||
      active.dataset.leagueKey ||
      active.dataset.league
    );
  }

  function activeSport() {
    const active = document.querySelector(
      "#league-controls .league-pill.active, " +
      "#league-filters .filter-pill.active, " +
      "#gt-filters .filter-pill.active, " +
      ".league-pill.active[data-sport][data-league]"
    );

    return (active && active.dataset.sport) || inferSport(activeLeague());
  }

  function captureKelly(trigger) {
    const fractionButton = document.querySelector(".fraction-btns button.active");
    const pickCount = Number.parseInt(
      (document.getElementById("total-picks") || {}).textContent || "",
      10
    );
    const bankroll = Number.parseFloat(
      (document.getElementById("bankroll") || {}).value || "0"
    );

    capture("kelly_calculated", {
      trigger,
      league: activeLeague(),
      sport: activeSport(),
      kelly_fraction: fractionButton ? Number(fractionButton.dataset.frac) : undefined,
      pick_count: Number.isFinite(pickCount) ? pickCount : undefined,
      has_bankroll: Number.isFinite(bankroll) && bankroll > 0
    });
  }

  window.SMHAnalytics = {
    version: VERSION,
    capture,
    inferSport,
    probabilityBand,
    confidenceTier
  };

  window.SMHTrack = function(eventName, properties = {}) {
    capture(eventName, properties);
  };

  const queuedEvents = window.__smhAnalyticsQueue || [];
  window.__smhAnalyticsQueue = [];
  queuedEvents.forEach(([eventName, properties]) => {
    capture(eventName, properties || {});
  });

  function captureSemanticPageView() {
    const page = pageName();

    if (page === "model_validation") {
      const activeMarket = document.querySelector(".market-pill.active");
      capture("model_validation_viewed", {
        league: activeLeague() || "all",
        sport: activeSport(),
        bet_type: activeMarket ? activeMarket.dataset.market : "all"
      });
    }

    if (page === "prop_engine") {
      capture("props_viewed", {
        view_type: "page",
        props_surface: "player_prop_engine",
        league: activeLeague(),
        sport: activeSport()
      });
    }

    if (page === "props_nfl") {
      capture("props_viewed", {
        view_type: "page",
        props_surface: "nfl_model_props",
        league: "NFL",
        sport: "football",
        season: (document.getElementById("seasonSelect") || {}).value,
        week: (document.getElementById("weekSelect") || {}).value
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", captureSemanticPageView, { once: true });
  } else {
    captureSemanticPageView();
  }

  document.addEventListener("click", event => {
    const target = event.target instanceof Element ? event.target : null;
    if (!target) return;

    const leagueControl = target.closest(
      ".filter-pill[data-league], " +
      ".league-pill[data-league], " +
      ".league-pill[data-league-key]"
    );

    if (leagueControl && !leagueControl.disabled) {
      const league = normalizeLeague(
        leagueControl.dataset.leagueSub ||
        leagueControl.dataset.leagueKey ||
        leagueControl.dataset.league
      );

      capture("league_selected", {
        league,
        sport: leagueControl.dataset.sport || inferSport(league)
      });
    }

    if (pageName() === "kelly_calculator") {
      if (target.closest(".fraction-btns button")) {
        setTimeout(() => captureKelly("fraction_change"), 0);
      }
    }

    if (pageName() === "prop_engine") {
      const analyzeButton = target.closest("#analyze-btn");
      if (analyzeButton) {
        const propSelect = document.getElementById("prop-select");
        capture("props_viewed", {
          view_type: "analysis",
          props_surface: "player_prop_engine",
          league: activeLeague(),
          sport: activeSport(),
          bet_type: propSelect && propSelect.selectedOptions.length
            ? propSelect.selectedOptions[0].textContent.trim()
            : undefined
        });
      }
    }

    if (pageName() === "props_nfl") {
      const propButton = target.closest("#propButtons button");
      if (propButton) {
        capture("props_viewed", {
          view_type: "filter",
          props_surface: "nfl_model_props",
          league: "NFL",
          sport: "football",
          bet_type: propButton.textContent.replace(/\s*\(\d+\)\s*$/, "").trim(),
          season: (document.getElementById("seasonSelect") || {}).value,
          week: (document.getElementById("weekSelect") || {}).value
        });
      }
    }

    const anchor = target.closest("a[href]");
    if (anchor) {
      try {
        const destination = new URL(anchor.href, location.href);
        if (
          (destination.protocol === "http:" || destination.protocol === "https:") &&
          destination.origin !== location.origin
        ) {
          capture("outbound_link_clicked", {
            destination_domain: destination.hostname,
            destination_url: destination.href
          });
        }
      } catch (_) {
        // Ignore malformed or non-web links.
      }
    }
  });

  document.addEventListener("change", event => {
    const target = event.target instanceof Element ? event.target : null;
    if (!target || pageName() !== "kelly_calculator") return;

    if (target.matches("#bankroll")) {
      captureKelly("bankroll_change");
    }
  });
})();
/* SMH_PRODUCT_ANALYTICS_END */