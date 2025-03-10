"""Create agency_title_search_descriptors table

Revision ID: 10e0055128ce
Revises: f10cd46d9e72
Create Date: 2025-03-04 19:35:39.134578

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '10e0055128ce'
down_revision: Union[str, None] = 'f10cd46d9e72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('agency_title_search_descriptors',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('agency_id', sa.Integer(), nullable=False),
    sa.Column('starts_on', sa.Date(), nullable=True),
    sa.Column('ends_on', sa.Date(), nullable=True),
    sa.Column('type', sa.String(), nullable=True),
    sa.Column('structure_index', sa.Integer(), nullable=True),
    sa.Column('reserved', sa.Boolean(), nullable=True),
    sa.Column('removed', sa.Boolean(), nullable=True),
    sa.Column('hierarchy', sa.JSON(), nullable=True),
    sa.Column('hierarchy_headings', sa.JSON(), nullable=True),
    sa.Column('headings', sa.JSON(), nullable=True),
    sa.Column('full_text_excerpt', sa.String(), nullable=True),
    sa.Column('score', sa.Float(), nullable=True),
    sa.Column('change_types', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('agency_title_search_descriptors')
    # ### end Alembic commands ###
