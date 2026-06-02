# MatchFlow — 40-minute hackathon build spec

**One goal:** Founder fills form → Investor fills form → Kanban pipeline shows matches with score.

---

## Project structure

```
matchflow-backend/
  main.py
  requirements.txt

matchflow-ui/
  app/
    page.tsx
    founder/page.tsx
    investor/page.tsx
    pipeline/page.tsx
```

---

## Backend — `main.py` (copy entire file)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ---------- In-memory store ----------
founders = {}
investors = {}
matches = {}

# ---------- Seed data ----------
SEED_FOUNDERS = [
    {"id": "seed_f1", "company": "SolarGrid",  "sector": "CleanTech",  "stage": "Seed",      "ask": 500000,  "pitch": "solar energy storage climate transition"},
    {"id": "seed_f2", "company": "MediAI",     "sector": "HealthTech", "stage": "Series A",  "ask": 2000000, "pitch": "AI diagnostics healthcare imaging platform"},
    {"id": "seed_f3", "company": "FinFlow",    "sector": "FinTech",    "stage": "Pre-seed",  "ask": 150000,  "pitch": "payments infrastructure banking fintech"},
]
SEED_INVESTORS = [
    {"id": "seed_i1", "fund": "Green Ventures", "sector": "CleanTech",  "stage": "Seed",     "thesis": "climate energy transition storage",  "min_check": 200000,  "max_check": 1000000},
    {"id": "seed_i2", "fund": "Health Alpha",   "sector": "HealthTech", "stage": "Series A", "thesis": "digital health AI diagnostics",       "min_check": 1000000, "max_check": 5000000},
    {"id": "seed_i3", "fund": "Fintech Fund I", "sector": "FinTech",    "stage": "Pre-seed", "thesis": "payments fintech infrastructure",      "min_check": 50000,   "max_check": 500000},
]

# ---------- Matching logic ----------
def score_match(founder: dict, investor: dict) -> dict:
    score = 0
    reasons = []

    # Sector match — 40 pts
    if founder["sector"] == investor["sector"]:
        score += 40
        reasons.append("sector alignment")

    # Stage match — 30 pts
    if founder["stage"] == investor["stage"]:
        score += 30
        reasons.append("stage fit")

    # Check size — 20 pts
    if investor["min_check"] <= founder["ask"] <= investor["max_check"]:
        score += 20
        reasons.append("check size match")

    # Keyword overlap — 10 pts
    f_words = set(founder.get("pitch", "").lower().split())
    i_words = set(investor.get("thesis", "").lower().split())
    if f_words & i_words:
        score += 10
        reasons.append("thesis overlap")

    explanation = "Matched on: " + ", ".join(reasons) if reasons else "Low signal match"
    grade = "Strong" if score >= 70 else "Good" if score >= 40 else "Weak"
    return {"score": score, "explanation": explanation, "grade": grade}

def run_matching(founder: dict, investor: dict) -> dict:
    result = score_match(founder, investor)
    match_id = str(uuid4())
    match = {
        "id": match_id,
        "founder_id": founder["id"],
        "investor_id": investor["id"],
        "company": founder["company"],
        "fund": investor["fund"],
        "sector": founder["sector"],
        "stage": founder["stage"],
        "ask": founder["ask"],
        "score": result["score"],
        "explanation": result["explanation"],
        "grade": result["grade"],
        "status": "new",
    }
    matches[match_id] = match
    return match

# ---------- Startup: load seed data ----------
@app.on_event("startup")
def load_seed():
    for f in SEED_FOUNDERS:
        founders[f["id"]] = f
    for i in SEED_INVESTORS:
        investors[i["id"]] = i
    # Pre-generate all 3x3 matches
    for f in SEED_FOUNDERS:
        for i in SEED_INVESTORS:
            run_matching(f, i)

# ---------- Routes ----------
@app.post("/founder")
def create_founder(body: dict):
    founder_id = str(uuid4())
    founder = {"id": founder_id, **body}
    founders[founder_id] = founder
    new_matches = [run_matching(founder, inv) for inv in investors.values()]
    new_matches.sort(key=lambda m: m["score"], reverse=True)
    return {"founder_id": founder_id, "matches": new_matches}

