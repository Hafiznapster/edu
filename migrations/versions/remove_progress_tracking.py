"""Remove progress tracking models

Revision ID: remove_progress_tracking
Revises: b750e33f1f2c
Create Date: 2023-07-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_progress_tracking'
down_revision = 'b750e33f1f2c'
branch_labels = None
depends_on = None


def upgrade():
    # Drop progress_milestone table
    op.drop_table('progress_milestone')
    
    # Drop progress_tracker table
    op.drop_table('progress_tracker')


def downgrade():
    # Create progress_tracker table
    op.create_table('progress_tracker',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('mentee_id', sa.Integer(), nullable=True),
    sa.Column('mentor_id', sa.Integer(), nullable=True),
    sa.Column('learning_path_id', sa.Integer(), nullable=True),
    sa.Column('start_date', sa.DateTime(), nullable=True),
    sa.Column('target_completion_date', sa.DateTime(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('overall_progress', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['learning_path_id'], ['learning_path.id'], ),
    sa.ForeignKeyConstraint(['mentee_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['mentor_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    
    # Create progress_milestone table
    op.create_table('progress_milestone',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tracker_id', sa.Integer(), nullable=True),
    sa.Column('title', sa.String(length=200), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('due_date', sa.DateTime(), nullable=True),
    sa.Column('completed_date', sa.DateTime(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('order', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['tracker_id'], ['progress_tracker.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
