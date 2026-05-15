"""Settings loads `.env` from the calliope2 workspace root regardless of cwd.

This pins the behavior that closes the "did I cd deep enough?" gotcha — a
single ``calliope2/.env`` should configure ``uvicorn`` (run from
``calliope2/``), ``alembic`` (run from ``calliope2/apps/api/``), and the CLI
(run from anywhere) without per-shell env exports.
"""

from __future__ import annotations

from pathlib import Path


def test_workspace_root_env_is_picked_up_from_any_cwd(monkeypatch, tmp_path):
    """Write a temporary .env at the resolved workspace root path and verify
    that ``Settings()`` reads it even when the process cwd is somewhere else."""
    # Compute the same path settings.py uses (parents[3]) — that's the
    # contract we're pinning.
    import calliope2.settings as settings_module
    workspace_root_env = (
        Path(settings_module.__file__).resolve().parents[3] / ".env"
    )

    # Don't clobber a real .env if one exists locally.
    pre_existing = workspace_root_env.exists()
    backup = workspace_root_env.read_text() if pre_existing else None
    workspace_root_env.write_text(
        "CALLIOPE2_DATABASE_URL=postgresql+asyncpg://test_user:test_pw@somewhere:1234/x\n"
    )

    try:
        # cwd is irrelevant — Settings should still find the workspace .env.
        monkeypatch.chdir(tmp_path)
        # Make sure no shell env var would short-circuit the test.
        monkeypatch.delenv("CALLIOPE2_DATABASE_URL", raising=False)

        # Reload settings.get_settings (lru_cached) so the new env file is read.
        settings_module.get_settings.cache_clear()
        s = settings_module.get_settings()
        assert "test_user" in s.database_url
        assert "somewhere:1234" in s.database_url
    finally:
        # Restore
        if pre_existing:
            workspace_root_env.write_text(backup or "")
        else:
            workspace_root_env.unlink(missing_ok=True)
        settings_module.get_settings.cache_clear()


def test_cwd_env_overrides_workspace_env(monkeypatch, tmp_path):
    """When both ``calliope2/.env`` and a cwd-local ``.env`` exist, the latter wins."""
    import calliope2.settings as settings_module
    workspace_root_env = (
        Path(settings_module.__file__).resolve().parents[3] / ".env"
    )
    pre_existing = workspace_root_env.exists()
    backup = workspace_root_env.read_text() if pre_existing else None

    workspace_root_env.write_text(
        "CALLIOPE2_DATABASE_URL=postgresql+asyncpg://from_workspace@h/x\n"
    )
    (tmp_path / ".env").write_text(
        "CALLIOPE2_DATABASE_URL=postgresql+asyncpg://from_cwd@h/x\n"
    )

    try:
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CALLIOPE2_DATABASE_URL", raising=False)

        settings_module.get_settings.cache_clear()
        assert "from_cwd" in settings_module.get_settings().database_url
    finally:
        if pre_existing:
            workspace_root_env.write_text(backup or "")
        else:
            workspace_root_env.unlink(missing_ok=True)
        settings_module.get_settings.cache_clear()


def test_explicit_env_var_still_wins_over_env_file(monkeypatch, tmp_path):
    """An explicit ``CALLIOPE2_DATABASE_URL=...`` in the shell beats any .env."""
    import calliope2.settings as settings_module
    workspace_root_env = (
        Path(settings_module.__file__).resolve().parents[3] / ".env"
    )
    pre_existing = workspace_root_env.exists()
    backup = workspace_root_env.read_text() if pre_existing else None

    workspace_root_env.write_text(
        "CALLIOPE2_DATABASE_URL=postgresql+asyncpg://from_env_file@h/x\n"
    )
    monkeypatch.setenv(
        "CALLIOPE2_DATABASE_URL",
        "postgresql+asyncpg://from_shell_env@h/x",
    )

    try:
        monkeypatch.chdir(tmp_path)
        settings_module.get_settings.cache_clear()
        assert "from_shell_env" in settings_module.get_settings().database_url
    finally:
        if pre_existing:
            workspace_root_env.write_text(backup or "")
        else:
            workspace_root_env.unlink(missing_ok=True)
        settings_module.get_settings.cache_clear()
