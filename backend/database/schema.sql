
-- CodeRace - MySQL database schema
-- File:   backend/database/schema.sql
-- Owner:  Hafiza Alizada (Member 2 - Database & API)
--
-- Creates the `coderace` database and its 4 tables:
--   users, problems, testcases, matches
--
-- WARNING: running this file DELETES the 4 tables and all their data,
--          then creates them again empty. Use it for development setup.


CREATE DATABASE IF NOT EXISTS coderace
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE coderace;

-- Drop in reverse dependency order (children first)
DROP TABLE IF EXISTS matches;
DROP TABLE IF EXISTS testcases;
DROP TABLE IF EXISTS problems;
DROP TABLE IF EXISTS users;


-- 1. USERS - accounts, Elo rating, rank tier and match statistics

CREATE TABLE users (
    id              INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    username        VARCHAR(30)   NOT NULL,
    email           VARCHAR(255)  NOT NULL,
    password_hash   VARCHAR(255)  NOT NULL,          -- salted scrypt hash, never the plain password
    elo_rating      INT           NOT NULL DEFAULT 1000,

    -- Rank tier is calculated automatically from elo_rating,
    -- so it can never be out of sync with the rating.
    rank_tier       VARCHAR(10) GENERATED ALWAYS AS (
                        CASE
                            WHEN elo_rating >= 1800 THEN 'Diamond'
                            WHEN elo_rating >= 1500 THEN 'Gold'
                            WHEN elo_rating >= 1200 THEN 'Silver'
                            ELSE 'Bronze'
                        END
                    ) STORED,

    matches_played  INT UNSIGNED  NOT NULL DEFAULT 0,
    wins            INT UNSIGNED  NOT NULL DEFAULT 0,
    losses          INT UNSIGNED  NOT NULL DEFAULT 0,
    draws           INT UNSIGNED  NOT NULL DEFAULT 0,
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                  ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_users_username (username),
    UNIQUE KEY uq_users_email (email),
    KEY idx_users_elo (elo_rating),                   -- fast leaderboard

    CONSTRAINT chk_users_elo   CHECK (elo_rating >= 0),
    CONSTRAINT chk_users_stats CHECK (wins + losses + draws = matches_played)
) ENGINE = InnoDB;


-- ---------------------------------------------------------------------
-- 2. PROBLEMS - coding challenges (written by Member 3)
-- ---------------------------------------------------------------------
CREATE TABLE problems (
    id               INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    slug             VARCHAR(100)  NOT NULL,          -- e.g. 'two-sum' (used in URLs)
    title            VARCHAR(150)  NOT NULL,
    description      TEXT          NOT NULL,
    difficulty       ENUM('Easy', 'Medium', 'Hard') NOT NULL,
    game_mode        ENUM('speed_duel', 'bug_hunt', 'optimization')
                                   NOT NULL DEFAULT 'speed_duel',
    function_name    VARCHAR(100)  NOT NULL,          -- function the player must implement
    starter_code     TEXT          NOT NULL,          -- skeleton (or buggy code for Bug Hunt)
    time_limit_ms    INT UNSIGNED  NOT NULL DEFAULT 2000,
    memory_limit_mb  INT UNSIGNED  NOT NULL DEFAULT 128,
    is_active        BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_problems_slug (slug),
    KEY idx_problems_pick (game_mode, difficulty, is_active)  -- matchmaking picks a problem
) ENGINE = InnoDB;


-- ---------------------------------------------------------------------
-- 3. TESTCASES - visible and hidden tests for each problem
--    input_data      = JSON array of function arguments, e.g. [[2,7,11,15], 9]
--    expected_output = JSON value the function must return, e.g. [0,1]
-- ---------------------------------------------------------------------
CREATE TABLE testcases (
    id               INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    problem_id       INT UNSIGNED  NOT NULL,
    input_data       JSON          NOT NULL,
    expected_output  JSON          NOT NULL,
    is_hidden        BOOLEAN       NOT NULL DEFAULT FALSE,
    order_index      INT UNSIGNED  NOT NULL DEFAULT 0,

    PRIMARY KEY (id),
    KEY idx_testcases_problem (problem_id, is_hidden, order_index),

    CONSTRAINT fk_testcases_problem
        FOREIGN KEY (problem_id) REFERENCES problems (id)
        ON DELETE CASCADE                             -- delete problem => delete its tests
) ENGINE = InnoDB;


-- ---------------------------------------------------------------------
-- 4. MATCHES - one duel between two players
-- ---------------------------------------------------------------------
CREATE TABLE matches (
    id                   INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    problem_id           INT UNSIGNED  NOT NULL,
    game_mode            ENUM('speed_duel', 'bug_hunt', 'optimization') NOT NULL,
    player1_id           INT UNSIGNED  NOT NULL,
    player2_id           INT UNSIGNED  NOT NULL,
    winner_id            INT UNSIGNED  NULL,          -- NULL = draw / not finished
    status               ENUM('in_progress', 'finished', 'abandoned')
                                       NOT NULL DEFAULT 'in_progress',
    player1_elo_before   INT           NOT NULL,
    player2_elo_before   INT           NOT NULL,
    player1_elo_change   INT           NULL,          -- e.g. +16 or -16, set when match ends
    player2_elo_change   INT           NULL,
    started_at           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at             DATETIME      NULL,
    duration_seconds     INT UNSIGNED  NULL,

    PRIMARY KEY (id),
    KEY idx_matches_player1 (player1_id, started_at),  -- match history
    KEY idx_matches_player2 (player2_id, started_at),
    KEY idx_matches_status  (status),

    CONSTRAINT fk_matches_problem FOREIGN KEY (problem_id) REFERENCES problems (id),
    CONSTRAINT fk_matches_player1 FOREIGN KEY (player1_id) REFERENCES users (id),
    CONSTRAINT fk_matches_player2 FOREIGN KEY (player2_id) REFERENCES users (id),
    CONSTRAINT fk_matches_winner  FOREIGN KEY (winner_id)  REFERENCES users (id),

    CONSTRAINT chk_matches_players CHECK (player1_id <> player2_id),
    CONSTRAINT chk_matches_winner  CHECK (winner_id IS NULL
                                          OR winner_id = player1_id
                                          OR winner_id = player2_id),
    CONSTRAINT chk_matches_end     CHECK (ended_at IS NULL OR ended_at >= started_at)
) ENGINE = InnoDB;