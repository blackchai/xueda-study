"""Transactional buddy requests, relationships and private notifications."""
from alembic import op
import sqlalchemy as sa

revision = "20261113_0003"
down_revision = "20261113_0002"
branch_labels = None
depends_on = None


def user_fk(name, *, nullable=False, ondelete="CASCADE"):
    return sa.Column(name, sa.Uuid(), sa.ForeignKey("users.id", ondelete=ondelete), nullable=nullable)


def upgrade():
    op.add_column("profiles", sa.Column("allow_invites", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table(
        "buddy_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        user_fk("sender_id"), user_fk("recipient_id"), user_fk("user_low_id"), user_fk("user_high_id"),
        sa.Column("message", sa.String(200), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("sender_id <> recipient_id", name="ck_buddy_request_not_self"),
        sa.CheckConstraint("user_low_id < user_high_id", name="ck_buddy_request_pair_order"),
        sa.CheckConstraint("(sender_id = user_low_id AND recipient_id = user_high_id) OR (sender_id = user_high_id AND recipient_id = user_low_id)", name="ck_buddy_request_participants"),
        sa.CheckConstraint("status IN ('pending','accepted','rejected','cancelled')", name="ck_buddy_request_status"),
    )
    op.create_index("uq_buddy_request_pending_pair", "buddy_requests", ["user_low_id", "user_high_id"], unique=True,
                    postgresql_where=sa.text("status = 'pending'"), sqlite_where=sa.text("status = 'pending'"))
    op.create_index("ix_buddy_request_sender_created", "buddy_requests", ["sender_id", "created_at"])
    op.create_index("ix_buddy_request_recipient_status", "buddy_requests", ["recipient_id", "status", "created_at"])
    op.create_table(
        "buddy_relations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        user_fk("user_low_id"), user_fk("user_high_id"),
        sa.Column("source_request_id", sa.Uuid(), sa.ForeignKey("buddy_requests.id", ondelete="SET NULL"), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        user_fk("ended_by", nullable=True, ondelete="SET NULL"),
        sa.CheckConstraint("user_low_id < user_high_id", name="ck_buddy_relation_pair_order"),
        sa.CheckConstraint("ended_by IS NULL OR ended_by = user_low_id OR ended_by = user_high_id", name="ck_buddy_relation_ended_by"),
    )
    op.create_index("uq_buddy_relation_active_pair", "buddy_relations", ["user_low_id", "user_high_id"], unique=True,
                    postgresql_where=sa.text("ended_at IS NULL"), sqlite_where=sa.text("ended_at IS NULL"))
    op.create_index("ix_buddy_relation_low_active", "buddy_relations", ["user_low_id", "ended_at"])
    op.create_index("ix_buddy_relation_high_active", "buddy_relations", ["user_high_id", "ended_at"])
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), primary_key=True), user_fk("user_id"),
        user_fk("actor_id", nullable=True, ondelete="SET NULL"),
        sa.Column("request_id", sa.Uuid(), sa.ForeignKey("buddy_requests.id", ondelete="SET NULL")),
        sa.Column("relation_id", sa.Uuid(), sa.ForeignKey("buddy_relations.id", ondelete="SET NULL")),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("event_key", sa.String(140), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("kind IN ('buddy_request_received','buddy_request_accepted','buddy_request_rejected','buddy_relation_removed')", name="ck_notification_kind"),
    )
    op.create_index("ix_notification_user_read_created", "notifications", ["user_id", "read_at", "created_at"])


def downgrade():
    raise RuntimeError("Buddy history rollback requires an explicit backup and data retention plan")
