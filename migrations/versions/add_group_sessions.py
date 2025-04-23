"""add group sessions

Revision ID: add_group_sessions
Revises: d741f47a405f
Create Date: 2024-01-20
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_group_sessions'
down_revision = 'd741f47a405f'
branch_labels = None
depends_on = None


def upgrade():
    # Check if session_participant table exists
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = inspector.get_table_names()

    if 'session_participant' not in tables:
        # Create session_participant table
        op.create_table('session_participant',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('session_id', sa.Integer(), nullable=True),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('role', sa.String(length=20), nullable=True),
            sa.Column('joined_at', sa.DateTime(), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=True),
            sa.ForeignKeyConstraint(['session_id'], ['session.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
            sa.PrimaryKeyConstraint('id')
        )

    # Modify session table
    with op.batch_alter_table('session', schema=None) as batch_op:
        batch_op.add_column(sa.Column('creator_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('session_type', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('max_participants', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(None, 'user', ['creator_id'], ['id'])

        # Copy existing mentor_id to creator_id
        op.execute('UPDATE session SET creator_id = mentor_id, session_type = \'individual\', max_participants = 2')

        # Drop old columns
        batch_op.drop_constraint('fk_session_mentor_id_user', type_='foreignkey')
        batch_op.drop_constraint('fk_session_mentee_id_user', type_='foreignkey')
        batch_op.drop_column('mentor_id')
        batch_op.drop_column('mentee_id')


def downgrade():
    # Revert session table changes
    with op.batch_alter_table('session', schema=None) as batch_op:
        batch_op.add_column(sa.Column('mentor_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('mentee_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_session_mentee_id_user', 'user', ['mentee_id'], ['id'])
        batch_op.create_foreign_key('fk_session_mentor_id_user', 'user', ['mentor_id'], ['id'])

        # Copy creator_id back to mentor_id for individual sessions
        op.execute('UPDATE session SET mentor_id = creator_id WHERE session_type = \'individual\'')

        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('max_participants')
        batch_op.drop_column('session_type')
        batch_op.drop_column('creator_id')

    # Drop session_participant table
    op.drop_table('session_participant')