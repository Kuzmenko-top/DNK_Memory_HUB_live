-- DNK Git Research — PostgreSQL + pgvector schema (повна структура)
-- Запуск: psql -d <db> -f db/schema.sql
-- Структура за рекомендацією ментора: 3 шари даних (raw метадані, похідні сигнали, семантичний шар)

CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- repositories — Шар 1: Сирі метадані з GitHub API + Шар 2: Похідні сигнали
-- ============================================
CREATE TABLE IF NOT EXISTS repositories (
    id          SERIAL PRIMARY KEY,
    -- Ідентифікація
    full_name   VARCHAR(255) UNIQUE NOT NULL,
    name        VARCHAR(255),
    url         TEXT,
    owner_type  VARCHAR(20),                -- user | organization
    -- Опис
    description TEXT,
    language    VARCHAR(100),               -- primary language
    languages_breakdown JSONB DEFAULT '{}', -- {"Python": 75.5, "JS": 24.5}
    license     VARCHAR(100),               -- SPDX ID
    topics      TEXT[]      DEFAULT '{}',
    -- Популярність
    stars       INTEGER     DEFAULT 0,
    forks       INTEGER     DEFAULT 0,
    watchers    INTEGER     DEFAULT 0,
    -- Активність
    pushed_at   TIMESTAMP,
    days_since_push INTEGER,
    latest_release_tag  VARCHAR(100),
    latest_release_date TIMESTAMP,
    release_cadence_days INTEGER,           -- avg днів між релізами
    -- Спільнота
    contributors_count INTEGER,
    -- Quality signals (з tree)
    has_tests   BOOLEAN     DEFAULT FALSE,
    has_ci      BOOLEAN     DEFAULT FALSE,
    has_changelog BOOLEAN   DEFAULT FALSE,
    -- Текстові артефакти
    readme_text TEXT,
    tree_text   TEXT,
    -- Шар 2: Похідні сигнали (комп'ютимо самі)
    newness_score      FLOAT,               -- 0-1, нормалізований за віком
    maintenance_status VARCHAR(20),         -- active | maintained | dormant | abandoned
    popularity_tier    VARCHAR(20),         -- viral | popular | niche | obscure
    license_permissions JSONB DEFAULT '{}', -- {commercial_use, derivative_works, patent_grant, copyleft}
    -- Часові поля
    saved_at    TIMESTAMP   DEFAULT NOW(),
    updated_at  TIMESTAMP   DEFAULT NOW()
);

-- ============================================
-- dossiers — Шар 3: Семантичний (LLM-генерований)
-- ============================================
CREATE TABLE IF NOT EXISTS dossiers (
    id                    SERIAL PRIMARY KEY,
    repository_id         INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
    -- Базова семантика
    stack                 TEXT,
    readiness             VARCHAR(50),
    summary_ua            TEXT,
    domain                VARCHAR(100),
    target_audience       VARCHAR(255),
    -- DNK-специфічні скоринги
    dnk_fit_score         FLOAT   DEFAULT 0,
    dnk_fit_reason        TEXT,
    dnk_total_score       FLOAT   DEFAULT 0,
    recommendation        VARCHAR(100),
    -- Можливості та обмеження
    capabilities          TEXT[]  DEFAULT '{}', -- список функцій
    use_cases             TEXT[]  DEFAULT '{}',
    integrations          TEXT[]  DEFAULT '{}', -- з чим стикується
    limitations           TEXT[]  DEFAULT '{}', -- де слабкий
    -- Інтеграція
    integration_complexity VARCHAR(50),
    integration_notes     TEXT,
    deployment_hints      TEXT,
    key_dependencies      TEXT[]  DEFAULT '{}',
    -- Модулі (для декомпозиції) — КЛЮЧОВЕ ПОЛЕ
    -- [{name, path, files: [...], purpose, reusable, dependencies}]
    key_modules           JSONB   DEFAULT '[]',
    -- Метадані аналізу
    analyzed_at           TIMESTAMP DEFAULT NOW(),
    model_used            VARCHAR(100)
);

-- ============================================
-- embeddings — для семантичного пошуку (768 dims = Gemini)
-- ============================================
CREATE TABLE IF NOT EXISTS embeddings (
    id            SERIAL PRIMARY KEY,
    repository_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
    embedding     vector(768),
    created_at    TIMESTAMP DEFAULT NOW()
);

-- Індекси
CREATE INDEX IF NOT EXISTS idx_repos_stars        ON repositories(stars DESC);
CREATE INDEX IF NOT EXISTS idx_repos_maintenance  ON repositories(maintenance_status);
CREATE INDEX IF NOT EXISTS idx_repos_popularity   ON repositories(popularity_tier);
CREATE INDEX IF NOT EXISTS idx_dossiers_repo_id   ON dossiers(repository_id);
CREATE INDEX IF NOT EXISTS idx_dossiers_domain    ON dossiers(domain);
CREATE INDEX IF NOT EXISTS idx_dossiers_score     ON dossiers(dnk_total_score DESC);
CREATE INDEX IF NOT EXISTS idx_dossiers_readiness ON dossiers(readiness);
CREATE INDEX IF NOT EXISTS idx_dossiers_modules_gin ON dossiers USING gin(key_modules);
CREATE INDEX IF NOT EXISTS idx_repos_fts ON repositories
    USING gin(to_tsvector('english', coalesce(name,'') || ' ' || coalesce(description,'')));

-- Векторний індекс для embeddings (cosine similarity)
-- CREATE INDEX idx_embeddings_vector ON embeddings
--     USING ivfflat (embedding vector_cosine_ops) WITH (lists = 16);
