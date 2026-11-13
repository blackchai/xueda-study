"""Account authentication and private learning data baseline.

Revision ID: 20261112_0001
Revises: None
Create Date: 2026-11-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20261112_0001"
down_revision = None
branch_labels = None
depends_on = None


def _create_users() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("username", sa.String(32), nullable=True),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("uq_users_username", "users", ["username"], unique=True)
    op.create_index("uq_users_email", "users", ["email"], unique=True)


def _upgrade_existing_users(inspector) -> None:
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "username" not in columns:
        op.add_column("users", sa.Column("username", sa.String(32), nullable=True))
    if "is_active" not in columns:
        op.add_column(
            "users",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )

    indexes = {index["name"] for index in inspector.get_indexes("users")}
    unique_constraints = {
        constraint["name"] for constraint in inspector.get_unique_constraints("users")
    }
    if "uq_users_username" not in indexes | unique_constraints:
        op.create_index("uq_users_username", "users", ["username"], unique=True)
    if "uq_users_email" not in indexes | unique_constraints:
        op.create_index("uq_users_email", "users", ["email"], unique=True)


def _create_profiles() -> None:
    op.create_table(
        "profiles",
        sa.Column("user_id", sa.Uuid(), primary_key=True),
        sa.Column("display_name", sa.String(50), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("timezone_name", sa.String(64), nullable=False),
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )


def _create_auth_sessions() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("uq_auth_sessions_token_hash", "auth_sessions", ["token_hash"], unique=True)
    op.create_index(
        "ix_auth_session_user_active", "auth_sessions", ["user_id", "revoked_at"]
    )
    op.create_index("ix_auth_session_expiry", "auth_sessions", ["expires_at"])


def _create_login_throttles() -> None:
    op.create_table(
        "login_throttles",
        sa.Column("key_hash", sa.String(64), primary_key=True),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def _create_goals() -> None:
    op.create_table(
        "goals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("color", sa.String(7), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("target_date >= start_date", name="ck_goals_date_range"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_goals_user_id", "goals", ["user_id"])
    op.create_index(
        "ix_goals_user_status_target", "goals", ["user_id", "status", "target_date"]
    )


def _create_tasks() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("goal_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_tasks_goal_id", "tasks", ["goal_id"])


def _create_checkins() -> None:
    op.create_table(
        "checkins",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("goal_id", sa.Uuid(), nullable=True),
        sa.Column("study_date", sa.Date(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("content", sa.String(1000), nullable=False),
        sa.Column("mood", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "duration_minutes >= 1 AND duration_minutes <= 1440",
            name="ck_checkins_duration",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_checkins_user_id", "checkins", ["user_id"])
    op.create_index("ix_checkins_user_date", "checkins", ["user_id", "study_date"])


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # Phase-one databases already contain users/profiles/auth_sessions. Add only
    # missing fields and tables so no existing identity or session is discarded.
    if "users" in existing_tables:
        _upgrade_existing_users(inspector)
    else:
        _create_users()

    creators = (
        ("profiles", _create_profiles),
        ("auth_sessions", _create_auth_sessions),
        ("login_throttles", _create_login_throttles),
        ("goals", _create_goals),
        ("tasks", _create_tasks),
        ("checkins", _create_checkins),
    )
    for table_name, creator in creators:
        if table_name not in existing_tables:
            creator()


def downgrade() -> None:
    # Deliberately non-destructive: automatically dropping account and learning
    # records is unsafe. A rollback requires an explicit, reviewed data plan.
    pass
