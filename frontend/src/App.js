import React, { useEffect, useState } from "react";
import { BrowserRouter, NavLink, Routes, Route, useNavigate } from "react-router-dom";
import { DCA, Regency } from "./api";

const RESPONSIBILITIES = [
  { n: "R1", path: "/veras", label: "Principal Identity", lineage: "vera registry" },
  { n: "R2", path: "/placements", label: "Environment & Runtime", lineage: "floks-pc" },
  { n: "R3", path: "/memory", label: "Durable State & Memory", lineage: "aeon-iq" },
  { n: "R4", path: "/authority", label: "Authority & Capability", lineage: "genesis" },
  { n: "R5", path: "/effects", label: "Effectful Execution", lineage: "nexus" },
  { n: "R6", path: "/evidence", label: "Evidence & Verification", lineage: "context-kernel" },
  { n: "R7", path: "/sessions", label: "Coordination & Interconnect", lineage: "agent-bridge" },
];

function Sidebar() {
  return (
    <aside className="sidebar" data-testid="sidebar">
      <div className="brand">floks-pc // DCA</div>
      <div className="brand-title">Continuum <span className="accent">Orchestrator</span></div>
      <div className="brand-sub">Distributed Cognitive Architecture · reference wiring</div>
      <nav className="nav">
        <NavLink to="/" end className={({isActive}) => "nav-item" + (isActive ? " active" : "")} data-testid="nav-overview">
          <span className="nav-num">00</span>Overview
        </NavLink>
        {RESPONSIBILITIES.map((r, i) => (
          <NavLink key={r.path} to={r.path} className={({isActive}) => "nav-item" + (isActive ? " active" : "")} data-testid={`nav-${r.n.toLowerCase()}`}>
            <span className="nav-num">{String(i+1).padStart(2,"0")}</span>
            <span>{r.n} · {r.label}</span>
          </NavLink>
        ))}
        <NavLink to="/regency" className={({isActive}) => "nav-item" + (isActive ? " active" : "")} data-testid="nav-regency">
          <span className="nav-num">08</span>The Regency
        </NavLink>
        <NavLink to="/packages" className={({isActive}) => "nav-item" + (isActive ? " active" : "")} data-testid="nav-packages">
          <span className="nav-num">09</span>Packages
        </NavLink>
      </nav>
    </aside>
  );
}

function PageHead({ title, sub, right }) {
  return (
    <div className="page-head">
      <div>
        <h1 className="page-title">{title}</h1>
        <div className="page-sub">{sub}</div>
      </div>
      <div>{right}</div>
    </div>
  );
}

function Badge({ v }) { return <span className={`badge ${v}`}>{v}</span>; }
function short(id) { return id ? id.slice(0, 8) + "…" : "—"; }

