"""Add creator_id, session_type, and max_participants columns to session table

Revision ID: add_session_columns
Revises: add_session_participant
Create Date: 2023-04-09 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_session_columns'
down_revision = 'add_session_participant'
branch_labels = None
depends_on = None


def upgrade():
    # Add creator_id, session_type, and max_participants columns to session table
    with op.batch_alter_table('session', schema=None) as batch_op:
        batch_op.add_column(sa.Column('creator_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('session_type', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('max_participants', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_session_creator_id_user', 'user', ['creator_id'], ['id'])
    
    # Update creator_id with mentor_id for existing sessions
    op.execute('UPDATE session SET creator_id = mentor_id, session_type = "individual", max_participants = 2')


def downgrade():
    # Remove creator_id, session_type, and max_participants columns from session table
    with op.batch_alter_table('session', schema=None) as batch_op:
        batch_op.drop_constraint('fk_session_creator_id_user', type_='foreignkey')
        batch_op.drop_column('max_participants')
        batch_op.drop_column('session_type')
        batch_op.drop_column('creator_id')
