"""Add outcome tracking columns to active_risks

Revision ID: 0002_active_risk_outcomes
Revises: 0001_initial
Create Date: 2026-02-24 00:00:00.000000

Adds 5 columns to active_risks for real-world outcome capture, which feeds
ground-truth labels back into the ML model training pipeline (Stage 1 of the
ML improvement roadmap).
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '0002_active_risk_outcomes'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('active_risks', sa.Column(
        'outcome', sa.String(50), nullable=True,
        comment='materialized_breach | materialized_incident | mitigated_successfully | accepted_no_incident | expired_unresolved'
    ))
    op.add_column('active_risks', sa.Column(
        'outcome_recorded_at', sa.DateTime(timezone=True), nullable=True
    ))
    op.add_column('active_risks', sa.Column(
        'outcome_severity', sa.String(20), nullable=True,
        comment='none | minor | moderate | major | critical'
    ))
    op.add_column('active_risks', sa.Column(
        'days_to_resolution', sa.Integer(), nullable=True,
        comment='Actual days open before closing — ground truth for survival model'
    ))
    op.add_column('active_risks', sa.Column(
        'false_positive', sa.Boolean(), nullable=False, server_default='false',
        comment='Risk owner marks: this was never a real risk'
    ))

    # Index on outcome for fast training data queries
    op.create_index(
        'ix_active_risks_outcome',
        'active_risks',
        ['outcome'],
        postgresql_where=sa.text("outcome IS NOT NULL")
    )


def downgrade() -> None:
    op.drop_index('ix_active_risks_outcome', table_name='active_risks')
    op.drop_column('active_risks', 'false_positive')
    op.drop_column('active_risks', 'days_to_resolution')
    op.drop_column('active_risks', 'outcome_severity')
    op.drop_column('active_risks', 'outcome_recorded_at')
    op.drop_column('active_risks', 'outcome')
