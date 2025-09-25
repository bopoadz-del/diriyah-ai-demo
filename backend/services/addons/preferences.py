from typing import Dict

class Preferences:
    def __init__(self):
        self.store: Dict[str, Dict] = {}

    def set_pref(self, user_id: str, key: str, value):
        self.store.setdefault(user_id, {})[key] = value
        return self.store[user_id]

    def get_pref(self, user_id: str, key: str, default=None):
        return self.store.get(user_id, {}).get(key, default)

    def all_prefs(self, user_id: str) -> Dict:
        return self.store.get(user_id, {})

preferences = Preferences()
