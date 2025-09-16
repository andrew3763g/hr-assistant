"""mvp: add original_text/doc_hash and file refs

Revision ID: 35fe5d9e9926
Revises: 7f2f66b5d14e
Create Date: 2025-09-13 16:43:41.863048

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '35fe5d9e9926'
down_revision: Union[str, Sequence[str], None] = '7f2f66b5d14e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def _col_exists(table: str, column: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return column in {c["name"] for c in insp.get_columns(table)}


def _idx_exists(table: str, name: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return name in {i["name"] for i in insp.get_indexes(table)}


def _uq_exists(table: str, name: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return name in {u["name"] for u in insp.get_unique_constraints(table)}


def upgrade() -> None:
    # ----- candidates -----
    if not _col_exists("candidates", "original_text"):
        op.add_column("candidates", sa.Column("original_text", sa.Text(), nullable=True))

    if not _col_exists("candidates", "doc_hash"):
        op.add_column("candidates", sa.Column("doc_hash", sa.String(length=64), nullable=True))

    if not _col_exists("candidates", "resume_file_path"):
        op.add_column("candidates", sa.Column("resume_file_path", sa.String(length=500), nullable=True))

    if not _col_exists("candidates", "resume_gdrive_id"):
        op.add_column("candidates", sa.Column("resume_gdrive_id", sa.String(length=255), nullable=True))

    # уникальность/индекс для doc_hash (NULL допускаются, дубликаты не-NULL запрещены)
    if not _uq_exists("candidates", "uq_candidates_doc_hash"):
        op.create_unique_constraint("uq_candidates_doc_hash", "candidates", ["doc_hash"])
    if not _idx_exists("candidates", "ix_candidates_doc_hash"):
        op.create_index("ix_candidates_doc_hash", "candidates", ["doc_hash"])

    # ----- vacancies (на случай, если этих полей ещё нет) -----
    if not _col_exists("vacancies", "source_file_path"):
        op.add_column("vacancies", sa.Column("source_file_path", sa.String(length=500), nullable=True))

    if not _col_exists("vacancies", "source_gdrive_id"):
        op.add_column("vacancies", sa.Column("source_gdrive_id", sa.String(length=255), nullable=True))

    if not _col_exists("vacancies", "original_text"):
        op.add_column("vacancies", sa.Column("original_text", sa.Text(), nullable=True))


def downgrade() -> None:
    # порядок обратный: сначала индексы/ограничения
    if _idx_exists("candidates", "ix_candidates_doc_hash"):
        op.drop_index("ix_candidates_doc_hash", table_name="candidates")
    if _uq_exists("candidates", "uq_candidates_doc_hash"):
        op.drop_constraint("uq_candidates_doc_hash", "candidates", type_="unique")

    # затем столбцы (проверка на существование, чтобы не падать)
    for col in ("resume_gdrive_id", "resume_file_path", "doc_hash", "original_text"):
        if _col_exists("candidates", col):
            op.drop_column("candidates", col)

    for col in ("source_gdrive_id", "source_file_path", "original_text"):
        if _col_exists("vacancies", col):
            op.drop_column("vacancies", col)
