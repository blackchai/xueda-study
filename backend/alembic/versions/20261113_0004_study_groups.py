"""Real groups and explicit shares referencing existing private checkins."""
from alembic import op
import sqlalchemy as sa

revision = "20261113_0004"
down_revision = "20261113_0003"
branch_labels = None
depends_on = None


def uid(name, target, *, nullable=False, primary_key=False, ondelete="CASCADE"):
    return sa.Column(name, sa.Uuid(), sa.ForeignKey(target, ondelete=ondelete), nullable=nullable, primary_key=primary_key)


def upgrade():
    with op.batch_alter_table("checkins") as batch:
        batch.create_unique_constraint("uq_checkins_id_user", ["id", "user_id"])
    op.create_table("groups",
        sa.Column("id", sa.Uuid(), primary_key=True), uid("owner_id", "users.id", ondelete="RESTRICT"),
        sa.Column("name", sa.String(50), nullable=False), sa.Column("category", sa.String(40), nullable=False),
        sa.Column("description", sa.String(500), nullable=False), sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("announcement", sa.String(500), nullable=False), sa.Column("max_members", sa.Integer(), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("max_members BETWEEN 2 AND 200", name="ck_groups_capacity"))
    op.create_index("ix_groups_active_category", "groups", ["archived_at", "category", "created_at"])
    op.create_index("uq_group_owner_name_active", "groups", ["owner_id", "name"], unique=True,
                    postgresql_where=sa.text("archived_at IS NULL"), sqlite_where=sa.text("archived_at IS NULL"))
    op.create_table("group_join_requests",
        sa.Column("id", sa.Uuid(), primary_key=True), uid("group_id", "groups.id"), uid("user_id", "users.id"),
        sa.Column("status", sa.String(16), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)), uid("resolved_by", "users.id", nullable=True, ondelete="SET NULL"),
        sa.CheckConstraint("status IN ('pending','approved','rejected','cancelled')", name="ck_group_join_status"))
    op.create_index("uq_group_join_pending", "group_join_requests", ["group_id", "user_id"], unique=True,
                    postgresql_where=sa.text("status = 'pending'"), sqlite_where=sa.text("status = 'pending'"))
    op.create_index("ix_group_join_group_status", "group_join_requests", ["group_id", "status", "created_at"])
    op.create_index("ix_group_join_user", "group_join_requests", ["user_id", "created_at"])
    op.create_table("group_members",
        uid("group_id", "groups.id", primary_key=True), uid("user_id", "users.id", primary_key=True),
        sa.Column("role", sa.String(16), nullable=False), sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        uid("source_request_id", "group_join_requests.id", nullable=True, ondelete="SET NULL"),
        sa.UniqueConstraint("source_request_id", name="uq_group_member_source_request"),
        sa.CheckConstraint("role IN ('owner','member')", name="ck_group_member_role"))
    op.create_index("uq_group_single_owner", "group_members", ["group_id"], unique=True,
                    postgresql_where=sa.text("role = 'owner'"), sqlite_where=sa.text("role = 'owner'"))
    op.create_index("ix_group_member_user", "group_members", ["user_id", "joined_at"])
    op.create_table("group_goals",
        sa.Column("id", sa.Uuid(), primary_key=True), uid("group_id", "groups.id"),
        sa.Column("title", sa.String(120), nullable=False), sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False), sa.Column("target_minutes", sa.Integer(), nullable=False),
        uid("created_by", "users.id", nullable=True, ondelete="SET NULL"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("group_id", name="uq_group_goal_group"),
        sa.CheckConstraint("end_date >= start_date", name="ck_group_goal_dates"),
        sa.CheckConstraint("target_minutes BETWEEN 1 AND 525600", name="ck_group_goal_minutes"))
    op.create_table("group_checkin_shares",
        sa.Column("group_id", sa.Uuid(), primary_key=True), sa.Column("checkin_id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False), sa.Column("share_content", sa.Boolean(), nullable=False),
        sa.Column("shared_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["group_id", "user_id"], ["group_members.group_id", "group_members.user_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["checkin_id", "user_id"], ["checkins.id", "checkins.user_id"], ondelete="CASCADE"))
    op.create_index("ix_group_share_feed", "group_checkin_shares", ["group_id", "shared_at"])
    op.create_index("ix_group_share_checkin", "group_checkin_shares", ["checkin_id", "user_id"])


def downgrade():
    raise RuntimeError("Group rollback requires a reviewed backup and data retention plan")
