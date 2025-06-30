# backend/alembic/versions/001_initial.py
"""Initial database schema."""
from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(length=32), nullable=False, unique=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('password_hash', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table('matches',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table('match_players',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('match_id', sa.Integer(), sa.ForeignKey('matches.id', ondelete='CASCADE')),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
    )
    op.create_table('words_played',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('match_id', sa.Integer(), sa.ForeignKey('matches.id', ondelete='CASCADE')),
        sa.Column('player_id', sa.Integer(), sa.ForeignKey('match_players.id', ondelete='CASCADE')),
        sa.Column('word', sa.String(length=32), nullable=False),
        sa.Column('points', sa.Integer(), nullable=False),
        sa.Column('was_stolen', sa.Boolean(), nullable=False, default=False),
    )
    op.create_index('ix_users_username', 'users', ['username'])
    # (Add any additional indexes or constraints as needed)

def downgrade() -> None:
    op.drop_index('ix_users_username', table_name='users')
    op.drop_table('words_played')
    op.drop_table('match_players')
    op.drop_table('matches')
    op.drop_table('users')
