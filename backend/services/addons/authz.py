from typing import Dict

class AuthzService:
    def __init__(self):
        self.policies = []

    def add_policy(self, policy_func):
        self.policies.append(policy_func)

    def check_access(self, user: Dict, resource: Dict, action: str, env: Dict) -> Dict:
        for policy in self.policies:
            if not policy(user, resource, action, env):
                return {"granted": False, "reason": "Policy denied"}
        return {"granted": True, "reason": "All policies passed"}

authz = AuthzService()

def pm_only_approval(user, resource, action, env):
    if action == "approve" and user.get("role") != "ProjectManager":
        return False
    return True

authz.add_policy(pm_only_approval)
