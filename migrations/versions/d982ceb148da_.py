"""empty message

Revision ID: d982ceb148da
Revises: 57f1490b974a
Create Date: 2016-04-16 16:45:30.410760

"""

# revision identifiers, used by Alembic.
revision = 'd982ceb148da'
down_revision = '57f1490b974a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('avatar_hash', sa.String(length=32), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'avatar_hash')
    ### end Alembic commands ###