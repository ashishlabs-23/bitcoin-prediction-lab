import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "web" / "app.js"


def _run_node(script, *args):
    node = shutil.which("node")
    assert node, "Node.js is required to exercise the served journal client and UI."
    result = subprocess.run(
        [node, "-e", script, str(APP_JS), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_active_served_api_exposes_manual_journal_routes_and_operations():
    _run_node(
        r"""
const fs = require("fs");
const vm = require("vm");
const app = fs.readFileSync(process.argv[1], "utf8");
const apiStart = app.indexOf("const api = {");
const apiAssignment = app.indexOf("window.api = api;", apiStart);
if (apiStart < 0 || apiAssignment < 0) throw new Error("Active API object was not found.");

const requests = [];
const context = {
  window: {},
  getApiBaseUrl: () => "http://served-api",
  async fetch(url, options = {}) {
    requests.push({ url, options });
    const isEvaluation = url.endsWith("/api/journal/evaluation");
    return {
      ok: !isEvaluation,
      status: isEvaluation ? 503 : 200,
      statusText: isEvaluation ? "Service Unavailable" : "OK",
      async json() {
        return isEvaluation ? { detail: "evaluation unavailable" } : { status: "SUCCESS" };
      }
    };
  },
  async resilientFetch(url, options = {}) {
    const response = await context.fetch(url, options);
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    return response.json();
  }
};
vm.createContext(context);
vm.runInContext(app.slice(apiStart, apiAssignment) + "\nwindow.api = api;", context);

async function main() {
  const api = context.window.api;
  for (const name of [
    "fetchJournalStatus", "fetchJournalTrades", "fetchJournalEvaluation",
    "recordEnterTrade", "recordExitTrade", "recordAdjustTrade"
  ]) {
    if (typeof api[name] !== "function") throw new Error(`Missing active API method ${name}.`);
  }
  await api.fetchJournalStatus();
  await api.fetchJournalTrades();
  let evaluationFailed = false;
  try { await api.fetchJournalEvaluation(); } catch { evaluationFailed = true; }
  if (!evaluationFailed) throw new Error("Evaluation HTTP failure was not propagated.");
  await api.recordEnterTrade({ entry_price: 100 });
  await api.recordExitTrade("trade/1", { exit_price: 101 });
  await api.recordAdjustTrade("trade/1", { field_name: "notes", new_value: "x", reason: "test" });

  const routes = requests.map(({ url }) => new URL(url).pathname);
  const expected = [
    "/api/journal/status",
    "/api/journal/trades",
    "/api/journal/evaluation",
    "/api/journal/trades/enter",
    "/api/journal/trades/trade%2F1/exit",
    "/api/journal/trades/trade%2F1/adjust"
  ];
  if (JSON.stringify(routes) !== JSON.stringify(expected)) {
    throw new Error(`Unexpected journal routes: ${JSON.stringify(routes)}`);
  }
  if (requests.slice(3).some(({ options }) => options.method !== "POST")) {
    throw new Error("Journal mutations must use POST.");
  }
}
main().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
"""
    )


def test_journal_ui_distinguishes_failed_load_from_successful_empty_records():
    _run_node(
        r"""
const fs = require("fs");
const vm = require("vm");
const app = fs.readFileSync(process.argv[1], "utf8");
const start = app.indexOf("function ManualTradeJournalView(");
const end = app.indexOf("\nfunction SmartEntrySimulatorView(", start);
if (start < 0 || end < 0) throw new Error("Manual trade journal view was not found.");

function text(node) {
  if (node == null || node === false || node === true) return "";
  if (Array.isArray(node)) return node.map(text).join("");
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (typeof node.type === "function") return text(node.type(node.props));
  return (node.children || []).map(text).join("");
}

async function render(mode) {
  const state = [];
  const refs = [];
  const effects = [];
  let stateIndex = 0;
  let refIndex = 0;
  let firstRender = true;
  const h = (type, props, ...children) => ({ type, props: props || {}, children: children.flat(Infinity) });
  const api = {
    fetchJournalTrades: async () => {
      if (mode === "failure") throw new Error("journal backend unavailable");
      return { open_trades: [], closed_trades: [] };
    },
    fetchJournalEvaluation: async () => { throw new Error("HTTP 503: Service Unavailable"); },
    fetchJournalStatus: async () => ({ status: "ONLINE" })
  };
  const context = {
    window: { api },
    useState(initial) {
      const index = stateIndex++;
      if (!(index in state)) state[index] = typeof initial === "function" ? initial() : initial;
      return [state[index], value => {
        state[index] = typeof value === "function" ? value(state[index]) : value;
      }];
    },
    useRef(initial) {
      const index = refIndex++;
      if (!(index in refs)) refs[index] = { current: initial };
      return refs[index];
    },
    useCallback(callback) { return callback; },
    useEffect(effect) { if (firstRender) effects.push(effect); },
    setInterval: () => 1,
    clearInterval: () => {},
    h,
    Date,
    Math,
    Number,
    String,
    parseFloat,
    console
  };
  vm.createContext(context);
  vm.runInContext(app.slice(start, end), context);
  function component() {
    stateIndex = 0;
    refIndex = 0;
    return context.ManualTradeJournalView({ setPath() {}, livePrice: 0 });
  }
  component();
  firstRender = false;
  for (const effect of effects) effect();
  await new Promise(resolve => setImmediate(resolve));
  return text(component());
}

async function main() {
  const failed = await render("failure");
  if (!failed.includes("Open trade records unavailable: journal backend unavailable") ||
      !failed.includes("Closed trade records unavailable: journal backend unavailable") ||
      failed.includes("No open manual trade records currently registered.") ||
      failed.includes("No closed manual trade records yet.")) {
    throw new Error("A failed journal request was shown as a successful empty journal.");
  }
  if (!failed.includes("Forecast evaluation unavailable: HTTP 503: Service Unavailable")) {
    throw new Error("An unavailable forecast evaluation was not identified in the UI.");
  }

  const empty = await render("empty");
  if (!empty.includes("No open manual trade records currently registered.") ||
      !empty.includes("No closed manual trade records yet.") ||
      empty.includes("Open trade records unavailable:") ||
      empty.includes("Closed trade records unavailable:")) {
    throw new Error("A successful empty journal was not preserved as an empty state.");
  }
}
main().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
"""
    )
