/**
 * Tipos del contrato v1 de la API FECNA (FastAPI).
 *
 * Reflejan exactamente las claves devueltas por `api/routers/*.py` — no
 * inventar campos aquí; si la API cambia, actualizar este archivo primero.
 */

// --- /catalogs -------------------------------------------------------------

export interface CatalogEntry {
  id: string;
  nombre: string;
}

export interface CatalogsResponse {
  pruebas: CatalogEntry[];
  categorias: CatalogEntry[];
  piscinas: string[];
  generos: string[];
}

// --- /rankings ---------------------------------------------------------------

export interface RankingItem {
  pos: number;
  swimmer_id: string;
  swimmer_name: string;
  time: string;
  time_ms: number;
  club: string;
  league: string;
  date: string;
}

export interface RankingResponse {
  event_id: string;
  total: number;
  items: RankingItem[];
}

// --- /swimmers/search ----------------------------------------------------------

export interface SwimmerSearchItem {
  swimmer_id: string;
  swimmer_name: string;
  club: string;
  league: string;
}

export interface SwimmerSearchResponse {
  items: SwimmerSearchItem[];
}

// --- /swimmers/{id} ------------------------------------------------------------

export interface SwimmerTopEvent {
  event_id: string;
  event_name: string;
  pool: string;
  best_ms: number;
  best_time: string;
  national_rank: number;
  national_total: number;
  league_rank: number;
  league_total: number;
}

export interface SwimmerProfile {
  swimmer_id: string;
  swimmer_name: string;
  gender: string;
  age: number;
  league: string;
  club: string;
  birth_date: string | null;
  reference_year: number;
  top_events: SwimmerTopEvent[];
}

// --- /swimmers/{id}/history ------------------------------------------------------

export interface SwimmerHistoryItem {
  date: string;
  time: string;
  time_ms: number;
  event_id: string;
  event_name: string;
  pool: string;
}

export interface SwimmerHistoryResponse {
  items: SwimmerHistoryItem[];
}

// --- /competitions -------------------------------------------------------------

export interface CompetitionSummary {
  id: number;
  name: string;
  pool_type: string;
  loaded_at: string;
  entradas: number;
}

export interface CompetitionsResponse {
  items: CompetitionSummary[];
}

// --- /competitions/{id}/schedule y /alerts (misma forma de entrada) --------------

export interface ScheduleItem {
  date: string;
  session_no: number;
  start_time: string | null;
  event_number: number;
  event_label: string;
  category: string;
  heat: number;
  lane: number;
  swimmer_name: string;
  club_code: string;
  seed: string | null;
  seed_ms: number | null;
  swimmer_id: string | null;
}

export interface ScheduleResponse {
  items: ScheduleItem[];
}

// --- /competitions/{id}/clubs ----------------------------------------------------

export interface CompetitionClubsResponse {
  items: string[];
}

// --- /competitions/{id}/swimmers --------------------------------------------------

export interface CompetitionSwimmerItem {
  swimmer_name: string;
  club_code: string;
}

export interface CompetitionSwimmersResponse {
  items: CompetitionSwimmerItem[];
}

// --- /competitions/{id}/watch (GET/PUT) -------------------------------------------

export interface WatchResponse {
  names: string[];
}

export interface WatchBody {
  names: string[];
}

// --- /competitions (POST, admin) --------------------------------------------------

export interface CompetitionUploadResponse {
  competition_id: number;
  status: string;
  entradas: number;
  cruzados: number;
}

// --- /auth/register, /auth/login ------------------------------------------------

export type UserRole = "user" | "admin";

export interface AuthResponse {
  token: string;
  email: string;
  role: UserRole;
}

export interface Credentials {
  email: string;
  password: string;
}

// --- /auth/me ------------------------------------------------------------------

export interface MeResponse {
  email: string;
  role: UserRole;
}

// --- /ask ------------------------------------------------------------------------

export interface AskBody {
  question: string;
  context?: Record<string, unknown> | null;
}

export interface AskResponse {
  reply: string;
  context: Record<string, unknown> | null;
}

// --- /health -----------------------------------------------------------------------

export interface HealthResponse {
  status: string;
  [key: string]: unknown;
}
