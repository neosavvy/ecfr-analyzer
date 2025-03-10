"""Create document_contents table

Revision ID: 567aa2c2e029
Revises: 10e0055128ce
Create Date: 2025-03-04 19:53:23.034527

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '567aa2c2e029'
down_revision: Union[str, None] = '10e0055128ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('document_contents',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('descriptor_id', sa.UUID(), nullable=False),
    sa.Column('agency_id', sa.Integer(), nullable=False),
    sa.Column('version_date', sa.Date(), nullable=False),
    sa.Column('raw_xml', sa.Text(), nullable=False),
    sa.Column('processed_text', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ),
    sa.ForeignKeyConstraint(['descriptor_id'], ['agency_title_search_descriptors.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('document_contents')
    # ### end Alembic commands ###
