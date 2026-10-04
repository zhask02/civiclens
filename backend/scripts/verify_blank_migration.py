"""Verify that the Alembic chain bootstraps an isolated blank PostgreSQL DB."""

import os
import subprocess
import sys
import uuid
import re
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


REQUIRED_TABLES = {
    "alembic_version",
    "incidents",
    "incident_evidence",
    "evidence_analyses",
    "authorities",
    "routing_decisions",
    "incident_assignments",
    "operator_notes",
    "incident_status_history",
}
HEAD_REVISION = "b102da6_operations"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    database_url = os.environ["DATABASE_URL"]
    admin_url = make_url(database_url)
    if len(sys.argv) == 3 and sys.argv[1] == "--cleanup":
        temporary_name = sys.argv[2]
        if not re.fullmatch(r"civiclens_migration_verify_[0-9a-f]{12}", temporary_name):
            raise ValueError("Refusing to remove a database outside this verifier's naming pattern")
        admin_engine = create_engine(admin_url)
        try:
            with admin_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                connection.execute(text(f'DROP DATABASE "{temporary_name}" WITH (FORCE)'))
        finally:
            admin_engine.dispose()
        print(f"Removed temporary database {temporary_name}.")
        return
    temporary_name = f"civiclens_migration_verify_{uuid.uuid4().hex[:12]}"
    admin_engine = create_engine(admin_url)
    temporary_url = admin_url.set(database=temporary_name).render_as_string(
        hide_password=False
    )
    created = False

    try:
        with admin_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(text(f'CREATE DATABASE "{temporary_name}"'))
        created = True

        environment = os.environ.copy()
        environment["DATABASE_URL"] = temporary_url
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            check=True,
            env=environment,
        )

        temporary_engine = create_engine(temporary_url)
        try:
            with temporary_engine.connect() as connection:
                tables = set(connection.execute(text(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                )).scalars())
                revision = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
        finally:
            temporary_engine.dispose()

        missing_tables = REQUIRED_TABLES - tables
        if missing_tables:
            raise RuntimeError(f"Missing tables after migration: {sorted(missing_tables)}")
        if revision != HEAD_REVISION:
            raise RuntimeError(f"Expected {HEAD_REVISION}, received {revision}")
        print("Blank migration bootstrap verified.")
    finally:
        if created:
            with admin_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                connection.execute(text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :database_name"
                ), {"database_name": temporary_name})
                connection.execute(text(f'DROP DATABASE "{temporary_name}" WITH (FORCE)'))
        admin_engine.dispose()


if __name__ == "__main__":
    main()
