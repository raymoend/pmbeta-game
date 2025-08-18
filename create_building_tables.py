#!/usr/bin/env python3
"""
Create Building System Database Tables
Simple script to create the necessary tables for the building system
"""
import sqlite3
import uuid
import os

def create_building_tables():
    """Create building system tables directly in SQLite"""
    
    db_path = 'db.sqlite3'
    if not os.path.exists(db_path):
        print("❌ Database file not found. Make sure you're in the right directory.")
        return False
    
    print("🔄 Creating building system tables...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create FlagColor table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pk_flag_colors (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            name VARCHAR(50) UNIQUE,
            hex_color VARCHAR(7),
            display_name VARCHAR(50),
            is_premium INTEGER DEFAULT 0,
            unlock_level INTEGER DEFAULT 1,
            unlock_cost INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        );
        """)
        print("✓ Created pk_flag_colors table")
        
        # Create BuildingType table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pk_building_types (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            name VARCHAR(100),
            description TEXT,
            category VARCHAR(20),
            base_cost_gold INTEGER DEFAULT 1000,
            base_cost_wood INTEGER DEFAULT 50,
            base_cost_stone INTEGER DEFAULT 25,
            base_revenue_per_hour INTEGER DEFAULT 10,
            max_revenue_per_hour INTEGER DEFAULT 2500,
            max_level INTEGER DEFAULT 10,
            construction_time_minutes INTEGER DEFAULT 60,
            icon_name VARCHAR(50) DEFAULT 'building',
            is_active INTEGER DEFAULT 1
        );
        """)
        print("✓ Created pk_building_types table")
        
        # Create BuildingTemplate table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pk_building_templates (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            name VARCHAR(100),
            building_type_id TEXT,
            description TEXT,
            is_starter INTEGER DEFAULT 0,
            level_required INTEGER DEFAULT 1,
            cost_gold INTEGER,
            cost_wood INTEGER,
            cost_stone INTEGER,
            FOREIGN KEY (building_type_id) REFERENCES pk_building_types(id)
        );
        """)
        print("✓ Created pk_building_templates table")
        
        # Create PlayerBuilding table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pk_player_buildings (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            owner_id TEXT,
            building_type_id TEXT,
            lat REAL,
            lon REAL,
            level INTEGER DEFAULT 1,
            status VARCHAR(20) DEFAULT 'constructing',
            flag_color_id TEXT,
            custom_name VARCHAR(100),
            last_collection TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_revenue_generated INTEGER DEFAULT 0,
            uncollected_revenue INTEGER DEFAULT 0,
            construction_started TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            construction_completed TIMESTAMP,
            upgrade_started TIMESTAMP,
            upgrade_completed TIMESTAMP,
            current_hp INTEGER DEFAULT 100,
            max_hp INTEGER DEFAULT 100,
            last_attacked TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES rpg_characters(id),
            FOREIGN KEY (building_type_id) REFERENCES pk_building_types(id),
            FOREIGN KEY (flag_color_id) REFERENCES pk_flag_colors(id),
            UNIQUE (lat, lon)
        );
        """)
        print("✓ Created pk_player_buildings table")
        
        # Create RevenueCollection table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pk_revenue_collections (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            building_id TEXT,
            amount_collected INTEGER,
            player_level INTEGER,
            building_level INTEGER,
            hours_since_last_collection REAL DEFAULT 0.0,
            FOREIGN KEY (building_id) REFERENCES pk_player_buildings(id)
        );
        """)
        print("✓ Created pk_revenue_collections table")
        
        # Create BuildingAttack table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pk_building_attacks (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            attacker_id TEXT,
            target_building_id TEXT,
            status VARCHAR(20) DEFAULT 'active',
            damage_dealt INTEGER DEFAULT 0,
            gold_stolen INTEGER DEFAULT 0,
            attack_power INTEGER,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (attacker_id) REFERENCES rpg_characters(id),
            FOREIGN KEY (target_building_id) REFERENCES pk_player_buildings(id)
        );
        """)
        print("✓ Created pk_building_attacks table")
        
        # Add initial flag colors
        print("\n→ Adding initial flag colors...")
        flag_colors = [
            # Basic colors (free)
            ('red', '#FF0000', 'Red', 0, 1, 0),
            ('blue', '#0000FF', 'Blue', 0, 1, 0),
            ('green', '#00FF00', 'Green', 0, 1, 0),
            ('yellow', '#FFFF00', 'Yellow', 0, 1, 0),
            ('purple', '#8000FF', 'Purple', 0, 1, 0),
            ('orange', '#FF8000', 'Orange', 0, 1, 0),
            ('white', '#FFFFFF', 'White', 0, 1, 0),
            ('black', '#000000', 'Black', 0, 1, 0),
            
            # Premium colors
            ('gold', '#FFD700', 'Gold', 1, 10, 5000),
            ('silver', '#C0C0C0', 'Silver', 1, 5, 2500),
        ]
        
        for name, hex_color, display_name, is_premium, unlock_level, unlock_cost in flag_colors:
            color_id = str(uuid.uuid4()).replace('-', '')
            cursor.execute("""
            INSERT OR IGNORE INTO pk_flag_colors 
            (id, name, hex_color, display_name, is_premium, unlock_level, unlock_cost, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (color_id, name, hex_color, display_name, is_premium, unlock_level, unlock_cost))
            print(f"  ✓ Added flag color: {display_name}")
        
        # Add building types
        print("\n→ Adding building types...")
        building_types = [
            ('Trading Post', 'A basic trading post that generates steady income from merchant activity.', 
             'economic', 500, 30, 15, 10, 2500, 10, 30, 'trading_post'),
            ('Guard Tower', 'A defensive structure that provides protection and generates income.', 
             'military', 800, 20, 60, 15, 1500, 8, 45, 'guard_tower'),
            ('Market', 'A bustling marketplace that attracts traders and generates substantial revenue.', 
             'economic', 1500, 75, 50, 25, 2500, 8, 60, 'market'),
            ('Bank', 'A secure bank that generates high revenue through financial services.', 
             'economic', 3000, 50, 100, 50, 2500, 6, 120, 'bank'),
            ('Workshop', 'A crafting workshop that generates income from creating and selling goods.', 
             'utility', 1200, 80, 30, 20, 1800, 7, 75, 'workshop'),
        ]
        
        for name, desc, category, gold_cost, wood_cost, stone_cost, base_rev, max_rev, max_level, time, icon in building_types:
            building_id = str(uuid.uuid4()).replace('-', '')
            cursor.execute("""
            INSERT OR IGNORE INTO pk_building_types 
            (id, name, description, category, base_cost_gold, base_cost_wood, base_cost_stone,
             base_revenue_per_hour, max_revenue_per_hour, max_level, construction_time_minutes, icon_name, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (building_id, name, desc, category, gold_cost, wood_cost, stone_cost, 
                  base_rev, max_rev, max_level, time, icon))
            print(f"  ✓ Added building type: {name}")
        
        conn.commit()
        conn.close()
        
        print("\n✅ Building system database setup complete!")
        print("🏗️ Tables created and initial data added successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

if __name__ == "__main__":
    create_building_tables()
