"""Persist opt-in matching profiles and weekly availability without publishing old accounts."""

from alembic import op
import sqlalchemy as sa

revision = "20261113_0002"
down_revision = "20261112_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("profiles") as batch:
        batch.add_column(sa.Column("school", sa.String(100), nullable=False, server_default=""))
        batch.add_column(sa.Column("major", sa.String(100), nullable=False, server_default=""))
        batch.add_column(sa.Column("bio", sa.String(300), nullable=False, server_default=""))
        for field in ("categories", "tags", "styles"):
            batch.add_column(sa.Column(field, sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
        batch.add_column(sa.Column("stage", sa.String(20), nullable=True))
        batch.add_column(sa.Column("daily_target_minutes", sa.Integer(), nullable=False, server_default="180"))
        batch.add_column(sa.Column("matching_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_check_constraint("ck_profiles_daily_target", "daily_target_minutes BETWEEN 30 AND 720")
        batch.create_index("ix_profiles_matching_enabled", ["matching_enabled", "user_id"])

    op.create_table(
        "profile_time_slots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("start_minute", sa.Integer(), nullable=False),
        sa.Column("end_minute", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["profiles.user_id"], ondelete="CASCADE"),
        sa.CheckConstraint("day BETWEEN 1 AND 7", name="ck_profile_slots_day"),
        sa.CheckConstraint(
            "start_minute >= 0 AND end_minute <= 1440 AND end_minute > start_minute",
            name="ck_profile_slots_interval",
        ),
        sa.UniqueConstraint("user_id", "day", "start_minute", "end_minute", name="uq_profile_slots_interval"),
    )
    op.create_index("ix_profile_slots_user_day", "profile_time_slots", ["user_id", "day"])


def downgrade() -> None:
    # A downgrade would discard voluntarily saved profiles and availability.
    raise RuntimeError("Matching profile rollback requires an explicit backup and data retention plan")
