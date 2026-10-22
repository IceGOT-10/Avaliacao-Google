"""initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-22 17:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tabela businesses
    op.create_table('businesses',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('google_review_url', sa.String(length=2048), nullable=False),
        sa.Column('timezone', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_businesses'))
    )
    op.create_index(op.f('ix_businesses_slug'), 'businesses', ['slug'], unique=True)

    # 2. Tabela users
    op.create_table('users',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_admin', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('email = lower(email)', name=op.f('ck_users_email_lower')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 3. Tabela business_memberships
    op.create_table('business_memberships',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('business_id', sa.BigInteger(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("role IN ('owner', 'manager')", name=op.f('ck_business_memberships_role_valid')),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], name=op.f('fk_business_memberships_business_id_businesses'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_business_memberships_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_business_memberships')),
        sa.UniqueConstraint('user_id', 'business_id', name='uq_business_memberships_user_business')
    )
    op.create_index('ix_business_memberships_business_id', 'business_memberships', ['business_id'], unique=False)
    op.create_index(op.f('ix_business_memberships_user_id'), 'business_memberships', ['user_id'], unique=False)

    # 4. Tabela review_links
    op.create_table('review_links',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('business_id', sa.BigInteger(), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('label', sa.String(length=100), nullable=True),
        sa.Column('destination_url', sa.String(length=2048), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("destination_url LIKE 'https://%%'", name=op.f('ck_review_links_destination_url_https')),
        sa.CheckConstraint("source IN ('nfc', 'qr', 'other')", name=op.f('ck_review_links_source_valid')),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], name=op.f('fk_review_links_business_id_businesses'), ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_review_links'))
    )
    op.create_index('ix_review_links_business_id', 'review_links', ['business_id'], unique=False)
    op.create_index(op.f('ix_review_links_code'), 'review_links', ['code'], unique=True)

    # 5. Tabela review_snapshots
    op.create_table('review_snapshots',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('business_id', sa.BigInteger(), nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('total_reviews', sa.Integer(), nullable=False),
        sa.Column('average_rating', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('error_message', sa.String(length=1000), nullable=True),
        sa.CheckConstraint("source IN ('manual', 'google_api')", name=op.f('ck_review_snapshots_source_valid')),
        sa.CheckConstraint('average_rating IS NULL OR (average_rating >= 0 AND average_rating <= 5)', name=op.f('ck_review_snapshots_average_rating_range')),
        sa.CheckConstraint('total_reviews >= 0', name=op.f('ck_review_snapshots_total_reviews_non_negative')),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], name=op.f('fk_review_snapshots_business_id_businesses'), ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_review_snapshots'))
    )
    op.create_index('ix_review_snapshots_business_captured', 'review_snapshots', ['business_id', 'captured_at'], unique=False)

    # 6. Tabela access_events
    op.create_table('access_events',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('review_link_id', sa.BigInteger(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('result', sa.String(length=30), nullable=False),
        sa.Column('is_probable_bot', sa.Boolean(), nullable=True),
        sa.CheckConstraint("result IN ('redirected', 'blocked_inactive')", name=op.f('ck_access_events_result_valid')),
        sa.ForeignKeyConstraint(['review_link_id'], ['review_links.id'], name=op.f('fk_access_events_review_link_id_review_links'), ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_access_events'))
    )
    op.create_index('ix_access_events_link_occurred', 'access_events', ['review_link_id', 'occurred_at'], unique=False)
    op.create_index('ix_access_events_occurred_at', 'access_events', ['occurred_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_access_events_occurred_at', table_name='access_events')
    op.drop_index('ix_access_events_link_occurred', table_name='access_events')
    op.drop_table('access_events')
    op.drop_index('ix_review_snapshots_business_captured', table_name='review_snapshots')
    op.drop_table('review_snapshots')
    op.drop_index(op.f('ix_review_links_code'), table_name='review_links')
    op.drop_index('ix_review_links_business_id', table_name='review_links')
    op.drop_table('review_links')
    op.drop_index(op.f('ix_business_memberships_user_id'), table_name='business_memberships')
    op.drop_index('ix_business_memberships_business_id', table_name='business_memberships')
    op.drop_table('business_memberships')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_businesses_slug'), table_name='businesses')
    op.drop_table('businesses')