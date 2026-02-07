"""Initial Phase 0 schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-02-05 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tenant table
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('region', sa.String(50), server_default='ca-west-1'),
        sa.Column('settings', postgresql.JSONB(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(255)),
        sa.Column('cognito_sub', sa.String(255)),
        sa.Column('roles', postgresql.JSONB(), server_default='["viewer"]'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', 'tenant_id', name='uq_user_email_tenant')
    )
    op.create_index('ix_users_email', 'users', ['email'])
    
    # Create assessments table
    op.create_table(
        'assessments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('system_background', sa.Text()),
        sa.Column('scope', sa.Text()),
        sa.Column('tech_stack', postgresql.JSONB(), server_default='[]'),
        sa.Column('overall_impact', sa.String(20), server_default='Medium'),
        sa.Column('status', sa.String(20), server_default='draft'),
        sa.Column('owner_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_assessments_tenant_id', 'assessments', ['tenant_id'])
    op.create_index('ix_assessments_owner_user_id', 'assessments', ['owner_user_id'])
    
    # Create threats table
    op.create_table(
        'threats',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('catalogue_key', sa.String(255)),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('detected_by', sa.String(50), server_default='manual'),
        sa.Column('cve_ids', postgresql.JSONB(), server_default='[]'),
        sa.Column('cvss_score', sa.String(10)),
        sa.Column('likelihood', sa.String(20), server_default='Medium'),
        sa.Column('likelihood_score', sa.Integer(), server_default='0'),
        sa.Column('impact', sa.String(20), server_default='Medium'),
        sa.Column('severity', sa.String(20), server_default='Medium'),
        sa.Column('ai_rationale', sa.Text()),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id']),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_threats_assessment_id', 'threats', ['assessment_id'])
    op.create_index('ix_threats_catalogue_key', 'threats', ['catalogue_key'])
    
    # Create evidence table
    op.create_table(
        'evidence',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('threat_id', postgresql.UUID(as_uuid=True)),
        sa.Column('uploaded_by_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('s3_key', sa.String(512), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('size_bytes', sa.Integer()),
        sa.Column('status', sa.String(50), server_default='ready'),
        sa.Column('extracted_text', sa.Text()),
        sa.Column('extract_metadata', postgresql.JSONB()),
        sa.Column('quality', sa.String(20), server_default='medium'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id']),
        sa.ForeignKeyConstraint(['threat_id'], ['threats.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_evidence_assessment_id', 'evidence', ['assessment_id'])
    
    # Create recommendations table
    op.create_table(
        'recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('threat_id', postgresql.UUID(as_uuid=True)),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('type', sa.String(50), server_default='remediation'),
        sa.Column('priority', sa.String(20), server_default='Medium'),
        sa.Column('status', sa.String(50), server_default='open'),
        sa.Column('owner_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_date', sa.DateTime(timezone=True)),
        sa.Column('confidence_score', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id']),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['threat_id'], ['threats.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create active_risks table
    op.create_table(
        'active_risks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('threat_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('residual_risk', sa.String(20), server_default='Medium'),
        sa.Column('risk_owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mitigation_plan', sa.Text()),
        sa.Column('acceptance_date', sa.DateTime(timezone=True)),
        sa.Column('review_cycle_days', sa.Integer(), server_default='30'),
        sa.Column('status', sa.String(50), server_default='open'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id']),
        sa.ForeignKeyConstraint(['risk_owner_id'], ['users.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['threat_id'], ['threats.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('action_type', sa.String(255), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=False),
        sa.Column('resource_id', sa.String(255), nullable=False),
        sa.Column('changes', postgresql.JSONB()),
        sa.Column('ip_address', sa.String(50)),
        sa.Column('user_agent', sa.String(512)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    
    # Create threat_catalogue table
    op.create_table(
        'threat_catalogue',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('catalogue_key', sa.String(255), nullable=False, unique=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('default_likelihood', sa.String(20), server_default='Medium'),
        sa.Column('default_impact', sa.String(20), server_default='Medium'),
        sa.Column('mitigations', postgresql.JSONB(), server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('threat_catalogue')
    op.drop_table('audit_logs')
    op.drop_table('active_risks')
    op.drop_table('recommendations')
    op.drop_table('evidence')
    op.drop_table('threats')
    op.drop_table('assessments')
    op.drop_table('users')
    op.drop_table('tenants')
