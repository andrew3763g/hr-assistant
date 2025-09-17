"""switch jsonb columns to json

Revision ID: 0a40bef62829
Revises: f96b6a424729
Create Date: 2025-09-17 17:42:20.068111

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0a40bef62829"
down_revision: Union[str, Sequence[str], None] = "f96b6a424729"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Column lists with nullability metadata
JSON_COLUMNS: dict[str, list[tuple[str, bool]]] = {
    "evaluations": [
        ("scores_breakdown", True),
        ("identity_match", True),
        ("red_flags", True),
        ("auto_reject_reasons", True),
        ("strengths", True),
        ("weaknesses", True),
        ("skills_match", True),
        ("follow_up_questions", True),
        ("areas_to_probe", True),
        ("gpt_personality_insights", True),
    ],
    "interviews": [
        ("questions_data", False),
        ("answers_data", True),
        ("audio_recordings", True),
        ("transcriptions", True),
        ("browser_info", True),
        ("red_flags_triggered", True),
        ("identity_verification", True),
        ("technical_issues", True),
    ],
    "interview_answers": [
        ("ai_analysis", True),
    ],
    "interview_evaluations": [
        ("match_details", True),
    ],
}


def _alter_columns(
    target_type: postgresql.JSON | postgresql.JSONB,
    using_cast: str,
) -> None:
    existing_type = (
        postgresql.JSONB(astext_type=sa.Text())
        if using_cast == "::json"
        else postgresql.JSON(astext_type=sa.Text())
    )
    for table, columns in JSON_COLUMNS.items():
        for column, nullable in columns:
            op.alter_column(
                table,
                column,
                existing_type=existing_type,
                type_=target_type,
                existing_nullable=nullable,
                postgresql_using=f"{column}{using_cast}",
            )


def upgrade() -> None:
    """Alter JSONB columns to JSON."""
    target = postgresql.JSON(astext_type=sa.Text())
    _alter_columns(target, "::json")


def downgrade() -> None:
    """Revert JSON columns back to JSONB."""
    target = postgresql.JSONB(astext_type=sa.Text())
    _alter_columns(target, "::jsonb")