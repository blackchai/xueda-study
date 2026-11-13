"""Extend existing private notifications with durable group business events."""
from alembic import op
import sqlalchemy as sa

revision = "20261113_0005"
down_revision = "20261113_0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("group_member_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("membership_joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("group_id", "user_id", "membership_joined_at", name="uq_group_removal_membership"),
        sa.CheckConstraint("kind = 'removed'", name="ck_group_member_event_kind"))
    with op.batch_alter_table("notifications") as batch:
        batch.add_column(sa.Column("group_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("group_request_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("group_event_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key("fk_notification_group", "groups", ["group_id"], ["id"], ondelete="SET NULL")
        batch.create_foreign_key("fk_notification_group_request", "group_join_requests", ["group_request_id"], ["id"], ondelete="SET NULL")
        batch.create_foreign_key("fk_notification_group_event", "group_member_events", ["group_event_id"], ["id"], ondelete="SET NULL")
        batch.drop_constraint("ck_notification_kind", type_="check")
        batch.create_check_constraint("ck_notification_kind", "kind IN ('buddy_request_received','buddy_request_accepted','buddy_request_rejected','buddy_relation_removed','group_join_requested','group_join_approved','group_join_rejected','group_member_removed')")


def downgrade():
    raise RuntimeError("Notification rollback requires a reviewed history retention plan")
