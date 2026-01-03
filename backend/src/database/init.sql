DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ifsi_app') THEN
    CREATE ROLE ifsi_app LOGIN PASSWORD 'admin';
  END IF;
END$$;


DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE p.proname = 'set_updated_at' AND n.nspname = 'public'
  ) THEN
    CREATE FUNCTION public.set_updated_at() RETURNS trigger
    LANGUAGE plpgsql AS $BODY$
    BEGIN
      NEW.updated_at := NOW();
      RETURN NEW;
    END;
    $BODY$;
  END IF;
END$$;


-- Schemas
DO $$
DECLARE
  s text;
BEGIN
  FOREACH s IN ARRAY ARRAY[
    'public','content','core','academics','learning','media',
    'comms','news','ai','revision','analytics','training' , 'anatomy'
  ]
  LOOP
    BEGIN
      EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', s);
    EXCEPTION
      WHEN invalid_schema_name THEN
        NULL;
    END;
  END LOOP;
END $$;

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS pgcrypto      WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS unaccent      WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS pg_trgm       WITH SCHEMA public;


CREATE TABLE IF NOT EXISTS public.users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  first_name VARCHAR(100),
  last_name  VARCHAR(100),
  pseudo     VARCHAR(100) UNIQUE,
  phone_number VARCHAR(20),
  address_line1 TEXT,
  address_line2 TEXT,
  postal_code VARCHAR(20),
  city   VARCHAR(100),
  country VARCHAR(100),
  date_of_birth DATE,
  profile_picture_url TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_email  ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_active ON public.users(is_active);
