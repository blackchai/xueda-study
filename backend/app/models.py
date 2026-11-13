import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("uq_users_username", "username", unique=True),
        Index("uq_users_email", "email", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint("daily_target_minutes BETWEEN 30 AND 720", name="ck_profiles_daily_target"),
        Index("ix_profiles_matching_enabled", "matching_enabled", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    display_name: Mapped[str] = mapped_column(String(50), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    timezone_name: Mapped[str] = mapped_column(String(64), default="Asia/Shanghai", nullable=False)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    school: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    major: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    bio: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    categories: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    styles: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    stage: Mapped[str | None] = mapped_column(String(20), nullable=True)
    daily_target_minutes: Mapped[int] = mapped_column(Integer, default=180, nullable=False)
    matching_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_invites: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    time_slots: Mapped[list["ProfileTimeSlot"]] = relationship(
        cascade="all, delete-orphan", order_by="(ProfileTimeSlot.day, ProfileTimeSlot.start_minute)"
    )


class ProfileTimeSlot(Base):
    __tablename__ = "profile_time_slots"
    __table_args__ = (
        CheckConstraint("day BETWEEN 1 AND 7", name="ck_profile_slots_day"),
        CheckConstraint(
            "start_minute >= 0 AND end_minute <= 1440 AND end_minute > start_minute",
            name="ck_profile_slots_interval",
        ),
        UniqueConstraint("user_id", "day", "start_minute", "end_minute", name="uq_profile_slots_interval"),
        Index("ix_profile_slots_user_day", "user_id", "day"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False
    )
    day: Mapped[int] = mapped_column(Integer, nullable=False)
    start_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    end_minute: Mapped[int] = mapped_column(Integer, nullable=False)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        Index("ix_auth_session_user_active", "user_id", "revoked_at"),
        Index("ix_auth_session_expiry", "expires_at"),
        Index("uq_auth_sessions_token_hash", "token_hash", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class LoginThrottle(Base):
    __tablename__ = "login_throttles"

    key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    window_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (
        CheckConstraint("target_date >= start_date", name="ck_goals_date_range"),
        Index("ix_goals_user_status_target", "user_id", "status", "target_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="进行中")
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#5b5ce2")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    tasks: Mapped[list["GoalTask"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan", order_by="GoalTask.created_at"
    )


class GoalTask(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    goal: Mapped[Goal] = relationship(back_populates="tasks")


class Checkin(Base):
    __tablename__ = "checkins"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_checkins_id_user"),
        CheckConstraint("duration_minutes >= 1 AND duration_minutes <= 1440", name="ck_checkins_duration"),
        Index("ix_checkins_user_date", "user_id", "study_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    goal_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("goals.id", ondelete="SET NULL"), nullable=True
    )
    study_date: Mapped[date] = mapped_column(Date, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(String(1000), nullable=False)
    mood: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class BuddyRequest(Base):
    __tablename__ = "buddy_requests"
    __table_args__ = (
        CheckConstraint("sender_id <> recipient_id", name="ck_buddy_request_not_self"),
        CheckConstraint("user_low_id < user_high_id", name="ck_buddy_request_pair_order"),
        CheckConstraint(
            "(sender_id = user_low_id AND recipient_id = user_high_id) OR "
            "(sender_id = user_high_id AND recipient_id = user_low_id)",
            name="ck_buddy_request_participants",
        ),
        CheckConstraint("status IN ('pending','accepted','rejected','cancelled')", name="ck_buddy_request_status"),
        Index("uq_buddy_request_pending_pair", "user_low_id", "user_high_id", unique=True,
              postgresql_where=text("status = 'pending'"), sqlite_where=text("status = 'pending'")),
        Index("ix_buddy_request_sender_created", "sender_id", "created_at"),
        Index("ix_buddy_request_recipient_status", "recipient_id", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recipient_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_low_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_high_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BuddyRelation(Base):
    __tablename__ = "buddy_relations"
    __table_args__ = (
        CheckConstraint("user_low_id < user_high_id", name="ck_buddy_relation_pair_order"),
        CheckConstraint("ended_by IS NULL OR ended_by = user_low_id OR ended_by = user_high_id", name="ck_buddy_relation_ended_by"),
        Index("uq_buddy_relation_active_pair", "user_low_id", "user_high_id", unique=True,
              postgresql_where=text("ended_at IS NULL"), sqlite_where=text("ended_at IS NULL")),
        Index("ix_buddy_relation_low_active", "user_low_id", "ended_at"),
        Index("ix_buddy_relation_high_active", "user_high_id", "ended_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_low_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_high_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source_request_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("buddy_requests.id", ondelete="SET NULL"), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint("kind IN ('buddy_request_received','buddy_request_accepted','buddy_request_rejected','buddy_relation_removed','group_join_requested','group_join_approved','group_join_rejected','group_member_removed')", name="ck_notification_kind"),
        Index("ix_notification_user_read_created", "user_id", "read_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    request_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("buddy_requests.id", ondelete="SET NULL"), nullable=True)
    relation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("buddy_relations.id", ondelete="SET NULL"), nullable=True)
    group_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("groups.id", ondelete="SET NULL"), nullable=True)
    group_request_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("group_join_requests.id", ondelete="SET NULL"), nullable=True)
    group_event_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("group_member_events.id", ondelete="SET NULL"), nullable=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    event_key: Mapped[str] = mapped_column(String(140), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StudyGroup(Base):
    __tablename__ = "groups"
    __table_args__ = (CheckConstraint("max_members BETWEEN 2 AND 200", name="ck_groups_capacity"),
                      Index("ix_groups_active_category", "archived_at", "category", "created_at"),
                      Index("uq_group_owner_name_active", "owner_id", "name", unique=True,
                            postgresql_where=text("archived_at IS NULL"), sqlite_where=text("archived_at IS NULL")))
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    announcement: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    max_members: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GroupJoinRequest(Base):
    __tablename__ = "group_join_requests"
    __table_args__ = (
        CheckConstraint("status IN ('pending','approved','rejected','cancelled')", name="ck_group_join_status"),
        Index("uq_group_join_pending", "group_id", "user_id", unique=True,
              postgresql_where=text("status = 'pending'"), sqlite_where=text("status = 'pending'")),
        Index("ix_group_join_group_status", "group_id", "status", "created_at"),
        Index("ix_group_join_user", "user_id", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (
        CheckConstraint("role IN ('owner','member')", name="ck_group_member_role"),
        Index("uq_group_single_owner", "group_id", unique=True,
              postgresql_where=text("role = 'owner'"), sqlite_where=text("role = 'owner'")),
        Index("ix_group_member_user", "user_id", "joined_at"),
    )
    group_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(16), default="member", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    source_request_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("group_join_requests.id", ondelete="SET NULL"), nullable=True, unique=True)


class GroupMemberEvent(Base):
    """Persistent source for removal notices after the active membership is deleted."""
    __tablename__ = "group_member_events"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", "membership_joined_at", name="uq_group_removal_membership"),
        CheckConstraint("kind = 'removed'", name="ck_group_member_event_kind"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    membership_joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="removed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class GroupGoal(Base):
    __tablename__ = "group_goals"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_group_goal_dates"),
        CheckConstraint("target_minutes BETWEEN 1 AND 525600", name="ck_group_goal_minutes"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class GroupCheckinShare(Base):
    __tablename__ = "group_checkin_shares"
    __table_args__ = (
        ForeignKeyConstraint(["group_id", "user_id"], ["group_members.group_id", "group_members.user_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["checkin_id", "user_id"], ["checkins.id", "checkins.user_id"], ondelete="CASCADE"),
        Index("ix_group_share_feed", "group_id", "shared_at"),
        Index("ix_group_share_checkin", "checkin_id", "user_id"),
    )
    group_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    checkin_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    share_content: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    shared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
