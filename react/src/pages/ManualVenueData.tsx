/*
  ManualVenueData - native React port of legacy pages/manual_venue_data.html + assets/js/pages/manual_venue_data.js.
  Same DOM ids/classes (styled by assets/css/pages/manual_venue_data.css), same cascading selects, target path,
  validation and status text, and the same GitHub workflow_dispatch request (POST, Bearer token from the
  "Magic" field, inputs league/variable_1/variable_2/raw_text/target_path, ref main, success on HTTP 204).
*/
import { useState } from "react";
import "../../../app/frontend/src/assets/css/pages/manual_venue_data.css";

const OWNER = "Clownworldenjoyer76";
const REPO = "bet_tracker";
const REF = "main";

type VarOption = { label: string; code: string };
type LeagueConfig = {
  label: string;
  workflowFile: string;
  outputDir: string;
  filePrefix: string;
  variable1Options: VarOption[];
  variable2Options: VarOption[];
};

const LEAGUE_CONFIG: Record<string, LeagueConfig> = {
  MLB: {
    label: "MLB",
    workflowFile: "manual_park_factors.yml",
    outputDir: "docs/win/baseball/mlb/data/park_factors",
    filePrefix: "park",
    variable1Options: [
      { label: "BOTH", code: "B" },
      { label: "LEFT", code: "L" },
      { label: "RIGHT", code: "R" },
    ],
    variable2Options: [
      { label: "DAY", code: "day" },
      { label: "NIGHT", code: "night" },
      { label: "OPEN AIR", code: "open_air" },
      { label: "ROOF CLOSED", code: "roof_closed" },
    ],
  },
};

type Msg = { cls: string; text: string };

function getOptionCode(options: VarOption[], selectedLabel: string) {
  const found = options.find((option) => option.label === selectedLabel);
  return found ? found.code : "";
}

function getTargetPath(config: LeagueConfig | null, variable1: string, variable2: string) {
  if (!config || !variable1 || !variable2) return "";
  const variable1Code = getOptionCode(config.variable1Options, variable1);
  const variable2Code = getOptionCode(config.variable2Options, variable2);
  if (!variable1Code || !variable2Code) return "";
  return `${config.outputDir}/${config.filePrefix}_${variable1Code}_${variable2Code}.csv`;
}

export default function ManualVenueData() {
  const [league, setLeague] = useState("");
  const [variable1, setVariable1] = useState("");
  const [variable2, setVariable2] = useState("");
  const [token, setToken] = useState("");
  const [raw, setRaw] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [out, setOut] = useState<Msg>({ cls: "", text: "" });
  const [status, setStatus] = useState<Msg>({ cls: "status", text: "" });

  const config = LEAGUE_CONFIG[league] ?? null;
  const targetPath = getTargetPath(config, variable1, variable2);

  const onLeagueChange = (value: string) => {
    setLeague(value);
    setVariable1("");
    setVariable2("");
  };

  const onVariable1Change = (value: string) => {
    setVariable1(value);
    setVariable2("");
  };

  const dispatch = async () => {
    const l = league.trim();
    const v1 = variable1.trim();
    const v2 = variable2.trim();
    const t = token.trim();

    if (!config || !l || !v1 || !v2 || !t || !raw.trim() || !targetPath) {
      setOut({ cls: "failure", text: "Major Failure Bro" });
      setStatus({ cls: "", text: "Missing Input" });
      return;
    }

    setSubmitting(true);
    setOut({ cls: "", text: `Submitting to ${config.workflowFile}...` });
    setStatus({ cls: "loading", text: "Submitting" });

    try {
      const url = `https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${config.workflowFile}/dispatches`;

      const res = await fetch(url, {
        method: "POST",
        headers: {
          Accept: "application/vnd.github+json",
          Authorization: `Bearer ${t}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ref: REF,
          inputs: {
            league: l,
            variable_1: v1,
            variable_2: v2,
            raw_text: raw,
            target_path: targetPath,
          },
        }),
      });

      if (res.status === 204) {
        setOut({ cls: "success", text: `Successfully Submitted: ${targetPath}` });
        setStatus({ cls: "", text: "Submitted" });
      } else {
        throw new Error();
      }
    } catch {
      setOut({ cls: "failure", text: `Major Failure Bro: ${config.workflowFile}` });
      setStatus({ cls: "", text: "Failed" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className="manual-header">
        <h1 className="manual-title">
          VENUE<span className="manual-title-slash">/</span>DATA
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
            {Object.keys(LEAGUE_CONFIG).map((key) => (
              <option key={key} value={key}>
                {LEAGUE_CONFIG[key].label}
              </option>
            ))}
          </select>
        </div>

        <div className="control-wrap">
          <span className="control-label">Variable 1</span>
          <select id="variable1" value={variable1} onChange={(e) => onVariable1Change(e.target.value)}>
            <option value="">{config ? "-- select --" : "-- select league first --"}</option>
            {config &&
              config.variable1Options.map((option) => (
                <option key={option.label} value={option.label}>
                  {option.label}
                </option>
              ))}
          </select>
        </div>

        <div className="control-wrap">
          <span className="control-label">Variable 2</span>
          <select id="variable2" value={variable2} onChange={(e) => setVariable2(e.target.value)}>
            <option value="">{config && variable1 ? "-- select --" : "-- select variable 1 first --"}</option>
            {config &&
              variable1 &&
              config.variable2Options.map((option) => (
                <option key={option.label} value={option.label}>
                  {option.label}
                </option>
              ))}
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
            <span className="raw-hint">Paste venue data dump here</span>
          </div>

          <textarea id="raw" value={raw} onChange={(e) => setRaw(e.target.value)} />

          <div id="targetPath" className="target-path">
            {targetPath ? `Target: ${targetPath}` : ""}
          </div>

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
