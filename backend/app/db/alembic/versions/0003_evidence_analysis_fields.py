"""Add analysis fields to evidence table

Revision ID: 0003_evidence_analysis_fields
Revises: 0002_active_risk_outcomes
Create Date: 2026-03-27 00:00:00.000000

Adds per-file AI analysis columns to the evidence table:
- analysis_summary: plain-English summary of what was found
- analysis_findings: structured findings array from Bedrock
- risk_indicators: key risk signals extracted by AI
- document_type_confidence: confidence in auto-detected document type
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers
revision = '0003_evidence_analysis_fields'
down_revision = '0002_active_risk_outcomes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('evidence', sa.Column(
        'analysis_summary', sa.Text(), nullable=True,
        comment='AI-generated plain-English summary of document findings'
    ))
    op.add_column('evidence', sa.Column(
        'analysis_findings', JSONB(), nullable=True,
        comment='Structured findings array from per-file Bedrock analysis'
    ))
    op.add_column('evidence', sa.Column(
        'risk_indicators', JSONB(), nullable=True,
        comment='Key risk signals: critical_vulns, missing_controls, compliance_gaps, etc.'
    ))
    op.add_column('evidence', sa.Column(
        'document_type_confidence', sa.Integer(), nullable=True,
        comment='0-100 confidence score for auto-detected document_type'
    ))


def downgrade() -> None:
    op.drop_column('evidence', 'document_type_confidence')
    op.drop_column('evidence', 'risk_indicators')
    op.drop_column('evidence', 'analysis_findings')
    op.drop_column('evidence', 'analysis_summary')
