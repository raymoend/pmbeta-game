"""
Dynamic Quest System for RPG Game
Handles quest generation, tracking, and completion
"""
import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from django.utils import timezone
from django.db import transaction
from enum import Enum


class QuestType(Enum):
    KILL = "kill"
    COLLECT = "collect"
    DELIVER = "deliver"
    EXPLORE = "explore"
    CRAFT = "craft"
    ESCORT = "escort"
    DAILY = "daily"
    WEEKLY = "weekly"


class QuestDifficulty(Enum):
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    EPIC = "epic"
    LEGENDARY = "legendary"


class QuestStatus(Enum):
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class QuestObjective:
    """Individual quest objective"""
    
    def __init__(self, objective_type: str, target: str, required: int, 
                 current: int = 0, data: Dict = None):
        self.objective_type = objective_type
        self.target = target
        self.required = required
        self.current = current
        self.data = data or {}
        self.completed = current >= required
    
    def update_progress(self, amount: int = 1) -> bool:
        """Update objective progress"""
        old_current = self.current
        self.current = min(self.required, self.current + amount)
        self.completed = self.current >= self.required
        return self.current > old_current
    
    def get_progress_text(self) -> str:
        """Get progress as text"""
        if self.objective_type == "kill":
            return f"Kill {self.target}: {self.current}/{self.required}"
        elif self.objective_type == "collect":
            return f"Collect {self.target}: {self.current}/{self.required}"
        elif self.objective_type == "deliver":
            return f"Deliver {self.target}: {self.current}/{self.required}"
        elif self.objective_type == "explore":
            return f"Visit {self.target}: {self.current}/{self.required}"
        elif self.objective_type == "craft":
            return f"Craft {self.target}: {self.current}/{self.required}"
        else:
            return f"{self.objective_type.title()} {self.target}: {self.current}/{self.required}"
    
    def to_dict(self) -> Dict:
        return {
            "type": self.objective_type,
            "target": self.target,
            "required": self.required,
            "current": self.current,
            "completed": self.completed,
            "data": self.data
        }


class QuestReward:
    """Quest completion rewards"""
    
    def __init__(self, experience: int = 0, gold: int = 0, items: List = None,
                 reputation: int = 0, skills: Dict = None):
        self.experience = experience
        self.gold = gold
        self.items = items or []
        self.reputation = reputation
        self.skills = skills or {}  # skill_name: experience
    
    def to_dict(self) -> Dict:
        return {
            "experience": self.experience,
            "gold": self.gold,
            "items": self.items,
            "reputation": self.reputation,
            "skills": self.skills
        }


