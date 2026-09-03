import { api } from "@/lib/api";

// Lightweight curriculum fetcher — modules cache in-memory.
let _cache = null;
let _pending = null;

export async function fetchCurriculum() {
  if (_cache) return _cache;
  if (_pending) return _pending;
  _pending = api.get("/curriculum").then(({ data }) => {
    _cache = data.curriculum || [];
    _pending = null;
    return _cache;
  }).catch((e) => { _pending = null; throw e; });
  return _pending;
}

export function invalidateCurriculumCache() { _cache = null; }
