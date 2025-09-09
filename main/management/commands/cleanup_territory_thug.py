"""
Cleanup command: delete all 'Territory Thug' MonsterTemplates and any Monsters using them.
Usage:
  python manage.py cleanup_territory_thug
"""
from django.core.management.base import BaseCommand
from django.db import transaction

class Command(BaseCommand):
    help = "Delete all 'Territory Thug' templates and monsters that reference them."

    @transaction.atomic
    def handle(self, *args, **options):
        from main.models import MonsterTemplate, Monster
        name_q = {'name__iexact': 'Territory Thug'}
        # Delete monsters first for clarity (templates have CASCADE anyway)
        monsters_qs = Monster.objects.filter(template__name__iexact='Territory Thug')
        monsters_count = monsters_qs.count()
        monsters_qs.delete()
        # Delete templates
        tmpl_qs = MonsterTemplate.objects.filter(**name_q)
        tmpl_count = tmpl_qs.count()
        tmpl_qs.delete()
        self.stdout.write(self.style.SUCCESS(
            f"Deleted monsters: {monsters_count}; deleted templates: {tmpl_count}"
        ))