class Quest:
    """Main quest object"""
    
    def __init__(self, quest_id: str, title: str, description: str,
                 quest_type: QuestType, difficulty: QuestDifficulty,
                 objectives: List[QuestObjective], rewards: QuestReward,
                 level_requirement: int = 1, time_limit: Optional[timedelta] = None,
                 prerequisites: List[str] = None, location: Dict = None):
        
        self.quest_id = quest_id
        self.title = title
        self.description = description
        self.quest_type = quest_type
        self.difficulty = difficulty
        self.objectives = objectives
        self.rewards = rewards
        self.level_requirement = level_requirement
        self.time_limit = time_limit
        self.prerequisites = prerequisites or []
        self.location = location or {}
        
        self.status = QuestStatus.AVAILABLE
        self.started_at = None
        self.completed_at = None
        self.expires_at = None
    
    def start(self) -> bool:
        """Start the quest"""
        if self.status != QuestStatus.AVAILABLE:
            return False
        
        self.status = QuestStatus.ACTIVE
        self.started_at = timezone.now()
        
        if self.time_limit:
            self.expires_at = self.started_at + self.time_limit
        
        return True
    
    def is_completed(self) -> bool:
        """Check if all objectives are completed"""
        return all(obj.completed for obj in self.objectives)
    
    def is_expired(self) -> bool:
        """Check if quest has expired"""
        return (self.expires_at and 
                timezone.now() > self.expires_at and 
                self.status == QuestStatus.ACTIVE)
    
    def update_objective(self, objective_type: str, target: str, amount: int = 1) -> bool:
        """Update specific objective progress"""
        updated = False
        for objective in self.objectives:
            if (objective.objective_type == objective_type and 
                objective.target == target and 
                not objective.completed):
                if objective.update_progress(amount):
                    updated = True
        
        # Check if quest is now completed
        if self.is_completed() and self.status == QuestStatus.ACTIVE:
            self.complete()
        
        return updated
    
    def complete(self) -> bool:
        """Complete the quest"""
        if not self.is_completed() or self.status != QuestStatus.ACTIVE:
            return False
        
        self.status = QuestStatus.COMPLETED
        self.completed_at = timezone.now()
        return True
    
    def fail(self, reason: str = "") -> bool:
        """Fail the quest"""
        if self.status != QuestStatus.ACTIVE:
            return False
        
        self.status = QuestStatus.FAILED
        return True
    
    def get_progress_percentage(self) -> float:
        """Get overall quest progress as percentage"""
        if not self.objectives:
            return 0.0
        
        total_progress = 0.0
        for objective in self.objectives:
            progress = objective.current / objective.required
            total_progress += min(1.0, progress)
        
        return (total_progress / len(self.objectives)) * 100
    
    def to_dict(self) -> Dict:
        return {
            "id": self.quest_id,
            "title": self.title,
            "description": self.description,
            "type": self.quest_type.value,
            "difficulty": self.difficulty.value,
            "status": self.status.value,
            "level_requirement": self.level_requirement,
            "objectives": [obj.to_dict() for obj in self.objectives],
            "rewards": self.rewards.to_dict(),
            "progress_percentage": self.get_progress_percentage(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "location": self.location
        }


class QuestGenerator:
    """Generates dynamic quests based on character level and game state"""
    
    def __init__(self):
        self.quest_templates = {
            QuestType.KILL: self._generate_kill_templates(),
            QuestType.COLLECT: self._generate_collect_templates(),
            QuestType.DELIVER: self._generate_deliver_templates(),
            QuestType.EXPLORE: self._generate_explore_templates(),
            QuestType.DAILY: self._generate_daily_templates()
        }
    
    def _generate_kill_templates(self) -> List[Dict]:
        return [
            {
                "title": "Pest Control",
                "description": "The local area is overrun with {monster_type}. Help clear them out.",
                "monsters": ["Goblin", "Wolf", "Rat", "Spider", "Orc"],
                "count_range": (3, 8),
                "difficulty_modifier": 1.0
            },
            {
                "title": "Elite Hunt",
                "description": "A powerful {monster_type} has been terrorizing travelers. Hunt it down.",
                "monsters": ["Elite Goblin", "Alpha Wolf", "Giant Spider", "Orc Chieftain"],
                "count_range": (1, 2),
                "difficulty_modifier": 2.0
            },
            {
                "title": "Monster Invasion",
                "description": "Waves of {monster_type} are attacking nearby settlements.",
                "monsters": ["Goblin", "Orc", "Wolf Pack", "Bandit"],
                "count_range": (10, 20),
                "difficulty_modifier": 1.5
            }
        ]
    
    def _generate_collect_templates(self) -> List[Dict]:
        return [
            {
                "title": "Herb Gathering",
                "description": "Collect {item_name} for the local healer.",
                "items": ["Healing Herbs", "Magic Flowers", "Rare Mushrooms", "Crystal Shards"],
                "count_range": (5, 15),
                "difficulty_modifier": 0.8
            },
            {
                "title": "Resource Collection",
                "description": "The town needs {item_name} for construction projects.",
                "items": ["Iron Ore", "Stone Blocks", "Wood Planks", "Cloth"],
                "count_range": (8, 20),
                "difficulty_modifier": 1.0
            }
        ]
    
    def _generate_deliver_templates(self) -> List[Dict]:
        return [
            {
                "title": "Important Delivery",
                "description": "Deliver this {item_name} to {npc_name} safely.",
                "items": ["Message", "Package", "Medicine", "Supplies"],
                "npcs": ["Town Guard", "Merchant", "Healer", "Scholar"],
                "difficulty_modifier": 1.2
            }
        ]
    
    def _generate_explore_templates(self) -> List[Dict]:
        return [
            {
                "title": "Scouting Mission",
                "description": "Explore the {location_name} and report back.",
                "locations": ["Abandoned Mine", "Dark Forest", "Ancient Ruins", "Mountain Pass"],
                "difficulty_modifier": 1.1
            }
        ]
    
    def _generate_daily_templates(self) -> List[Dict]:
        return [
            {
                "title": "Daily Training",
                "description": "Complete combat training exercises.",
                "objectives": [("kill", "Any Monster", 5)],
                "difficulty_modifier": 0.7,
                "time_limit": timedelta(hours=24)
            },
            {
                "title": "Daily Gathering",
                "description": "Gather resources for the community.",
                "objectives": [("collect", "Any Resource", 10)],
                "difficulty_modifier": 0.6,
                "time_limit": timedelta(hours=24)
            }
        ]
    
    def generate_quest(self, character_level: int, quest_type: QuestType = None,
                      difficulty: QuestDifficulty = None) -> Quest:
        """Generate a new quest for the given character level"""
        
        # Select quest type if not specified
        if not quest_type:
            quest_type = random.choice(list(QuestType))
        
        # Select difficulty if not specified
        if not difficulty:
            difficulty = self._determine_difficulty(character_level)
        
        # Get appropriate template
        templates = self.quest_templates.get(quest_type, [])
        if not templates:
            return None
        
        template = random.choice(templates)
        
        # Generate quest based on template
        if quest_type == QuestType.KILL:
            return self._create_kill_quest(template, character_level, difficulty)
        elif quest_type == QuestType.COLLECT:
            return self._create_collect_quest(template, character_level, difficulty)
        elif quest_type == QuestType.DELIVER:
            return self._create_deliver_quest(template, character_level, difficulty)
        elif quest_type == QuestType.EXPLORE:
            return self._create_explore_quest(template, character_level, difficulty)
        elif quest_type == QuestType.DAILY:
            return self._create_daily_quest(template, character_level, difficulty)
        
        return None
    
    def _determine_difficulty(self, character_level: int) -> QuestDifficulty:
        """Determine appropriate difficulty for character level"""
        if character_level <= 5:
            return random.choice([QuestDifficulty.EASY, QuestDifficulty.NORMAL])
        elif character_level <= 15:
            return random.choice([QuestDifficulty.NORMAL, QuestDifficulty.HARD])
        elif character_level <= 25:
            return random.choice([QuestDifficulty.HARD, QuestDifficulty.EPIC])
        else:
            return random.choice([QuestDifficulty.EPIC, QuestDifficulty.LEGENDARY])
    
    def _create_kill_quest(self, template: Dict, level: int, difficulty: QuestDifficulty) -> Quest:
        """Create a kill quest from template"""
        monster_type = random.choice(template["monsters"])
        count_min, count_max = template["count_range"]
        
        # Adjust count based on difficulty and level
        difficulty_multiplier = {
            QuestDifficulty.EASY: 0.7,
            QuestDifficulty.NORMAL: 1.0,
            QuestDifficulty.HARD: 1.5,
            QuestDifficulty.EPIC: 2.0,
            QuestDifficulty.LEGENDARY: 3.0
        }[difficulty]
        
        count = int(random.randint(count_min, count_max) * difficulty_multiplier)
        count = max(1, count)
        
        quest_id = f"kill_{monster_type.lower().replace(' ', '_')}_{random.randint(1000, 9999)}"
        title = template["title"].format(monster_type=monster_type)
        description = template["description"].format(monster_type=monster_type)
        
        objectives = [QuestObjective("kill", monster_type, count)]
        rewards = self._calculate_rewards(level, difficulty, template["difficulty_modifier"])
        
        return Quest(
            quest_id=quest_id,
            title=title,
            description=description,
            quest_type=QuestType.KILL,
            difficulty=difficulty,
            objectives=objectives,
            rewards=rewards,
            level_requirement=max(1, level - 2)
        )
    
    def _create_collect_quest(self, template: Dict, level: int, difficulty: QuestDifficulty) -> Quest:
        """Create a collect quest from template"""
        item_name = random.choice(template["items"])
        count_min, count_max = template["count_range"]
        count = random.randint(count_min, count_max)
        
        quest_id = f"collect_{item_name.lower().replace(' ', '_')}_{random.randint(1000, 9999)}"
        title = template["title"]
        description = template["description"].format(item_name=item_name)
        
        objectives = [QuestObjective("collect", item_name, count)]
        rewards = self._calculate_rewards(level, difficulty, template["difficulty_modifier"])
        
        return Quest(
            quest_id=quest_id,
            title=title,
            description=description,
            quest_type=QuestType.COLLECT,
            difficulty=difficulty,
            objectives=objectives,
            rewards=rewards,
            level_requirement=max(1, level - 2)
        )
    
    def _create_deliver_quest(self, template: Dict, level: int, difficulty: QuestDifficulty) -> Quest:
        """Create a delivery quest from template"""
        item_name = random.choice(template["items"])
        npc_name = random.choice(template["npcs"])
        
        quest_id = f"deliver_{item_name.lower().replace(' ', '_')}_{random.randint(1000, 9999)}"
        title = template["title"]
        description = template["description"].format(item_name=item_name, npc_name=npc_name)
        
        objectives = [QuestObjective("deliver", f"{item_name} to {npc_name}", 1)]
        rewards = self._calculate_rewards(level, difficulty, template["difficulty_modifier"])
        
        # Add time limit for delivery quests
        time_limit = timedelta(hours=random.randint(6, 24))
        
        return Quest(
            quest_id=quest_id,
            title=title,
            description=description,
            quest_type=QuestType.DELIVER,
            difficulty=difficulty,
            objectives=objectives,
            rewards=rewards,
            level_requirement=max(1, level - 2),
            time_limit=time_limit
        )
    
    def _create_explore_quest(self, template: Dict, level: int, difficulty: QuestDifficulty) -> Quest:
        """Create an exploration quest from template"""
        location_name = random.choice(template["locations"])
        
        quest_id = f"explore_{location_name.lower().replace(' ', '_')}_{random.randint(1000, 9999)}"
        title = template["title"]
        description = template["description"].format(location_name=location_name)
        
        objectives = [QuestObjective("explore", location_name, 1)]
        rewards = self._calculate_rewards(level, difficulty, template["difficulty_modifier"])
        
        return Quest(
            quest_id=quest_id,
            title=title,
            description=description,
            quest_type=QuestType.EXPLORE,
            difficulty=difficulty,
            objectives=objectives,
            rewards=rewards,
            level_requirement=max(1, level - 2)
        )
    
    def _create_daily_quest(self, template: Dict, level: int, difficulty: QuestDifficulty) -> Quest:
        """Create a daily quest from template"""
        quest_id = f"daily_{template['title'].lower().replace(' ', '_')}_{timezone.now().strftime('%Y%m%d')}"
        title = f"[Daily] {template['title']}"
        description = template["description"]
        
        objectives = []
        for obj_type, target, count in template["objectives"]:
            objectives.append(QuestObjective(obj_type, target, count))
        
        rewards = self._calculate_rewards(level, difficulty, template["difficulty_modifier"])
        time_limit = template.get("time_limit", timedelta(hours=24))
        
        return Quest(
            quest_id=quest_id,
            title=title,
            description=description,
            quest_type=QuestType.DAILY,
            difficulty=difficulty,
            objectives=objectives,
            rewards=rewards,
            level_requirement=1,
            time_limit=time_limit
        )
    
    def _calculate_rewards(self, level: int, difficulty: QuestDifficulty, 
                          modifier: float = 1.0) -> QuestReward:
        """Calculate quest rewards based on level and difficulty"""
        
        difficulty_multipliers = {
            QuestDifficulty.EASY: 0.8,
            QuestDifficulty.NORMAL: 1.0,
            QuestDifficulty.HARD: 1.5,
            QuestDifficulty.EPIC: 2.5,
            QuestDifficulty.LEGENDARY: 4.0
        }
        
        multiplier = difficulty_multipliers[difficulty] * modifier
        base_exp = level * 50
        base_gold = level * 25
        
        experience = int(base_exp * multiplier)
        gold = int(base_gold * multiplier)
        reputation = max(1, int(level * 0.5 * multiplier))
        
        # Chance for item rewards at higher difficulties
        items = []
        if difficulty in [QuestDifficulty.HARD, QuestDifficulty.EPIC, QuestDifficulty.LEGENDARY]:
            if random.random() < 0.3:  # 30% chance
                items = [self._generate_item_reward(level, difficulty)]
        
        return QuestReward(
            experience=experience,
            gold=gold,
            items=items,
            reputation=reputation
        )
    
    def _generate_item_reward(self, level: int, difficulty: QuestDifficulty) -> Dict:
        """Generate random item reward"""
        item_types = ["weapon", "armor", "consumable", "material"]
        item_type = random.choice(item_types)
        
        rarity_weights = {
            QuestDifficulty.EASY: {"common": 0.9, "uncommon": 0.1},
            QuestDifficulty.NORMAL: {"common": 0.7, "uncommon": 0.3},
            QuestDifficulty.HARD: {"common": 0.4, "uncommon": 0.5, "rare": 0.1},
            QuestDifficulty.EPIC: {"uncommon": 0.4, "rare": 0.5, "epic": 0.1},
            QuestDifficulty.LEGENDARY: {"rare": 0.4, "epic": 0.5, "legendary": 0.1}
        }
        
        rarities = list(rarity_weights[difficulty].keys())
        weights = list(rarity_weights[difficulty].values())
        rarity = random.choices(rarities, weights=weights)[0]
        
        return {
            "type": item_type,
            "rarity": rarity,
            "level": level,
            "name": f"{rarity.title()} {item_type.title()}"
        }


class QuestManager:
    """Manages quest state and progression for characters"""
    
    def __init__(self):
        self.generator = QuestGenerator()
    
    def get_available_quests(self, character_level: int, location: str = None) -> List[Quest]:
        """Get list of available quests for character"""
        quests = []
        
        # Generate random quests
        for _ in range(random.randint(3, 6)):
            quest = self.generator.generate_quest(character_level)
            if quest:
                quests.append(quest)
        
        # Always include a daily quest
        daily_quest = self.generator.generate_quest(
            character_level, 
            quest_type=QuestType.DAILY
        )
        if daily_quest:
            quests.append(daily_quest)
        
        return quests
    
    def start_quest(self, character, quest: Quest) -> bool:
        """Start a quest for character"""
        # Check prerequisites
        if character.level < quest.level_requirement:
            return False
        
        # Check if character already has this quest
        # This would typically check the database
        
        return quest.start()
    
    def update_quest_progress(self, character, action: str, target: str, amount: int = 1) -> List[str]:
        """Update quest progress for character actions"""
        # This would typically load active quests from database
        # For now, return empty list as placeholder
        updated_quests = []
        
        # Example logic:
        # for quest in character.active_quests:
        #     if quest.update_objective(action, target, amount):
        #         updated_quests.append(quest.quest_id)
        #         if quest.status == QuestStatus.COMPLETED:
        #             self._complete_quest(character, quest)
        
        return updated_quests
    
    def complete_quest(self, character, quest: Quest) -> Dict:
        """Complete quest and give rewards"""
        if not quest.complete():
            return {"success": False, "message": "Quest cannot be completed"}
        
        # Apply rewards
        rewards_applied = {
            "experience": 0,
            "gold": 0,
            "items": [],
            "reputation": 0
        }
        
        # This would typically update the character in database
        # character.experience += quest.rewards.experience
        # character.gold += quest.rewards.gold
        # etc.
        
        rewards_applied.update(quest.rewards.to_dict())
        
        return {
            "success": True,
            "message": f"Quest '{quest.title}' completed!",
            "rewards": rewards_applied
        }
    
    def cleanup_expired_quests(self, character) -> int:
        """Remove expired quests"""
        # This would typically update quests in database
        expired_count = 0
        
        # for quest in character.active_quests:
        #     if quest.is_expired():
        #         quest.status = QuestStatus.EXPIRED
        #         expired_count += 1
        
        return expired_count


# Global quest manager instance
quest_manager = QuestManager()
