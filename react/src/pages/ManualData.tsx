/*
  ManualData - native React port of legacy pages/manual_data.html + assets/js/pages/manual_data.js.
  Same DOM ids/classes (styled by assets/css/pages/manual_data.css), same validation and status text,
  same GitHub workflow_dispatch request (POST, Bearer token from the "Magic" field, inputs
  league/market/source/raw_text, ref main, workflow _manual_intake.yml, success on HTTP 204).
*/
import { useState } from "react";
import "../../../app/frontend/src/assets/css/pages/manual_data.css";

const OWNER = "Clownworldenjoyer76";
const REPO = "bet_tracker";
const WORKFLOW_FILE = "_manual_intake.yml";
const REF = "main";

const MARKET_MAP: Record<string, string[]> = {
  soccer: ["Bundesliga", "MLS", "EPL", "La Liga", "Ligue 1", "Serie A"],
  mma: ["UFC"],
};

type Msg = { cls: string; text: string };

export default function ManualData() {
  const [league, setLeague] = useState("");
  const [market, setMarket] = useState("");
  const [source, setSource] = useState("");
  const [token, setToken] = useState("");
  const [raw, setRaw] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [out, setOut] = useState<Msg>({ cls: "", text: "" });
  const [status, setStatus] = useState<Msg>({ cls: "status", text: "" });

  const markets = MARKET_MAP[league] ?? null;

  const applySourceRule = (l: string, m: string) => {
    if (l === "mma" && m === "UFC") setSource("Predictions");
  };

  const onLeagueChange = (value: string) => {
    setLeague(value);
    const list = MARKET_MAP[value];
    const first = value && list ? list[0] : "";
    setMarket(first);
    applySourceRule(value, first);
  };

  const onMarketChange = (value: string) => {
    setMarket(value);
    applySourceRule(league, value);
  };

  const dispatch = async () => {
    const l = league.trim();
    const m = market.trim();
    const s = source.trim();
    const t = token.trim();

    if (!l || !m || !s || !t || !raw.trim()) {
      setOut({ cls: "failure", text: "Major Failure Bro" });
      setStatus({ cls: "", text: "Missing Input" });
      return;
    }

    setSubmitting(true);
    setOut({ cls: "", text: `Submitting to ${WORKFLOW_FILE}...` });
    setStatus({ cls: "loading", text: "Submitting" });

    try {
      const url = `https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW_FILE}/dispatches`;

      const res = await fetch(url, {
        method: "POST",
        headers: {
          Accept: "application/vnd.github+json",
          Authorization: `Bearer ${t}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ref: REF,
          inputs: { league: l, market: m, source: s, raw_text: raw },
        }),
      });

      if (res.status === 204) {
        setOut({ cls: "success", text: `Successfully Submitted: ${WORKFLOW_FILE}` });
        setStatus({ cls: "", text: "Submitted" });
      } else {
        throw new Error();
      }
    } catch {
      setOut({ cls: "failure", text: `Major Failure Bro: ${WORKFLOW_FILE}` });
      setStatus({ cls: "", text: "Failed" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className="manual-header">
        <h1 className="manual-title">
          MANUAL<span className="manual-title-slash">/</span>DATA
        </h1>
        <div id="status" className={status.cls}>
          {status.text}
        </div>
      </div>

      <div className="manual-controls">
        <div className="control-wrap">
          <span className="control-label">League</span>
          <select id="league" value={league} onChange={(e) => onLeagueChange(e.target.value)}>
            <option value="">-- select --</option>
            <option value="soccer">Soccer</option>
            <option value="mma">MMA</option>
          </select>
        </div>

        <div className="control-wrap">
          <span className="control-label">Market</span>
          <select id="market" value={market} onChange={(e) => onMarketChange(e.target.value)}>
            {league && markets ? (
              markets.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))
            ) : (
              <option value="">-- placeholder --</option>
            )}
          </select>
        </div>

        <div className="control-wrap">
          <span className="control-label">Source</span>
          <select id="source" value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="">-- select --</option>
            <option value="Predictions">Predictions</option>
            <option value="Soccer Totals">Soccer Results</option>
            <option value="UFC Results">UFC Results</option>
          </select>
        </div>

        <div className="control-wrap">
          <span className="control-label">Magic</span>
          <input
            id="token"
            type="password"
            placeholder={"\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022"}
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
        </div>
      </div>

      <div className="manual-body">
        <div className="manual-card">
          <div className="raw-label-row">
            <span className="raw-label">Raw Text</span>
            <span className="raw-hint">Paste dump here</span>
          </div>

          <textarea id="raw" value={raw} onChange={(e) => setRaw(e.target.value)} />

          <button
            id="btn"
            className={submitting ? "submitting" : undefined}
            disabled={submitting}
            onClick={dispatch}
          >
            {submitting ? "Processing..." : "Create File"}
          </button>
          <div id="out" className={out.cls}>
            {out.text}
          </div>
        </div>
      </div>
    </>
  );
}
