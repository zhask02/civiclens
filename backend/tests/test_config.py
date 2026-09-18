"""Regression tests for project environment loading."""

import os

from dotenv import dotenv_values

from app.config import PROJECT_ROOT, load_project_environment


def test_project_dotenv_overrides_an_inherited_operator_token(monkeypatch):
    """A terminal's stale token must not shadow the project configuration."""

    configured_token = dotenv_values(PROJECT_ROOT / ".env")[
        "CIVICLENS_OPERATOR_TOKEN"
    ]
    monkeypatch.setenv("CIVICLENS_OPERATOR_TOKEN", "stale-process-token")

    load_project_environment()

    assert os.environ["CIVICLENS_OPERATOR_TOKEN"] == configured_token
