"""Add interview and evaluation tables

Revision ID: 001
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create interviews table
    op.create_table('interviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('vacancy_id', sa.Integer(), nullable=False),
        sa.Column('interview_token', sa.String(length=255), nullable=False),
        sa.Column('interview_url', sa.String(length=500), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('progress_percent', sa.Integer(), nullable=True),
        sa.Column('questions_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('total_questions', sa.Integer(), nullable=False),
        sa.Column('answered_questions', sa.Integer(), nullable=True),
        sa.Column('skipped_questions', sa.Integer(), nullable=True),
        sa.Column('answers_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('audio_recordings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('transcriptions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('browser_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('total_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('average_answer_time', sa.Float(), nullable=True),
        sa.Column('red_flags_triggered', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('identity_verification', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('technical_issues', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('evaluated_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('audio_gdrive_id', sa.String(length=255), nullable=True),
        sa.Column('transcript_gdrive_id', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ),
        sa.ForeignKeyConstraint(['vacancy_id'], ['vacancies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_interviews_id'), 'interviews', ['id'], unique=False)
    op.create_index('ix_interviews_candidate_id', 'interviews', ['candidate_id'], unique=False)
    op.create_index('ix_interviews_interview_token', 'interviews', ['interview_token'], unique=True)
    op.create_index('ix_interviews_started_at', 'interviews', ['started_at'], unique=False)
    op.create_index('ix_interviews_status', 'interviews', ['status'], unique=False)
    op.create_index('ix_interviews_vacancy_id', 'interviews', ['vacancy_id'], unique=False)

    # Create interview_questions table
    op.create_table('interview_questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('interview_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('question_type', sa.String(length=50), nullable=False),
        sa.Column('question_category', sa.String(length=50), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('is_required', sa.Boolean(), nullable=True),
        sa.Column('time_limit_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['interview_id'], ['interviews.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_interview_questions_id'), 'interview_questions', ['id'], unique=False)

    # Create interview_answers table
    op.create_table('interview_answers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('interview_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('answer_text', sa.Text(), nullable=True),
        sa.Column('answer_audio_url', sa.String(length=500), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('is_answered', sa.Boolean(), nullable=True),
        sa.Column('is_skipped', sa.Boolean(), nullable=True),
        sa.Column('is_timeout', sa.Boolean(), nullable=True),
        sa.Column('ai_analysis', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('sentiment_score', sa.Float(), nullable=True),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('answered_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['interview_id'], ['interviews.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_interview_answers_id'), 'interview_answers', ['id'], unique=False)
    op.create_index('ix_interview_answers_interview_question', 'interview_answers', ['interview_id', 'question_id'], unique=False)

    # Create evaluations table
    op.create_table('evaluations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('interview_id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('total_score', sa.Float(), nullable=False),
        sa.Column('max_possible_score', sa.Float(), nullable=False),
        sa.Column('score_percentage', sa.Float(), nullable=False),
        sa.Column('scores_breakdown', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('response_rate', sa.Float(), nullable=False),
        sa.Column('confidence_average', sa.Float(), nullable=True),
        sa.Column('identity_match', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('red_flags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('auto_reject_reasons', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('strengths', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('weaknesses', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('skills_match', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('decision', sa.String(length=50), nullable=False),
        sa.Column('rank_in_vacancy', sa.Integer(), nullable=True),
        sa.Column('percentile', sa.Float(), nullable=True),
        sa.Column('hr_recommendations', sa.Text(), nullable=True),
        sa.Column('follow_up_questions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('areas_to_probe', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('gpt_summary', sa.Text(), nullable=True),
        sa.Column('gpt_personality_insights', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('gpt_cultural_fit', sa.Float(), nullable=True),
        sa.Column('report_generated', sa.Boolean(), nullable=True),
        sa.Column('report_gdrive_id', sa.String(length=255), nullable=True),
        sa.Column('notification_sent', sa.Boolean(), nullable=True),
        sa.Column('notification_template', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('hr_reviewed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('hr_override_decision', sa.String(length=50), nullable=True),
        sa.Column('hr_comments', sa.Text(), nullable=True),
        sa.Column('hr_adjusted_score', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ),
        sa.ForeignKeyConstraint(['interview_id'], ['interviews.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('interview_id')
    )
    op.create_index(op.f('ix_evaluations_id'), 'evaluations', ['id'], unique=False)
    op.create_index('ix_evaluations_candidate_id', 'evaluations', ['candidate_id'], unique=False)
    op.create_index('ix_evaluations_decision', 'evaluations', ['decision'], unique=False)
    op.create_index('ix_evaluations_interview_id', 'evaluations', ['interview_id'], unique=False)
    op.create_index('ix_evaluations_total_score', 'evaluations', ['total_score'], unique=False)

    # Create vacancy_matches table
    op.create_table('vacancy_matches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('vacancy_id', sa.Integer(), nullable=False),
        sa.Column('match_score', sa.Float(), nullable=False),
        sa.Column('match_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('skills_coverage', sa.Float(), nullable=True),
        sa.Column('experience_fit', sa.Float(), nullable=True),
        sa.Column('salary_fit', sa.Float(), nullable=True),
        sa.Column('gpt_match_reasoning', sa.Text(), nullable=True),
        sa.Column('gpt_recommended', sa.Boolean(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('interview_scheduled', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=True),
