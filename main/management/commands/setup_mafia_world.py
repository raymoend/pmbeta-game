"""
Django management command to set up the initial mafia game world.
Creates territories, criminal activities, weapons, and sample businesses.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from main.models import (
    Territory, CriminalActivity, Weapon, Business, Player
)
import random


class Command(BaseCommand):
    help = 'Set up the initial mafia game world with territories, activities, and weapons'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing territories and activities before creating new ones',
        )

    def handle(self, *args, **options):
        if options['clear_existing']:
            self.stdout.write('Clearing existing game world data...')
            Territory.objects.all().delete()
            CriminalActivity.objects.all().delete()
            Weapon.objects.all().delete()
            Business.objects.all().delete()

        self.stdout.write('Setting up mafia game world...')
        
        # Create territories around Cleveland area
        self.create_territories()
        
        # Create criminal activities
        self.create_criminal_activities()
        
        # Create weapons
        self.create_weapons()
        
        # Create sample businesses
        self.create_sample_businesses()

        self.stdout.write(
            self.style.SUCCESS('Successfully set up mafia game world!')
        )

    def create_territories(self):
        """Create territories around the Cleveland area"""
        self.stdout.write('Creating territories...')
        
        # Cleveland area territories
        cleveland_territories = [
            # Downtown Cleveland
            {
                'name': 'Downtown Cleveland',
                'territory_type': 'downtown',
                'chunk_x': -8064,  # Calculated from Cleveland coords
                'chunk_y': 4106,
                'income_per_hour': 500,
                'population': 5000,
            },
            # Warehouse District
            {
                'name': 'Warehouse District',
                'territory_type': 'industrial',
                'chunk_x': -8065,
                'chunk_y': 4106,
                'income_per_hour': 300,
                'population': 2000,
            },
            # Little Italy
            {
                'name': 'Little Italy',
                'territory_type': 'residential',
                'chunk_x': -8063,
                'chunk_y': 4107,
                'income_per_hour': 200,
                'population': 3000,
            },
            # Flats East Bank
            {
                'name': 'Flats East Bank',
                'territory_type': 'commercial',
                'chunk_x': -8064,
                'chunk_y': 4105,
                'income_per_hour': 400,
                'population': 1500,
            },
            # Port of Cleveland
            {
                'name': 'Port of Cleveland',
                'territory_type': 'port',
                'chunk_x': -8065,
                'chunk_y': 4107,
                'income_per_hour': 600,
                'population': 1000,
            },
            # Ohio City
            {
                'name': 'Ohio City',
                'territory_type': 'residential',
                'chunk_x': -8065,
                'chunk_y': 4105,
                'income_per_hour': 250,
                'population': 4000,
            },
            # Tremont
            {
                'name': 'Tremont',
                'territory_type': 'residential',
                'chunk_x': -8066,
                'chunk_y': 4105,
                'income_per_hour': 180,
                'population': 2500,
            },
            # Industrial Valley
            {
                'name': 'Industrial Valley',
                'territory_type': 'industrial',
                'chunk_x': -8063,
                'chunk_y': 4105,
                'income_per_hour': 350,
                'population': 1200,
            },
        ]
        
        for territory_data in cleveland_territories:
            territory, created = Territory.objects.get_or_create(
                chunk_x=territory_data['chunk_x'],
                chunk_y=territory_data['chunk_y'],
                defaults=territory_data
            )
            if created:
                self.stdout.write(f'  Created territory: {territory.name}')

    def create_criminal_activities(self):
        """Create various criminal activities"""
        self.stdout.write('Creating criminal activities...')
        
        activities = [
            # Easy activities for beginners
            {
                'name': 'Street Corner Drug Deal',
                'activity_type': 'drugs',
                'difficulty': 'easy',
                'description': 'Sell small quantities of drugs on street corners. Low risk, low reward.',
                'min_level': 1,
                'min_reputation': 0,
                'required_cash': 50,
                'lat': 41.0646633,
                'lon': -80.6391736,
                'min_payout': 100,
                'max_payout': 300,
                'heat_gain': 0.5,
                'success_chance': 0.9,
                'duration_minutes': 30,
                'cooldown_hours': 2,
            },
            {
                'name': 'Small Store Protection',
                'activity_type': 'protection',
                'difficulty': 'easy',
                'description': 'Collect protection money from small local businesses.',
                'min_level': 2,
                'min_reputation': 10,
                'required_cash': 0,
                'lat': 41.0656633,
                'lon': -80.6381736,
                'min_payout': 150,
                'max_payout': 400,
                'heat_gain': 1.0,
                'success_chance': 0.8,
                'duration_minutes': 45,
                'cooldown_hours': 6,
            },
            
            # Medium activities
            {
                'name': 'Warehouse Heist',
                'activity_type': 'heist',
                'difficulty': 'medium',
                'description': 'Break into a warehouse and steal valuable goods.',
                'min_level': 5,
                'min_reputation': 50,
                'required_cash': 200,
                'lat': 41.0636633,
                'lon': -80.6401736,
                'min_payout': 500,
                'max_payout': 1500,
                'heat_gain': 3.0,
                'success_chance': 0.7,
                'duration_minutes': 90,
                'cooldown_hours': 12,
            },
            {
                'name': 'Port Smuggling Operation',
                'activity_type': 'smuggling',
                'difficulty': 'medium',
                'description': 'Smuggle contraband through the port facilities.',
                'min_level': 7,
                'min_reputation': 75,
                'required_cash': 500,
                'lat': 41.0676633,
                'lon': -80.6421736,
                'min_payout': 800,
                'max_payout': 2500,
                'heat_gain': 4.0,
                'success_chance': 0.65,
                'duration_minutes': 120,
                'cooldown_hours': 18,
            },
            
            # Hard activities
            {
                'name': 'Bank Robbery',
                'activity_type': 'robbery',
                'difficulty': 'hard',
                'description': 'Rob a downtown bank. High risk, high reward operation.',
                'min_level': 10,
                'min_reputation': 150,
                'required_cash': 1000,
                'lat': 41.0696633,
                'lon': -80.6371736,
                'min_payout': 2000,
                'max_payout': 8000,
                'heat_gain': 8.0,
                'success_chance': 0.5,
                'duration_minutes': 180,
                'cooldown_hours': 48,
            },
            {
                'name': 'High-Stakes Money Laundering',
                'activity_type': 'money_laundering',
                'difficulty': 'hard',
                'description': 'Launder large amounts of dirty money through shell companies.',
                'min_level': 12,
                'min_reputation': 200,
                'required_cash': 2000,
                'lat': 41.0616633,
                'lon': -80.6361736,
                'min_payout': 1500,
                'max_payout': 6000,
                'heat_gain': 2.0,
                'success_chance': 0.8,
                'duration_minutes': 240,
                'cooldown_hours': 24,
            },
            
            # Extreme activities
            {
                'name': 'Federal Witness Elimination',
                'activity_type': 'assassination',
                'difficulty': 'extreme',
                'description': 'Eliminate a federal witness before they can testify.',
                'min_level': 15,
                'min_reputation': 300,
                'required_cash': 5000,
                'lat': 41.0726633,
                'lon': -80.6331736,
                'min_payout': 5000,
                'max_payout': 15000,
                'heat_gain': 15.0,
                'success_chance': 0.4,
                'duration_minutes': 300,
                'cooldown_hours': 72,
            },
        ]
        
        for activity_data in activities:
            activity, created = CriminalActivity.objects.get_or_create(
                name=activity_data['name'],
                defaults=activity_data
            )
            if created:
                self.stdout.write(f'  Created activity: {activity.name}')

    def create_weapons(self):
        """Create weapons for combat"""
        self.stdout.write('Creating weapons...')
        
        weapons = [
            # Melee weapons
            {
                'name': 'Baseball Bat',
                'weapon_type': 'melee',
                'description': 'A wooden baseball bat. Subtle and effective.',
                'damage': 15,
                'accuracy': 8,
                'defense': 0,
                'min_level': 1,
                'cost': 100,
                'heat_to_purchase': 0.1,
            },
            {
                'name': 'Switchblade',
                'weapon_type': 'melee',
                'description': 'A sharp switchblade knife. Quick and deadly.',
                'damage': 20,
                'accuracy': 12,
                'defense': 0,
                'min_level': 3,
                'cost': 250,
                'heat_to_purchase': 0.3,
            },
            
            # Pistols
            {
                'name': '.38 Special Revolver',
                'weapon_type': 'pistol',
                'description': 'A reliable .38 Special revolver. Classic and dependable.',
                'damage': 25,
                'accuracy': 10,
                'defense': 0,
                'min_level': 5,
                'cost': 800,
                'heat_to_purchase': 1.0,
            },
            {
                'name': '9mm Pistol',
                'weapon_type': 'pistol',
                'description': 'A modern 9mm semi-automatic pistol.',
                'damage': 30,
                'accuracy': 15,
                'defense': 0,
                'min_level': 7,
                'cost': 1200,
                'heat_to_purchase': 1.5,
            },
            
            # Rifles
            {
                'name': 'Hunting Rifle',
                'weapon_type': 'rifle',
                'description': 'A hunting rifle repurposed for criminal activities.',
                'damage': 40,
                'accuracy': 20,
                'defense': 0,
                'min_level': 10,
                'cost': 2000,
                'heat_to_purchase': 2.0,
            },
            {
                'name': 'Assault Rifle',
                'weapon_type': 'rifle',
                'description': 'Military-grade assault rifle. Highly illegal.',
                'damage': 50,
                'accuracy': 18,
                'defense': 0,
                'min_level': 15,
                'cost': 5000,
                'heat_to_purchase': 5.0,
            },
            
            # Armor
            {
                'name': 'Light Body Armor',
                'weapon_type': 'armor',
                'description': 'Lightweight bulletproof vest.',
                'damage': 0,
                'accuracy': 0,
                'defense': 15,
                'min_level': 8,
                'cost': 1500,
                'heat_to_purchase': 0.5,
            },
            {
                'name': 'Heavy Body Armor',
                'weapon_type': 'armor',
                'description': 'Military-grade body armor. Maximum protection.',
                'damage': 0,
                'accuracy': -5,  # Reduces accuracy due to bulk
                'defense': 30,
                'min_level': 12,
                'cost': 3500,
                'heat_to_purchase': 1.0,
            },
            
            # Vehicles
            {
                'name': 'Stolen Sedan',
                'weapon_type': 'vehicle',
                'description': 'A stolen sedan for quick getaways.',
                'damage': 5,
                'accuracy': 0,
                'defense': 10,
                'min_level': 3,
                'cost': 2500,
                'heat_to_purchase': 2.0,
            },
            {
                'name': 'Armored SUV',
                'weapon_type': 'vehicle',
                'description': 'Bulletproof SUV for dangerous operations.',
                'damage': 10,
                'accuracy': 0,
                'defense': 25,
                'min_level': 12,
                'cost': 15000,
                'heat_to_purchase': 3.0,
            },
        ]
        
        for weapon_data in weapons:
            weapon, created = Weapon.objects.get_or_create(
                name=weapon_data['name'],
                defaults=weapon_data
            )
            if created:
                self.stdout.write(f'  Created weapon: {weapon.name}')

    def create_sample_businesses(self):
        """Create some sample businesses (requires at least one player to exist)"""
        self.stdout.write('Creating sample businesses...')
        
        # Check if we have any players to assign as owners
        players = Player.objects.all()
        if not players.exists():
            self.stdout.write('  No players found - skipping business creation')
            return
            
        owner = players.first()  # Use first available player as owner
        
        businesses = [
            {
                'name': "Tony's Pizza Palace",
                'business_type': 'restaurant',
                'lat': 41.0646633,
                'lon': -80.6391736,
                'level': 1,
                'legitimate_income': 50,
                'illegal_income': 20,
                'upkeep_cost': 30,
                'heat_generated': 0.1,
            },
            {
                'name': 'Club Midnight',
                'business_type': 'club',
                'lat': 41.0656633,
                'lon': -80.6381736,
                'level': 2,
                'legitimate_income': 80,
                'illegal_income': 60,
                'upkeep_cost': 50,
                'heat_generated': 0.3,
            },
            {
                'name': 'Downtown Laundromat',
                'business_type': 'laundromat',
                'lat': 41.0636633,
                'lon': -80.6401736,
                'level': 1,
                'legitimate_income': 30,
                'illegal_income': 100,  # Perfect for money laundering
                'upkeep_cost': 25,
                'heat_generated': 0.5,
            },
        ]
        
        for business_data in businesses:
            business_data['owner'] = owner
            business, created = Business.objects.get_or_create(
                name=business_data['name'],
                defaults=business_data
            )
            if created:
                self.stdout.write(f'  Created business: {business.name}')
