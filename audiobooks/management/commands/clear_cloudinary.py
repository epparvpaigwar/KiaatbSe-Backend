"""
Django management command to clear all files from Cloudinary
"""
import cloudinary
import cloudinary.api
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Delete all audio files from Cloudinary cloud storage'

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        """Delete all files from Cloudinary"""

        # Check if Cloudinary is configured
        try:
            from decouple import config
            cloud_name = config('CLOUDINARY_CLOUD_NAME', default='')
            if not cloud_name:
                self.stdout.write(self.style.ERROR('Cloudinary not configured! Check your .env file.'))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error checking Cloudinary config: {str(e)}'))
            return

        # Confirmation prompt
        if not options['yes']:
            confirm = input('This will delete ALL files from Cloudinary. Are you sure? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING('Operation cancelled.'))
                return

        try:
            self.stdout.write('Fetching files from Cloudinary...')

            # Delete all resources in the kitaabse folder
            deleted_count = 0

            # Get all resources with prefix 'kitaabse'
            result = cloudinary.api.resources(
                type='upload',
                prefix='kitaabse/',
                resource_type='video',  # MP3 files are stored as video
                max_results=500
            )

            if not result.get('resources'):
                self.stdout.write(self.style.SUCCESS('No files found in Cloudinary.'))
                return

            total_files = len(result['resources'])
            self.stdout.write(f'Found {total_files} files. Deleting...')

            # Delete each resource
            for resource in result['resources']:
                public_id = resource['public_id']
                try:
                    cloudinary.uploader.destroy(
                        public_id,
                        resource_type='video',
                        invalidate=True
                    )
                    deleted_count += 1
                    self.stdout.write(f'Deleted: {public_id}')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Failed to delete {public_id}: {str(e)}'))

            # Also delete the folder
            try:
                cloudinary.api.delete_folder('kitaabse')
                self.stdout.write('Deleted folder: kitaabse')
            except:
                pass  # Folder might not be empty or might not exist

            self.stdout.write(self.style.SUCCESS(f'\nSuccessfully deleted {deleted_count} files from Cloudinary!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
