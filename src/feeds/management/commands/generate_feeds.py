# feeds/management/commands/generate_feeds.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from src.feeds.models import DataFeed, FeedGeneration
from src.feeds.generators import FeedGeneratorFactory
from src.core.notifications import NotificationService
import logging

logger = logging.getLogger('solidus.feeds')


class Command(BaseCommand):
    help = 'Generate scheduled data feeds'

    def add_arguments(self, parser):
        parser.add_argument(
            '--feed-id',
            type=int,
            help='Generate a specific feed by ID'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force generation even if not scheduled'
        )

    def handle(self, *args, **options):
        feed_id = options.get('feed_id')
        force = options.get('force', False)

        if feed_id:
            # Generate specific feed
            try:
                feed = DataFeed.objects.get(id=feed_id)
                if not feed.is_active and not force:
                    self.stdout.write(
                        self.style.WARNING(f'Feed {feed.name} is not active')
                    )
                    return

                self.generate_feed(feed)
            except DataFeed.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Feed {feed_id} not found')
                )
        else:
            # Generate all scheduled feeds
            self.generate_scheduled_feeds()

    def generate_scheduled_feeds(self):
        """Generate all feeds that are due"""
        now = timezone.now()

        # Find feeds that need generation
        feeds = DataFeed.objects.filter(
            is_active=True
        ).exclude(
            frequency='manual'
        )

        generated_count = 0

        for feed in feeds:
            next_run = feed.get_next_run_time()

            # Check if feed should run
            should_run = False

            if feed.frequency == 'hourly':
                # Run if last generated more than an hour ago
                if not feed.last_generated or (now - feed.last_generated).seconds >= 3600:
                    should_run = True

            elif feed.frequency == 'daily' and feed.schedule_time:
                # Run if it's past the scheduled time and hasn't run today
                if not feed.last_generated or feed.last_generated.date() < now.date():
                    scheduled_today = timezone.datetime.combine(
                        now.date(), feed.schedule_time
                    )
                    if now.time() >= feed.schedule_time:
                        should_run = True

            elif feed.frequency == 'weekly' and feed.schedule_day is not None:
                # Run if it's the right day and hasn't run this week
                if now.weekday() == feed.schedule_day:
                    if not feed.last_generated or (now - feed.last_generated).days >= 7:
                        should_run = True

            elif feed.frequency == 'monthly' and feed.schedule_day:
                # Run if it's the right day and hasn't run this month
                if now.day == feed.schedule_day:
                    if not feed.last_generated or feed.last_generated.month != now.month:
                        should_run = True

            if should_run:
                self.stdout.write(f'Generating feed: {feed.name}')
                self.generate_feed(feed)
                generated_count += 1

        if generated_count == 0:
            self.stdout.write('No feeds to generate at this time')
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Generated {generated_count} feeds')
            )

    def generate_feed(self, feed):
        """Generate a single feed"""
        generation = None

        try:
            # Create generation record
            generation = FeedGeneration.objects.create(
                feed=feed,
                status='generating'
            )

            # Notify user that generation started
            NotificationService.send_feed_status_update(
                user=feed.customer,
                feed_id=generation.generation_id,
                status='generating',
                message=f'Generating {feed.name}...'
            )

            # Get appropriate generator
            generator = FeedGeneratorFactory.get_generator(feed)

            # Generate the feed
            result = generator.generate(generation)

            if result['success']:
                # Update generation record
                generation.status = 'generated'
                generation.completed_at = timezone.now()
                generation.file_path = result['file_path']
                generation.file_size = result['file_size']
                generation.row_count = result.get('row_count', 0)
                generation.save()

                # Update feed
                feed.last_generated = timezone.now()
                feed.generation_count += 1
                feed.save()

                # Deliver the feed
                if feed.delivery_method != 'download':
                    self.deliver_feed(generation)
                else:
                    generation.status = 'completed'
                    generation.save()

                    # Notify user
                    NotificationService.notify_feed_ready(generation)

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully generated feed: {feed.name}'
                    )
                )
            else:
                raise Exception(result.get('error', 'Unknown error'))

        except Exception as e:
            logger.error(f'Error generating feed {feed.id}: {str(e)}')

            if generation:
                generation.status = 'failed'
                generation.completed_at = timezone.now()
                generation.error_message = str(e)
                generation.save()

            # Notify user of failure
            NotificationService.send_feed_status_update(
                user=feed.customer,
                feed_id=generation.generation_id if generation else None,
                status='failed',
                message=f'Failed to generate {feed.name}: {str(e)}'
            )

            self.stdout.write(
                self.style.ERROR(f'Failed to generate feed {feed.name}: {str(e)}')
            )

    def deliver_feed(self, generation):
        """Deliver the generated feed"""
        try:
            generation.status = 'delivering'
            generation.save()

            # Get delivery handler
            from src.feeds.delivery import DeliveryHandlerFactory
            handler = DeliveryHandlerFactory.get_handler(generation.feed)

            # Deliver the feed
            result = handler.deliver(generation)

            if result['success']:
                generation.status = 'completed'
                generation.delivered_at = timezone.now()
                generation.delivery_status = 'delivered'
                generation.delivery_details = result.get('details', {})

                # Update feed
                generation.feed.last_delivered = timezone.now()
                generation.feed.save()

                # Notify user
                NotificationService.notify_feed_ready(generation)
            else:
                generation.status = 'failed'
                generation.delivery_status = 'failed'
                generation.error_message = result.get('error', 'Delivery failed')

            generation.save()

        except Exception as e:
            logger.error(f'Error delivering feed: {str(e)}')
            generation.status = 'failed'
            generation.delivery_status = 'failed'
            generation.error_message = str(e)
            generation.save()