# storage.py
# PostgreSQL 저장 / 조회 유틸

from __future__ import annotations

import os
import json
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL 환경변수가 설정되어 있지 않습니다.")
    return database_url


@contextmanager
def get_connection():
    conn = psycopg.connect(get_database_url(), row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()


def fetch_one(sql: str, params: tuple | list | None = None) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            row = cur.fetchone()
        conn.commit()
    return row


def fetch_all(sql: str, params: tuple | list | None = None) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            rows = cur.fetchall()
        conn.commit()
    return rows


def execute(sql: str, params: tuple | list | None = None) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
        conn.commit()


def execute_returning_id(sql: str, params: tuple | list | None = None) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            row = cur.fetchone()
        conn.commit()

    if not row:
        raise RuntimeError("INSERT RETURNING 결과가 없습니다.")

    return int(row["id"])


def init_db() -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id BIGINT PRIMARY KEY,
            race_code VARCHAR(30) NOT NULL,
            race_name VARCHAR(50) NOT NULL,
            server_code VARCHAR(30) NOT NULL,
            server_name VARCHAR(50) NOT NULL,
            updated_by BIGINT NOT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS raids (
            id BIGSERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            raid_name VARCHAR(100) NOT NULL,
            condition_type VARCHAR(20) NOT NULL
                CHECK (condition_type IN ('item_level', 'combat_score')),
            condition_value INTEGER NOT NULL
                CHECK (condition_value >= 0),
            created_by BIGINT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

            CONSTRAINT uq_raids_guild_name UNIQUE (guild_id, raid_name)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS applications (
            id BIGSERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            user_name VARCHAR(100) NOT NULL,
            raid_name VARCHAR(100) NOT NULL,

            race_code VARCHAR(30) NOT NULL,
            race_name VARCHAR(50) NOT NULL,
            server_code VARCHAR(30) NOT NULL,
            server_name VARCHAR(50) NOT NULL,

            character_name VARCHAR(100) NOT NULL,
            job_name VARCHAR(50) NOT NULL,
            item_level INTEGER NOT NULL DEFAULT 0,
            combat_score INTEGER NOT NULL DEFAULT 0,
            peak_combat_score INTEGER NOT NULL DEFAULT 0,
            
            note TEXT,
            available_days JSONB NOT NULL DEFAULT '[]'::jsonb,

            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

            CONSTRAINT uq_applications_unique_character
                UNIQUE (guild_id, raid_name, race_code, server_code, character_name)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS party_rules (
            id BIGSERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            raid_name VARCHAR(100) NOT NULL,
            slot_index INTEGER NOT NULL
                CHECK (slot_index BETWEEN 1 AND 8),
            role_type VARCHAR(20) NOT NULL
                CHECK (role_type IN ('ALL', 'TANK', 'DPS', 'HEAL')),
            preferred_jobs JSONB NOT NULL DEFAULT '[]'::jsonb,
            updated_by BIGINT NOT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

            CONSTRAINT uq_party_rules_slot UNIQUE (guild_id, raid_name, slot_index)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS raid_parties (
            id BIGSERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            raid_name VARCHAR(100) NOT NULL,
            weekday VARCHAR(10) NOT NULL
                CHECK (weekday IN ('월', '화', '수', '목', '금', '토', '일')),

            raid_no INTEGER NOT NULL
                CHECK (raid_no >= 1),
            party_no INTEGER
                CHECK (party_no BETWEEN 1 AND 2),
            slot_no INTEGER
                CHECK (slot_no BETWEEN 1 AND 4),
            status VARCHAR(20) NOT NULL
                CHECK (status IN ('ASSIGNED', 'WAITING')),

            user_id BIGINT NOT NULL,
            user_name VARCHAR(100) NOT NULL,

            race_code VARCHAR(30) NOT NULL,
            race_name VARCHAR(50) NOT NULL,
            server_code VARCHAR(30) NOT NULL,
            server_name VARCHAR(50) NOT NULL,

            character_name VARCHAR(100) NOT NULL,
            job_name VARCHAR(50) NOT NULL,
            item_level INTEGER NOT NULL DEFAULT 0,
            combat_score INTEGER NOT NULL DEFAULT 0,
            note TEXT,

            source_application_id BIGINT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

            CONSTRAINT uq_raid_parties_character_once
                UNIQUE (guild_id, raid_name, weekday, race_code, server_code, character_name)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS raid_generation_logs (
            id BIGSERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            raid_name VARCHAR(100) NOT NULL,
            weekday VARCHAR(10) NOT NULL
                CHECK (weekday IN ('월', '화', '수', '목', '금', '토', '일')),
            generated_by BIGINT NOT NULL,
            generated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            assigned_count INTEGER NOT NULL DEFAULT 0,
            waiting_count INTEGER NOT NULL DEFAULT 0,
            note TEXT
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_raids_guild_id
            ON raids (guild_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_applications_guild_raid
            ON applications (guild_id, raid_name);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_applications_user
            ON applications (guild_id, user_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_raid_parties_guild_raid_weekday
            ON raid_parties (guild_id, raid_name, weekday);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_raid_parties_user
            ON raid_parties (guild_id, user_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_party_rules_guild_raid
            ON party_rules (guild_id, raid_name);
        """,
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
        """
        DROP TRIGGER IF EXISTS trg_guild_settings_updated_at ON guild_settings;
        """,
        """
        CREATE TRIGGER trg_guild_settings_updated_at
        BEFORE UPDATE ON guild_settings
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """,
        """
        DROP TRIGGER IF EXISTS trg_raids_updated_at ON raids;
        """,
        """
        CREATE TRIGGER trg_raids_updated_at
        BEFORE UPDATE ON raids
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """,
        """
        DROP TRIGGER IF EXISTS trg_applications_updated_at ON applications;
        """,
        """
        CREATE TRIGGER trg_applications_updated_at
        BEFORE UPDATE ON applications
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """,
        """
        DROP TRIGGER IF EXISTS trg_party_rules_updated_at ON party_rules;
        """,
        """
        CREATE TRIGGER trg_party_rules_updated_at
        BEFORE UPDATE ON party_rules
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """,
        """
        DROP TRIGGER IF EXISTS trg_raid_parties_updated_at ON raid_parties;
        """,
        """
        CREATE TRIGGER trg_raid_parties_updated_at
        BEFORE UPDATE ON raid_parties
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """,
    ]

    with get_connection() as conn:
        with conn.cursor() as cur:
            for sql in statements:
                cur.execute(sql)
        conn.commit()

def json_dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False)


# =========================================================
# guild_settings CRUD
# =========================================================

def upsert_guild_setting(
    guild_id: int,
    race_code: str,
    race_name: str,
    server_code: str,
    server_name: str,
    updated_by: int,
) -> None:
    sql = """
    INSERT INTO guild_settings (
        guild_id,
        race_code,
        race_name,
        server_code,
        server_name,
        updated_by
    )
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (guild_id)
    DO UPDATE SET
        race_code = EXCLUDED.race_code,
        race_name = EXCLUDED.race_name,
        server_code = EXCLUDED.server_code,
        server_name = EXCLUDED.server_name,
        updated_by = EXCLUDED.updated_by;
    """
    execute(
        sql,
        (
            guild_id,
            race_code.strip(),
            race_name.strip(),
            server_code.strip(),
            server_name.strip(),
            updated_by,
        ),
    )


def get_guild_setting(guild_id: int) -> dict | None:
    sql = """
    SELECT
        guild_id,
        race_code,
        race_name,
        server_code,
        server_name,
        updated_by,
        updated_at
    FROM guild_settings
    WHERE guild_id = %s;
    """
    return fetch_one(sql, (guild_id,))


def delete_guild_setting(guild_id: int) -> int:
    sql = """
    DELETE FROM guild_settings
    WHERE guild_id = %s
    RETURNING guild_id;
    """
    row = fetch_one(sql, (guild_id,))
    return 1 if row else 0


# =========================================================
# raids CRUD
# =========================================================

def create_raid(
    guild_id: int,
    raid_name: str,
    condition_type: str,
    condition_value: int,
    created_by: int,
) -> int:
    normalized_name = raid_name.strip()
    normalized_type = condition_type.strip()

    if normalized_type not in ("item_level", "combat_score"):
        raise ValueError("condition_type은 'item_level' 또는 'combat_score'여야 합니다.")

    sql = """
    INSERT INTO raids (
        guild_id,
        raid_name,
        condition_type,
        condition_value,
        created_by
    )
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id;
    """
    return execute_returning_id(
        sql,
        (
            guild_id,
            normalized_name,
            normalized_type,
            int(condition_value),
            created_by,
        ),
    )


def get_raid(guild_id: int, raid_name: str) -> dict | None:
    sql = """
    SELECT
        id,
        guild_id,
        raid_name,
        condition_type,
        condition_value,
        created_by,
        created_at,
        updated_at
    FROM raids
    WHERE guild_id = %s
      AND raid_name = %s;
    """
    return fetch_one(sql, (guild_id, raid_name.strip()))


def list_raids(guild_id: int) -> list[dict]:
    sql = """
    SELECT
        id,
        guild_id,
        raid_name,
        condition_type,
        condition_value,
        created_by,
        created_at,
        updated_at
    FROM raids
    WHERE guild_id = %s
    ORDER BY raid_name ASC;
    """
    return fetch_all(sql, (guild_id,))


def delete_raid(guild_id: int, raid_name: str) -> int:
    sql = """
    DELETE FROM raids
    WHERE guild_id = %s
      AND raid_name = %s
    RETURNING id;
    """
    row = fetch_one(sql, (guild_id, raid_name.strip()))
    return 1 if row else 0


def raid_exists(guild_id: int, raid_name: str) -> bool:
    sql = """
    SELECT 1
    FROM raids
    WHERE guild_id = %s
      AND raid_name = %s;
    """
    row = fetch_one(sql, (guild_id, raid_name.strip()))
    return row is not None


def count_raid_applications(guild_id: int, raid_name: str) -> int:
    sql = """
    SELECT COUNT(*) AS cnt
    FROM applications
    WHERE guild_id = %s
      AND raid_name = %s;
    """
    row = fetch_one(sql, (guild_id, raid_name.strip()))
    if not row:
        return 0
    return int(row["cnt"])


# =========================================================
# 신청/공대 삭제용 함수
# =========================================================

def delete_raid_applications(guild_id: int, raid_name: str) -> int:
    sql = """
    DELETE FROM applications
    WHERE guild_id = %s
      AND raid_name = %s
    RETURNING id;
    """
    rows = fetch_all(sql, (guild_id, raid_name.strip()))
    return len(rows)


def clear_raid_parties(guild_id: int, raid_name: str, weekday: str | None = None) -> int:
    if weekday is None:
        sql = """
        DELETE FROM raid_parties
        WHERE guild_id = %s
          AND raid_name = %s
        RETURNING id;
        """
        rows = fetch_all(sql, (guild_id, raid_name.strip()))
        return len(rows)

    sql = """
    DELETE FROM raid_parties
    WHERE guild_id = %s
      AND raid_name = %s
      AND weekday = %s
    RETURNING id;
    """
    rows = fetch_all(sql, (guild_id, raid_name.strip(), weekday.strip()))
    return len(rows)


# =========================================================
# applications CRUD
# =========================================================

def create_application(data: dict) -> int:
    sql = """
    INSERT INTO applications (
        guild_id,
        user_id,
        user_name,
        raid_name,
        race_code,
        race_name,
        server_code,
        server_name,
        character_name,
        job_name,
        item_level,
        combat_score,
        peak_combat_score,
        note,
        available_days
    )
    VALUES (
        %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s::jsonb
    )
    RETURNING id;
    """
    return execute_returning_id(
        sql,
        (
            int(data["guild_id"]),
            int(data["user_id"]),
            str(data["user_name"]).strip(),
            str(data["raid_name"]).strip(),
            str(data["race_code"]).strip(),
            str(data["race_name"]).strip(),
            str(data["server_code"]).strip(),
            str(data["server_name"]).strip(),
            str(data["character_name"]).strip(),
            str(data["job_name"]).strip(),
            int(data["item_level"]),
            int(data["combat_score"]),
            int(data.get("peak_combat_score", 0)),
            str(data.get("note", "")).strip() or None,
            json_dumps(data.get("available_days", [])),
        ),
    )

def update_application(application_id: int, data: dict) -> None:
    sql = """
    UPDATE applications
    SET
        user_name = %s,
        raid_name = %s,
        race_code = %s,
        race_name = %s,
        server_code = %s,
        server_name = %s,
        character_name = %s,
        job_name = %s,
        item_level = %s,
        combat_score = %s,
        peak_combat_score = %s,
        note = %s,
        available_days = %s::jsonb
    WHERE id = %s;
    """
    execute(
        sql,
        (
            str(data["user_name"]).strip(),
            str(data["raid_name"]).strip(),
            str(data["race_code"]).strip(),
            str(data["race_name"]).strip(),
            str(data["server_code"]).strip(),
            str(data["server_name"]).strip(),
            str(data["character_name"]).strip(),
            str(data["job_name"]).strip(),
            int(data["item_level"]),
            int(data["combat_score"]),
            int(data.get("peak_combat_score", 0)),
            str(data.get("note", "")).strip() or None,
            json_dumps(data.get("available_days", [])),
            int(application_id),
        ),
    )

def get_application_by_character(
    guild_id: int,
    raid_name: str,
    race_code: str,
    server_code: str,
    character_name: str,
) -> dict | None:
    sql = """
    SELECT
        id,
        guild_id,
        user_id,
        user_name,
        raid_name,
        race_code,
        race_name,
        server_code,
        server_name,
        character_name,
        job_name,
        item_level,
        combat_score,
        peak_combat_score,
        note,
        available_days,
        created_at,
        updated_at
    FROM applications
    WHERE guild_id = %s
      AND raid_name = %s
      AND race_code = %s
      AND server_code = %s
      AND character_name = %s;
    """
    return fetch_one(
        sql,
        (
            guild_id,
            raid_name.strip(),
            race_code.strip(),
            server_code.strip(),
            character_name.strip(),
        ),
    )


def get_user_application(
    guild_id: int,
    user_id: int,
    raid_name: str,
    race_code: str,
    server_code: str,
    character_name: str,
) -> dict | None:
    sql = """
    SELECT
        id,
        guild_id,
        user_id,
        user_name,
        raid_name,
        race_code,
        race_name,
        server_code,
        server_name,
        character_name,
        job_name,
        item_level,
        combat_score,
        peak_combat_score,
        note,
        available_days,
        created_at,
        updated_at
    FROM applications
    WHERE guild_id = %s
      AND user_id = %s
      AND raid_name = %s
      AND race_code = %s
      AND server_code = %s
      AND character_name = %s;
    """
    return fetch_one(
        sql,
        (
            guild_id,
            user_id,
            raid_name.strip(),
            race_code.strip(),
            server_code.strip(),
            character_name.strip(),
        ),
    )


def list_user_applications(
    guild_id: int,
    user_id: int,
    raid_name: str | None = None,
) -> list[dict]:
    if raid_name is None:
        sql = """
        SELECT
            id,
            guild_id,
            user_id,
            user_name,
            raid_name,
            race_code,
            race_name,
            server_code,
            server_name,
            character_name,
            job_name,
            item_level,
            combat_score,
            peak_combat_score,
            note,
            available_days,
            created_at,
            updated_at
        FROM applications
        WHERE guild_id = %s
          AND user_id = %s
        ORDER BY raid_name ASC, character_name ASC;
        """
        return fetch_all(sql, (guild_id, user_id))

    sql = """
    SELECT
        id,
        guild_id,
        user_id,
        user_name,
        raid_name,
        race_code,
        race_name,
        server_code,
        server_name,
        character_name,
        job_name,
        item_level,
        combat_score,
        peak_combat_score,
        note,
        available_days,
        created_at,
        updated_at
    FROM applications
    WHERE guild_id = %s
      AND user_id = %s
      AND raid_name = %s
    ORDER BY character_name ASC;
    """
    return fetch_all(sql, (guild_id, user_id, raid_name.strip()))


def list_raid_applications(guild_id: int, raid_name: str) -> list[dict]:
    sql = """
    SELECT
        id,
        guild_id,
        user_id,
        user_name,
        raid_name,
        race_code,
        race_name,
        server_code,
        server_name,
        character_name,
        job_name,
        item_level,
        combat_score,
        peak_combat_score,
        note,
        available_days,
        created_at,
        updated_at
    FROM applications
    WHERE guild_id = %s
      AND raid_name = %s
    ORDER BY combat_score DESC, item_level DESC, character_name ASC;
    """
    return fetch_all(sql, (guild_id, raid_name.strip()))


def list_raid_applications_by_weekday(
    guild_id: int,
    raid_name: str,
    weekday: str,
) -> list[dict]:
    sql = """
    SELECT
        id,
        guild_id,
        user_id,
        user_name,
        raid_name,
        race_code,
        race_name,
        server_code,
        server_name,
        character_name,
        job_name,
        item_level,
        combat_score,
        peak_combat_score,
        note,
        available_days,
        created_at,
        updated_at
    FROM applications
    WHERE guild_id = %s
      AND raid_name = %s
      AND available_days @> %s::jsonb
    ORDER BY combat_score DESC, item_level DESC, character_name ASC;
    """
    return fetch_all(
        sql,
        (
            guild_id,
            raid_name.strip(),
            json_dumps([weekday.strip()]),
        ),
    )


def delete_application(application_id: int) -> int:
    sql = """
    DELETE FROM applications
    WHERE id = %s
    RETURNING id;
    """
    row = fetch_one(sql, (application_id,))
    return 1 if row else 0


def delete_application_by_character(
    guild_id: int,
    raid_name: str,
    race_code: str,
    server_code: str,
    character_name: str,
) -> int:
    sql = """
    DELETE FROM applications
    WHERE guild_id = %s
      AND raid_name = %s
      AND race_code = %s
      AND server_code = %s
      AND character_name = %s
    RETURNING id;
    """
    row = fetch_one(
        sql,
        (
            guild_id,
            raid_name.strip(),
            race_code.strip(),
            server_code.strip(),
            character_name.strip(),
        ),
    )
    return 1 if row else 0

# 같은 레이드 + 같은 캐릭터명 신청 전부 찾는 함수
def list_applications_by_character_name(
    guild_id: int,
    raid_name: str,
    character_name: str,
) -> list[dict]:
    sql = """
    SELECT
        id,
        guild_id,
        user_id,
        user_name,
        raid_name,
        race_code,
        race_name,
        server_code,
        server_name,
        character_name,
        job_name,
        item_level,
        combat_score,
        peak_combat_score,
        note,
        available_days,
        created_at,
        updated_at
    FROM applications
    WHERE guild_id = %s
      AND raid_name = %s
      AND character_name = %s
    ORDER BY race_name ASC, server_name ASC, user_name ASC;
    """
    return fetch_all(
        sql,
        (
            guild_id,
            raid_name.strip(),
            character_name.strip(),
        ),
    )

# =========================================================
# party_rules CRUD
# =========================================================

def save_party_rules(
    guild_id: int,
    raid_name: str,
    slots: list[dict],
    updated_by: int,
) -> None:
    """
    slots 예시:
    [
        {"slot_index": 1, "role_type": "TANK", "preferred_jobs": ["수호성", "검성"]},
        {"slot_index": 2, "role_type": "HEAL", "preferred_jobs": ["치유성"]},
        ...
    ]
    """
    raid_name = raid_name.strip()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM party_rules
                WHERE guild_id = %s
                  AND raid_name = %s;
                """,
                (guild_id, raid_name),
            )

            for slot in slots:
                cur.execute(
                    """
                    INSERT INTO party_rules (
                        guild_id,
                        raid_name,
                        slot_index,
                        role_type,
                        preferred_jobs,
                        updated_by
                    )
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s);
                    """,
                    (
                        guild_id,
                        raid_name,
                        int(slot["slot_index"]),
                        str(slot["role_type"]).strip(),
                        json_dumps(slot.get("preferred_jobs", [])),
                        updated_by,
                    ),
                )
        conn.commit()


def load_party_rules(guild_id: int, raid_name: str) -> list[dict]:
    sql = """
    SELECT
        id,
        guild_id,
        raid_name,
        slot_index,
        role_type,
        preferred_jobs,
        updated_by,
        updated_at
    FROM party_rules
    WHERE guild_id = %s
      AND raid_name = %s
    ORDER BY slot_index ASC;
    """
    return fetch_all(sql, (guild_id, raid_name.strip()))


def delete_party_rules(guild_id: int, raid_name: str) -> int:
    sql = """
    DELETE FROM party_rules
    WHERE guild_id = %s
      AND raid_name = %s
    RETURNING id;
    """
    rows = fetch_all(sql, (guild_id, raid_name.strip()))
    return len(rows)


def has_party_rules(guild_id: int, raid_name: str) -> bool:
    sql = """
    SELECT 1
    FROM party_rules
    WHERE guild_id = %s
      AND raid_name = %s
    LIMIT 1;
    """
    row = fetch_one(sql, (guild_id, raid_name.strip()))
    return row is not None


# =========================================================
# raid_parties CRUD
# =========================================================

def replace_raid_parties(
    guild_id: int,
    raid_name: str,
    weekday: str,
    members: list[dict],
) -> None:
    """
    members 예시:
    [
        {
            "raid_no": 1,
            "party_no": 1,
            "slot_no": 1,
            "status": "ASSIGNED",
            "user_id": 123,
            "user_name": "홍길동",
            "race_code": "2",
            "race_name": "마족",
            "server_code": "2019",
            "server_name": "진",
            "character_name": "버터와플",
            "job_name": "수호성",
            "item_level": 3335,
            "combat_score": 39187,
            "note": "평일 22시 이후 가능",
            "source_application_id": 10,
        },
        {
            "raid_no": 3,
            "party_no": None,
            "slot_no": None,
            "status": "WAITING",
            ...
        }
    ]
    """
    raid_name = raid_name.strip()
    weekday = weekday.strip()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM raid_parties
                WHERE guild_id = %s
                  AND raid_name = %s
                  AND weekday = %s;
                """,
                (guild_id, raid_name, weekday),
            )

            for member in members:
                cur.execute(
                    """
                    INSERT INTO raid_parties (
                        guild_id,
                        raid_name,
                        weekday,
                        raid_no,
                        party_no,
                        slot_no,
                        status,
                        user_id,
                        user_name,
                        race_code,
                        race_name,
                        server_code,
                        server_name,
                        character_name,
                        job_name,
                        item_level,
                        combat_score,
                        note,
                        source_application_id
                    )
                    VALUES (
                        %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s
                    );
                    """,
                    (
                        guild_id,
                        raid_name,
                        weekday,
                        int(member["raid_no"]),
                        member.get("party_no"),
                        member.get("slot_no"),
                        str(member["status"]).strip(),
                        int(member["user_id"]),
                        str(member["user_name"]).strip(),
                        str(member["race_code"]).strip(),
                        str(member["race_name"]).strip(),
                        str(member["server_code"]).strip(),
                        str(member["server_name"]).strip(),
                        str(member["character_name"]).strip(),
                        str(member["job_name"]).strip(),
                        int(member["item_level"]),
                        int(member["combat_score"]),
                        str(member.get("note", "")).strip() or None,
                        member.get("source_application_id"),
                    ),
                )
        conn.commit()


def list_raid_parties(
    guild_id: int,
    raid_name: str,
    weekday: str | None = None,
) -> list[dict]:
    if weekday is None:
        sql = """
        SELECT
            id,
            guild_id,
            raid_name,
            weekday,
            raid_no,
            party_no,
            slot_no,
            status,
            user_id,
            user_name,
            race_code,
            race_name,
            server_code,
            server_name,
            character_name,
            job_name,
            item_level,
            combat_score,
            note,
            source_application_id,
            created_at,
            updated_at
        FROM raid_parties
        WHERE guild_id = %s
          AND raid_name = %s
        ORDER BY weekday ASC, raid_no ASC, party_no ASC NULLS LAST, slot_no ASC NULLS LAST, character_name ASC;
        """
        return fetch_all(sql, (guild_id, raid_name.strip()))

    sql = """
    SELECT
        id,
        guild_id,
        raid_name,
        weekday,
        raid_no,
        party_no,
        slot_no,
        status,
        user_id,
        user_name,
        race_code,
        race_name,
        server_code,
        server_name,
        character_name,
        job_name,
        item_level,
        combat_score,
        note,
        source_application_id,
        created_at,
        updated_at
    FROM raid_parties
    WHERE guild_id = %s
      AND raid_name = %s
      AND weekday = %s
    ORDER BY raid_no ASC, party_no ASC NULLS LAST, slot_no ASC NULLS LAST, character_name ASC;
    """
    return fetch_all(sql, (guild_id, raid_name.strip(), weekday.strip()))


def list_assigned_party_members(
    guild_id: int,
    raid_name: str,
    weekday: str | None = None,
) -> list[dict]:
    if weekday is None:
        sql = """
        SELECT *
        FROM raid_parties
        WHERE guild_id = %s
          AND raid_name = %s
          AND status = 'ASSIGNED'
        ORDER BY weekday ASC, raid_no ASC, party_no ASC, slot_no ASC;
        """
        return fetch_all(sql, (guild_id, raid_name.strip()))

    sql = """
    SELECT *
    FROM raid_parties
    WHERE guild_id = %s
      AND raid_name = %s
      AND weekday = %s
      AND status = 'ASSIGNED'
    ORDER BY raid_no ASC, party_no ASC, slot_no ASC;
    """
    return fetch_all(sql, (guild_id, raid_name.strip(), weekday.strip()))


def list_waiting_party_members(
    guild_id: int,
    raid_name: str,
    weekday: str | None = None,
) -> list[dict]:
    if weekday is None:
        sql = """
        SELECT *
        FROM raid_parties
        WHERE guild_id = %s
          AND raid_name = %s
          AND status = 'WAITING'
        ORDER BY weekday ASC, raid_no ASC, character_name ASC;
        """
        return fetch_all(sql, (guild_id, raid_name.strip()))

    sql = """
    SELECT *
    FROM raid_parties
    WHERE guild_id = %s
      AND raid_name = %s
      AND weekday = %s
      AND status = 'WAITING'
    ORDER BY raid_no ASC, character_name ASC;
    """
    return fetch_all(sql, (guild_id, raid_name.strip(), weekday.strip()))


def get_party_member(
    guild_id: int,
    raid_name: str,
    weekday: str,
    race_code: str,
    server_code: str,
    character_name: str,
) -> dict | None:
    sql = """
    SELECT *
    FROM raid_parties
    WHERE guild_id = %s
      AND raid_name = %s
      AND weekday = %s
      AND race_code = %s
      AND server_code = %s
      AND character_name = %s;
    """
    return fetch_one(
        sql,
        (
            guild_id,
            raid_name.strip(),
            weekday.strip(),
            race_code.strip(),
            server_code.strip(),
            character_name.strip(),
        ),
    )


def get_party_slot_member(
    guild_id: int,
    raid_name: str,
    weekday: str,
    raid_no: int,
    party_no: int,
    slot_no: int,
) -> dict | None:
    sql = """
    SELECT *
    FROM raid_parties
    WHERE guild_id = %s
      AND raid_name = %s
      AND weekday = %s
      AND raid_no = %s
      AND party_no = %s
      AND slot_no = %s
      AND status = 'ASSIGNED';
    """
    return fetch_one(
        sql,
        (
            guild_id,
            raid_name.strip(),
            weekday.strip(),
            int(raid_no),
            int(party_no),
            int(slot_no),
        ),
    )


def has_generated_parties(
    guild_id: int,
    raid_name: str,
    weekday: str | None = None,
) -> bool:
    if weekday is None:
        sql = """
        SELECT 1
        FROM raid_parties
        WHERE guild_id = %s
          AND raid_name = %s
        LIMIT 1;
        """
        row = fetch_one(sql, (guild_id, raid_name.strip()))
        return row is not None

    sql = """
    SELECT 1
    FROM raid_parties
    WHERE guild_id = %s
      AND raid_name = %s
      AND weekday = %s
    LIMIT 1;
    """
    row = fetch_one(sql, (guild_id, raid_name.strip(), weekday.strip()))
    return row is not None


def move_party_member_to_slot(
    party_row_id: int,
    raid_no: int,
    party_no: int,
    slot_no: int,
) -> None:
    sql = """
    UPDATE raid_parties
    SET
        raid_no = %s,
        party_no = %s,
        slot_no = %s,
        status = 'ASSIGNED'
    WHERE id = %s;
    """
    execute(sql, (int(raid_no), int(party_no), int(slot_no), int(party_row_id)))


def move_party_member_to_waiting(
    party_row_id: int,
    raid_no: int,
) -> None:
    sql = """
    UPDATE raid_parties
    SET
        raid_no = %s,
        party_no = NULL,
        slot_no = NULL,
        status = 'WAITING'
    WHERE id = %s;
    """
    execute(sql, (int(raid_no), int(party_row_id)))


def update_party_member_position(
    party_row_id: int,
    raid_no: int,
    party_no: int | None,
    slot_no: int | None,
    status: str,
) -> None:
    sql = """
    UPDATE raid_parties
    SET
        raid_no = %s,
        party_no = %s,
        slot_no = %s,
        status = %s
    WHERE id = %s;
    """
    execute(
        sql,
        (
            int(raid_no),
            party_no,
            slot_no,
            str(status).strip(),
            int(party_row_id),
        ),
    )
