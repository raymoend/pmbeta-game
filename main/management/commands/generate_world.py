"""
Management command to generate P2K-style world data
Creates flags, NPCs, resources, and structures like Parallel Kingdom
"""
import random
import math
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
from main.models import (
    Player, Flag, NPC, ResourceNode, Structure, NatureStructure, 
    Family, Territory, CriminalActivity, Business, Weapon
)


class Command(BaseCommand):
    help = 'Generate P2K-style world data including flags, NPCs, resources, and structures'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--center-lat',
            type=float,
            default=41.0646633,
            help='Center latitude for world generation'
        )
        parser.add_argument(
            '--center-lon', 
            type=float,
            default=-80.6391736,
            help='Center longitude for world generation'
        )
        parser.add_argument(
            '--radius',
            type=float,
            default=0.05,  # About 5km radius
            help='Radius in degrees for world generation'
        )
        parser.add_argument(
            '--num-flags',
            type=int,
            default=20,
            help='Number of flags to generate'
        )
        parser.add_argument(
            '--num-npcs',
            type=int,
            default=100,
            help='Number of NPCs to generate'
        )
        parser.add_argument(
            '--num-resources',
            type=int,
            default=200,
            help='Number of resource nodes to generate'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing world data before generating'
        )
    
    def handle(self, *args, **options):
        center_lat = options['center_lat']
        center_lon = options['center_lon']
        radius = options['radius']
        
        if options['clear_existing']:
            self.stdout.write('Clearing existing world data...')
            self.clear_existing_data()
        
        self.stdout.write(f'Generating world around {center_lat:.6f}, {center_lon:.6f}')
        self.stdout.write(f'Radius: {radius:.6f} degrees (~{radius * 111:.1f} km)')
        
        # Create basic game data first
        self.create_weapons()
        self.create_criminal_activities(center_lat, center_lon, radius)
        self.create_families()
        self.create_territories(center_lat, center_lon, radius)
        
        # Generate world entities
        self.generate_flags(center_lat, center_lon, radius, options['num_flags'])
        self.generate_npcs(center_lat, center_lon, radius, options['num_npcs'])
        self.generate_resources(center_lat, center_lon, radius, options['num_resources'])
        self.generate_structures(center_lat, center_lon, radius, 50)
        
        self.stdout.write(self.style.SUCCESS('World generation complete!'))
    
    def clear_existing_data(self):
        """Clear existing world data"""
        Flag.objects.all().delete()
        NPC.objects.all().delete()
        ResourceNode.objects.all().delete()
        Structure.objects.all().delete()
        Territory.objects.all().delete()
        CriminalActivity.objects.all().delete()
        Business.objects.all().delete()
        self.stdout.write('Existing data cleared.')
    
    def create_weapons(self):
        """Create basic weapon types"""
        weapons = [
            # Melee weapons
            ('Brass Knuckles', 'melee', 15, 8, 500),
            ('Baseball Bat', 'melee', 25, 7, 800),
            ('Crowbar', 'melee', 20, 8, 600),
            ('Knife', 'melee', 18, 9, 400),
            
            # Pistols
            ('Glock 17', 'pistol', 35, 8, 2500),
            ('.38 Special', 'pistol', 30, 9, 2000),
            ('Desert Eagle', 'pistol', 45, 7, 4000),
            
            # Rifles
            ('AK-47', 'rifle', 60, 8, 8000),
            ('M16', 'rifle', 55, 9, 7500),
            
            # Shotguns
            ('Pump Shotgun', 'shotgun', 70, 6, 3500),
            ('Sawed-off', 'shotgun', 65, 5, 3000),
            
            # Armor
            ('Leather Jacket', 'armor', 0, 0, 800, 15),
            ('Bulletproof Vest', 'armor', 0, 0, 2500, 35),
            ('Military Armor', 'armor', 0, 0, 8000, 60),
        ]
        
        for weapon_data in weapons:
            name, weapon_type, damage, accuracy, cost = weapon_data[:5]
            defense = weapon_data[5] if len(weapon_data) > 5 else 0
            
            weapon, created = Weapon.objects.get_or_create(
                name=name,
                defaults={
                    'weapon_type': weapon_type,
                    'damage': damage,
                    'accuracy': accuracy,
                    'defense': defense,
                    'cost': cost,
                    'description': f'{weapon_type.title()} weapon'
                }
            )
            if created:
                self.stdout.write(f'Created weapon: {name}')
    
    def create_families(self):
        """Create some mafia families"""
        # Create admin user if doesn't exist
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={'is_staff': True, 'is_superuser': True}
        )
        admin_player, created = Player.objects.get_or_create(
            user=admin_user,
            defaults={
                'lat': 41.0646633,
                'lon': -80.6391736,
                'center_lat': 41.0646633,
                'center_lon': -80.6391736
            }
        )
        
        families = [
            ('Corleone Family', 'Traditional Italian-American mafia family'),
            ('Bratva', 'Russian organized crime syndicate'),
            ('Yakuza', 'Japanese crime organization'),
            ('Triads', 'Chinese criminal organization'),
            ('Los Hermanos', 'Mexican cartel operations'),
        ]
        
        for family_name, description in families:
            family, created = Family.objects.get_or_create(
                name=family_name,
                defaults={
                    'description': description,
                    'boss': admin_player,
                    'treasury': random.randint(100000, 1000000),
                    'reputation': random.randint(50, 200)
                }
            )
            if created:
                self.stdout.write(f'Created family: {family_name}')
    
    def create_territories(self, center_lat, center_lon, radius):
        """Create territory control zones"""
        territory_types = ['residential', 'commercial', 'industrial', 'downtown', 'port']
        territory_names = [
            'Little Italy', 'Chinatown', 'Financial District', 'The Docks',
            'Industrial Zone', 'Residential Area', 'Shopping District', 
            'Old Town', 'Harbor District', 'Business Park'
        ]
        
        granularity = 100  # 0.01 degree chunks
        
        for i in range(15):  # Create 15 territories
            # Generate territory center
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(0, radius)
            
            lat = center_lat + distance * math.cos(angle)
            lon = center_lon + distance * math.sin(angle)
            
            chunk_x = int(lon * granularity)
            chunk_y = int(lat * granularity)
            
            # Skip if territory already exists at this chunk
            if Territory.objects.filter(chunk_x=chunk_x, chunk_y=chunk_y).exists():
                continue
            
            territory = Territory.objects.create(
                name=random.choice(territory_names),
                territory_type=random.choice(territory_types),
                chunk_x=chunk_x,
                chunk_y=chunk_y,
                influence_level=random.uniform(0, 100),
                income_per_hour=random.randint(50, 500),
                population=random.randint(500, 5000)
            )
            self.stdout.write(f'Created territory: {territory.name}')
    
    def create_criminal_activities(self, center_lat, center_lon, radius):
        """Create criminal activities around the map"""
        activities = [
            ('Bank Heist', 'heist', 'hard', 'Rob the First National Bank', 10, 500, 50000, 150000),
            ('Jewelry Store Job', 'robbery', 'medium', 'Hit the diamond district', 5, 200, 10000, 50000),
            ('Drug Deal', 'drugs', 'easy', 'Move some product for the family', 1, 50, 1000, 5000),
            ('Protection Collection', 'protection', 'easy', 'Collect payments from local businesses', 1, 100, 500, 2000),
            ('Rival Hit', 'assassination', 'extreme', 'Take out a rival family member', 15, 1000, 100000, 500000),
            ('Smuggling Run', 'smuggling', 'medium', 'Move contraband across the city', 5, 300, 5000, 25000),
            ('Casino Shakedown', 'extortion', 'hard', 'Convince casino owners to pay up', 8, 400, 20000, 80000),
        ]
        
        for activity_data in activities:
            name, activity_type, difficulty, description, min_level, min_rep, min_pay, max_pay = activity_data
            
            # Generate random location
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(0, radius)
            
            lat = center_lat + distance * math.cos(angle)
            lon = center_lon + distance * math.sin(angle)
            
            activity = CriminalActivity.objects.create(
                name=name,
                activity_type=activity_type,
                difficulty=difficulty,
                description=description,
                min_level=min_level,
                min_reputation=min_rep,
                lat=lat,
                lon=lon,
                min_payout=min_pay,
                max_payout=max_pay,
                duration_minutes=random.randint(30, 180),
                success_chance=random.uniform(0.5, 0.9)
            )
            self.stdout.write(f'Created activity: {name} at {lat:.6f}, {lon:.6f}')
    
    def generate_flags(self, center_lat, center_lon, radius, count):
        """Generate flags like P2K"""
        # Get admin player as default owner
        admin_user = User.objects.get(username='admin')
        admin_player = Player.objects.get(user=admin_user)
        families = list(Family.objects.all())
        
        flag_names = [
            'Corleone Stronghold', 'Bratva Outpost', 'Yakuza Territory', 
            'Triad Holdings', 'Cartel Base', 'Family Headquarters',
            'Crime Syndicate', 'Underground Bunker', 'Safe House',
            'Black Market Hub', 'Money Laundering Front', 'Chop Shop',
            'Drug Lab', 'Weapons Cache', 'Smugglers Den',
            'Protection Racket', 'Gambling Den', 'Loan Shark Office'
        ]
        
        generated_positions = []
        
        for i in range(count):
            attempts = 0
            while attempts < 50:  # Try up to 50 times to find valid position
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(0, radius)
                
                lat = center_lat + distance * math.cos(angle)
                lon = center_lon + distance * math.sin(angle)
                
                # Check minimum distance from other flags (200m)
                too_close = False
                for pos_lat, pos_lon in generated_positions:
                    dist = self.calculate_distance(lat, lon, pos_lat, pos_lon)
                    if dist < 200:
                        too_close = True
                        break
                
                if not too_close:
                    break
                    
                attempts += 1
            
            if attempts >= 50:
                continue  # Skip if can't find valid position
            
            flag_name = random.choice(flag_names)
            flag_type = random.choice(['territory', 'family', 'outpost', 'stronghold'])
            
            flag = Flag.objects.create(
                name=f"{flag_name} {i+1}",
                flag_type=flag_type,
                lat=lat,
                lon=lon,
                owner=admin_player,
                controlling_family=random.choice(families) if families else None,
                level=random.randint(1, 5),
                hp=random.randint(500, 2000),
                max_hp=random.randint(500, 2000),
                defense_rating=random.randint(20, 100),
                income_per_hour=random.randint(100, 1000)
            )
            
            # Spawn NPCs around this flag
            flag.spawn_npcs(random.randint(1, 3))
            
            generated_positions.append((lat, lon))
            self.stdout.write(f'Generated flag: {flag.name} at {lat:.6f}, {lon:.6f}')
    
    def generate_npcs(self, center_lat, center_lon, radius, count):
        """Generate NPCs like P2K"""
        npc_names = [
            'Tony', 'Vinny', 'Joey', 'Sal', 'Rocco', 'Frankie', 'Nick', 'Bobby', 'Sammy', 'Lou',
            'Maria', 'Sofia', 'Lucia', 'Isabella', 'Carmen', 'Rosa', 'Gina', 'Angela', 'Teresa'
        ]
        
        npc_nicknames = [
            'The Knife', 'Two-Times', 'Big Nose', 'The Bull', 'Scar', 'Iron Fist', 
            'Mad Dog', 'The Hammer', 'Cold Eyes', 'Knuckles', 'The Shadow', 'Lucky',
            'The Fox', 'Steel', 'The Ghost', 'Razor', 'The Wolf', 'Diamond', 'Thunder'
        ]
        
        generated_positions = []
        
        for i in range(count):
            attempts = 0
            while attempts < 30:
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(0, radius)
                
                lat = center_lat + distance * math.cos(angle)
                lon = center_lon + distance * math.sin(angle)
                
                # Check minimum distance from other NPCs (50m)
                too_close = False
                for pos_lat, pos_lon in generated_positions:
                    dist = self.calculate_distance(lat, lon, pos_lat, pos_lon)
                    if dist < 50:
                        too_close = True
                        break
                
                if not too_close:
                    break
                    
                attempts += 1
            
            if attempts >= 30:
                continue
            
            first_name = random.choice(npc_names)
            nickname = random.choice(npc_nicknames)
            npc_name = f"{first_name} '{nickname}'"
            
            npc_type = random.choice(['bandit', 'thug', 'enforcer', 'dealer', 'bouncer', 'cop'])
            level = random.randint(1, 10)
            
            npc = NPC.objects.create(
                npc_type=npc_type,
                name=npc_name,
                lat=lat,
                lon=lon,
                level=level,
                hp=50 + (level * 25),
                max_hp=50 + (level * 25),
                strength=8 + (level * 3),
                defense=8 + (level * 2),
                speed=5 + level,
                base_experience_reward=15 + (level * 10),
                base_gold_reward=50 + (level * 25),
                base_reputation_reward=3 + level,
                aggression=random.uniform(0.2, 0.8),
                respawn_time=random.randint(300, 900)  # 5-15 minutes
            )
            
            generated_positions.append((lat, lon))
            if i % 20 == 0:
                self.stdout.write(f'Generated {i} NPCs...')
        
        self.stdout.write(f'Generated {len(generated_positions)} NPCs')
    
    def generate_resources(self, center_lat, center_lon, radius, count):
        """Generate resource nodes like Parallel Kingdom"""
        resource_types = ['tree', 'iron_mine', 'gold_mine', 'stone_quarry', 'herb_patch', 'ruins', 'cave', 'well']
        generated_positions = []
        
        for i in range(count):
            attempts = 0
            while attempts < 30:
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(0, radius)
                
                lat = center_lat + distance * math.cos(angle)
                lon = center_lon + distance * math.sin(angle)
                
                # Check minimum distance from other resources (30m)
                too_close = False
                for pos_lat, pos_lon in generated_positions:
                    dist = self.calculate_distance(lat, lon, pos_lat, pos_lon)
                    if dist < 30:
                        too_close = True
                        break
                
                if not too_close:
                    break
                    
                attempts += 1
            
            if attempts >= 30:
                continue
            
            resource_type = random.choice(resource_types)
            level = random.randint(1, 5)
            
            resource = ResourceNode.objects.create(
                resource_type=resource_type,
                lat=lat,
                lon=lon,
                level=level,
                hp=50 + (level * 20),
                max_hp=50 + (level * 20),
                base_experience=10 + (level * 5),
                base_gold_reward=25 + (level * 25),
                base_resource_amount=5 + level,
                respawn_time=random.randint(1800, 7200)  # 30min to 2hr
            )
            
            generated_positions.append((lat, lon))
            if i % 50 == 0:
                self.stdout.write(f'Generated {i} resources...')
        
        self.stdout.write(f'Generated {len(generated_positions)} resource nodes')
    
    def generate_structures(self, center_lat, center_lon, radius, count):
        """Generate basic structures"""
        structure_types = [1, 2, 3, 4, 5]  # Tree, Rock, Building, Flag, City
        generated_positions = []
        
        for i in range(count):
            attempts = 0
            while attempts < 30:
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(0, radius)
                
                lat = center_lat + distance * math.cos(angle)
                lon = center_lon + distance * math.sin(angle)
                
                # Check minimum distance (100m)
                too_close = False
                for pos_lat, pos_lon in generated_positions:
                    dist = self.calculate_distance(lat, lon, pos_lat, pos_lon)
                    if dist < 100:
                        too_close = True
                        break
                
                if not too_close:
                    break
                    
                attempts += 1
            
            if attempts >= 30:
                continue
            
            structure_type = random.choice(structure_types)
            
            if structure_type in [1, 2]:  # Tree or Rock - make it harvestable
                structure = NatureStructure.objects.create(
                    structure_type=structure_type,
                    lat=lat,
                    lon=lon,
                    hp=random.randint(50, 200),
                    respawn_time=random.randint(3600, 7200)
                )
            else:
                structure = Structure.objects.create(
                    structure_type=structure_type,
                    lat=lat,
                    lon=lon,
                    hp=random.randint(100, 500)
                )
            
            generated_positions.append((lat, lon))
        
        self.stdout.write(f'Generated {len(generated_positions)} structures')
    
    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """Calculate distance between two points in meters"""
        R = 6371000  # Earth radius in meters
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
