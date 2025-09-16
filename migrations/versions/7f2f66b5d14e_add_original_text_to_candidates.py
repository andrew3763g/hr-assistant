"""add original_text to candidates

Revision ID: 7f2f66b5d14e
Revises: 812664fcf5ec
Create Date: 2025-09-13 14:51:31.262484

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f2f66b5d14e'
down_revision: Union[str, Sequence[str], None] = '812664fcf5ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("candidates", sa.Column("original_text", sa.Text(), nullable=True))

def downgrade():
    op.drop_column("candidates", "original_text")