DROP TRIGGER IF EXISTS trg_users_updated ON public.users;
CREATE TRIGGER trg_users_updated
BEFORE UPDATE ON public.users
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TABLE IF NOT EXISTS public.roles (
  id SERIAL PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_roles_code ON public.roles(code);
DROP TRIGGER IF EXISTS trg_roles_updated ON public.roles;
CREATE TRIGGER trg_roles_updated
BEFORE UPDATE ON public.roles
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TABLE IF NOT EXISTS public.permissions (
  id SERIAL PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
DROP TRIGGER IF EXISTS trg_permissions_updated ON public.permissions;
CREATE TRIGGER trg_permissions_updated
BEFORE UPDATE ON public.permissions
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TABLE IF NOT EXISTS public.user_roles (
  user_id INT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  role_id INT NOT NULL REFERENCES public.roles(id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS public.role_permissions (
  role_id INT NOT NULL REFERENCES public.roles(id) ON DELETE CASCADE,
  permission_id INT NOT NULL REFERENCES public.permissions(id) ON DELETE CASCADE,
  PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS public.sessions (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_expires ON public.sessions(user_id, expires_at);

CREATE TABLE IF NOT EXISTS content.categories (
  id   SERIAL PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_cat_code_nonvide CHECK (length(btrim(code)) > 0)
);
DROP TRIGGER IF EXISTS trg_cat_upd ON content.categories;
CREATE TRIGGER trg_cat_upd
BEFORE UPDATE ON content.categories
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TABLE IF NOT EXISTS media.assets (
  id          SERIAL PRIMARY KEY,
  kind        TEXT NOT NULL CHECK (kind IN ('image','video','pdf','audio','other')),
  storage_key TEXT NOT NULL UNIQUE,
  mime_type   TEXT NOT NULL,
  bytes_size  INT CHECK (bytes_size IS NULL OR bytes_size >= 0),
  width_px    INT CHECK (width_px IS NULL OR width_px > 0),
  height_px   INT CHECK (height_px IS NULL OR height_px > 0),
  duration_ms INT CHECK (duration_ms IS NULL OR duration_ms >= 0),
  alt_text    TEXT,
  created_by  INT REFERENCES public.users(id) ON DELETE SET NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_assets_kind    ON media.assets(kind);
CREATE INDEX IF NOT EXISTS idx_assets_created ON media.assets(created_at DESC);

CREATE TABLE IF NOT EXISTS media.asset_variants (
  id           SERIAL PRIMARY KEY,
  asset_id     INT NOT NULL REFERENCES media.assets(id) ON DELETE CASCADE,
  variant_key  TEXT NOT NULL,
  storage_key  TEXT NOT NULL UNIQUE,
  mime_type    TEXT NOT NULL,
  width_px     INT CHECK (width_px IS NULL OR width_px > 0),
  height_px    INT CHECK (height_px IS NULL OR height_px > 0),
  bitrate_kbps INT CHECK (bitrate_kbps IS NULL OR bitrate_kbps > 0),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (asset_id, variant_key)
);
CREATE INDEX IF NOT EXISTS idx_asset_variants_asset ON media.asset_variants(asset_id);

CREATE TABLE IF NOT EXISTS media.entity_assets (
  id          SERIAL PRIMARY KEY,
  entity_type TEXT NOT NULL CHECK (entity_type IN (
     'category','protocol','protocol_version',
     'checklist','checklist_run',
     'dose_calculation',
     'ue','course','lesson',
     'quiz','quiz_item',
     'favorite','user'
  )),
  entity_id   INT NOT NULL,
  asset_id    INT NOT NULL REFERENCES media.assets(id) ON DELETE CASCADE,
  role        TEXT,
  order_no    INT NOT NULL DEFAULT 0,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (entity_type, entity_id, asset_id)
);
CREATE INDEX IF NOT EXISTS idx_entity_assets_entity ON media.entity_assets(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_assets_asset  ON media.entity_assets(asset_id);

CREATE TABLE IF NOT EXISTS content.protocols (
  id            SERIAL PRIMARY KEY,
  category_id   INT REFERENCES content.categories(id) ON DELETE SET NULL,
  code          TEXT NOT NULL UNIQUE,
  title         TEXT NOT NULL,
  summary       TEXT,
  tags          TEXT[] NOT NULL DEFAULT '{}',
  is_published  BOOLEAN NOT NULL DEFAULT FALSE,
  created_by    INT REFERENCES public.users(id) ON DELETE SET NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  search_vector TSVECTOR,
  metadata      JSONB NOT NULL DEFAULT '{}'::jsonb,
  external_url  TEXT,
  thumbnail_asset_id INT REFERENCES media.assets(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_protocols_title_trgm ON content.protocols USING GIN (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_protocols_fts        ON content.protocols USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_protocols_published  ON content.protocols (is_published);
CREATE INDEX IF NOT EXISTS idx_protocols_tags_gin   ON content.protocols USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_protocols_meta_gin   ON content.protocols USING GIN (metadata);

DROP TRIGGER IF EXISTS trg_protocols_upd ON content.protocols;
CREATE TRIGGER trg_protocols_upd
BEFORE UPDATE ON content.protocols
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TABLE IF NOT EXISTS content.protocol_versions (
  id           SERIAL PRIMARY KEY,
  protocol_id  INT NOT NULL REFERENCES content.protocols(id) ON DELETE CASCADE,
  version      INT NOT NULL CHECK (version >= 1),
  body_md      TEXT NOT NULL,
  changelog    TEXT,
  published_at TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (protocol_id, version)
);

CREATE OR REPLACE FUNCTION content.fn_update_protocols_search_vector()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
  latest_body TEXT;
  tags_text   TEXT;
BEGIN
  SELECT pv.body_md
  INTO latest_body
  FROM content.protocol_versions pv
  WHERE pv.protocol_id = NEW.id
  ORDER BY COALESCE(pv.published_at, pv.created_at) DESC, pv.version DESC
  LIMIT 1;

  tags_text := array_to_string(NEW.tags, ' ');

  NEW.search_vector :=
      setweight(to_tsvector('simple', unaccent(coalesce(NEW.title,''))),   'A')
    || setweight(to_tsvector('simple', unaccent(coalesce(NEW.summary,''))), 'B')
    || setweight(to_tsvector('simple', unaccent(coalesce(tags_text,''))),   'B')
    || setweight(to_tsvector('simple', unaccent(coalesce(latest_body,''))), 'C');

  RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_protocols_fts ON content.protocols;
CREATE TRIGGER trg_protocols_fts
BEFORE INSERT OR UPDATE ON content.protocols
FOR EACH ROW EXECUTE FUNCTION content.fn_update_protocols_search_vector();

CREATE OR REPLACE FUNCTION content.fn_touch_protocol_on_new_version()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  UPDATE content.protocols SET updated_at = NOW() WHERE id = NEW.protocol_id;
  RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_touch_protocol ON content.protocol_versions;
CREATE TRIGGER trg_touch_protocol
AFTER INSERT OR UPDATE ON content.protocol_versions
FOR EACH ROW EXECUTE FUNCTION content.fn_touch_protocol_on_new_version();

CREATE TABLE IF NOT EXISTS content.checklists (
    id  SERIAL PRIMARY KEY,
    titre    TEXT NOT NULL,
    description   TEXT,
    items    JSONB NOT NULL,
    is_published  BOOLEAN NOT NULL DEFAULT TRUE,
    created_by INT REFERENCES public.users(id) ON DELETE SET NULL ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_chk_upd ON content.checklists;
CREATE TRIGGER trg_chk_upd BEFORE UPDATE ON content.checklists
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS content.checklist_runs(
    id   SERIAL PRIMARY KEY,
    checklist_id INT NOT NULL REFERENCES content.checklists(id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES public.users(id)   ON DELETE CASCADE,
    answers   JSONB NOT NULL,
    signed_by  TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS core.favorites (
    user_id INT NOT NULL REFERENCES public.users(id)  ON DELETE CASCADE,
    protocol_id INT NOT NULL REFERENCES content.protocols(id) ON DELETE CASCADE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, protocol_id)
);


CREATE INDEX IF NOT EXISTS idx_fav_user_created ON core.favorites(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS core.unit_conversions (
  id SERIAL PRIMARY KEY,
  from_unit TEXT NOT NULL,
  to_unit   TEXT NOT NULL,
  factor    NUMERIC NOT NULL, -- multiplier from_unit par factor => to_unit
  UNIQUE(from_unit, to_unit)
); 

CREATE TABLE IF NOT EXISTS core.drug_safety_rules (
  id SERIAL PRIMARY KEY,
  drug_id INT NOT NULL REFERENCES core.drugs(id) ON DELETE CASCADE,
  rule_type TEXT NOT NULL CHECK (rule_type IN ('MAX_PER_KG_PER_DAY','MAX_PER_DOSE','MIN_AGE_Y','MAX_AGE_Y')),
  value NUMERIC NOT NULL,
  unit  TEXT NULL,
  meta JSONB NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE(drug_id, rule_type)
);


CREATE TABLE core.dose_calculations (
    id        SERIAL PRIMARY KEY,
    user_id   INT REFERENCES public.users(id) ON DELETE SET NULL,

    context   TEXT NOT NULL DEFAULT 'FREE'
             CHECK (context IN ('FREE','TRAINING_EXERCISE','CLINICAL_CASE')),

    exercise_id INT NULL REFERENCES training.dose_exercises(id) ON DELETE SET NULL,
    case_id     INT NULL REFERENCES training.clinical_cases(id) ON DELETE SET NULL,

    patient_age_y NUMERIC CHECK(patient_age_y IS NULL OR patient_age_y >= 0),
    weight_kg     NUMERIC CHECK(weight_kg IS NULL OR weight_kg > 0),

    drug_name   TEXT NOT NULL,
    dose_input  JSONB NOT NULL,
    dose_result JSONB NOT NULL,

    notes      TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_drug_name_nonvide CHECK (length(btrim(drug_name)) > 0)
);

CREATE INDEX IF NOT EXISTS idx_dose_user_created
  ON core.dose_calculations(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_dose_context
  ON core.dose_calculations(context);

DROP TRIGGER IF EXISTS trg_dose_calculations_upd ON core.dose_calculations;
CREATE TRIGGER trg_dose_calculations_upd
BEFORE UPDATE ON core.dose_calculations
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


CREATE TABLE IF NOT EXISTS core.drugs(
  id     SERIAL PRIMARY KEY,
  name   TEXT NOT NULL UNIQUE,
  act_code   TEXT NULL, 
  default_unit    TEXT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::json,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.drug_presentations(
  id                  SERIAL PRIMARY KEY,
  drug_id             INT NOT NULL REFERENCES core.drugs(id) ON DELETE CASCADE,
  label               TEXT NOT NULL,
  concentration_value  NUMERIC NULL,
  concentration_unit   TEXT NULL,
  volume_ml            NUMERIC NULL,
  metadata             JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(drug_id, label)
);

CREATE INDEX IF NOT EXISTS idx_drug_presentations_drug
  ON core.drug_presentations(drug_id);


CREATE TABLE IF NOT EXISTS core.units (
  id SERIAL PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,     -- mg, g, mL, UI, mmol...
  kind TEXT NOT NULL CHECK (kind IN ('mass','volume','dose','time','rate','other')),
  to_base_factor NUMERIC,        -- ex: g -> mg = 1000
  base_code TEXT,                -- mg est la base du 'mass'
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.drug_safety_rules (
  id         SERIAL PRIMARY KEY,
  drug_id    INT NOT NULL REFERENCES core.drugs(id) ON DELETE CASCADE,

  rule_type  TEXT NOT NULL CHECK (rule_type IN (
    'MAX_DAILY',        -- dose max/jour
    'MAX_SINGLE',       -- dose max/prise
    'MAX_RATE',         -- débit max
    'MIN_INTERVAL',     -- intervalle min entre prises
    'MIN_AGE_Y',
    'MAX_AGE_Y'
  )),

  value      NUMERIC NOT NULL,
  unit       TEXT NULL,
  applies_to JSONB NOT NULL DEFAULT '{}'::jsonb, -- ex: {"age_min_y":0,"age_max_y":12,"weight_min_kg":3}

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(drug_id, rule_type)
);

CREATE INDEX IF NOT EXISTS idx_safety_rules_drug
  ON core.drug_safety_rules(drug_id);

-- =================== PROGRAMS / COHORTS / ENROLLMENTS ===================

CREATE TABLE IF NOT EXISTS academics.programs (
  id         SERIAL PRIMARY KEY,
  code       TEXT NOT NULL UNIQUE,
  label      TEXT NOT NULL,
  ects_total INT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS academics.cohorts (
  id         SERIAL PRIMARY KEY,
  program_id INT NOT NULL REFERENCES academics.programs(id) ON DELETE CASCADE,
  label      TEXT NOT NULL,
  year_start INT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (program_id, label)
);

CREATE TABLE IF NOT EXISTS academics.enrollments (
  id           SERIAL PRIMARY KEY,
  cohort_id    INT NOT NULL REFERENCES academics.cohorts(id) ON DELETE CASCADE,
  user_id      INT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  current_year SMALLINT NOT NULL CHECK (current_year BETWEEN 1 AND 3),
  current_sem  SMALLINT     CHECK (current_sem  BETWEEN 1 AND 6),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (cohort_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_enroll_user ON academics.enrollments(user_id);

-- =================== YEARS / SEMESTERS / UE ===================

CREATE TABLE IF NOT EXISTS academics.years (
  id         SERIAL PRIMARY KEY,
  program_id INT NOT NULL REFERENCES academics.programs(id) ON DELETE CASCADE,
  year_no    SMALLINT NOT NULL CHECK(year_no BETWEEN 1 AND 3),
  label      TEXT NOT NULL,
  ects       INT,
  UNIQUE(program_id, year_no)
);

CREATE TABLE IF NOT EXISTS academics.semesters (
  id         SERIAL PRIMARY KEY,
  program_id INT NOT NULL REFERENCES academics.programs(id) ON DELETE CASCADE,
  sem_no     SMALLINT NOT NULL CHECK(sem_no BETWEEN 1 AND 6),
  label      TEXT NOT NULL,
  year_no    SMALLINT NOT NULL CHECK(year_no BETWEEN 1 AND 3),
  UNIQUE (program_id, sem_no)
);

CREATE TABLE IF NOT EXISTS academics.ue (
  id          SERIAL PRIMARY KEY,
  program_id  INT NOT NULL REFERENCES academics.programs(id) ON DELETE CASCADE,
  code        TEXT NOT NULL,
  title       TEXT NOT NULL,
  year_no     SMALLINT NOT NULL CHECK(year_no BETWEEN 1 AND 3),
  sem_no      SMALLINT NOT NULL CHECK(sem_no BETWEEN 1 AND 6),
  ects        NUMERIC(4,1),
  description TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(program_id, code)
);

CREATE INDEX IF NOT EXISTS idx_ue_year_sem ON academics.ue(program_id, year_no, sem_no);

-- =================== COURSES ===================

CREATE TABLE IF NOT EXISTS academics.courses (
  id          SERIAL PRIMARY KEY,
  ue_id       INT  NOT NULL REFERENCES academics.ue(id) ON DELETE CASCADE,
  code        TEXT NOT NULL,                                 
  title       TEXT NOT NULL,
  description TEXT,
  order_no    INT  NOT NULL DEFAULT 0,

  doc_mode TEXT NOT NULL DEFAULT 'CLASSIC'
    CHECK (doc_mode IN ('CLASSIC','SLIDE','SEMI_MANUAL','MANUAL')),

  published_version_id INT NULL,

  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),             
  UNIQUE (ue_id, code)
);

CREATE INDEX IF NOT EXISTS idx_courses_ue            ON academics.courses(ue_id);
CREATE INDEX IF NOT EXISTS idx_courses_updated_at    ON academics.courses(updated_at);
CREATE INDEX IF NOT EXISTS idx_courses_order_per_ue  ON academics.courses(ue_id, order_no);
CREATE INDEX IF NOT EXISTS idx_courses_doc_mode       ON academics.courses(doc_mode);


DROP TRIGGER IF EXISTS trg_courses_touch_updated_at ON academics.courses;
CREATE TRIGGER trg_courses_touch_updated_at
BEFORE UPDATE ON academics.courses
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


CREATE TABLE IF NOT EXISTS academics.sources (
  id       SERIAL PRIMARY KEY,
  title    TEXT NOT NULL,
  year     INT,
 doc_mode    TEXT NOT NULL DEFAULT 'CLASSIC'
    CHECK (doc_mode IN ('CLASSIC','SLIDE','SEMI_MANUAL','MANUAL')),
  md5         TEXT UNIQUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS academics.source_files (
  id         SERIAL PRIMARY KEY,
  source_id  INT NOT NULL
             REFERENCES academics.sources(id) ON DELETE CASCADE,
  pdf_data   BYTEA NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (source_id)
);

CREATE INDEX IF NOT EXISTS idx_source_files_source_id
  ON academics.source_files(source_id);

CREATE TABLE IF NOT EXISTS academics.source_pages (
  id         SERIAL PRIMARY KEY,
  source_id  INT NOT NULL
             REFERENCES academics.sources(id) ON DELETE CASCADE,
  page_no    INT NOT NULL CHECK (page_no >= 1),
  text       TEXT,
  ocr_text   TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (source_id, page_no)
);

CREATE INDEX IF NOT EXISTS idx_source_pages_source_page
  ON academics.source_pages(source_id, page_no);



CREATE TABLE IF NOT EXISTS academics.page_media_assets (
  id         SERIAL PRIMARY KEY,

  source_id  INT NOT NULL
             REFERENCES academics.sources(id) ON DELETE CASCADE,

  page_no    INT NOT NULL CHECK (page_no >= 1),

  kind       TEXT NOT NULL
             CHECK (kind IN ('figure', 'image', 'manual', 'embedded')),

  mime       TEXT NOT NULL DEFAULT 'image/png',

  data       BYTEA,
  path       TEXT,

  md5        TEXT NOT NULL,

  bbox       JSONB,
  width      INT CHECK (width  IS NULL OR width  > 0),
  height     INT CHECK (height IS NULL OR height > 0),

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT chk_media_storage
    CHECK (
      (data IS NOT NULL AND path IS NULL)
      OR
      (data IS NULL AND path IS NOT NULL)
    )
);

-- Anti-doublons (très utile)
CREATE UNIQUE INDEX IF NOT EXISTS uq_media_assets_source_md5
  ON academics.page_media_assets(source_id, md5);

-- Index pour requêtes classiques
CREATE INDEX IF NOT EXISTS idx_media_assets_source_page
  ON academics.page_media_assets(source_id, page_no);

CREATE INDEX IF NOT EXISTS idx_media_assets_md5
  ON academics.page_media_assets(md5);


CREATE TABLE IF NOT EXISTS academics.course_versions (
  id            SERIAL PRIMARY KEY,
  course_id     INT NOT NULL REFERENCES academics.courses(id) ON DELETE CASCADE,
  version_label TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'draft'
    CHECK(status IN ('draft','published','archived')),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(course_id, version_label)
);

DROP TRIGGER IF EXISTS trg_course_versions_upd ON academics.course_versions;
CREATE TRIGGER trg_course_versions_upd
BEFORE UPDATE ON academics.course_versions
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TABLE IF NOT EXISTS academics.course_sources (
  id            SERIAL PRIMARY KEY,
  course_id     INT NOT NULL REFERENCES academics.courses(id) ON DELETE CASCADE,
  version_id    INT NULL REFERENCES academics.course_versions(id) ON DELETE SET NULL,
  source_id     INT NOT NULL REFERENCES academics.sources(id) ON DELETE CASCADE,

  role          TEXT NOT NULL DEFAULT 'PRIMARY'
                CHECK (role IN ('PRIMARY','SLIDES','HANDOUT','ANNEX','EXAMS','OTHER')),

  doc_mode      TEXT NOT NULL DEFAULT 'CLASSIC'
                CHECK (doc_mode IN ('CLASSIC','SLIDE','UNKNOWN')),

  images_policy TEXT NOT NULL DEFAULT 'AUTO'
                CHECK (images_policy IN ('AUTO','SEMI_MANUAL','PRUDENT')),

  language      TEXT NULL,
  is_primary    BOOLEAN NOT NULL DEFAULT FALSE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE(course_id, source_id, version_id, role)  -- La contrainte UNIQUE corrigée
);

CREATE INDEX IF NOT EXISTS idx_course_sources_course
  ON academics.course_sources(course_id);

CREATE INDEX IF NOT EXISTS idx_course_sources_source
  ON academics.course_sources(source_id);

CREATE INDEX IF NOT EXISTS idx_course_sources_course_version
  ON academics.course_sources(course_id, version_id);


CREATE TABLE IF NOT EXISTS academics.sections (
  id          SERIAL PRIMARY KEY,
  course_id   INT NOT NULL REFERENCES academics.courses(id) ON DELETE CASCADE,
  version_id  INT NOT NULL REFERENCES academics.course_versions(id) ON DELETE CASCADE,
  parent_id   INT REFERENCES academics.sections(id) ON DELETE CASCADE,
  position    INT NOT NULL DEFAULT 0,
  title       TEXT NOT NULL,
  content_md  TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sections_course_ver ON academics.sections(course_id, version_id);
CREATE INDEX IF NOT EXISTS idx_sections_parent_pos ON academics.sections(parent_id, position);

DROP TRIGGER IF EXISTS trg_sections_upd ON academics.sections;
CREATE TRIGGER trg_sections_upd
BEFORE UPDATE ON academics.sections
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TABLE IF NOT EXISTS academics.citations (
  id          SERIAL PRIMARY KEY,
  section_id  INT NOT NULL REFERENCES academics.sections(id) ON DELETE CASCADE,
  source_id   INT NOT NULL REFERENCES academics.sources(id) ON DELETE CASCADE,
  page_start  INT NOT NULL CHECK(page_start >= 1),
  page_end    INT NOT NULL CHECK(page_end >= page_start),
  quote       TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_citations_section ON academics.citations(section_id);
CREATE INDEX IF NOT EXISTS idx_citations_source_pages ON academics.citations(source_id, page_start, page_end);

CREATE TABLE IF NOT EXISTS academics.section_media (
  id            SERIAL PRIMARY KEY,
  section_id    INT NOT NULL REFERENCES academics.sections(id) ON DELETE CASCADE,
  media_asset_id INT NOT NULL REFERENCES academics.page_media_assets(id) ON DELETE CASCADE,
  position      INT NOT NULL DEFAULT 0,
  caption       TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(section_id, media_asset_id)
);

CREATE INDEX IF NOT EXISTS idx_section_media_section_pos ON academics.section_media(section_id, position);

-- =================== ANATOMY  ===================

CREATE TABLE IF NOT EXISTS anatomy.nodes (
  id SERIAL PRIMARY KEY,
  code TEXT UNIQUE,
  title TEXT NOT NULL,
  description_md TEXT,
  node_type TEXT NOT NULL DEFAULT 'STRUCTURE'
    CHECK (node_type IN ('SYSTEM','REGION','STRUCTURE','FUNCTION','CLINICAL')),
  tags TEXT[] NOT NULL DEFAULT '{}',
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_anatomy_nodes_tags
  ON anatomy.nodes USING GIN (tags);

CREATE TABLE IF NOT EXISTS anatomy.edges (
  parent_id INT NOT NULL REFERENCES anatomy.nodes(id) ON DELETE CASCADE,
  child_id  INT NOT NULL REFERENCES anatomy.nodes(id) ON DELETE CASCADE,
  relation  TEXT NOT NULL DEFAULT 'PART_OF'
    CHECK (relation IN ('PART_OF','CONNECTED_TO','SUPPLIES','INNERVATES','DRAINS','RELATED_TO')),
  PRIMARY KEY(parent_id, child_id, relation)
);

CREATE INDEX IF NOT EXISTS idx_anatomy_edges_parent ON anatomy.edges(parent_id);
CREATE INDEX IF NOT EXISTS idx_anatomy_edges_child  ON anatomy.edges(child_id);

CREATE TABLE IF NOT EXISTS academics.course_anatomy (
  id SERIAL PRIMARY KEY,
  course_id INT NOT NULL REFERENCES academics.courses(id) ON DELETE CASCADE,
  node_id   INT NOT NULL REFERENCES anatomy.nodes(id) ON DELETE CASCADE,
  importance INT NOT NULL DEFAULT 3 CHECK (importance BETWEEN 1 AND 5),
  UNIQUE(course_id, node_id)
);


-- =================== LEARNING (types normalisés) ===================
CREATE TABLE IF NOT EXISTS learning.quizzes (
    id    SERIAL PRIMARY KEY,
    titre   TEXT NOT NULL,
    tags    TEXT[] NOT NULL DEFAULT '{}',
    niveau   TEXT,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    mode     TEXT CHECK( mode IN ('entrainement', 'examen_blanc', 'diagnostic')) DEFAULT 'entrainement',
    duration_sec INT CHECK (duration_sec IS NULL OR duration_sec BETWEEN 30 AND 7200),
    pass_mark  NUMERIC(5, 2),
    shuffle_items BOOLEAN DEFAULT TRUE,
    shuffle_options BOOLEAN DEFAULT TRUE,
    attempts_limit INT ,
 created_by     INT REFERENCES public.users(id) ON DELETE SET NULL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quizzes_tags ON learning.quizzes USING GIN (tags);
DROP TRIGGER IF EXISTS trg_quizzes_upd ON learning.quizzes;
CREATE TRIGGER trg_quizzes_upd BEFORE UPDATE ON learning.quizzes
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS learning.quiz_items(
    id   SERIAL PRIMARY KEY,
    quiz_id INT NOT NULL REFERENCES learning.quizzes(id) ON DELETE CASCADE,
    type  TEXT NOT NULL CHECK(type IN('qcm', 'vf', 'carte')),
    question_md  TEXT NOT NULL,
    options_json JSONB,
    bonne_reponse JSONB,
    explication_md TEXT,
    ordre   INT NOT NULL DEFAULT 0,
    difficulty SMALLINT CHECK (difficulty BETWEEN 1 AND 5),
    tags  TEXT[] DEFAULT '{}',
    CONSTRAINT chk_qcm_options CHECK (
            (type <> 'qcm') OR (options_json IS NOT NULL AND jsonb_array_length(options_json) >= 2)
    )
);

CREATE INDEX IF NOT EXISTS idx_quiz_items_quiz ON learning.quiz_items(quiz_id);

CREATE TABLE IF NOT EXISTS learning.quiz_attempts (
  id SERIAL PRIMARY KEY,
  quiz_id INT NOT NULL REFERENCES learning.quizzes(id) ON DELETE CASCADE,
  user_id INT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ,
  score_raw INT,
  score_max INT,
  meta JSONB NOT NULL DEFAULT '{}'::jsonb
);


CREATE TABLE IF NOT EXISTS learning.quiz_answers(
    id   SERIAL PRIMARY KEY,
    attempt_id INT NOT NULL REFERENCES learning.quiz_attempts(id) ON DELETE CASCADE,
    item_id   INT NOT NULL REFERENCES learning.quiz_items(id) ON DELETE CASCADE,
    answers_json JSONB NOT NULL,
    is_correct BOOLEAN,
    responded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(attempt_id, item_id)
);

CREATE INDEX IF NOT EXISTS idx_answers_attempt ON learning.quiz_answers(attempt_id);

CREATE TABLE IF NOT EXISTS academics.ue_quizzes (
    id  SERIAL PRIMARY KEY,
    ue_id  INT REFERENCES academics.ue(id) ON DELETE CASCADE,
    quiz_id  INT NOT NULL REFERENCES learning.quizzes(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL CHECK(purpose IN ('diagnostic', 'entrainement', 'examen_blanc')),
    weight  NUMERIC(4, 2) NOT NULL DEFAULT 1.0,
    UNIQUE (ue_id, quiz_id, purpose)
);

CREATE INDEX IF NOT EXISTS idx_ue_quizzes_ue ON academics.ue_quizzes(ue_id);

CREATE TABLE IF NOT EXISTS academics.exam_types (
  code        TEXT PRIMARY KEY,
  label       TEXT NOT NULL,
  description TEXT NULL,
  is_active   BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS academics.exam_sessions (
  id            SERIAL PRIMARY KEY,
  course_id     INT NOT NULL
                REFERENCES academics.courses(id)
                ON DELETE CASCADE,

  title         TEXT NOT NULL,
  description   TEXT NULL,

  exam_type     TEXT NOT NULL DEFAULT 'EXAM'
                REFERENCES academics.exam_types(code),

  duration_min  INT NOT NULL CHECK (duration_min > 0),

  max_score     NUMERIC(5,2) NULL,
  pass_score    NUMERIC(5,2) NULL,

  is_active     BOOLEAN NOT NULL DEFAULT TRUE,

  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE(course_id, title)
);

CREATE INDEX IF NOT EXISTS idx_acad_exam_course
  ON academics.exam_sessions(course_id);

CREATE INDEX IF NOT EXISTS idx_acad_exam_type
  ON academics.exam_sessions(exam_type);

CREATE TABLE IF NOT EXISTS academics.exam_parts (
  id       SERIAL PRIMARY KEY,
  exam_id  INT NOT NULL REFERENCES academics.exam_sessions(id) ON DELETE CASCADE,
  quiz_id  INT NOT NULL REFERENCES learning.quizzes(id)       ON DELETE CASCADE,
  order_no INT NOT NULL DEFAULT 0,
  weight   NUMERIC(4,2) NOT NULL DEFAULT 1.0,

  UNIQUE (exam_id, order_no),
  UNIQUE (exam_id, quiz_id)
);

CREATE INDEX IF NOT EXISTS idx_exam_parts_exam
  ON academics.exam_parts(exam_id);

CREATE TABLE IF NOT EXISTS academics.exam_results (
  id          SERIAL PRIMARY KEY,
  exam_id     INT NOT NULL REFERENCES academics.exam_sessions(id) ON DELETE CASCADE,
  user_id     INT NOT NULL REFERENCES public.users(id)           ON DELETE CASCADE,

  score_raw   NUMERIC(6,2),
  score_max   NUMERIC(6,2),
  grade       TEXT,

  computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (exam_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_exam_results_user
  ON academics.exam_results(user_id, exam_id);

CREATE TABLE IF NOT EXISTS revision.entity_links (
  id SERIAL PRIMARY KEY,
  entity_type TEXT NOT NULL CHECK (entity_type IN ('flashcard','revision_sheet')),
  entity_id   INT NOT NULL,
  target_type TEXT NOT NULL CHECK (target_type IN ('course','lesson','ue','section','competency','anatomy_node')),
  target_id   INT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(entity_type, entity_id, target_type, target_id)
);

CREATE INDEX IF NOT EXISTS idx_rev_links_target
  ON revision.entity_links(target_type, target_id);


-- =================== REVISION (types normalisés) ===================
CREATE TABLE IF NOT EXISTS revision.revision_sheets(
  id     SERIAL PRIMARY KEY,
  course_id  INT NOT NULL REFERENCES academics.courses(id) ON DELETE CASCADE,
  version_id INT NULL REFERENCES academics.course_versions(id) ON DELETE SET NULL,

  title   TEXT NOT NULL,
   status      TEXT NOT NULL DEFAULT 'DRAFT'
              CHECK (status IN ('DRAFT','PUBLISHED','ARCHIVED')),

  content_md  TEXT NULL,

  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_revision_sheets_course
  ON revision.revision_sheets(course_id, version_id);

CREATE TABLE IF NOT EXISTS revision.revision_sheet_items (
  id        SERIAL PRIMARY KEY,
  sheet_id  INT NOT NULL REFERENCES revision.revision_sheets(id) ON DELETE CASCADE,

  item_type TEXT NOT NULL DEFAULT 'BULLET'
            CHECK (item_type IN ('BULLET','DEFINITION','FORMULA','STEP','WARNING','EXAMPLE','QA')),

  position  INT NOT NULL DEFAULT 1,
  title     TEXT NULL,
  body_md   TEXT NOT NULL,

  source_id    INT NULL REFERENCES academics.sources(id) ON DELETE SET NULL,
  page_start   INT NULL,
  page_end     INT NULL,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sheet_items_sheet
  ON revision.revision_sheet_items(sheet_id, position);


  CREATE TABLE IF NOT EXISTS revision.srs_schedules (
  id            SERIAL PRIMARY KEY,
  user_id       INT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  flashcard_id  INT NOT NULL REFERENCES revision.flashcards(id) ON DELETE CASCADE,
  interval_days INT NOT NULL DEFAULT 1,
  ease_factor   NUMERIC(4,2) NOT NULL DEFAULT 2.5,
  repetitions   INT NOT NULL DEFAULT 0,
  due_at        TIMESTAMPTZ NOT NULL,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, flashcard_id)
);

CREATE TABLE IF NOT EXISTS revision.srs_reviews (
  id           SERIAL PRIMARY KEY,
  user_id      INT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  flashcard_id INT NOT NULL REFERENCES revision.flashcards(id) ON DELETE CASCADE,
  quality      SMALLINT NOT NULL CHECK (quality BETWEEN 0 AND 5),
  reviewed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  meta         JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_srs_due
  ON revision.srs_schedules(user_id, due_at);

CREATE INDEX IF NOT EXISTS idx_srs_reviews_user_time
  ON revision.srs_reviews(user_id, reviewed_at DESC);

-- =================== LESSONS ===================

CREATE TABLE IF NOT EXISTS academics.lessons (
  id          SERIAL PRIMARY KEY,
  course_id   INT NOT NULL REFERENCES academics.courses(id) ON DELETE CASCADE,
  version_id  INT NULL REFERENCES academics.course_versions(id) ON DELETE SET NULL,

  lesson_type TEXT NOT NULL
              CHECK (lesson_type IN (
                'INTRO','CHAPTER','REVISION_SHEET','QUIZ','MOCK_EXAM','EXAM','RESOURCE'
              )),

  title       TEXT NOT NULL,
  position    INT  NOT NULL DEFAULT 1,

  content_md  TEXT NULL,

  root_section_id    INT NULL REFERENCES academics.sections(id) ON DELETE SET NULL,
  quiz_id            INT NULL REFERENCES learning.quizzes(id) ON DELETE SET NULL,
  exam_id            INT NULL REFERENCES academics.exam_sessions(id) ON DELETE SET NULL,
  revision_sheet_id  INT NULL REFERENCES revision.revision_sheets(id) ON DELETE SET NULL,

  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE(course_id, version_id, lesson_type, position)
);

CREATE INDEX IF NOT EXISTS idx_lessons_course
  ON academics.lessons(course_id);

CREATE INDEX IF NOT EXISTS idx_lessons_course_version
  ON academics.lessons(course_id, version_id);

CREATE INDEX IF NOT EXISTS idx_lessons_type
  ON academics.lessons(lesson_type);


CREATE TABLE IF NOT EXISTS academics.lesson_resources (
  id         SERIAL PRIMARY KEY,
  lesson_id  INT  NOT NULL REFERENCES academics.lessons(id) ON DELETE CASCADE,
  type       TEXT NOT NULL CHECK (type IN ('image','video','pdf','link','article','audio','protocol','quiz')),
  title      TEXT,
  url        TEXT,
  protocol_id INT REFERENCES content.protocols(id) ON DELETE SET NULL,
  quiz_id     INT,
  order_no    INT  NOT NULL DEFAULT 0,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lesson_res ON academics.lesson_resources(lesson_id);


 CREATE TABLE IF NOT EXISTS academics.competencies (
    id   SERIAL PRIMARY KEY,
    code  TEXT NOT NULL UNIQUE,
    label   TEXT NOT NULL,
    description TEXT
 );


CREATE TABLE IF NOT EXISTS academics.ue_competencies (
    id   SERIAL  PRIMARY KEY,
    ue_id  INT NOT NULL REFERENCES academics.ue(id) ON DELETE CASCADE,
    competency_id INT NOT NULL REFERENCES academics.competencies(id) ON DELETE CASCADE,
    UNIQUE(ue_id, competency_id)
);

CREATE TABLE IF NOT EXISTS academics.user_competencies (
    id    SERIAL PRIMARY KEY, 
    user_id  INT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    competency_id INT NOT NULL REFERENCES academics.competencies(id) ON DELETE CASCADE,
    source TEXT NOT NULL CHECK(source IN ('cours', 'stage','examen')),
    evidence_json JSONB NOT NULL DEFAULT '{}' ::jsonb,
    validated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, competency_id, source)
);

CREATE INDEX IF NOT EXISTS idx_user_comp_user ON academics.user_competencies(user_id);

CREATE TABLE IF NOT EXISTS academics.lesson_progress (
  id SERIAL PRIMARY KEY,
  lesson_id INT NOT NULL REFERENCES academics.lessons(id) ON DELETE CASCADE,
  user_id INT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  status TEXT NOT NULL CHECK (status IN ('non_commence','en_cours','termine','a_revoir')),
  last_score NUMERIC(5,2),
  attempts INT NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (lesson_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_lesson_prog_user ON academics.lesson_progress(user_id);

CREATE TABLE IF NOT EXISTS academics.prerequisites (
    id   SERIAL PRIMARY KEY,
    ue_id   INT REFERENCES academics.ue(id) ON DELETE CASCADE,
   requires_ue INT NOT NULL REFERENCES academics.ue(id) ON DELETE CASCADE,
  UNIQUE (ue_id, requires_ue),
  CHECK (ue_id <> requires_ue)
);

CREATE TABLE IF NOT EXISTS academics.ue_completion_rules (
    id     SERIAL PRIMARY KEY,
    ue_id   INT NOT NULL REFERENCES academics.ue(id) ON DELETE CASCADE,
    min_avg  NUMERIC(4, 2),
    required_competencies INT[] DEFAULT '{}',
    UNIQUE (ue_id)
);


CREATE OR REPLACE VIEW academics.v_user_ue_progress AS
SELECT
  u.id AS user_id,
  ue.id AS ue_id,
  ue.title AS ue_title,
  COUNT(DISTINCT l.id) AS total_lessons,
  COUNT(DISTINCT lp.id) FILTER (WHERE lp.status IN ('en_cours','termine')) AS started_lessons,
  COUNT(DISTINCT lp.id) FILTER (WHERE lp.status='termine') AS done_lessons
FROM public.users u
JOIN academics.enrollments e ON e.user_id = u.id
JOIN academics.cohorts co ON co.id = e.cohort_id
JOIN academics.ue ue ON ue.program_id = co.program_id
LEFT JOIN academics.courses c ON c.ue_id = ue.id
LEFT JOIN academics.lessons l ON l.course_id = c.id
LEFT JOIN academics.lesson_progress lp ON lp.lesson_id = l.id AND lp.user_id = u.id
GROUP BY u.id, ue.id, ue.title;

-- =================== TRAINING (types normalisés) ===================
CREATE TABLE IF NOT EXISTS training.dose_exercises (
  id           SERIAL PRIMARY KEY,
  title        TEXT NOT NULL,
  statement_md TEXT NOT NULL,

  exercise_type TEXT NOT NULL DEFAULT 'DOSE_BASIC'
    CHECK (exercise_type IN (
      'DOSE_BASIC',        -- ex mg/kg
      'DILUTION',          -- reconstitution / dilution
      'INFUSION_RATE',     -- débit ml/h, gouttes/min
      'CONCENTRATION',     -- mg/ml, UI/ml, etc.
      'PEDIATRIC',         -- pédiatrie (poids + sécurité)
      'UNIT_CONVERSION',   -- conversions
      'MIXED'              -- combo
    )),

  difficulty   INT NOT NULL DEFAULT 1 CHECK (difficulty BETWEEN 1 AND 10),
  tags         TEXT[] NOT NULL DEFAULT '{}',

  expected     JSONB NOT NULL DEFAULT '{}'::jsonb,
  solution_steps JSONB NOT NULL DEFAULT '[]'::jsonb,

  created_by   INT REFERENCES public.users(id) ON DELETE SET NULL,
  source       TEXT NOT NULL DEFAULT 'TEACHER'
              CHECK (source IN ('TEACHER','AI','IMPORT')),

  metadata     JSONB NOT NULL DEFAULT '{}'::jsonb,

  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dose_exercises_difficulty
  ON training.dose_exercises(difficulty);

CREATE INDEX IF NOT EXISTS idx_dose_exercises_type
  ON training.dose_exercises(exercise_type);

CREATE INDEX IF NOT EXISTS idx_dose_exercises_tags
  ON training.dose_exercises USING GIN (tags);

CREATE TABLE training.dose_attempts (
  id            SERIAL PRIMARY KEY,
  user_id       INT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  exercise_id   INT NOT NULL REFERENCES training.dose_exercises(id) ON DELETE CASCADE,

  submitted_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  submitted_value NUMERIC NULL,
  submitted_unit  TEXT NULL,

  is_correct    BOOLEAN NOT NULL DEFAULT FALSE,
  score         NUMERIC(5,2) NOT NULL DEFAULT 0,
  error_codes   TEXT[] NOT NULL DEFAULT '{}'::text[],

  ai_feedback_md TEXT NULL,

  calculation_id INT NULL REFERENCES core.dose_calculations(id) ON DELETE SET NULL,

  time_ms      INT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dose_attempts_user_time
  ON training.dose_attempts(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_dose_attempts_exercise
  ON training.dose_attempts(exercise_id);

CREATE TABLE IF NOT EXISTS training.clinical_cases (
  id          SERIAL PRIMARY KEY,
  title       TEXT NOT NULL,
  intro_md    TEXT NOT NULL,

  difficulty  INT NOT NULL DEFAULT 1 CHECK (difficulty BETWEEN 1 AND 10),
  tags        TEXT[] NULL,

  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS training.case_steps (
  id        SERIAL PRIMARY KEY,
  case_id   INT NOT NULL REFERENCES training.clinical_cases(id) ON DELETE CASCADE,
  position  INT NOT NULL DEFAULT 1,

  prompt_md TEXT NOT NULL,

  step_type TEXT NOT NULL DEFAULT 'MCQ'
            CHECK (step_type IN ('MCQ','FREE','CALC','DECISION')),

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE(case_id, position)
);

CREATE INDEX IF NOT EXISTS idx_case_steps_case_pos
  ON training.case_steps(case_id, position);

CREATE TABLE IF NOT EXISTS training.case_step_choices (
  id        SERIAL PRIMARY KEY,
  step_id   INT NOT NULL REFERENCES training.case_steps(id) ON DELETE CASCADE,
  position  INT NOT NULL DEFAULT 1,

  label     TEXT NOT NULL,
  is_correct BOOLEAN NOT NULL DEFAULT FALSE,
  feedback_md TEXT NULL,

  UNIQUE(step_id, position)
);
CREATE TABLE IF NOT EXISTS training.case_attempts (
  id        SERIAL PRIMARY KEY,
  user_id   INT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  case_id   INT NOT NULL REFERENCES training.clinical_cases(id) ON DELETE CASCADE,

  score     NUMERIC NOT NULL DEFAULT 0,
  completed BOOLEAN NOT NULL DEFAULT FALSE,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS training.case_step_answers (
  id          SERIAL PRIMARY KEY,
  attempt_id  INT NOT NULL REFERENCES training.case_attempts(id) ON DELETE CASCADE,
  step_id     INT NOT NULL REFERENCES training.case_steps(id) ON DELETE CASCADE,

  selected_choice_id INT NULL REFERENCES training.case_step_choices(id) ON DELETE SET NULL,
  free_answer_text   TEXT NULL,

  is_correct BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE(attempt_id, step_id)
);

CREATE TABLE IF NOT EXISTS training.level_tiers (
  id        SERIAL PRIMARY KEY,
  level     INT NOT NULL,
  tier      INT NOT NULL,
  xp_min    INT NOT NULL,
  xp_max    INT NOT NULL,

  unlock_rule JSONB NULL,

  UNIQUE(level, tier),
  UNIQUE(xp_min, xp_max)
);

CREATE TABLE IF NOT EXISTS training.dose_exercise_competencies (
  id            SERIAL PRIMARY KEY,
  exercise_id   INT NOT NULL REFERENCES training.dose_exercises(id) ON DELETE CASCADE,
  competency_id INT NOT NULL REFERENCES academics.competencies(id) ON DELETE CASCADE,
  weight        NUMERIC(4,2) NOT NULL DEFAULT 1.0,
  UNIQUE(exercise_id, competency_id)
);

CREATE INDEX IF NOT EXISTS idx_dose_ex_comp_ex
  ON training.dose_exercise_competencies(exercise_id);


CREATE TABLE training.dose_attempt_feedback (
  id          SERIAL PRIMARY KEY,
  attempt_id  INT NOT NULL REFERENCES training.dose_attempts(id) ON DELETE CASCADE,
  code        TEXT NOT NULL,
  severity    INT NOT NULL DEFAULT 1 CHECK (severity BETWEEN 1 AND 5),
  message_md  TEXT NOT NULL,
  meta        JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dose_feedback_attempt
  ON training.dose_attempt_feedback(attempt_id);

-- =================== COMMUNICATION    ===================

CREATE TABLE IF NOT EXISTS comms.threads (
    id   SERIAL PRIMARY KEY,
    thread_type TEXT NOT NULL CHECK(thread_type IN ('direct', 'group', 'cohort','course','lesson','support')),
    title TEXT,
    created_by INT REFERENCES public.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_activity TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS comms.thread_participants (
    thread_id INT NOT NULL REFERENCES comms.threads(id) ON DELETE CASCADE ,
    user_id INT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    role  TEXT CHECK (role IN ('owner', 'menber', 'moderator')),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (thread_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_threads_type_last
  ON comms.threads(thread_type, last_activity DESC);

CREATE INDEX IF NOT EXISTS idx_thread_participants_user
  ON comms.thread_participants(user_id);

CREATE TABLE IF NOT EXISTS comms.messages_shadow (
  id           SERIAL PRIMARY KEY,
  thread_id    INT NOT NULL REFERENCES comms.threads(id) ON DELETE CASCADE,
  user_id      INT REFERENCES public.users(id) ON DELETE SET NULL,
  mongo_msg_id TEXT NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  edited_at    TIMESTAMPTZ,
  deleted_at   TIMESTAMPTZ,
  UNIQUE (thread_id, mongo_msg_id)
);
CREATE INDEX IF NOT EXISTS idx_msgshadow_thread_created ON comms.messages_shadow(thread_id, created_at);
CREATE INDEX IF NOT EXISTS idx_msgshadow_user_created   ON comms.messages_shadow(user_id, created_at);

CREATE TABLE IF NOT EXISTS comms.message_attachments (
  id         SERIAL PRIMARY KEY,
  message_id INT NOT NULL REFERENCES comms.messages_shadow(id) ON DELETE CASCADE,
  asset_id   INT NOT NULL REFERENCES media.assets(id)          ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (message_id, asset_id)
);

CREATE TABLE IF NOT EXISTS comms.calls (
  id           SERIAL PRIMARY KEY,
  thread_id    INT REFERENCES comms.threads(id) ON DELETE SET NULL,
  created_by   INT REFERENCES public.users(id)  ON DELETE SET NULL,
  status       TEXT NOT NULL CHECK (status IN ('scheduled','ringing','live','ended','canceled')) DEFAULT 'scheduled',
  scheduled_at TIMESTAMPTZ,
  started_at   TIMESTAMPTZ,
  ended_at     TIMESTAMPTZ,
  signaling    JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_calls_status_time ON comms.calls(status, COALESCE(started_at, scheduled_at));
CREATE INDEX IF NOT EXISTS idx_calls_thread      ON comms.calls(thread_id);

CREATE TABLE IF NOT EXISTS comms.call_participants (
  call_id   INT NOT NULL REFERENCES comms.calls(id) ON DELETE CASCADE,
  user_id   INT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  role TEXT CHECK (role IN ('owner','member','moderator')),
  joined_at TIMESTAMPTZ,
  left_at   TIMESTAMPTZ,
  PRIMARY KEY (call_id, user_id)
);

CREATE TABLE IF NOT EXISTS comms.message_reactions (
  message_id INT NOT NULL REFERENCES comms.messages_shadow(id) ON DELETE CASCADE,
  user_id    INT NOT NULL REFERENCES public.users(id)          ON DELETE CASCADE,
  emoji      TEXT NOT NULL,
  reacted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (message_id, user_id, emoji)
);

CREATE TABLE IF NOT EXISTS news.feeds (
    id    SERIAL   PRIMARY KEY,
    name    TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    category TEXT,
    country  TEXT,
    language TEXT,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS news.articles (
    id      SERIAL PRIMARY KEY,
    feed_id INT REFERENCES news.feeds(id) ON DELETE SET NULL,
    title  TEXT NOT  NULL ,
    url TEXT  NOT NULL UNIQUE,
    published_at TIMESTAMPTZ,
    authors TEXT[],
    experct TEXT,
    content_md TEXT,
    topics TEXT[] NOT NULL DEFAULT '{}',
    importance SMALLINT CHECK (importance BETWEEN 1 AND 5),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS news.user_bookmarks (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  article_id INT NOT NULL REFERENCES news.articles(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, article_id)
);


CREATE TABLE IF NOT EXISTS ai.documents( 
    id     SERIAL PRIMARY KEY,
    owner_id INT REFERENCES public.users(id) ON DELETE SET NULL,
    origin   TEXT NOT NULL CHECK (origin IN ('upload', 'url', 'official', 'note')),
    title  TEXT,
    url  TEXT,
    file_key TEXT,
    language TEXT,
    raw_md  TEXT,
    meta  JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS ai.document_chunks (
    id     SERIAL PRIMARY KEY,
    doc_id   INT NOT NULL REFERENCES ai.documents(id) ON DELETE CASCADE,
    seq   INT NOT NULL,
    content_md TEXT NOT NULL,
    UNIQUE (doc_id, seq)
);

CREATE TABLE IF NOT EXISTS ai.extractions (
    id    SERIAL PRIMARY KEY,
    doc_id   INT NOT NULL REFERENCES ai.documents(id) ON DELETE CASCADE,
    schema_code TEXT NOT NULL,
    data_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai.generated_notes (
   id   SERIAL PRIMARY KEY,
   doc_id INT REFERENCES ai.documents(id) ON DELETE SET NULL,
   ue_id  INT REFERENCES academics.ue(id) ON DELETE SET NULL, 
   lesson_id INT REFERENCES academics.lessons(id) ON DELETE SET NULL,
   title TEXT NOT NULL,
   content_md  TEXT NOT NULL,
   citations JSONB NOT NULL DEFAULT '[]'::jsonb,
   created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai.generated_quizzes (
  id           SERIAL PRIMARY KEY,
  source       TEXT NOT NULL CHECK (source IN ('document','lesson','ue','article')),
  source_id    INT,
  quiz_id      INT NOT NULL REFERENCES learning.quizzes(id) ON DELETE CASCADE,
  method       TEXT,
  quality_score NUMERIC(4,2),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai.verified_sources (
  id          SERIAL PRIMARY KEY,
  title       TEXT NOT NULL,
  url         TEXT NOT NULL UNIQUE,
  publisher   TEXT,
  source_type TEXT,
  last_checked TIMESTAMPTZ,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai.content_citations (
  id          SERIAL PRIMARY KEY,
  entity_type TEXT NOT NULL CHECK (entity_type IN ('ue','course','lesson','protocol','note')),
  entity_id   INT NOT NULL,
  source_id   INT NOT NULL REFERENCES ai.verified_sources(id) ON DELETE CASCADE,
  note        TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (entity_type, entity_id, source_id)
);

CREATE TABLE IF NOT EXISTS ai.jobs (
  id        SERIAL PRIMARY KEY,
  kind      TEXT NOT NULL CHECK (kind IN ('ingest','chunk','embed','extract','generate_note','generate_quiz','image_fetch')),
  payload   JSONB NOT NULL,
  status    TEXT NOT NULL CHECK (status IN ('queued','running','done','error')) DEFAULT 'queued',
  error     TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_jobs_status ON ai.jobs(status);


CREATE TABLE IF NOT EXISTS ai.tutor_messages (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES public.users(id) ON DELETE SET NULL,
  context TEXT NOT NULL CHECK (context IN ('DOSE_TRAINING','DOSE_FREE','COURSE_HELP')),
  ref_id INT NULL, -- attempt_id ou calculation_id
  role TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
  content_md TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS revision.notes (
  id            SERIAL PRIMARY KEY,
  owner_id      INT REFERENCES public.users(id) ON DELETE SET NULL,
  ue_id         INT REFERENCES academics.ue(id) ON DELETE SET NULL,
  lesson_id     INT REFERENCES academics.lessons(id) ON DELETE SET NULL,
  title         TEXT NOT NULL,
  content_md    TEXT NOT NULL,
  is_ai_generated BOOLEAN NOT NULL DEFAULT FALSE,
  sources       JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
DROP TRIGGER IF EXISTS trg_rev_notes_upd ON revision.notes;
CREATE TRIGGER trg_rev_notes_upd BEFORE UPDATE ON revision.notes
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS revision.flashcards (
  id        SERIAL PRIMARY KEY,
  note_id   INT REFERENCES revision.notes(id)    ON DELETE SET NULL,
  lesson_id INT REFERENCES academics.lessons(id) ON DELETE SET NULL,
  front_md  TEXT NOT NULL,
  back_md   TEXT NOT NULL,
  tags      TEXT[] NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS revision.srs_schedules (
  id           SERIAL PRIMARY KEY,
  user_id      INT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  flashcard_id INT NOT NULL REFERENCES revision.flashcards(id) ON DELETE CASCADE,
  interval_days INT NOT NULL DEFAULT 1,
  ease_factor  NUMERIC(4,2) NOT NULL DEFAULT 2.5,
  repetitions  INT NOT NULL DEFAULT 0,
  due_at       TIMESTAMPTZ NOT NULL,
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, flashcard_id)
);

CREATE TABLE IF NOT EXISTS revision.srs_reviews (
  id           SERIAL PRIMARY KEY,
  user_id      INT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  flashcard_id INT NOT NULL REFERENCES revision.flashcards(id) ON DELETE CASCADE,
  quality      SMALLINT NOT NULL CHECK (quality BETWEEN 0 AND 5),
  reviewed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  meta         JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS revision.gamification_users (
  user_id   INT PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
  points    INT NOT NULL DEFAULT 0,
  level     INT NOT NULL DEFAULT 1,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS revision.badges (
  id          SERIAL PRIMARY KEY,
  code        TEXT NOT NULL UNIQUE,
  label       TEXT NOT NULL,
  description TEXT,
  icon        TEXT
);

CREATE TABLE IF NOT EXISTS revision.user_badges (
  id        SERIAL PRIMARY KEY,
  user_id   INT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  badge_id  INT NOT NULL REFERENCES revision.badges(id) ON DELETE CASCADE,
  earned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, badge_id)
);

CREATE TABLE IF NOT EXISTS analytics.events (
  id          SERIAL PRIMARY KEY,
  user_id     INT REFERENCES public.users(id) ON DELETE SET NULL,
  event_name  TEXT NOT NULL,
  event_props JSONB NOT NULL DEFAULT '{}'::jsonb,
  context     JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_event_name_nonvide CHECK (length(btrim(event_name)) > 0)
);
CREATE INDEX IF NOT EXISTS idx_events_user_created ON analytics.events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_name_created ON analytics.events(event_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_created      ON analytics.events(created_at DESC);

INSERT INTO content.categories (code, label) VALUES
 ('urgence','Urgences'), ('pediatrie','Pédiatrie'), ('geriatrie','Gériatrie')
ON CONFLICT (code) DO NOTHING;

DO $$
DECLARE v_uid INT; v_cat INT; v_pid INT; v_asset INT;
BEGIN
  SELECT id INTO v_uid FROM public.users WHERE email='admin@admin.com';
  SELECT id INTO v_cat FROM content.categories WHERE code='urgence';

  INSERT INTO content.protocols (category_id, code, title, summary, tags, is_published, created_by)
  VALUES (v_cat,'abc-surveillance','Surveillance ABC',
          'Airway, Breathing, Circulation', ARRAY['abc','urgence'], TRUE, v_uid)
  ON CONFLICT (code) DO NOTHING;

  SELECT id INTO v_pid FROM content.protocols WHERE code='abc-surveillance';

  IF v_pid IS NOT NULL THEN
    INSERT INTO content.protocol_versions (protocol_id, version, body_md, changelog, published_at)
    VALUES (v_pid,1,'# ABC
- A : voies aériennes
- B : ventilation
- C : circulation
','Initiale', NOW())
    ON CONFLICT DO NOTHING;
    UPDATE content.protocols SET updated_at = NOW() WHERE id = v_pid;

    INSERT INTO media.assets(kind, storage_key, mime_type, width_px, height_px, alt_text, created_by)
    VALUES ('image','/cdn/protocols/abc/cover.jpg','image/jpeg',1200,800,'Schéma ABC',v_uid)
    ON CONFLICT (storage_key) DO NOTHING;

    SELECT id INTO v_asset FROM media.assets WHERE storage_key='/cdn/protocols/abc/cover.jpg';
    IF v_asset IS NOT NULL THEN
      INSERT INTO media.entity_assets(entity_type, entity_id, asset_id, role, order_no)
      VALUES ('protocol', v_pid, v_asset, 'cover', 0)
      ON CONFLICT DO NOTHING;
    END IF;
  END IF;
END $$;