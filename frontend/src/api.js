import axios from "axios";
const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API });

export const DCA = {
  status: () => api.get("/dca/status").then(r => r.data),
  seed: () => api.post("/dca/seed").then(r => r.data),
  memoryStatus: () => api.get("/dca/memory/status").then(r => r.data),
  pubkey: () => api.get("/dca/orchestrator/pubkey").then(r => r.data),

  // R1
  listVeras: () => api.get("/dca/veras").then(r => r.data),
  createVera: (b) => api.post("/dca/veras", b).then(r => r.data),
  suspendVera: (id) => api.post(`/dca/veras/${id}/suspend`).then(r => r.data),
  decommissionVera: (id) => api.post(`/dca/veras/${id}/decommission`).then(r => r.data),

  // R2
  listPlacements: () => api.get("/dca/placements").then(r => r.data),
  leasePlacement: (b) => api.post("/dca/placements/lease", b).then(r => r.data),
  fencePlacement: (id) => api.post(`/dca/placements/${id}/fence`).then(r => r.data),

  // R3
  writeMemory: (b) => api.post("/dca/memory", b).then(r => r.data),
  recallMemory: (veraId, q, mode = "auto") =>
    api.get(`/dca/memory/recall/${veraId}`, { params: { ...(q ? { q } : {}), mode } }).then(r => r.data),

  // R4
  listGrants: (veraId) =>
    api.get("/dca/authority/grants", { params: veraId ? { vera_id: veraId } : {} }).then(r => r.data),
  issueGrant: (b) => api.post("/dca/authority/grants", b).then(r => r.data),
  revokeGrant: (id) => api.post(`/dca/authority/grants/${id}/revoke`).then(r => r.data),

  // R5
  listEffects: (veraId) =>
    api.get("/dca/effects", { params: veraId ? { vera_id: veraId } : {} }).then(r => r.data),
  proposeEffect: (b) => api.post("/dca/effects/propose", b).then(r => r.data),
  dispatchEffect: (id) => api.post(`/dca/effects/${id}/dispatch`).then(r => r.data),
  createCapsule: (id) => api.post(`/dca/effects/${id}/capsule`).then(r => r.data),
  capsuleDownloadUrl: (id) => `${API}/dca/capsules/${id}`,

  // R6
  listEvidence: (subjectId, limit = 100) =>
    api.get("/dca/evidence", { params: { subject_id: subjectId, limit } }).then(r => r.data),
  verifyEvidence: () => api.get("/dca/evidence/verify").then(r => r.data),

  // R7
  listSessions: () => api.get("/dca/sessions").then(r => r.data),
  openSession: (b) => api.post("/dca/sessions/open", b).then(r => r.data),
  closeSession: (id) => api.post(`/dca/sessions/${id}/close`).then(r => r.data),
  handoff: (b) => api.post("/dca/sessions/handoff", b).then(r => r.data),
};

// Regency (governance)
export const Regency = {
  listMandates: () => api.get("/regency/mandates").then(r => r.data),
  createMandate: (b) => api.post("/regency/mandates", b).then(r => r.data),
  listRoles: () => api.get("/regency/roles").then(r => r.data),
  createRole: (b) => api.post("/regency/roles", b).then(r => r.data),
  listAssignments: () => api.get("/regency/assignments").then(r => r.data),
  assignRole: (b) => api.post("/regency/assignments", b).then(r => r.data),
  emergencySuspend: (b) => api.post("/regency/emergency-suspend", b).then(r => r.data),
};
