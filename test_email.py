#!/usr/bin/env python
"""
Quick script to test SendGrid email sending
Run with: python test_email.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

print('=' * 60)
print('Testing SendGrid Email Configuration')
print('=' * 60)
print(f'Backend: {settings.EMAIL_BACKEND}')
print(f'Host: {settings.EMAIL_HOST}')
print(f'Port: {settings.EMAIL_PORT}')
print(f'From Email: {settings.DEFAULT_FROM_EMAIL}')
print(f'Use TLS: {settings.EMAIL_USE_TLS}')
print('=' * 60)

recipient = input('Enter recipient email (or press Enter for same as sender): ').strip()
if not recipient:
    recipient = settings.DEFAULT_FROM_EMAIL

try:
    result = send_mail(
        subject='KitaabSe - SendGrid Test',
        message='🎉 Congratulations! Your SendGrid integration is working perfectly!',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
        fail_silently=False,
    )
    print(f'\n✅ SUCCESS! Email sent to {recipient}')
    print(f'   Result: {result} email(s) sent')
except Exception as e:
    print(f'\n❌ ERROR: {str(e)}')
    print('\nTroubleshooting:')
    print('1. Verify your sender email at: https://app.sendgrid.com/settings/sender_auth/senders')
    print('2. Check that SENDGRID_API_KEY in .env is correct')
    print('3. Ensure DEFAULT_FROM_EMAIL matches the verified sender')
