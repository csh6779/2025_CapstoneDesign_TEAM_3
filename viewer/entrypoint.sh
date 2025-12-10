#!/bin/bash
set -e

echo "=========================================="
echo "🚀 Starting ATI Viewer Backend"
echo "=========================================="

cd /viewer

# JSON 기반 사용자 데이터 초기화
echo "👤 Initializing user data..."
python -c "
import json
import os
from pathlib import Path
from passlib.context import CryptContext
from datetime import datetime

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

users_file = Path('/viewer/data/users.json')
users_file.parent.mkdir(parents=True, exist_ok=True)

if not users_file.exists():
    users = {
        'admin': {
            'LoginId': 'admin',
            'UserName': 'Administrator',
            'PasswordHash': pwd_context.hash('admin1234'),
            'Role': 'admin',
            'CreatedAt': datetime.now().isoformat(),
            'UpdatedAt': datetime.now().isoformat()
        }
    }
    with open(users_file, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)
    print('✅ Admin account created: admin / admin1234')
else:
    print('ℹ️  User data already exists')
"

echo "=========================================="
echo "🎉 Starting Uvicorn server..."
echo "=========================================="

exec uvicorn main:app --host 0.0.0.0 --port 9000 --reload