@app.post("/investor")
def create_investor(body: dict):
    investor_id = str(uuid4())
    investor = {"id": investor_id, **body}
    investors[investor_id] = investor
    new_matches = [run_matching(f, investor) for f in founders.values()]
    new_matches.sort(key=lambda m: m["score"], reverse=True)
    return {"investor_id": investor_id, "matches": new_matches}

@app.get("/matches/{profile_id}")
def get_matches(profile_id: str):
    result = [m for m in matches.values() if m["founder_id"] == profile_id or m["investor_id"] == profile_id]
    result.sort(key=lambda m: m["score"], reverse=True)
    return result

@app.patch("/match/{match_id}")
def update_match(match_id: str, body: dict):
    if match_id not in matches:
        return {"error": "not found"}
    matches[match_id]["status"] = body["status"]
    return matches[match_id]

@app.get("/seed-matches")
def get_seed_matches():
    """Returns all pre-seeded matches — use this for the demo pipeline."""
    result = list(matches.values())
    result.sort(key=lambda m: m["score"], reverse=True)
    return result

@app.get("/health")
def health():
    return {"status": "ok", "founders": len(founders), "investors": len(investors), "matches": len(matches)}
```

### `requirements.txt`

```
fastapi
uvicorn
```

### Run

```bash
pip install fastapi uvicorn
uvicorn main:app --reload --port 8000

# Verify seed data loaded:
curl http://localhost:8000/health
curl http://localhost:8000/seed-matches
```

---

## Frontend — Next.js pages

### `app/page.tsx` — landing / role select

```tsx
"use client";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();
  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-8 bg-stone-50">
      <div className="text-center">
        <h1 className="text-4xl font-semibold text-stone-800">MatchFlow</h1>
        <p className="text-stone-500 mt-2">AI-powered founder–investor matching</p>
      </div>
      <div className="flex gap-4">
        <button
          onClick={() => router.push("/founder")}
          className="px-8 py-4 bg-teal-700 text-white rounded-xl font-medium hover:bg-teal-800 transition"
        >
          I'm a Founder
        </button>
        <button
          onClick={() => router.push("/investor")}
          className="px-8 py-4 border border-teal-700 text-teal-700 rounded-xl font-medium hover:bg-teal-50 transition"
        >
          I'm an Investor
        </button>
      </div>
      <button
        onClick={() => { localStorage.setItem("profile_id", "seed_f1"); router.push("/pipeline"); }}
        className="text-sm text-stone-400 underline"
      >
        Skip to demo pipeline →
      </button>
    </main>
  );
}
```

### `app/founder/page.tsx`

```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

const SECTORS = ["CleanTech", "HealthTech", "FinTech", "SaaS", "Other"];
const STAGES  = ["Pre-seed", "Seed", "Series A"];

export default function FounderForm() {
  const router = useRouter();
  const [form, setForm] = useState({ company: "", sector: "CleanTech", stage: "Seed", ask: "", pitch: "" });
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setLoading(true);
    const res = await fetch("http://localhost:8000/founder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...form, ask: parseInt(form.ask) }),
    });
    const data = await res.json();
    localStorage.setItem("profile_id", data.founder_id);
    localStorage.setItem("role", "founder");
    router.push("/pipeline");
  };

  return (
    <main className="min-h-screen flex items-center justify-center bg-stone-50">
      <div className="bg-white rounded-2xl border border-stone-200 p-8 w-full max-w-md">
        <h2 className="text-xl font-semibold text-stone-800 mb-6">Create your founder profile</h2>
        <div className="flex flex-col gap-4">
          <input className="border border-stone-200 rounded-lg px-4 py-2.5 text-sm" placeholder="Company name"
            value={form.company} onChange={e => setForm({...form, company: e.target.value})} />
          <select className="border border-stone-200 rounded-lg px-4 py-2.5 text-sm"
            value={form.sector} onChange={e => setForm({...form, sector: e.target.value})}>
            {SECTORS.map(s => <option key={s}>{s}</option>)}
          </select>
          <select className="border border-stone-200 rounded-lg px-4 py-2.5 text-sm"
            value={form.stage} onChange={e => setForm({...form, stage: e.target.value})}>
            {STAGES.map(s => <option key={s}>{s}</option>)}
          </select>
          <input className="border border-stone-200 rounded-lg px-4 py-2.5 text-sm" placeholder="Funding ask (€)"
            type="number" value={form.ask} onChange={e => setForm({...form, ask: e.target.value})} />
          <textarea className="border border-stone-200 rounded-lg px-4 py-2.5 text-sm resize-none" rows={3}
            placeholder="One-line pitch (keywords help matching)"
            value={form.pitch} onChange={e => setForm({...form, pitch: e.target.value})} />
          <button onClick={submit} disabled={loading}
            className="bg-teal-700 text-white rounded-lg py-2.5 text-sm font-medium hover:bg-teal-800 transition disabled:opacity-50">
            {loading ? "Matching…" : "Find investors →"}
          </button>
        </div>
      </div>
    </main>
  );
}
```

### `app/investor/page.tsx`

```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

