"""
Django management command to clear all data from Redis
"""
import redis
from django.core.management.base import BaseCommand
from decouple import config


class Command(BaseCommand):
    help = 'Clear all data from Redis database (Celery tasks, cache, etc.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        """Clear all data from Redis"""

        # Get Redis connection details from environment
        try:
            redis_url = config('REDIS_URL', default='redis://localhost:6379/0')

            if not redis_url:
                self.stdout.write(self.style.ERROR('Redis not configured! Check your .env file.'))
                return

            self.stdout.write(f'Using Redis URL: {redis_url.split("@")[-1] if "@" in redis_url else redis_url}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error reading Redis config: {str(e)}'))
            return

        # Confirmation prompt
        if not options['yes']:
            confirm = input('This will delete ALL data from Redis (Celery tasks, cache, etc.). Are you sure? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING('Operation cancelled.'))
                return

        try:
            self.stdout.write('Connecting to Redis...')

            # Connect to Redis
            r = redis.from_url(redis_url)

            # Get database info before clearing
            info = r.info('keyspace')
            db_info = info.get('db0', {})
            keys_count = db_info.get('keys', 0) if isinstance(db_info, dict) else 0

            if keys_count == 0:
                self.stdout.write(self.style.SUCCESS('Redis is already empty.'))
                return

            self.stdout.write(f'Found {keys_count} keys in Redis. Clearing...')

            # Flush all data from current database
            r.flushdb()

            self.stdout.write(self.style.SUCCESS(f'\nSuccessfully cleared {keys_count} keys from Redis!'))
            self.stdout.write(self.style.SUCCESS('All Celery tasks and cache data have been removed.'))

        except redis.exceptions.ConnectionError as e:
            self.stdout.write(self.style.ERROR(f'Cannot connect to Redis: {str(e)}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
