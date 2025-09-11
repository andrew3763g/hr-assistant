# r: 4a9a2026e490  |  dr: 7cb3fd326005
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4a9a2026e490'
down_revision = '7cb3fd326005'
branch_labels = None
depends_on = None


def upgrade():
    # Оставляем таблицу и все существующие FK/индексы как есть.
    # Подчищаем только лишние колонки, если вдруг они есть.
    op.execute("""
    ALTER TABLE vacancy_matches
        DROP COLUMN IF EXISTS match_score,
        DROP COLUMN IF EXISTS match_details,
        DROP COLUMN IF EXISTS is_active,
        DROP COLUMN IF EXISTS skills_coverage,
        DROP COLUMN IF EXISTS experience_fit,
        DROP COLUMN IF EXISTS salary_fit,
        DROP COLUMN IF EXISTS gpt_reasoning,
        DROP COLUMN IF EXISTS gpt_recommended,
        DROP COLUMN IF EXISTS interview_scheduled
    """)
    # Никаких create_foreign_key / create_index тут не делаем.


def downgrade():
    # Восстановление колонок на случай отката (типы подобраны безопасно).
    op.add_column('vacancy_matches', sa.Column('match_score', sa.Float(), nullable=True))
    op.add_column('vacancy_matches', sa.Column('match_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('vacancy_matches', sa.Column('is_active', sa.Boolean(), nullable=True))
    op.add_column('vacancy_matches', sa.Column('skills_coverage', sa.Float(), nullable=True))
    op.add_column('vacancy_matches', sa.Column('experience_fit', sa.Float(), nullable=True))
    op.add_column('vacancy_matches', sa.Column('salary_fit', sa.Float(), nullable=True))
    op.add_column('vacancy_matches', sa.Column('gpt_reasoning', sa.Text(), nullable=True))
    op.add_column('vacancy_matches', sa.Column('gpt_recommended', sa.Boolean(), nullable=True))
    op.add_column('vacancy_matches', sa.Column('interview_scheduled', sa.Boolean(), nullable=True))
