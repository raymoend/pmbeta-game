"""
Management command to give admin character resources for testing flags
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from main.models import Character


class Command(BaseCommand):
    help = 'Give admin character lots of resources for testing flags'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username', 
            type=str, 
            default='admin',
            help='Username to give resources to (default: admin)'
        )
        parser.add_argument(
            '--gold',
            type=int,
            default=100000,
            help='Amount of gold to give (default: 100000)'
        )

    def handle(self, *args, **options):
        username = options['username']
        gold_amount = options['gold']
        
        try:
            user = User.objects.get(username=username)
            character = Character.objects.get(user=user)
            
            # Give tons of resources
            character.gold += gold_amount
            character.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully gave {character.name} ({username}):')
            )
            self.stdout.write(f'  - {gold_amount:,} gold')
            self.stdout.write(f'  - Total gold now: {character.gold:,}')
            
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User "{username}" not found')
            )
        except Character.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Character for user "{username}" not found')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )
