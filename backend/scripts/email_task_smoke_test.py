import os
import subprocess
import sys

base_env = os.environ.copy()
base_env.setdefault('SECRET_KEY', 'x' * 32)
base_env.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///./dummy.db')
base_env.setdefault('REDIS_URL', 'redis://localhost:6379/0')

fake_env = base_env.copy()
fake_env['EMAIL_PROVIDER'] = 'fake'
cmd = [sys.executable, '-c', 'from app.services.email_service import EmailService; print(EmailService.send_email("a@b.com","t","<p>x</p>"))']
print('fake run:')
subprocess.run(cmd, env={**fake_env, 'PYTHONPATH': 'backend'}, check=True)

resend_env = base_env.copy()
resend_env['EMAIL_PROVIDER'] = 'resend'
resend_env.pop('RESEND_API_KEY', None)
print('resend(no key) run:')
subprocess.run(cmd, env={**resend_env, 'PYTHONPATH': 'backend'}, check=True)