const SECTORS = ["CleanTech", "HealthTech", "FinTech", "SaaS", "Other"];
const STAGES  = ["Pre-seed", "Seed", "Series A"];

export default function InvestorForm() {
  const router = useRouter();
  const [form, setForm] = useState({ fund: "", sector: "CleanTech", stage: "Seed", thesis: "", min_check: "", max_check: "" });
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setLoading(true);
    const res = await fetch("http://localhost:8000/investor", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...form, min_check: parseInt(form.min_check), max_check: parseInt(form.max_check) }),
    });
    const data = await res.json();
    localStorage.setItem("profile_id", data.investor_id);
    localStorage.setItem("role", "investor");
    router.push("/pipeline");
  };

  return (
    <main className="min-h-screen flex items-center justify-center bg-stone-50">
      <div className="bg-white rounded-2xl border border-stone-200 p-8 w-full max-w-md">
        <h2 className="text-xl font-semibold text-stone-800 mb-6">Create your investor profile</h2>
        <div className="flex flex-col gap-4">
          <input className="border border-stone-200 rounded-lg px-4 py-2.5 text-sm" placeholder="Fund name"
            value={form.fund} onChange={e => setForm({...form, fund: e.target.value})} />
          <select className="border border-stone-200 rounded-lg px-4 py-2.5 text-sm"
            value={form.sector} onChange={e => setForm({...form, sector: e.target.value})}>
            {SECTORS.map(s => <option key={s}>{s}</option>)}
          </select>
          <select className="border border-stone-200 rounded-lg px-4 py-2.5 text-sm"
            value={form.stage} onChange={e => setForm({...form, stage: e.target.value})}>
            {STAGES.map(s => <option key={s}>{s}</option>)}
          </select>
          <input className="border border-stone-200 rounded-lg px-4 py-2.5 text-sm" placeholder="Min check size (€)"
            type="number" value={form.min_check} onChange={e => setForm({...form, min_check: e.target.value})} />
          <input className="border border-stone-200 rounded-lg px-4 py-2.5 text-sm" placeholder="Max check size (€)"
            type="number" value={form.max_check} onChange={e => setForm({...form, max_check: e.target.value})} />
          <textarea className="border border-stone-200 rounded-lg px-4 py-2.5 text-sm resize-none" rows={3}
            placeholder="Investment thesis (keywords help matching)"
            value={form.thesis} onChange={e => setForm({...form, thesis: e.target.value})} />
          <button onClick={submit} disabled={loading}
            className="bg-teal-700 text-white rounded-lg py-2.5 text-sm font-medium hover:bg-teal-800 transition disabled:opacity-50">
            {loading ? "Matching…" : "See deal flow →"}
          </button>
        </div>
      </div>
    </main>
  );
}
```

### `app/pipeline/page.tsx` — the kanban (demo hero)

```tsx
"use client";
import { useEffect, useState } from "react";

const LOGO_COLORS: Record<string, string> = {
  CleanTech: "#5DCAA5", HealthTech: "#378ADD", FinTech: "#D85A30", SaaS: "#7F77DD", Other: "#D4537E",
};

