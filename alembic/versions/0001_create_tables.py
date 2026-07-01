"""create tables

Revision ID: 0001_create_tables
Revises: 
Create Date: 2026-07-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = '0001_create_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'clientes',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('apellido', sa.String(length=100), nullable=False),
        sa.Column('identificacion', sa.String(length=50), nullable=False, unique=True),
        sa.Column('telefono', sa.String(length=30), nullable=True),
        sa.Column('email', sa.String(length=120), nullable=True),
        sa.Column('fecha_registro', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_table(
        'estados_reserva',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('nombre', sa.String(length=50), nullable=False, unique=True),
    )
    op.create_table(
        'reservas',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.Column('restaurante_id', sa.Integer(), nullable=False),
        sa.Column('sucursal_id', sa.Integer(), nullable=False),
        sa.Column('mesa_id', sa.Integer(), nullable=False),
        sa.Column('fecha', sa.DateTime(timezone=True), nullable=False),
        sa.Column('hora_inicio', sa.DateTime(timezone=True), nullable=False),
        sa.Column('hora_fin', sa.DateTime(timezone=True), nullable=False),
        sa.Column('numero_personas', sa.Integer(), nullable=False),
        sa.Column('estado_id', sa.Integer(), nullable=False),
        sa.Column('fecha_creacion', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('fecha_confirmacion', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        'anticipos',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('reserva_id', sa.Integer(), nullable=False),
        sa.Column('monto', sa.Numeric(10, 2), nullable=False),
        sa.Column('metodo_pago', sa.String(length=50), nullable=False),
        sa.Column('fecha_pago', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('estado', sa.Enum('Pagado', 'Pendiente', name='estadoanticipo'), nullable=False),
    )
    op.create_table(
        'historial_estados_reserva',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('reserva_id', sa.Integer(), nullable=False),
        sa.Column('estado_anterior', sa.String(length=50), nullable=False),
        sa.Column('estado_nuevo', sa.String(length=50), nullable=False),
        sa.Column('fecha_cambio', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_table('historial_estados_reserva')
    op.drop_table('anticipos')
    op.drop_table('reservas')
    op.drop_table('estados_reserva')
    op.drop_table('clientes')
