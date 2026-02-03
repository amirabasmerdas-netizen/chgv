import random
from datetime import datetime

class GameLogic:
    def __init__(self):
        pass
    
    def generate_resources(self, country_data):
        """تولید منابع برای کشور"""
        resources = {
            'gold': random.randint(50, 150),
            'iron': random.randint(20, 80),
            'stone': random.randint(15, 60),
            'food': random.randint(100, 300)
        }
        return resources
    
    def simulate_battle(self, attacker, defender):
        """شبیه‌سازی نبرد"""
        attacker_power = attacker.get('power', 100)
        defender_power = defender.get('power', 100)
        
        # شانس تصادفی
        attacker_luck = random.uniform(0.8, 1.2)
        defender_luck = random.uniform(0.8, 1.2)
        
        return attacker_power * attacker_luck > defender_power * defender_luck