type Match = {
  id: string; company: string; fund: string; sector: string;
  stage: string; ask: number; score: number; explanation: string;
  grade: string; status: "new" | "interested" | "active" | "declined";
};

const COLUMNS = [
  { key: "new",        label: "Matches",       badge: "bg-teal-100 text-teal-800"   },
  { key: "interested", label: "Intro Requests", badge: "bg-purple-100 text-purple-800" },
  { key: "active",     label: "Active",         badge: "bg-green-100 text-green-800"  },
  { key: "declined",   label: "Declined",       badge: "bg-stone-100 text-stone-500"  },
];

function ScoreBadge({ score }: { score: number }) {
  const cls = score >= 70 ? "bg-teal-100 text-teal-800" : score >= 40 ? "bg-amber-100 text-amber-800" : "bg-red-100 text-red-700";
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${cls}`}>{score}%</span>;
}

function MatchCard({ match, onMove }: { match: Match; onMove: (id: string, status: string) => void }) {
  const initial = match.company[0];
  const color = LOGO_COLORS[match.sector] || "#888";
  const dimmed = match.status === "declined";

  return (
    <div className={`bg-white rounded-xl border border-stone-200 p-3 mb-2 ${dimmed ? "opacity-50" : ""}`}>
      <div className="flex items-start gap-2.5 mb-2.5">
        <div className="w-9 h-9 rounded-lg flex items-center justify-center text-sm font-semibold flex-shrink-0"
          style={{ background: color + "20", color }}>
          {initial}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-stone-800 truncate">{match.company}</p>
          <p className="text-xs text-stone-400 truncate">{match.fund}</p>
        </div>
        <ScoreBadge score={match.score} />
      </div>

      <div className="flex flex-wrap gap-1 mb-2">
        {[match.sector, match.stage, `€${(match.ask/1000).toFixed(0)}k`].map(tag => (
          <span key={tag} className="text-xs bg-stone-100 text-stone-500 px-2 py-0.5 rounded-full">{tag}</span>
        ))}
      </div>

      <p className="text-xs text-stone-400 italic border-l-2 border-teal-400 pl-2 mb-3 leading-relaxed">
        {match.explanation}
      </p>

      <div className="flex gap-2 pt-2 border-t border-stone-100">
        {match.status === "new" && <>
          <button onClick={() => onMove(match.id, "interested")}
            className="flex-1 text-xs font-medium bg-teal-700 text-white rounded-lg py-1.5 hover:bg-teal-800 transition">
            Interested
          </button>
          <button onClick={() => onMove(match.id, "declined")}
            className="flex-1 text-xs font-medium border border-stone-200 text-stone-500 rounded-lg py-1.5 hover:bg-stone-50 transition">
            Not for me
          </button>
        </>}
        {match.status === "interested" && <>
          <button onClick={() => onMove(match.id, "active")}
            className="flex-1 text-xs font-medium border border-teal-700 text-teal-700 rounded-lg py-1.5 hover:bg-teal-50 transition">
            Accept intro
          </button>
          <button onClick={() => onMove(match.id, "declined")}
            className="flex-1 text-xs font-medium border border-stone-200 text-stone-500 rounded-lg py-1.5 hover:bg-stone-50 transition">
            Decline
          </button>
        </>}
        {match.status === "active" && (
          <button className="flex-1 text-xs font-medium bg-blue-600 text-white rounded-lg py-1.5 hover:bg-blue-700 transition">
            Schedule call
          </button>
        )}
        {match.status === "declined" && (
          <span className="text-xs text-stone-400 w-full text-right">Declined</span>
        )}
      </div>
    </div>
  );
}

export default function Pipeline() {
  const [matches, setMatches] = useState<Match[]>([]);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    const profileId = localStorage.getItem("profile_id") || "seed_f1";
    const endpoint = profileId.startsWith("seed_f") || !profileId.includes("seed_i")
      ? "http://localhost:8000/seed-matches"
      : `http://localhost:8000/matches/${profileId}`;
    fetch(endpoint).then(r => r.json()).then(setMatches).catch(() => {});
  }, []);

  const move = async (id: string, status: string) => {
    await fetch(`http://localhost:8000/match/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    setMatches(prev => prev.map(m => m.id === id ? { ...m, status: status as Match["status"] } : m));
  };

  const sectors = ["all", ...Array.from(new Set(matches.map(m => m.sector)))];
  const visible = filter === "all" ? matches : matches.filter(m => m.sector === filter);

  return (
    <main className="min-h-screen bg-stone-50 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-stone-800">Pipeline</h1>
          <p className="text-stone-400 text-sm mt-1">Track your opportunities across stages</p>
        </div>

        <div className="flex gap-2 mb-5">
          {sectors.map(s => (
            <button key={s} onClick={() => setFilter(s)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition ${
                filter === s ? "bg-teal-700 text-white" : "border border-stone-200 text-stone-500 hover:bg-stone-100"}`}>
              {s === "all" ? "All deals" : s}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-4 gap-4 items-start">
          {COLUMNS.map(col => {
            const colMatches = visible.filter(m => m.status === col.key);
            return (
              <div key={col.key} className="bg-stone-100 rounded-2xl p-3">
                <div className="flex items-center justify-between mb-3 px-1">
                  <span className="text-sm font-medium text-stone-700">{col.label}</span>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${col.badge}`}>
                    {colMatches.length}
                  </span>
                </div>
                {colMatches.length === 0 ? (
                  <div className="text-center py-10 text-stone-400 text-xs leading-loose">
                    <div className="text-2xl mb-2 opacity-30">□</div>
                    {col.key === "interested" ? "Intro requests appear here." :
                     col.key === "active" ? "Active deals appear here." : "No matches yet."}
                  </div>
                ) : colMatches.map(m => <MatchCard key={m.id} match={m} onMove={move} />)}
              </div>
            );
          })}
        </div>
      </div>
    </main>
  );
}
```

---

## Setup commands

```bash
# Backend
cd matchflow-backend
pip install fastapi uvicorn
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd matchflow-ui
npx create-next-app . --typescript --tailwind --app --no-src-dir --import-alias "@/*"
# paste in the page files above
npm run dev
```

Open `http://localhost:3000` — click "Skip to demo pipeline →" to see the kanban immediately without filling forms.

---

## Demo flow (practise twice)

1. Open `localhost:3000` → click "Skip to demo pipeline →" — kanban loads with seed matches
2. Point at SolarGrid at 100% — *"sector, stage and check size all aligned"*
3. Click **Interested** — card moves to Intro Requests column
4. Click **Accept intro** — card moves to Active
5. *"One click from match to active deal. That's intelligent deal flow."*

## Emergency fallback

If the backend is down — hardcode this at the top of `pipeline/page.tsx` and remove the `fetch`:

```ts
const [matches, setMatches] = useState<Match[]>([
  { id:"1", company:"SolarGrid",  fund:"Green Ventures", sector:"CleanTech",  stage:"Seed",     ask:500000,  score:100, explanation:"Perfect sector, stage and check size alignment.", grade:"Strong", status:"new" },
  { id:"2", company:"MediAI",     fund:"Health Alpha",   sector:"HealthTech", stage:"Series A", ask:2000000, score:90,  explanation:"Strong thesis alignment on AI diagnostics.",     grade:"Strong", status:"new" },
  { id:"3", company:"FinFlow",    fund:"Fintech Fund I", sector:"FinTech",    stage:"Pre-seed", ask:150000,  score:85,  explanation:"Payments infrastructure thesis overlap.",         grade:"Strong", status:"interested" },
  { id:"4", company:"GridSense",  fund:"Climate First",  sector:"CleanTech",  stage:"Seed",     ask:300000,  score:70,  explanation:"CleanTech sector and grid technology match.",    grade:"Strong", status:"active" },
  { id:"5", company:"BioTrack",   fund:"Health Alpha",   sector:"HealthTech", stage:"Pre-seed", ask:80000,   score:45,  explanation:"Sector match but stage and check size mismatch.", grade:"Good",  status:"declined" },
]);
```
