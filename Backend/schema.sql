--
-- PostgreSQL database dump
--

\restrict 7fArB76grngOQv0JJAuxUdlsaeBhd9j4qUnZSVAHFkUN8gT074oFaqjOuUVwY5l

-- Dumped from database version 18.3
-- Dumped by pg_dump version 18.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: attempt_badges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.attempt_badges (
    attempt_id integer NOT NULL,
    badge_id integer NOT NULL,
    event_id integer,
    earned_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: attempts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.attempts (
    attempt_id integer NOT NULL,
    run_id integer NOT NULL,
    attempt_number integer NOT NULL,
    is_active integer DEFAULT 1,
    starter text,
    badges_earned text
);


--
-- Name: attempts_attempt_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.attempts_attempt_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: attempts_attempt_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.attempts_attempt_id_seq OWNED BY public.attempts.attempt_id;


--
-- Name: badges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.badges (
    badge_id integer NOT NULL,
    badge_name text,
    region text,
    sprite_key text
);


--
-- Name: bonus_locations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bonus_locations (
    bonus_location_id integer NOT NULL,
    run_id integer,
    attempt_id integer,
    canonical_location_id integer,
    canonical_name text NOT NULL,
    sort_order integer,
    secondary_sort_order integer DEFAULT 0,
    is_active integer DEFAULT 1,
    version_group_id integer,
    event_type text
);


--
-- Name: bonus_locations_bonus_location_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.bonus_locations_bonus_location_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: bonus_locations_bonus_location_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.bonus_locations_bonus_location_id_seq OWNED BY public.bonus_locations.bonus_location_id;


--
-- Name: event_locations_canon_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_locations_canon_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: canon_locations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.canon_locations (
    canonical_location_id integer DEFAULT nextval('public.event_locations_canon_id_seq'::regclass) NOT NULL,
    canonical_location_name text
);


--
-- Name: contact_reports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contact_reports (
    report_id integer NOT NULL,
    report_type text NOT NULL,
    topic text,
    title text,
    details text NOT NULL,
    reproduction_steps text,
    status text DEFAULT 'open'::text NOT NULL,
    priority text DEFAULT 'normal'::text NOT NULL,
    admin_notes text,
    user_id integer,
    run_id text,
    attempt_number integer,
    game_id integer,
    version_group_id integer,
    run_name text,
    game_name text,
    page_url text,
    user_agent text,
    created_at text DEFAULT to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL,
    updated_at text DEFAULT to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'::text) NOT NULL,
    resolved_at text
);


--
-- Name: contact_reports_report_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contact_reports_report_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contact_reports_report_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contact_reports_report_id_seq OWNED BY public.contact_reports.report_id;


--
-- Name: encounter_pool; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.encounter_pool (
    game_id text,
    location_id integer,
    canonical_location_id integer,
    species_id integer,
    min_level integer,
    max_level integer,
    method text,
    enounter_rate integer,
    encounter_id integer NOT NULL
);


--
-- Name: encounter_pool_encounter_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.encounter_pool ALTER COLUMN encounter_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.encounter_pool_encounter_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: event_bosses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_bosses (
    event_id integer NOT NULL,
    trainer_id integer,
    sort_order text,
    encounter_title text,
    starter text,
    type_focus text,
    version_group_id integer,
    event_type text,
    game_id integer,
    badge_id integer
);


--
-- Name: event_bosses_event_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_bosses_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_bosses_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_bosses_event_id_seq OWNED BY public.event_bosses.event_id;


--
-- Name: event_locations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_locations (
    canonical_location_id integer NOT NULL,
    sort_order integer,
    secondary_sort_order integer,
    is_active integer DEFAULT 1,
    version_group_id integer,
    event_type text DEFAULT 'Location'::text,
    canon_pk integer NOT NULL
);


--
-- Name: event_locations_canon_pk_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_locations_canon_pk_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_locations_canon_pk_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_locations_canon_pk_seq OWNED BY public.event_locations.canon_pk;


--
-- Name: event_locations_canonical_location_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_locations_canonical_location_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_locations_canonical_location_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_locations_canonical_location_id_seq OWNED BY public.event_locations.canonical_location_id;


--
-- Name: evolutions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.evolutions (
    from_species_id integer NOT NULL,
    to_species_id integer NOT NULL,
    method text,
    detail text
);


--
-- Name: forms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.forms (
    form_id integer NOT NULL,
    parent_species_id integer,
    child_species_id integer
);


--
-- Name: forms_form_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.forms ALTER COLUMN form_id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.forms_form_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: games; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.games (
    game_id integer NOT NULL,
    name text NOT NULL,
    version_group_id integer,
    game_tag text,
    valid_game text,
    generation integer,
    pool_game_id integer,
    s_ref text,
    b_ref text,
    pdb_ref text
);


--
-- Name: location_alias_map_frlg; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.location_alias_map_frlg (
    raw_location_id integer NOT NULL,
    canonical_location_id integer NOT NULL,
    match_method text DEFAULT 'rule'::text NOT NULL,
    notes text
);


--
-- Name: locations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.locations (
    location_name text NOT NULL,
    location_id integer NOT NULL,
    canonical_location_id integer
);


--
-- Name: moves; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.moves (
    move_id integer,
    move_name text,
    type text,
    damage_class text,
    power integer,
    accuracy integer,
    version_group_id integer
);


--
-- Name: movesets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.movesets (
    species_id integer,
    move_id integer,
    version_group_id numeric,
    learn_method text,
    learn_level integer
);


--
-- Name: party; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.party (
    attempt_id integer NOT NULL,
    party_slot integer NOT NULL,
    pokemon_id integer
);


--
-- Name: pokebank; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pokebank (
    run_id integer NOT NULL,
    attempt_id integer NOT NULL,
    pokemon_id integer NOT NULL,
    species_id integer NOT NULL,
    canonical_location_id integer CONSTRAINT pokebank_location_id_not_null NOT NULL,
    nickname text,
    nature text,
    status text NOT NULL,
    storage text,
    party_slot integer,
    bonus_location integer DEFAULT 0,
    level_met integer,
    bonus_note text,
    shiny text,
    badges_earned text,
    trainers_defeated text,
    gender text DEFAULT 'male'::text
);


--
-- Name: pokebank_pokemon_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pokebank_pokemon_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pokebank_pokemon_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pokebank_pokemon_id_seq OWNED BY public.pokebank.pokemon_id;


--
-- Name: pokemon_badges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pokemon_badges (
    pokemon_id integer NOT NULL,
    badge_id integer NOT NULL,
    event_id integer,
    earned_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.runs (
    run_id integer NOT NULL,
    game_id text NOT NULL,
    name text NOT NULL,
    created_at text DEFAULT CURRENT_TIMESTAMP,
    victory text DEFAULT 'False'::text,
    beaten_at text,
    user_id integer,
    last_opened_at timestamp with time zone,
    last_opened_attempt_number integer
);


--
-- Name: runs_run_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.runs_run_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: runs_run_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.runs_run_id_seq OWNED BY public.runs.run_id;


--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schema_migrations (
    migration_name text NOT NULL,
    applied_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: species; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.species (
    species_id integer NOT NULL,
    name text NOT NULL,
    valid text DEFAULT true,
    details text,
    has_gender text DEFAULT true,
    has_female text DEFAULT false,
    default_gender text,
    one_gender text
);


--
-- Name: species_abilities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.species_abilities (
    species_id numeric,
    ability1 text,
    ability2 text,
    ability3 text,
    generation numeric,
    ability_pk integer NOT NULL
);


--
-- Name: species_stats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.species_stats (
    species_id integer,
    bst integer,
    hp integer NOT NULL,
    atk integer NOT NULL,
    def integer NOT NULL,
    spa integer NOT NULL,
    spd integer NOT NULL,
    spe integer NOT NULL,
    generation numeric,
    pk_id integer
);


--
-- Name: species_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.species_types (
    species_id integer,
    type1 text,
    type2 text,
    generation numeric,
    type_pk integer NOT NULL
);


--
-- Name: species_types_type_pk_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.species_types ALTER COLUMN type_pk ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.species_types_type_pk_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: trainer_pokemon; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.trainer_pokemon (
    encounter_name text,
    species_name text,
    lvl integer,
    moves text,
    held_item text,
    iv integer,
    pk_id integer NOT NULL,
    version_group_id integer,
    load_build integer
);


--
-- Name: trainer_pokemon_pk_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.trainer_pokemon ALTER COLUMN pk_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.trainer_pokemon_pk_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: trainer_pool; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.trainer_pool (
    trainer_id integer NOT NULL,
    trainer_class text,
    encounter_name text,
    canonical_location_id integer,
    is_rematch text,
    is_event text,
    trainer_name text,
    trainer_items text,
    version_group_id integer,
    trainer_pic text,
    trainer_double text,
    load_build integer,
    game_id integer,
    details text
);


--
-- Name: trainer_pool_trainer_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.trainer_pool_trainer_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: trainer_pool_trainer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.trainer_pool_trainer_id_seq OWNED BY public.trainer_pool.trainer_id;


--
-- Name: trainers_defeated; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.trainers_defeated (
    run_id integer,
    attempt_id integer,
    trainer_id integer
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    user_id integer NOT NULL,
    email text NOT NULL,
    password_hash text NOT NULL,
    display_name text,
    created_at text DEFAULT CURRENT_TIMESTAMP NOT NULL,
    supabase_id text,
    account_type text
);


--
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_user_id_seq OWNED BY public.users.user_id;


--
-- Name: attempts attempt_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attempts ALTER COLUMN attempt_id SET DEFAULT nextval('public.attempts_attempt_id_seq'::regclass);


--
-- Name: bonus_locations bonus_location_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bonus_locations ALTER COLUMN bonus_location_id SET DEFAULT nextval('public.bonus_locations_bonus_location_id_seq'::regclass);


--
-- Name: contact_reports report_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_reports ALTER COLUMN report_id SET DEFAULT nextval('public.contact_reports_report_id_seq'::regclass);


--
-- Name: event_bosses event_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_bosses ALTER COLUMN event_id SET DEFAULT nextval('public.event_bosses_event_id_seq'::regclass);


--
-- Name: event_locations canon_pk; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_locations ALTER COLUMN canon_pk SET DEFAULT nextval('public.event_locations_canon_pk_seq'::regclass);


--
-- Name: pokebank pokemon_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokebank ALTER COLUMN pokemon_id SET DEFAULT nextval('public.pokebank_pokemon_id_seq'::regclass);


--
-- Name: runs run_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.runs ALTER COLUMN run_id SET DEFAULT nextval('public.runs_run_id_seq'::regclass);


--
-- Name: trainer_pool trainer_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trainer_pool ALTER COLUMN trainer_id SET DEFAULT nextval('public.trainer_pool_trainer_id_seq'::regclass);


--
-- Name: users user_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN user_id SET DEFAULT nextval('public.users_user_id_seq'::regclass);


--
-- Name: species_abilities ability_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.species_abilities
    ADD CONSTRAINT ability_pk PRIMARY KEY (ability_pk);


--
-- Name: attempt_badges attempt_badges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attempt_badges
    ADD CONSTRAINT attempt_badges_pkey PRIMARY KEY (attempt_id, badge_id);


--
-- Name: attempts attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attempts
    ADD CONSTRAINT attempts_pkey PRIMARY KEY (attempt_id);


--
-- Name: attempts attempts_run_id_attempt_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attempts
    ADD CONSTRAINT attempts_run_id_attempt_number_key UNIQUE (run_id, attempt_number);


--
-- Name: badges badges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.badges
    ADD CONSTRAINT badges_pkey PRIMARY KEY (badge_id);


--
-- Name: bonus_locations bonus_locations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bonus_locations
    ADD CONSTRAINT bonus_locations_pkey PRIMARY KEY (bonus_location_id);


--
-- Name: canon_locations canon_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canon_locations
    ADD CONSTRAINT canon_pk PRIMARY KEY (canonical_location_id);


--
-- Name: contact_reports contact_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_reports
    ADD CONSTRAINT contact_reports_pkey PRIMARY KEY (report_id);


--
-- Name: encounter_pool encounter_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.encounter_pool
    ADD CONSTRAINT encounter_id PRIMARY KEY (encounter_id);


--
-- Name: event_bosses event_bosses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_bosses
    ADD CONSTRAINT event_bosses_pkey PRIMARY KEY (event_id);


--
-- Name: event_locations event_locations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_locations
    ADD CONSTRAINT event_locations_pkey PRIMARY KEY (canon_pk);


--
-- Name: evolutions evolutions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evolutions
    ADD CONSTRAINT evolutions_pkey PRIMARY KEY (from_species_id, to_species_id);


--
-- Name: forms forms_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.forms
    ADD CONSTRAINT forms_pkey PRIMARY KEY (form_id);


--
-- Name: games games_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.games
    ADD CONSTRAINT games_pkey PRIMARY KEY (game_id);


--
-- Name: locations locations_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT locations_pk PRIMARY KEY (location_id);


--
-- Name: party party_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.party
    ADD CONSTRAINT party_pkey PRIMARY KEY (attempt_id, party_slot);


--
-- Name: trainer_pokemon pk_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trainer_pokemon
    ADD CONSTRAINT pk_id PRIMARY KEY (pk_id);


--
-- Name: pokebank pokebank_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokebank
    ADD CONSTRAINT pokebank_pkey PRIMARY KEY (pokemon_id);


--
-- Name: pokemon_badges pokemon_badges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_badges
    ADD CONSTRAINT pokemon_badges_pkey PRIMARY KEY (pokemon_id, badge_id);


--
-- Name: runs runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.runs
    ADD CONSTRAINT runs_pkey PRIMARY KEY (run_id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (migration_name);


--
-- Name: species species_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.species
    ADD CONSTRAINT species_pkey PRIMARY KEY (species_id);


--
-- Name: trainer_pool trainer_pool_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trainer_pool
    ADD CONSTRAINT trainer_pool_pkey PRIMARY KEY (trainer_id);


--
-- Name: species_types type_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.species_types
    ADD CONSTRAINT type_pk PRIMARY KEY (type_pk);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: users users_supabase_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_supabase_id_key UNIQUE (supabase_id);


--
-- Name: idx_attempt_badges_badge_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_attempt_badges_badge_id ON public.attempt_badges USING btree (badge_id);


--
-- Name: idx_badges_badge_id_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_badges_badge_id_unique ON public.badges USING btree (badge_id);


--
-- Name: idx_contact_reports_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contact_reports_created_at ON public.contact_reports USING btree (created_at);


--
-- Name: idx_contact_reports_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contact_reports_status ON public.contact_reports USING btree (status);


--
-- Name: idx_contact_reports_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contact_reports_user_id ON public.contact_reports USING btree (user_id);


--
-- Name: idx_pokemon_badges_badge_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pokemon_badges_badge_id ON public.pokemon_badges USING btree (badge_id);


--
-- Name: idx_runs_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_runs_user_id ON public.runs USING btree (user_id);


--
-- Name: idx_runs_user_last_opened; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_runs_user_last_opened ON public.runs USING btree (user_id, last_opened_at DESC);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- Name: idx_users_supabase_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_supabase_id ON public.users USING btree (supabase_id);


--
-- Name: attempt_badges attempt_badges_attempt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attempt_badges
    ADD CONSTRAINT attempt_badges_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES public.attempts(attempt_id) ON DELETE CASCADE;


--
-- Name: attempt_badges attempt_badges_badge_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attempt_badges
    ADD CONSTRAINT attempt_badges_badge_id_fkey FOREIGN KEY (badge_id) REFERENCES public.badges(badge_id);


--
-- Name: attempt_badges attempt_badges_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attempt_badges
    ADD CONSTRAINT attempt_badges_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.event_bosses(event_id) ON DELETE SET NULL;


--
-- Name: attempts attempts_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attempts
    ADD CONSTRAINT attempts_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(run_id) ON DELETE CASCADE;


--
-- Name: event_bosses event_bosses_badge_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_bosses
    ADD CONSTRAINT event_bosses_badge_id_fkey FOREIGN KEY (badge_id) REFERENCES public.badges(badge_id);


--
-- Name: evolutions evolutions_from_species_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evolutions
    ADD CONSTRAINT evolutions_from_species_id_fkey FOREIGN KEY (from_species_id) REFERENCES public.species(species_id);


--
-- Name: evolutions evolutions_to_species_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evolutions
    ADD CONSTRAINT evolutions_to_species_id_fkey FOREIGN KEY (to_species_id) REFERENCES public.species(species_id);


--
-- Name: pokebank pokebank_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokebank
    ADD CONSTRAINT pokebank_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(run_id);


--
-- Name: pokebank pokebank_species_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokebank
    ADD CONSTRAINT pokebank_species_id_fkey FOREIGN KEY (species_id) REFERENCES public.species(species_id);


--
-- Name: pokemon_badges pokemon_badges_badge_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_badges
    ADD CONSTRAINT pokemon_badges_badge_id_fkey FOREIGN KEY (badge_id) REFERENCES public.badges(badge_id);


--
-- Name: pokemon_badges pokemon_badges_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_badges
    ADD CONSTRAINT pokemon_badges_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.event_bosses(event_id) ON DELETE SET NULL;


--
-- Name: pokemon_badges pokemon_badges_pokemon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pokemon_badges
    ADD CONSTRAINT pokemon_badges_pokemon_id_fkey FOREIGN KEY (pokemon_id) REFERENCES public.pokebank(pokemon_id) ON DELETE CASCADE;


--
-- Name: species_stats species_stats_species_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.species_stats
    ADD CONSTRAINT species_stats_species_id_fkey FOREIGN KEY (species_id) REFERENCES public.species(species_id);


--
-- PostgreSQL database dump complete
--

\unrestrict 7fArB76grngOQv0JJAuxUdlsaeBhd9j4qUnZSVAHFkUN8gT074oFaqjOuUVwY5l

