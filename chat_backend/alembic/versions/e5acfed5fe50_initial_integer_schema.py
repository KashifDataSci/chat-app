"""initial_integer_schema

Revision ID: 84047e391bcb
Revises: 
Create Date: 2026-06-03 23:52:29.900691

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '84047e391bcb'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Users Table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('phone_number', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone_number')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # 2. OTP Table
    op.create_table(
        'otps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('phone_number', sa.String(), nullable=False),
        sa.Column('otp_code', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_used', sa.Boolean(), server_default='false', nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_otps_id'), 'otps', ['id'], unique=False)

    # 3. Conversations Table
    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('is_group', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('group_name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversations_id'), 'conversations', ['id'], unique=False)

    # 4. Conversation Participants Association Table (Many-to-Many)
    op.create_table(
        'conversation_participants',
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('conversation_id', 'user_id')
    )

    # 5. Messages Table
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('encrypted_content', sa.Text(), nullable=False),
        sa.Column('nonce', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_id'), 'messages', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_messages_id'), table_name='messages')
    op.drop_table('messages')
    op.drop_table('conversation_participants')
    op.drop_index(op.f('ix_conversations_id'), table_name='conversations')
    op.drop_table('conversations')
    op.drop_index(op.f('ix_otps_id'), table_name='otps')
    op.drop_table('otps')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')