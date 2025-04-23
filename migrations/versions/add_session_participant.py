"""Add session_participant table

Revision ID: add_session_participant
Revises: bc9c936b80ce
Create Date: 2023-04-09 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_session_participant'
down_revision = 'bc9c936b80ce'
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

    # Check if columns exist in session table
    inspector = sa.inspect(connection)
    columns = [c['name'] for c in inspector.get_columns('session')]

    # Add creator_id, session_type, and max_participants columns to session table if they don't exist
    with op.batch_alter_table('session', schema=None) as batch_op:
        if 'creator_id' not in columns:
            batch_op.add_column(sa.Column('creator_id', sa.Integer(), nullable=True))
        if 'session_type' not in columns:
            batch_op.add_column(sa.Column('session_type', sa.String(length=20), nullable=True))
        if 'max_participants' not in columns:
            batch_op.add_column(sa.Column('max_participants', sa.Integer(), nullable=True))

        # Check if foreign key exists
        foreign_keys = inspector.get_foreign_keys('session')
        creator_fk_exists = any(fk['constrained_columns'] == ['creator_id'] for fk in foreign_keys)

        if not creator_fk_exists and 'creator_id' in columns:
            batch_op.create_foreign_key(None, 'user', ['creator_id'], ['id'])

    # Migrate existing data
    # Get all sessions
    connection = op.get_bind()
    sessions = connection.execute(sa.text("SELECT id, mentor_id, mentee_id FROM session")).fetchall()

    # Update session table
    for session in sessions:
        session_id, mentor_id, mentee_id = session

        # Update session with creator_id, session_type, and max_participants
        connection.execute(
            sa.text("UPDATE session SET creator_id = :mentor_id, session_type = 'individual', max_participants = 2 WHERE id = :session_id"),
            {"mentor_id": mentor_id, "session_id": session_id}
        )

        # Add mentor to session_participant
        if mentor_id:
            connection.execute(
                sa.text("INSERT INTO session_participant (session_id, user_id, role, status) VALUES (:session_id, :user_id, 'mentor', 'accepted')"),
                {"session_id": session_id, "user_id": mentor_id}
            )

        # Add mentee to session_participant
        if mentee_id:
            connection.execute(
                sa.text("INSERT INTO session_participant (session_id, user_id, role, status) VALUES (:session_id, :user_id, 'mentee', 'accepted')"),
                {"session_id": session_id, "user_id": mentee_id}
            )


def downgrade():
    # Drop session_participant table
    op.drop_table('session_participant')

    # Remove creator_id, session_type, and max_participants columns from session table
    with op.batch_alter_table('session', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('max_participants')
        batch_op.drop_column('session_type')
        batch_op.drop_column('creator_id')
