# src/feeds/management/commands/generate_scheduled_feeds.py
from django.core.management.base import BaseCommand
from feeds.models import DataFeed, FeedGeneration
from django.utils import timezone


class Command(BaseCommand):
    help = 'Generate feeds that are scheduled for generation'

    def handle(self, *args, **options):
        # Find feeds that need to be generated
        feeds_to_generate = DataFeed.objects.filter(
            is_active=True,
            # Add scheduling logic here based on subscription settings
        )

        generated_count = 0

        for feed in feeds_to_generate:
            # Check if there's already a pending generation
            if feed.generations.filter(status='pending').exists():
                self.stdout.write(f'Skipping {feed.name} - generation in progress')
                continue

            # Create new generation
            generation = FeedGeneration.objects.create(
                feed=feed,
                status='pending'
            )

            # Start generation (would use Celery in production)
            # generate_feed_task.delay(generation.id)

            generated_count += 1
            self.stdout.write(f'Started generation for {feed.name}')

        self.stdout.write(
            self.style.SUCCESS(f'Started generation for {generated_count} feeds')
        )