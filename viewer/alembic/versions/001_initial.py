"""Initial database schema

Revision ID: 001_initial
Revises: 
Create Date: 2025-11-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users 테이블 생성
    op.create_table(
        'Users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('LoginId', sa.String(50), nullable=False),
        sa.Column('PasswordHash', sa.String(255), nullable=False),
        sa.Column('UserName', sa.String(30), nullable=False),
        sa.Column('Role', sa.String(10), nullable=False, server_default='user'),
        sa.Column('UserImage', sa.String(255), nullable=True),
        sa.Column('CreatedAt', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('UpdatedAt', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('LoginId')
    )
    op.create_index('ix_users_id', 'Users', ['id'])
    op.create_index('ix_users_loginid', 'Users', ['LoginId'])

    # Bookmarks 테이블 생성
    op.create_table(
        'Bookmarks',
        sa.Column('BookmarkId', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('UserId', sa.Integer(), nullable=False),
        sa.Column('VolumeName', sa.String(255), nullable=False),
        sa.Column('VolumeUrl', sa.Text(), nullable=False),
        sa.Column('Title', sa.String(255), nullable=True),
        sa.Column('Description', sa.Text(), nullable=True),
        sa.Column('CreatedAt', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('UpdatedAt', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('BookmarkId'),
        sa.ForeignKeyConstraint(['UserId'], ['Users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_bookmarks_id', 'Bookmarks', ['BookmarkId'])
    op.create_index('ix_bookmarks_userid', 'Bookmarks', ['UserId'])

    # ImageLog 테이블 생성
    op.create_table(
        'ImageLog',
        sa.Column('ImageLogId', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('UserId', sa.Integer(), nullable=False),
        sa.Column('ImageId', sa.String(100), nullable=True),
        sa.Column('ChunkCount', sa.Integer(), nullable=True),
        sa.Column('ImageSize', sa.Integer(), nullable=True),
        sa.Column('CreateAt', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('EndAt', sa.DateTime(), nullable=True),
        sa.Column('Status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('FileBasePath', sa.String(255), nullable=True),
        sa.Column('TotalTime', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('ImageLogId'),
        sa.ForeignKeyConstraint(['UserId'], ['Users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_imagelog_id', 'ImageLog', ['ImageLogId'])
    op.create_index('ix_imagelog_userid', 'ImageLog', ['UserId'])


def downgrade() -> None:
    op.drop_index('ix_imagelog_userid', table_name='ImageLog')
    op.drop_index('ix_imagelog_id', table_name='ImageLog')
    op.drop_table('ImageLog')
    
    op.drop_index('ix_bookmarks_userid', table_name='Bookmarks')
    op.drop_index('ix_bookmarks_id', table_name='Bookmarks')
    op.drop_table('Bookmarks')
    
    op.drop_index('ix_users_loginid', table_name='Users')
    op.drop_index('ix_users_id', table_name='Users')
    op.drop_table('Users')
