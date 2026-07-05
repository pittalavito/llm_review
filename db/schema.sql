-- =============================================================================
-- LLM Review — Run Records Relational Schema (proposta, design-only)
-- =============================================================================
-- Scopo:
--   Modello dati SQL molto normalizzato per analizzare le review via query
--   strutturate, prepopolare il grafo con mock reali di run storici e supportare
--   interrogazioni multi-campo (modello, temperatura, decisione, rating, ecc.).
--
-- Note di portabilita':
--   - Scritto in stile ANSI, compatibile con SQLite (target semplice) e adattabile
--     a PostgreSQL. Dove i tipi differiscono sono indicati con commenti.
--   - I timestamp sono memorizzati come TEXT ISO-8601 (coerente con i JSON attuali).
--   - Le colonne *_json conservano il payload/trace completo per audit e flessibilita'
--     evolutiva (schema payload potenzialmente in evoluzione); i campi frequenti sono
--     invece normalizzati in colonne dedicate e indicizzate.
--   - Enum modellati con CHECK per restare portabili (in PostgreSQL si possono
--     convertire in tipi ENUM nativi).
--
-- SQLite: abilitare le foreign key ad ogni connessione.
PRAGMA foreign_keys = ON;

-- =============================================================================
-- 1. RUN — un record per esecuzione del grafo di review
-- =============================================================================
CREATE TABLE run (
    run_id            TEXT PRIMARY KEY,             -- es. "2026-04-21T14-32-00_paper-name"
    timestamp         TEXT NOT NULL,                -- ISO-8601 UTC
    paper_path        TEXT NOT NULL,
    run_description   TEXT,                          -- nullable per retrocompat legacy
    decision          TEXT
        CHECK (decision IS NULL OR decision IN
            ('accept', 'minor_revision', 'major_revision', 'reject')),
    total_rounds      INTEGER NOT NULL DEFAULT 0,
    max_rounds        INTEGER,                       -- da graph_config.max_rounds
    graph_config_json TEXT,                          -- graph_config completo (audit/replay)
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_run_timestamp   ON run (timestamp);
CREATE INDEX idx_run_decision    ON run (decision);
CREATE INDEX idx_run_paper_path  ON run (paper_path);

-- =============================================================================
-- 2. RUN_AGENT_CONFIG — configurazione LLM per singolo agente (1:N con run)
-- =============================================================================
CREATE TABLE run_agent_config (
    id                                 INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id                             TEXT NOT NULL
        REFERENCES run (run_id) ON DELETE CASCADE,
    agent_name                         TEXT NOT NULL
        CHECK (agent_name IN
            ('reviewer_1', 'reviewer_2', 'reviewer_3',
             'meta_reviewer', 'area_chair', 'author_agent')),
    model                              TEXT NOT NULL,      -- LlmModelName (es. "gpt-4o-mini")
    temperature                        REAL NOT NULL,
    -- Reviewer persona (solo per reviewer_1/2/3, altrimenti NULL)
    reviewer_persona_commitment        TEXT
        CHECK (reviewer_persona_commitment IS NULL OR
               reviewer_persona_commitment IN ('responsible', 'irresponsible')),
    reviewer_persona_intention         TEXT
        CHECK (reviewer_persona_intention IS NULL OR
               reviewer_persona_intention IN ('benign', 'malicious')),
    reviewer_persona_knowledgeability  TEXT
        CHECK (reviewer_persona_knowledgeability IS NULL OR
               reviewer_persona_knowledgeability IN ('knowledgeable', 'unknowledgeable')),
    reviewer_persona_focus             TEXT
        CHECK (reviewer_persona_focus IS NULL OR
               reviewer_persona_focus IN ('soundness', 'empirical', 'novelty')),
    -- Area chair style (solo per area_chair, altrimenti NULL)
    area_chair_style                   TEXT
        CHECK (area_chair_style IS NULL OR
               area_chair_style IN ('authoritarian', 'conformist', 'inclusive')),
    UNIQUE (run_id, agent_name)
);

CREATE INDEX idx_agent_config_run     ON run_agent_config (run_id);
CREATE INDEX idx_agent_config_model   ON run_agent_config (model, temperature);
CREATE INDEX idx_agent_config_agent   ON run_agent_config (agent_name);

-- =============================================================================
-- 3. AGENT_RUN — ogni singola invocazione di un agente (1:N con run)
-- =============================================================================
CREATE TABLE agent_run (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id                TEXT NOT NULL
        REFERENCES run (run_id) ON DELETE CASCADE,
    agent_name            TEXT NOT NULL
        CHECK (agent_name IN
            ('reviewer_1', 'reviewer_2', 'reviewer_3',
             'meta_reviewer', 'area_chair', 'author_agent')),
    round_index           INTEGER NOT NULL,          -- 0-based (round_offset gia' applicato)
    sequence_index        INTEGER NOT NULL,          -- ordine di invocazione nel run
    input_message         TEXT NOT NULL,
    context_used          TEXT,                       -- chunk RAG iniettati (se presenti)
    response_payload_json TEXT NOT NULL,              -- payload strutturato completo
    UNIQUE (run_id, sequence_index)
);

CREATE INDEX idx_agent_run_run        ON agent_run (run_id);
CREATE INDEX idx_agent_run_agent      ON agent_run (run_id, agent_name, round_index);

-- =============================================================================
-- 4. REVIEWER_REVIEW — review strutturata di un reviewer (1:N con run)
-- =============================================================================
CREATE TABLE reviewer_review (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id                   TEXT NOT NULL
        REFERENCES run (run_id) ON DELETE CASCADE,
    agent_run_id             INTEGER
        REFERENCES agent_run (id) ON DELETE SET NULL,
    reviewer_agent           TEXT NOT NULL
        CHECK (reviewer_agent IN ('reviewer_1', 'reviewer_2', 'reviewer_3')),
    round_index              INTEGER NOT NULL,
    summary                  TEXT NOT NULL,
    significance_and_novelty TEXT NOT NULL,
    rating                   INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 10),
    confidence               INTEGER NOT NULL CHECK (confidence BETWEEN 1 AND 5),
    payload_json             TEXT NOT NULL             -- ReviewerResponse completo
);

CREATE INDEX idx_reviewer_review_run     ON reviewer_review (run_id);
CREATE INDEX idx_reviewer_review_scores  ON reviewer_review (reviewer_agent, rating, confidence);

-- 4b. REVIEWER_REVIEW_POINT — liste normalizzate (accettazione/rifiuto/suggerimenti)
CREATE TABLE reviewer_review_point (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id  INTEGER NOT NULL
        REFERENCES reviewer_review (id) ON DELETE CASCADE,
    kind       TEXT NOT NULL
        CHECK (kind IN ('acceptance', 'rejection', 'suggestion')),
    position   INTEGER NOT NULL,                       -- ordine nella lista
    text       TEXT NOT NULL
);

CREATE INDEX idx_review_point_review  ON reviewer_review_point (review_id, kind);

-- =============================================================================
-- 5. META_REVIEW — aggregazione delle review (0..1 per run)
-- =============================================================================
CREATE TABLE meta_review (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         TEXT NOT NULL UNIQUE
        REFERENCES run (run_id) ON DELETE CASCADE,
    agent_run_id   INTEGER
        REFERENCES agent_run (id) ON DELETE SET NULL,
    summary        TEXT NOT NULL,
    overall_score  INTEGER NOT NULL CHECK (overall_score BETWEEN 1 AND 10),
    recommendation TEXT NOT NULL
        CHECK (recommendation IN
            ('accept', 'minor_revision', 'major_revision', 'reject')),
    payload_json   TEXT NOT NULL
);

CREATE INDEX idx_meta_review_reco  ON meta_review (recommendation, overall_score);

-- 5b. META_REVIEW_KEY_POINT — key_points normalizzati
CREATE TABLE meta_review_key_point (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    meta_review_id  INTEGER NOT NULL
        REFERENCES meta_review (id) ON DELETE CASCADE,
    position        INTEGER NOT NULL,
    text            TEXT NOT NULL
);

-- =============================================================================
-- 6. AREA_CHAIR_RESPONSE — decisione finale vincolante (0..1 per run)
-- =============================================================================
CREATE TABLE area_chair_response (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        TEXT NOT NULL UNIQUE
        REFERENCES run (run_id) ON DELETE CASCADE,
    agent_run_id  INTEGER
        REFERENCES agent_run (id) ON DELETE SET NULL,
    summary       TEXT NOT NULL,
    justification TEXT NOT NULL,
    decision      TEXT NOT NULL
        CHECK (decision IN
            ('accept', 'minor_revision', 'major_revision', 'reject')),
    confidence    INTEGER NOT NULL CHECK (confidence BETWEEN 1 AND 5),
    payload_json  TEXT NOT NULL
);

CREATE INDEX idx_area_chair_decision  ON area_chair_response (decision, confidence);

-- =============================================================================
-- 7. AUTHOR_RESPONSE — rebuttal dell'autore (0..1 per run)
-- =============================================================================
CREATE TABLE author_response (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        TEXT NOT NULL UNIQUE
        REFERENCES run (run_id) ON DELETE CASCADE,
    agent_run_id  INTEGER
        REFERENCES agent_run (id) ON DELETE SET NULL,
    rebuttal      TEXT NOT NULL,
    payload_json  TEXT NOT NULL
);

-- 7b. AUTHOR_REVIEWER_REBUTTAL — risposte mirate per reviewer (1:N)
CREATE TABLE author_reviewer_rebuttal (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    author_response_id  INTEGER NOT NULL
        REFERENCES author_response (id) ON DELETE CASCADE,
    position            INTEGER NOT NULL,
    reviewer_name       TEXT NOT NULL,                -- es. "reviewer_1"
    response            TEXT NOT NULL
);

CREATE INDEX idx_author_rebuttal_parent  ON author_reviewer_rebuttal (author_response_id);

-- 7c. AUTHOR_REVISED_SECTION — sezioni riviste del paper (1:N)
CREATE TABLE author_revised_section (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    author_response_id  INTEGER NOT NULL
        REFERENCES author_response (id) ON DELETE CASCADE,
    position            INTEGER NOT NULL,
    section_name        TEXT NOT NULL,
    content             TEXT NOT NULL
);

CREATE INDEX idx_author_section_parent  ON author_revised_section (author_response_id);

-- 7d. AUTHOR_KEY_CHANGE — elenco delle modifiche chiave (1:N)
CREATE TABLE author_key_change (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    author_response_id  INTEGER NOT NULL
        REFERENCES author_response (id) ON DELETE CASCADE,
    position            INTEGER NOT NULL,
    text                TEXT NOT NULL
);

CREATE INDEX idx_author_key_change_parent  ON author_key_change (author_response_id);

-- =============================================================================
-- 8. RETRIEVAL_RUN_METADATA — metadati retrieval a livello di run (0..1)
-- =============================================================================
CREATE TABLE retrieval_run_metadata (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id                 TEXT NOT NULL UNIQUE
        REFERENCES run (run_id) ON DELETE CASCADE,
    paper_path             TEXT,
    index_status           TEXT,                       -- es. "reused", "built", "skipped"
    chunk_count_total      INTEGER,
    chunk_count_retrieved  INTEGER,
    top_k                  INTEGER,
    metadata_json          TEXT                         -- retrieval_metadata completo
);

CREATE INDEX idx_retrieval_index_status  ON retrieval_run_metadata (index_status);

-- =============================================================================
-- 9. AGENT_RUN_PROMPT_TRACE — traccia prompt per invocazione (0..1 per agent_run)
-- =============================================================================
CREATE TABLE agent_run_prompt_trace (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_run_id   INTEGER NOT NULL UNIQUE
        REFERENCES agent_run (id) ON DELETE CASCADE,
    system_prompt  TEXT,
    human_prompt   TEXT,
    full_prompt    TEXT,
    trace_json     TEXT NOT NULL                        -- prompt_trace completo (template/rendered/schema)
);

-- =============================================================================
-- 10. AGENT_RUN_RUNTIME_TRACE — metriche runtime per invocazione (0..1)
-- =============================================================================
CREATE TABLE agent_run_runtime_trace (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_run_id       INTEGER NOT NULL UNIQUE
        REFERENCES agent_run (id) ON DELETE CASCADE,
    llm_class          TEXT,                            -- es. "ChatOllama", "ChatOpenAI"
    llm_model          TEXT,
    llm_temperature    REAL,
    started_at         TEXT,                            -- ISO-8601
    ended_at           TEXT,                            -- ISO-8601
    latency_ms         REAL,
    prompt_tokens      INTEGER,                         -- da provider_usage (se disponibile)
    completion_tokens  INTEGER,
    total_tokens       INTEGER,
    trace_json         TEXT NOT NULL                    -- runtime_trace completo (provider_usage/metadata raw)
);

CREATE INDEX idx_runtime_trace_model    ON agent_run_runtime_trace (llm_model);
CREATE INDEX idx_runtime_trace_latency  ON agent_run_runtime_trace (latency_ms);

-- =============================================================================
-- 11. AGENT_RUN_RETRIEVAL — dettaglio retrieval per invocazione (0..1)
-- =============================================================================
CREATE TABLE agent_run_retrieval (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_run_id   INTEGER NOT NULL UNIQUE
        REFERENCES agent_run (id) ON DELETE CASCADE,
    provider       TEXT,                                -- es. "RetrievalContextProvider"
    paper_path     TEXT,
    base_query     TEXT,
    query_suffix   TEXT,
    resolved_query TEXT
);

CREATE INDEX idx_agent_retrieval_paper  ON agent_run_retrieval (paper_path);

-- =============================================================================
-- 12. RUN_REVIEW_RAW — compatibilita' legacy (reviews come stringhe JSON)
-- =============================================================================
-- Conserva l'array `reviews` storico (stringhe JSON) per riconciliazione durante
-- la migrazione graduale (dual-read/dual-write) e per i consumer legacy (docs SPA).
CREATE TABLE run_review_raw (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT NOT NULL
        REFERENCES run (run_id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,                       -- indice nell'array originale
    review_json TEXT NOT NULL                            -- stringa JSON originale
);

CREATE INDEX idx_run_review_raw_run  ON run_review_raw (run_id);

-- =============================================================================
-- VISTE ANALYTICS — accelerano le interrogazioni ricorrenti
-- =============================================================================

-- V1. Panoramica per run con esito e metadati retrieval
CREATE VIEW v_run_overview AS
SELECT
    r.run_id,
    r.timestamp,
    r.paper_path,
    r.run_description,
    r.decision,
    r.total_rounds,
    r.max_rounds,
    mr.overall_score          AS meta_overall_score,
    mr.recommendation         AS meta_recommendation,
    ac.decision               AS area_chair_decision,
    ac.confidence             AS area_chair_confidence,
    rm.index_status,
    rm.chunk_count_total,
    rm.chunk_count_retrieved,
    rm.top_k
FROM run r
LEFT JOIN meta_review            mr ON mr.run_id = r.run_id
LEFT JOIN area_chair_response    ac ON ac.run_id = r.run_id
LEFT JOIN retrieval_run_metadata rm ON rm.run_id = r.run_id;

-- V2. Punteggi reviewer con configurazione modello/temperatura/persona
CREATE VIEW v_reviewer_scores AS
SELECT
    rr.run_id,
    r.timestamp,
    r.paper_path,
    rr.reviewer_agent,
    rr.round_index,
    rr.rating,
    rr.confidence,
    cfg.model,
    cfg.temperature,
    cfg.reviewer_persona_focus,
    cfg.reviewer_persona_commitment,
    cfg.reviewer_persona_intention,
    cfg.reviewer_persona_knowledgeability
FROM reviewer_review rr
JOIN run r        ON r.run_id = rr.run_id
LEFT JOIN run_agent_config cfg
    ON cfg.run_id = rr.run_id AND cfg.agent_name = rr.reviewer_agent;

-- V3. Performance per invocazione agente (latenza/modello per agente e round)
CREATE VIEW v_agent_performance AS
SELECT
    ar.run_id,
    r.timestamp,
    ar.agent_name,
    ar.round_index,
    ar.sequence_index,
    rt.llm_class,
    rt.llm_model,
    rt.llm_temperature,
    rt.latency_ms,
    rt.prompt_tokens,
    rt.completion_tokens,
    rt.total_tokens
FROM agent_run ar
JOIN run r ON r.run_id = ar.run_id
LEFT JOIN agent_run_runtime_trace rt ON rt.agent_run_id = ar.id;

-- V4. Relazione configurazione modello/temperatura vs decisione finale del run
CREATE VIEW v_model_decision AS
SELECT
    cfg.run_id,
    r.timestamp,
    r.paper_path,
    cfg.agent_name,
    cfg.model,
    cfg.temperature,
    r.decision                AS run_decision,
    ac.decision               AS area_chair_decision
FROM run_agent_config cfg
JOIN run r ON r.run_id = cfg.run_id
LEFT JOIN area_chair_response ac ON ac.run_id = cfg.run_id;