// ============= OVERVIEW =============
function Overview() {
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();

  const load = async () => setStatus(await DCA.status());
  useEffect(() => { load(); const t = setInterval(load, 5000); return () => clearInterval(t); }, []);

  const seed = async () => {
    setBusy(true);
    try { await DCA.seed(); await load(); } finally { setBusy(false); }
  };

  if (!status) return <div className="empty" data-testid="loading">Loading DCA status…</div>;

  return (
    <>
      <PageHead
        title="Overview /::/ floks-pc"
        sub="Continuum lineage · six-package DCA reference"
        right={<button className="btn primary" onClick={seed} disabled={busy} data-testid="btn-seed">
          {busy ? "seeding…" : "Seed demo VERA"}
        </button>}
      />

      <div className="grid grid-4" data-testid="stats-grid">
        {[
          ["veras", "R1 · VERA principals"],
          ["placements", "R2 · Runtime placements"],
          ["memories", "R3 · Memory facts"],
          ["grants", "R4 · Authority grants"],
          ["effects", "R5 · Effects"],
          ["evidence", "R6 · Evidence entries"],
          ["sessions", "R7 · Sessions"],
        ].map(([k, label]) => (
          <div className="card" key={k} data-testid={`stat-${k}`}>
            <div className="card-title">{label}</div>
            <div className="stat-num">{status.counts[k]}</div>
          </div>
        ))}
        <div className="card" data-testid="stat-chain">
          <div className="card-title">R6 · Chain verify</div>
          <div className="stat-num" style={{fontSize:20}}>
            {status.evidence_chain.broken_at
              ? <span className="err">broken@{status.evidence_chain.broken_at}</span>
              : <span className="ok">{status.evidence_chain.verified_entries} ✓</span>}
          </div>
          <div className="small mono">tip: {status.evidence_chain.tip_hash.slice(0,16)}…</div>
        </div>
      </div>

      <hr className="divider" />

      <PageHead title="Seven mandatory responsibilities" sub="One canonical vocabulary · profile-neutral" />
      <div className="card">
        {RESPONSIBILITIES.map(r => (
          <div className="responsibility-plate" key={r.n} onClick={() => nav(r.path)} style={{cursor:"pointer"}} data-testid={`resp-${r.n.toLowerCase()}`}>
            <div className="responsibility-num">{r.n}</div>
            <div className="responsibility-body">
              <div className="responsibility-name">{r.label}</div>
              <div className="responsibility-lineage">lineage · {r.lineage} — {status.subsystems[r.lineage]?.state || "linked"}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="effect-boundary-note">
        <strong>Effect Boundary</strong> — cross-cutting mediation. Cognition proposes; authority (R4) decides; nexus (R5) contains;
        evidence (R6) records. Not an eighth responsibility. Committed effects are exportable as Ed25519-signed Proof Capsules.
      </div>
      <div className="effect-boundary-note" style={{borderLeftColor:"var(--accent-2)"}}>
        <strong>The Regency</strong> — governance product bound to R4. Materializes mandates + roles as attenuated grants;
        emergency-suspension cascades through all subsystems. Open <span className="mono">/regency</span> to operate.
      </div>
    </>
  );
}

// ============= R1 VERAs =============
function Veras() {
  const [list, setList] = useState([]);
  const [form, setForm] = useState({ trust_domain: "asentxia.local", principal_id: "", display_name: "", mandate: "" });
  const load = async () => setList(await DCA.listVeras());
  useEffect(() => { load(); }, []);
  const submit = async (e) => {
    e.preventDefault();
    if (!form.principal_id || !form.display_name) return;
    await DCA.createVera(form);
    setForm({ trust_domain: "asentxia.local", principal_id: "", display_name: "", mandate: "" });
    load();
  };
  return (
    <>
      <PageHead title="R1 /::/ Principal Identity" sub="VERA — Verifiable Entity with Revocable Authority" />
      <div className="grid grid-2" style={{gridTemplateColumns:"1fr 360px"}}>
        <div className="card">
          {list.length === 0 ? <div className="empty">No VERAs. Create one, or seed demo data on Overview.</div> :
            <table className="table" data-testid="veras-table">
              <thead><tr><th>ID</th><th>Principal</th><th>Display</th><th>Mandate</th><th>State</th><th></th></tr></thead>
              <tbody>
                {list.map(v => (
                  <tr key={v.id} data-testid={`vera-row-${v.id}`}>
                    <td className="mono">{short(v.id)}</td>
                    <td className="mono">{v.trust_domain}<br/><span className="muted">{v.principal_id}</span></td>
                    <td>{v.display_name}</td>
                    <td className="small">{v.mandate}</td>
                    <td><Badge v={v.state}/></td>
                    <td>
                      {v.state === "ACTIVE" && <>
                        <button className="btn" onClick={async ()=>{await DCA.suspendVera(v.id); load();}} data-testid={`btn-suspend-${v.id}`}>suspend</button>{" "}
                        <button className="btn danger" onClick={async ()=>{await DCA.decommissionVera(v.id); load();}} data-testid={`btn-decom-${v.id}`}>decom</button>
                      </>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          }
        </div>
        <div className="card">
          <div className="card-title">Register new VERA</div>
          <form onSubmit={submit} data-testid="create-vera-form">
            <div className="form-row"><label>trust_domain</label><input value={form.trust_domain} onChange={e=>setForm({...form, trust_domain: e.target.value})} data-testid="input-trust-domain"/></div>
            <div className="form-row"><label>principal_id</label><input value={form.principal_id} onChange={e=>setForm({...form, principal_id: e.target.value})} required data-testid="input-principal-id"/></div>
            <div className="form-row"><label>display_name</label><input value={form.display_name} onChange={e=>setForm({...form, display_name: e.target.value})} required data-testid="input-display-name"/></div>
            <div className="form-row"><label>mandate</label><textarea value={form.mandate} onChange={e=>setForm({...form, mandate: e.target.value})} data-testid="input-mandate"/></div>
            <button className="btn primary" type="submit" data-testid="btn-create-vera">Create VERA</button>
          </form>
        </div>
      </div>
    </>
  );
}

// ============= R2 Placements =============
function Placements() {
  const [list, setList] = useState([]);
  const [veras, setVeras] = useState([]);
  const [form, setForm] = useState({ vera_id: "", provider: "runloop-devbox", ttl_seconds: 3600, capabilities: "fs.read,browser.observe" });
  const load = async () => { setList(await DCA.listPlacements()); setVeras(await DCA.listVeras()); };
  useEffect(() => { load(); }, []);
  const submit = async (e) => {
    e.preventDefault();
    if (!form.vera_id) return;
    await DCA.leasePlacement({
      vera_id: form.vera_id, provider: form.provider, ttl_seconds: +form.ttl_seconds,
      capabilities: form.capabilities.split(",").map(s=>s.trim()).filter(Boolean),
    });
    load();
  };
  return (
    <>
      <PageHead title="R2 /::/ Environment & Runtime" sub="floks-pc Agent Computer · lease ≠ authority · fencing-safe" />
      <div className="grid grid-2" style={{gridTemplateColumns:"1fr 360px"}}>
        <div className="card">
          {list.length === 0 ? <div className="empty">No placements. Lease one for an ACTIVE VERA.</div> :
            <table className="table" data-testid="placements-table">
              <thead><tr><th>Computer</th><th>VERA</th><th>Provider</th><th>Epoch</th><th>State</th><th>Capabilities</th><th></th></tr></thead>
              <tbody>
                {list.map(p => (
                  <tr key={p.id} data-testid={`placement-row-${p.id}`}>
                    <td className="mono">{p.computer_id}</td>
                    <td className="mono">{short(p.vera_id)}</td>
                    <td className="mono">{p.provider}</td>
                    <td className="mono">{p.lease_epoch}</td>
                    <td><Badge v={p.state}/></td>
                    <td><div className="pill-line">{p.capabilities.map(c=><span className="pill" key={c}>{c}</span>)}</div></td>
                    <td>{p.state === "ACTIVE" && <button className="btn danger" onClick={async ()=>{await DCA.fencePlacement(p.id); load();}} data-testid={`btn-fence-${p.id}`}>fence</button>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          }
        </div>
        <div className="card">
          <div className="card-title">Lease Agent Computer</div>
          <form onSubmit={submit} data-testid="lease-form">
            <div className="form-row"><label>vera_id</label>
              <select value={form.vera_id} onChange={e=>setForm({...form, vera_id: e.target.value})} required data-testid="select-vera">
                <option value="">— pick VERA —</option>
                {veras.filter(v=>v.state==="ACTIVE").map(v => <option key={v.id} value={v.id}>{v.display_name} ({short(v.id)})</option>)}
              </select>
            </div>
            <div className="form-row"><label>provider</label><input value={form.provider} onChange={e=>setForm({...form, provider: e.target.value})} data-testid="input-provider"/></div>
            <div className="form-row"><label>ttl_seconds</label><input type="number" value={form.ttl_seconds} onChange={e=>setForm({...form, ttl_seconds: e.target.value})} data-testid="input-ttl"/></div>
            <div className="form-row"><label>capabilities (csv)</label><input value={form.capabilities} onChange={e=>setForm({...form, capabilities: e.target.value})} data-testid="input-caps"/></div>
            <button className="btn primary" type="submit" data-testid="btn-lease">Lease</button>
          </form>
          <div className="small" style={{marginTop:12}}>
            Runloop Devbox is provider v1 per <span className="mono">floks-pc/AUTHORITY.md</span>. Lease controls placement eligibility only — never effect authority.
          </div>
        </div>
      </div>
    </>
  );
}

// ============= R3 Memory =============
function Memory() {
  const [veras, setVeras] = useState([]);
  const [selectedVera, setSelectedVera] = useState("");
  const [facts, setFacts] = useState([]);
  const [q, setQ] = useState("");
  const [mode, setMode] = useState("auto");
  const [memStatus, setMemStatus] = useState(null);
  const [form, setForm] = useState({ kind: "semantic", content: "" });
  const load = async () => { setVeras(await DCA.listVeras()); setMemStatus(await DCA.memoryStatus()); };
  useEffect(() => { load(); }, []);
  useEffect(() => { if (selectedVera) DCA.recallMemory(selectedVera, q, mode).then(setFacts); else setFacts([]); }, [selectedVera, q, mode]);
  const submit = async (e) => {
    e.preventDefault();
    if (!selectedVera || !form.content) return;
    await DCA.writeMemory({ vera_id: selectedVera, kind: form.kind, content: form.content, source: { origin: "console" } });
    setForm({ kind: "semantic", content: "" });
    setFacts(await DCA.recallMemory(selectedVera, q, mode));
  };
  return (
    <>
      <PageHead
        title="R3 /::/ Durable State & Memory"
        sub="aeon-iq lineage · facts bound to VERA with provenance"
        right={memStatus && <span className="mono small">
          backend: <span className="accent">{memStatus.embedding_backend}</span>
        </span>}
      />
      <div className="grid grid-2" style={{gridTemplateColumns:"1fr 360px"}}>
        <div className="card">
          <div style={{display:"flex", gap:12, marginBottom:12}}>
            <select value={selectedVera} onChange={e=>setSelectedVera(e.target.value)} className="mono" style={{background:"var(--bg)",color:"var(--text)",border:"1px solid var(--border)",padding:"8px 12px",borderRadius:3, flex:1}} data-testid="mem-select-vera">
              <option value="">— pick VERA to recall —</option>
              {veras.map(v => <option key={v.id} value={v.id}>{v.display_name} ({short(v.id)})</option>)}
            </select>
            <input placeholder="query" value={q} onChange={e=>setQ(e.target.value)} style={{background:"var(--bg)",color:"var(--text)",border:"1px solid var(--border)",padding:"8px 12px",borderRadius:3, fontFamily:"var(--mono)", flex:1}} data-testid="mem-search"/>
            <select value={mode} onChange={e=>setMode(e.target.value)} style={{background:"var(--bg)",color:"var(--text)",border:"1px solid var(--border)",padding:"8px 12px",borderRadius:3, fontFamily:"var(--mono)"}} data-testid="mem-mode">
              <option value="auto">auto</option>
              <option value="semantic">semantic</option>
              <option value="substring">substring</option>
            </select>
          </div>
          {selectedVera && facts.length === 0 ? <div className="empty">No memories recalled.</div> :
            !selectedVera ? <div className="empty">Pick a VERA above.</div> :
            <table className="table" data-testid="memory-table">
              <thead><tr><th>Kind</th><th>Content</th><th>Similarity</th><th>Source</th></tr></thead>
              <tbody>
                {facts.map(f => (
                  <tr key={f.id} data-testid={`memory-row-${f.id}`}>
                    <td><span className="pill">{f.kind}</span></td>
                    <td>{f.content}</td>
                    <td className="mono accent">{f.source?._similarity !== undefined ? f.source._similarity : "—"}</td>
                    <td className="small mono">{JSON.stringify({...f.source, _similarity: undefined}).replace(',"_similarity":undefined','')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          }
        </div>
        <div className="card">
          <div className="card-title">Write memory fact</div>
          <form onSubmit={submit} data-testid="write-memory-form">
            <div className="form-row"><label>vera</label>
              <select value={selectedVera} onChange={e=>setSelectedVera(e.target.value)} required data-testid="mem-write-vera">
                <option value="">— pick VERA —</option>
                {veras.map(v => <option key={v.id} value={v.id}>{v.display_name}</option>)}
              </select>
            </div>
            <div className="form-row"><label>kind</label>
              <select value={form.kind} onChange={e=>setForm({...form, kind:e.target.value})} data-testid="mem-write-kind">
                <option>semantic</option><option>episodic</option><option>operational</option><option>derived</option>
              </select>
            </div>
            <div className="form-row"><label>content</label><textarea value={form.content} onChange={e=>setForm({...form, content: e.target.value})} required data-testid="mem-write-content"/></div>
            <button className="btn primary" type="submit" data-testid="btn-write-memory">Persist</button>
          </form>
          <div className="small" style={{marginTop:12}}>
            {memStatus && memStatus.embedding_backend === "local" &&
              `Local deterministic embedder (256-d char-3gram feature hashing). ${memStatus.embedding_note}.`}
            {memStatus && memStatus.embedding_backend === "openai" &&
              "OpenAI text-embedding-3-small (1536-d). Matches aeon-iq contract."}
          </div>
        </div>
      </div>
    </>
  );
}

// ============= R4 Authority =============
function Authority() {
  const [veras, setVeras] = useState([]);
  const [grants, setGrants] = useState([]);
  const [form, setForm] = useState({ vera_id: "", capability: "effect:http.fetch", scope: '{"host_allowlist":["example.com"]}', ttl_seconds: 3600, granted_by: "human:owner" });
  const load = async () => { setVeras(await DCA.listVeras()); setGrants(await DCA.listGrants()); };
  useEffect(() => { load(); }, []);
  const submit = async (e) => {
    e.preventDefault();
    let scope = {}; try { scope = JSON.parse(form.scope); } catch { alert("scope must be JSON"); return; }
    await DCA.issueGrant({ vera_id: form.vera_id, granted_by: form.granted_by, capability: form.capability, scope, ttl_seconds: +form.ttl_seconds });
    load();
  };
  return (
    <>
      <PageHead title="R4 /::/ Authority & Capability Governance" sub="genesis lineage · attenuated · revocable · fail-closed" />
      <div className="grid grid-2" style={{gridTemplateColumns:"1fr 360px"}}>
        <div className="card">
          {grants.length === 0 ? <div className="empty">No grants issued yet.</div> :
            <table className="table" data-testid="grants-table">
              <thead><tr><th>ID</th><th>VERA</th><th>Capability</th><th>Scope</th><th>State</th><th>Expires</th><th></th></tr></thead>
              <tbody>
                {grants.map(g => (
                  <tr key={g.id} data-testid={`grant-row-${g.id}`}>
                    <td className="mono">{short(g.id)}</td>
                    <td className="mono">{short(g.vera_id)}</td>
                    <td className="mono">{g.capability}</td>
                    <td className="small mono">{JSON.stringify(g.scope)}</td>
                    <td><Badge v={g.state}/></td>
                    <td className="small mono">{g.expires_at.slice(0,19)}</td>
                    <td>{g.state === "ACTIVE" && <button className="btn danger" onClick={async ()=>{await DCA.revokeGrant(g.id); load();}} data-testid={`btn-revoke-${g.id}`}>revoke</button>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          }
        </div>
        <div className="card">
          <div className="card-title">Issue authority grant</div>
          <form onSubmit={submit} data-testid="issue-grant-form">
            <div className="form-row"><label>vera</label>
              <select value={form.vera_id} onChange={e=>setForm({...form, vera_id: e.target.value})} required data-testid="grant-vera">
                <option value="">— pick VERA —</option>
                {veras.filter(v=>v.state==="ACTIVE").map(v => <option key={v.id} value={v.id}>{v.display_name}</option>)}
              </select>
            </div>
            <div className="form-row"><label>granted_by</label><input value={form.granted_by} onChange={e=>setForm({...form, granted_by: e.target.value})} data-testid="grant-by"/></div>
            <div className="form-row"><label>capability</label><input value={form.capability} onChange={e=>setForm({...form, capability: e.target.value})} data-testid="grant-cap"/></div>
            <div className="form-row"><label>scope (JSON)</label><textarea value={form.scope} onChange={e=>setForm({...form, scope: e.target.value})} data-testid="grant-scope"/></div>
            <div className="form-row"><label>ttl_seconds</label><input type="number" value={form.ttl_seconds} onChange={e=>setForm({...form, ttl_seconds: e.target.value})} data-testid="grant-ttl"/></div>
            <button className="btn primary" type="submit" data-testid="btn-issue-grant">Issue</button>
          </form>
        </div>
      </div>
    </>
  );
}

// ============= R5 Effects =============
function Effects() {
  const [veras, setVeras] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [effects, setEffects] = useState([]);
  const [form, setForm] = useState({ vera_id: "", session_id: "", capability_required: "effect:wasm.run", payload: '{"use_nexus_demo":true}' });
  const [detail, setDetail] = useState(null);
  const load = async () => {
    setVeras(await DCA.listVeras());
    setSessions(await DCA.listSessions());
    setEffects(await DCA.listEffects());
  };
  useEffect(() => { load(); const t = setInterval(load, 3000); return () => clearInterval(t); }, []);
  const submit = async (e) => {
    e.preventDefault();
    let payload = {}; try { payload = JSON.parse(form.payload); } catch { alert("payload must be JSON"); return; }
    const action_id = `act-${Math.random().toString(36).slice(2, 10)}`;
    await DCA.proposeEffect({
      vera_id: form.vera_id, session_id: form.session_id || null,
      action_id, capability_required: form.capability_required, payload,
    });
    load();
  };
  const dispatch = async (id) => { await DCA.dispatchEffect(id); load(); };
  const downloadCapsule = (id) => { window.location.href = DCA.capsuleDownloadUrl(id); };
  return (
    <>
      <PageHead title="R5 /::/ Effectful Execution" sub="nexus lineage · wasmtime · capability-gated · exactly-once via action_id" />
      <div className="effect-boundary-note">
        <strong>Effect Boundary</strong> · dispatch verifies (1) placement not fenced, (2) an ACTIVE grant covers the capability,
        (3) action_id has not been committed. Unknown outcomes are recorded as UNKNOWN, never blind-retried. Committed effects
        can be exported as signed Proof Capsules.
      </div>
      <div className="grid grid-2" style={{gridTemplateColumns:"1fr 360px"}}>
        <div className="card">
          {effects.length === 0 ? <div className="empty">No effects proposed yet.</div> :
            <table className="table" data-testid="effects-table">
              <thead><tr><th>Action</th><th>VERA</th><th>Capability</th><th>Outcome</th><th>Adapter</th><th></th></tr></thead>
              <tbody>
                {effects.map(e => (
                  <tr key={e.id} data-testid={`effect-row-${e.id}`}>
                    <td className="mono">{e.action_id}</td>
                    <td className="mono">{short(e.vera_id)}</td>
                    <td className="mono">{e.capability_required}</td>
                    <td><Badge v={e.outcome}/>{e.denial_reason && <div className="small err">{e.denial_reason}</div>}</td>
                    <td className="mono small">{e.result?.adapter || "—"}<br/>{e.result?.exit_code !== undefined && <span className="muted">exit={e.result.exit_code}</span>}</td>
                    <td>
                      {e.outcome === "PREPARED" && <button className="btn primary" onClick={()=>dispatch(e.id)} data-testid={`btn-dispatch-${e.id}`}>dispatch</button>}
                      {["COMMITTED", "UNKNOWN"].includes(e.outcome) && <>
                        <button className="btn" onClick={()=>setDetail(e)} data-testid={`btn-detail-${e.id}`}>inspect</button>{" "}
                        {e.outcome === "COMMITTED" && <button className="btn primary" onClick={()=>downloadCapsule(e.id)} data-testid={`btn-capsule-${e.id}`}>capsule</button>}
                      </>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          }
          {detail && (
            <div className="card" style={{marginTop:12, background:"var(--bg)"}} data-testid="effect-detail">
              <div className="card-title">Effect result · {detail.action_id}
                <button className="btn" style={{float:"right"}} onClick={()=>setDetail(null)} data-testid="btn-close-detail">close</button>
              </div>
              <pre className="mono small" style={{whiteSpace:"pre-wrap", margin:0, color:"var(--text)"}}>
{JSON.stringify(detail.result, null, 2)}
              </pre>
            </div>
          )}
        </div>
        <div className="card">
          <div className="card-title">Propose effect</div>
          <form onSubmit={submit} data-testid="propose-effect-form">
            <div className="form-row"><label>vera</label>
              <select value={form.vera_id} onChange={e=>setForm({...form, vera_id: e.target.value})} required data-testid="eff-vera">
                <option value="">— pick VERA —</option>
                {veras.filter(v=>v.state==="ACTIVE").map(v => <option key={v.id} value={v.id}>{v.display_name}</option>)}
              </select>
            </div>
            <div className="form-row"><label>session (optional)</label>
              <select value={form.session_id} onChange={e=>setForm({...form, session_id: e.target.value})} data-testid="eff-session">
                <option value="">— none —</option>
                {sessions.filter(s=>s.state==="OPEN" && s.vera_id === form.vera_id).map(s => <option key={s.id} value={s.id}>{short(s.id)}</option>)}
              </select>
            </div>
            <div className="form-row"><label>capability_required</label><input value={form.capability_required} onChange={e=>setForm({...form, capability_required: e.target.value})} data-testid="eff-cap"/></div>
            <div className="form-row"><label>payload (JSON)</label>
              <textarea value={form.payload} onChange={e=>setForm({...form, payload: e.target.value})} data-testid="eff-payload"/>
              <div className="small">
                <code>{"{\"use_nexus_demo\":true}"}</code> runs the bundled pure-compute module through the live Nexus daemon.
                Supply <code>wasm_b64</code> or <code>wasm_path</code> for custom modules.
              </div>
            </div>
            <button className="btn primary" type="submit" data-testid="btn-propose-effect">Propose</button>
          </form>
        </div>
      </div>
    </>
  );
}

// ============= R6 Evidence =============
function Evidence() {
  const [entries, setEntries] = useState([]);
  const [verify, setVerify] = useState(null);
  const load = async () => { setEntries(await DCA.listEvidence()); setVerify(await DCA.verifyEvidence()); };
  useEffect(() => { load(); const t = setInterval(load, 4000); return () => clearInterval(t); }, []);
  return (
    <>
      <PageHead
        title="R6 /::/ Evidence, Verification & Recovery"
        sub="context-kernel lineage · hash-chained · replayable · external to self-report"
        right={verify && <span className={verify.broken_at ? "err mono" : "ok mono"}>
          {verify.broken_at ? `broken at seq ${verify.broken_at}` : `verified ${verify.verified_entries} entries`}
        </span>}
      />
      <div className="card">
        {entries.length === 0 ? <div className="empty">No evidence yet. Seed demo to see the chain populate.</div> :
          <table className="table" data-testid="evidence-table">
            <thead><tr><th>Seq</th><th>Kind</th><th>Subject</th><th>Payload</th><th>Prev</th><th>Self</th></tr></thead>
            <tbody>
              {entries.map(e => (
                <tr key={e.id} data-testid={`evidence-row-${e.seq}`}>
                  <td className="mono accent">#{e.seq}</td>
                  <td className="mono">{e.kind}</td>
                  <td className="mono">{short(e.subject_id)}</td>
                  <td className="small mono">{JSON.stringify(e.payload)}</td>
                  <td><span className="hash">{e.prev_hash === "GENESIS" ? "GENESIS" : e.prev_hash.slice(0,16)+"…"}</span></td>
                  <td><span className="hash">{e.self_hash.slice(0,16)}…</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        }
      </div>
    </>
  );
}

// ============= R7 Sessions =============
function Sessions() {
  const [veras, setVeras] = useState([]);
  const [placements, setPlacements] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [form, setForm] = useState({ vera_id: "", placement_id: "" });
  const [handoffForm, setHandoffForm] = useState({ session_id: "", handoff_to_vera_id: "" });
  const load = async () => { setVeras(await DCA.listVeras()); setPlacements(await DCA.listPlacements()); setSessions(await DCA.listSessions()); };
  useEffect(() => { load(); }, []);
  const openS = async (e) => { e.preventDefault(); if(!form.vera_id||!form.placement_id) return; await DCA.openSession(form); setForm({vera_id:"",placement_id:""}); load(); };
  const doHandoff = async (e) => { e.preventDefault(); if(!handoffForm.session_id||!handoffForm.handoff_to_vera_id) return; await DCA.handoff(handoffForm); setHandoffForm({session_id:"",handoff_to_vera_id:""}); load(); };
  return (
    <>
      <PageHead title="R7 /::/ Coordination & Interconnect" sub="authenticated sessions · handoffs preserve participant separation" />
      <div className="grid grid-2" style={{gridTemplateColumns:"1fr 360px"}}>
        <div className="card">
          {sessions.length === 0 ? <div className="empty">No sessions yet.</div> :
            <table className="table" data-testid="sessions-table">
              <thead><tr><th>ID</th><th>VERA</th><th>Placement</th><th>State</th><th>Handoff→</th><th></th></tr></thead>
              <tbody>
                {sessions.map(s => (
                  <tr key={s.id} data-testid={`session-row-${s.id}`}>
                    <td className="mono">{short(s.id)}</td>
                    <td className="mono">{short(s.vera_id)}</td>
                    <td className="mono">{short(s.placement_id)}</td>
                    <td><Badge v={s.state}/></td>
                    <td className="mono">{short(s.handoff_to)}</td>
                    <td>{s.state === "OPEN" && <button className="btn" onClick={async()=>{await DCA.closeSession(s.id); load();}} data-testid={`btn-close-${s.id}`}>close</button>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          }
        </div>
        <div>
          <div className="card" style={{marginBottom:16}}>
            <div className="card-title">Open session</div>
            <form onSubmit={openS} data-testid="open-session-form">
              <div className="form-row"><label>vera</label>
                <select value={form.vera_id} onChange={e=>setForm({...form, vera_id: e.target.value})} required data-testid="sess-vera">
                  <option value="">— pick VERA —</option>
                  {veras.filter(v=>v.state==="ACTIVE").map(v => <option key={v.id} value={v.id}>{v.display_name}</option>)}
                </select>
              </div>
              <div className="form-row"><label>placement (leased to this VERA)</label>
                <select value={form.placement_id} onChange={e=>setForm({...form, placement_id: e.target.value})} required data-testid="sess-placement">
                  <option value="">— pick placement —</option>
                  {placements.filter(p=>p.state==="ACTIVE" && p.vera_id === form.vera_id).map(p => <option key={p.id} value={p.id}>{p.computer_id}</option>)}
                </select>
              </div>
              <button className="btn primary" type="submit" data-testid="btn-open-session">Open</button>
            </form>
          </div>
          <div className="card">
            <div className="card-title">Handoff to another VERA</div>
            <form onSubmit={doHandoff} data-testid="handoff-form">
              <div className="form-row"><label>session</label>
                <select value={handoffForm.session_id} onChange={e=>setHandoffForm({...handoffForm, session_id: e.target.value})} required data-testid="handoff-session">
                  <option value="">— pick session —</option>
                  {sessions.filter(s=>s.state==="OPEN").map(s => <option key={s.id} value={s.id}>{short(s.id)}</option>)}
                </select>
              </div>
              <div className="form-row"><label>to VERA</label>
                <select value={handoffForm.handoff_to_vera_id} onChange={e=>setHandoffForm({...handoffForm, handoff_to_vera_id: e.target.value})} required data-testid="handoff-target">
                  <option value="">— pick target —</option>
                  {veras.filter(v=>v.state==="ACTIVE").map(v => <option key={v.id} value={v.id}>{v.display_name}</option>)}
                </select>
              </div>
              <button className="btn primary" type="submit" data-testid="btn-handoff">Handoff</button>
            </form>
          </div>
        </div>
      </div>
    </>
  );
}

// ============= Regency Console =============
function RegencyConsole() {
  const [veras, setVeras] = useState([]);
  const [mandates, setMandates] = useState([]);
  const [roles, setRoles] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [mForm, setMForm] = useState({ title: "", description: "", envelope: '{"max_daily_effects":100}' });
  const [rForm, setRForm] = useState({ name: "", capabilities: "effect:wasm.run,effect:http.fetch", mandate_id: "" });
  const [aForm, setAForm] = useState({ vera_id: "", role_id: "" });
  const [suspendSet, setSuspendSet] = useState(new Set());
  const [suspendReason, setSuspendReason] = useState("");
  const [lastResult, setLastResult] = useState(null);

  const load = async () => {
    setVeras(await DCA.listVeras());
    setMandates(await Regency.listMandates());
    setRoles(await Regency.listRoles());
    setAssignments(await Regency.listAssignments());
  };
  useEffect(() => { load(); }, []);

  const createMandate = async (e) => {
    e.preventDefault(); if (!mForm.title) return;
    let envelope = {}; try { envelope = JSON.parse(mForm.envelope); } catch { alert("envelope must be JSON"); return; }
    await Regency.createMandate({ title: mForm.title, description: mForm.description, envelope });
    setMForm({ title: "", description: "", envelope: '{"max_daily_effects":100}' }); load();
  };
  const createRole = async (e) => {
    e.preventDefault(); if (!rForm.name) return;
    const caps = rForm.capabilities.split(",").map(s=>s.trim()).filter(Boolean);
    await Regency.createRole({ name: rForm.name, capabilities: caps, mandate_id: rForm.mandate_id || null });
    setRForm({ name: "", capabilities: "effect:wasm.run,effect:http.fetch", mandate_id: "" }); load();
  };
  const assignRole = async (e) => {
    e.preventDefault(); if (!aForm.vera_id || !aForm.role_id) return;
    await Regency.assignRole(aForm); setAForm({ vera_id: "", role_id: "" }); load();
  };
  const toggleSuspend = (id) => {
    const n = new Set(suspendSet);
    if (n.has(id)) n.delete(id); else n.add(id);
    setSuspendSet(n);
  };
  const emergencySuspend = async () => {
    if (suspendSet.size === 0 || !suspendReason) return;
    if (!window.confirm(`Emergency-suspend ${suspendSet.size} VERA(s)? Cascades: grants→SUSPENDED, placements→FENCED.`)) return;
    const r = await Regency.emergencySuspend({ vera_ids: [...suspendSet], reason: suspendReason });
    setLastResult(r); setSuspendSet(new Set()); setSuspendReason(""); load();
  };

  return (
    <>
      <PageHead title="The Regency /::/ Governance"
        sub="Regency Console · human-facing client · bounded authority · not an authority root" />

      <div className="effect-boundary-note" data-testid="regency-boundary">
        <strong>Regency locks</strong> · Regency Console cannot promise instantaneous global stop across
        partitions (Foundation §6). Emergency suspension requests suspension/revocation; reachable
        enforcement points act. Regency Core supersedes Aeon as the product-facing engine name (ADR-024).
      </div>

      <div className="grid grid-2" style={{gridTemplateColumns:"1fr 1fr"}}>
        {/* Mandates */}
        <div className="card" data-testid="mandates-card">
          <div className="card-title">Mandates · governing instruments</div>
          {mandates.length === 0 ? <div className="empty">No mandates yet.</div> :
            <table className="table" data-testid="mandates-table">
              <thead><tr><th>Title</th><th>Envelope</th><th>State</th></tr></thead>
              <tbody>
                {mandates.map(m => (
                  <tr key={m.id} data-testid={`mandate-row-${m.id}`}>
                    <td>{m.title}<div className="small muted">{m.description}</div></td>
                    <td className="small mono">{JSON.stringify(m.envelope)}</td>
                    <td><Badge v={m.state}/></td>
                  </tr>
                ))}
              </tbody>
            </table>
          }
          <form onSubmit={createMandate} style={{marginTop:12}} data-testid="mandate-form">
            <div className="form-row"><label>title</label><input value={mForm.title} onChange={e=>setMForm({...mForm, title: e.target.value})} required data-testid="mandate-title"/></div>
            <div className="form-row"><label>description</label><input value={mForm.description} onChange={e=>setMForm({...mForm, description: e.target.value})} data-testid="mandate-desc"/></div>
            <div className="form-row"><label>envelope (JSON)</label><textarea value={mForm.envelope} onChange={e=>setMForm({...mForm, envelope: e.target.value})} data-testid="mandate-envelope"/></div>
            <button className="btn primary" type="submit" data-testid="btn-create-mandate">Create mandate</button>
          </form>
        </div>

        {/* Roles */}
        <div className="card" data-testid="roles-card">
          <div className="card-title">Roles · capability bundles</div>
          {roles.length === 0 ? <div className="empty">No roles yet.</div> :
            <table className="table" data-testid="roles-table">
              <thead><tr><th>Name</th><th>Capabilities</th><th>Mandate</th></tr></thead>
              <tbody>
                {roles.map(r => (
                  <tr key={r.id} data-testid={`role-row-${r.id}`}>
                    <td className="mono accent">{r.name}</td>
                    <td><div className="pill-line">{r.capabilities.map(c=><span className="pill" key={c}>{c}</span>)}</div></td>
                    <td className="small mono">{short(r.mandate_id)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          }
          <form onSubmit={createRole} style={{marginTop:12}} data-testid="role-form">
            <div className="form-row"><label>name</label><input value={rForm.name} onChange={e=>setRForm({...rForm, name: e.target.value})} required data-testid="role-name"/></div>
            <div className="form-row"><label>capabilities (csv)</label><input value={rForm.capabilities} onChange={e=>setRForm({...rForm, capabilities: e.target.value})} data-testid="role-caps"/></div>
            <div className="form-row"><label>mandate (optional)</label>
              <select value={rForm.mandate_id} onChange={e=>setRForm({...rForm, mandate_id: e.target.value})} data-testid="role-mandate">
                <option value="">— none —</option>
                {mandates.map(m => <option key={m.id} value={m.id}>{m.title}</option>)}
              </select>
            </div>
            <button className="btn primary" type="submit" data-testid="btn-create-role">Create role</button>
          </form>
        </div>
      </div>

      <hr className="divider" />

      {/* Assignments */}
      <div className="card" data-testid="assignments-card">
        <div className="card-title">Role assignments · materialize as R4 grants</div>
        {assignments.length === 0 ? <div className="empty">No role assignments yet.</div> :
          <table className="table" data-testid="assignments-table">
            <thead><tr><th>VERA</th><th>Role</th><th>Assigned by</th><th>State</th></tr></thead>
            <tbody>
              {assignments.map(a => {
                const vera = veras.find(v => v.id === a.vera_id);
                const role = roles.find(r => r.id === a.role_id);
                return <tr key={a.id} data-testid={`assignment-row-${a.id}`}>
                  <td>{vera?.display_name || short(a.vera_id)}</td>
                  <td className="mono accent">{role?.name || short(a.role_id)}</td>
                  <td className="mono small">{a.assigned_by}</td>
                  <td><Badge v={a.state}/></td>
                </tr>;
              })}
            </tbody>
          </table>
        }
        <form onSubmit={assignRole} style={{marginTop:12, display:"flex", gap:12, flexWrap:"wrap"}} data-testid="assign-form">
          <select value={aForm.vera_id} onChange={e=>setAForm({...aForm, vera_id: e.target.value})} required data-testid="assign-vera" style={{flex:1, minWidth:180, background:"var(--bg)",color:"var(--text)",border:"1px solid var(--border)",padding:"8px 12px",borderRadius:3, fontFamily:"var(--mono)"}}>
            <option value="">— pick VERA —</option>
            {veras.filter(v=>v.state==="ACTIVE").map(v => <option key={v.id} value={v.id}>{v.display_name}</option>)}
          </select>
          <select value={aForm.role_id} onChange={e=>setAForm({...aForm, role_id: e.target.value})} required data-testid="assign-role" style={{flex:1, minWidth:180, background:"var(--bg)",color:"var(--text)",border:"1px solid var(--border)",padding:"8px 12px",borderRadius:3, fontFamily:"var(--mono)"}}>
            <option value="">— pick role —</option>
            {roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
          <button className="btn primary" type="submit" data-testid="btn-assign">Assign</button>
        </form>
      </div>

      <hr className="divider" />

      {/* Emergency Suspend */}
      <div className="card" style={{borderColor:"var(--err)"}} data-testid="emergency-card">
        <div className="card-title" style={{color:"var(--err)"}}>Emergency suspension</div>
        <div className="small muted" style={{marginBottom:12}}>
          Select ACTIVE VERAs to suspend. Cascades: VERA→SUSPENDED, all ACTIVE grants→SUSPENDED,
          all ACTIVE placements→FENCED with epoch bump. Every action emits an evidence entry.
        </div>
        <table className="table" data-testid="suspend-table">
          <thead><tr><th style={{width:32}}></th><th>VERA</th><th>Mandate</th><th>State</th></tr></thead>
          <tbody>
            {veras.map(v => (
              <tr key={v.id} data-testid={`suspend-row-${v.id}`}>
                <td><input type="checkbox" checked={suspendSet.has(v.id)} onChange={()=>toggleSuspend(v.id)} disabled={v.state!=="ACTIVE"} data-testid={`suspend-check-${v.id}`}/></td>
                <td>{v.display_name} <span className="small mono muted">({short(v.id)})</span></td>
                <td className="small">{v.mandate}</td>
                <td><Badge v={v.state}/></td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{display:"flex", gap:12, marginTop:12, alignItems:"center"}}>
          <input placeholder="reason (required)" value={suspendReason} onChange={e=>setSuspendReason(e.target.value)} style={{flex:1, background:"var(--bg)",color:"var(--text)",border:"1px solid var(--border)",padding:"8px 12px",borderRadius:3, fontFamily:"var(--mono)"}} data-testid="suspend-reason"/>
          <button className="btn danger" onClick={emergencySuspend} disabled={suspendSet.size===0||!suspendReason} data-testid="btn-emergency-suspend">
            Emergency-suspend {suspendSet.size || ""}
          </button>
        </div>
        {lastResult && (
          <div style={{marginTop:12, padding:12, background:"var(--bg)", border:"1px solid var(--border)", borderRadius:3}} data-testid="suspend-result">
            <div className="small accent mono">Enforcement report</div>
            <pre className="mono small" style={{margin:"6px 0 0 0", whiteSpace:"pre-wrap", color:"var(--text)"}}>{JSON.stringify(lastResult, null, 2)}</pre>
          </div>
        )}
      </div>
    </>
  );
}

// ============= Packages =============
const PACKAGES = [
  { name: "floks-pc", role: "R2 · Environment & Runtime Continuity", lineage: "Agent Computer cloud (Runloop devbox v1)", origin: "Adaptive-Liquidity/floks-pc", lang: "TypeScript" },
  { name: "aeon-iq", role: "R3 · Durable State & Memory", lineage: "MemoryOS transparent OpenAI proxy", origin: "Adaptive-Liquidity/AEON-IQ-temp", lang: "Rust" },
  { name: "nexus", role: "R5 · Effectful Execution", lineage: "Capability-gated WASM/WASI snap-rollback sandbox", origin: "Adaptive-Liquidity/Nexus-temp", lang: "Rust/WASM" },
  { name: "nexus-iq", role: "R5+R6 · Self-host + proof capsules", lineage: "Provider-keyless self-host for Nexus + optional AEON plane", origin: "Adaptive-Liquidity/Nexus-IQ-temp", lang: "Shell/Docker" },
  { name: "genesis", role: "R1+R4 · Identity + Authority", lineage: "AEON Agent Runtime — signed identities, attenuation, revocation", origin: "Adaptive-Liquidity/genesis-runtime", lang: "Rust" },
  { name: "context-kernel", role: "R6 · Context provenance + Evidence", lineage: "Verifier-issued context provenance & hash-chained trace", origin: "Adaptive-Liquidity/aeon-context-kernel", lang: "Python 3.12" },
];

function Packages() {
  return (
    <>
      <PageHead title="Packages" sub={`Six-package DCA reference · combined at packages/*`} />
      <div className="card">
        <table className="table" data-testid="packages-table">
          <thead><tr><th>Name</th><th>Role</th><th>Lineage</th><th>Language</th><th>Origin</th></tr></thead>
          <tbody>
            {PACKAGES.map(p => (
              <tr key={p.name} data-testid={`pkg-row-${p.name}`}>
                <td className="mono accent">{p.name}</td>
                <td className="mono">{p.role}</td>
                <td>{p.lineage}</td>
                <td className="mono small">{p.lang}</td>
                <td className="mono small"><a href={`https://github.com/${p.origin}`} target="_blank" rel="noreferrer">{p.origin}</a></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="effect-boundary-note">
        <strong>Isolation rule</strong> — per <span className="mono">floks-pc/AUTHORITY.md</span>: no package modifies another. The orchestrator
        (this app) provides the integration surface without editing package internals.
      </div>
    </>
  );
}

// ============= App =============
export default function App() {
  return (
    <BrowserRouter>
      <div className="shell">
        <Sidebar />
        <main className="main">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/veras" element={<Veras />} />
            <Route path="/placements" element={<Placements />} />
            <Route path="/memory" element={<Memory />} />
            <Route path="/authority" element={<Authority />} />
            <Route path="/effects" element={<Effects />} />
            <Route path="/evidence" element={<Evidence />} />
            <Route path="/sessions" element={<Sessions />} />
            <Route path="/regency" element={<RegencyConsole />} />
            <Route path="/packages" element={<Packages />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
