"""
Remove unique constraint from model_key, add composite unique on (provider, model_key)

Revision ID: fix_model_key_constraint
Revises: 
Create Date: 2025-11-03
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fix_model_key_constraint'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # SQLite doesn't support ALTER COLUMN or DROP CONSTRAINT directly
    # We need to recreate the table
    
    # Step 1: Create new table with correct constraints
    op.create_table(
        'ai_model_pricing_new',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_key', sa.String(), nullable=False),
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('credit_multiplier', sa.Float(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('api_cost_per_1m_input', sa.Float(), nullable=True),
        sa.Column('api_cost_per_1m_output', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'model_key', name='uq_provider_model_key')  # Composite unique
    )
    
    # Step 2: Copy data from old table
    op.execute('''
        INSERT INTO ai_model_pricing_new 
        SELECT * FROM ai_model_pricing
    ''')
    
    # Step 3: Drop old table
    op.drop_table('ai_model_pricing')
    
    # Step 4: Rename new table
    op.rename_table('ai_model_pricing_new', 'ai_model_pricing')
    
    # Step 5: Recreate indexes
    op.create_index('ix_ai_model_pricing_id', 'ai_model_pricing', ['id'])
    op.create_index('ix_ai_model_pricing_model_key', 'ai_model_pricing', ['model_key'])

def downgrade():
    # Reverse: back to unique model_key only
    op.create_table(
        'ai_model_pricing_old',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_key', sa.String(), nullable=False),
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('credit_multiplier', sa.Float(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('api_cost_per_1m_input', sa.Float(), nullable=True),
        sa.Column('api_cost_per_1m_output', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('model_key', name='uq_model_key')  # Single unique
    )
    
    op.execute('''
        INSERT INTO ai_model_pricing_old 
        SELECT * FROM ai_model_pricing
    ''')
    
    op.drop_table('ai_model_pricing')
    op.rename_table('ai_model_pricing_old', 'ai_model_pricing')
    op.create_index('ix_ai_model_pricing_id', 'ai_model_pricing', ['id'])
    op.create_index('ix_ai_model_pricing_model_key', 'ai_model_pricing', ['model_key'])
