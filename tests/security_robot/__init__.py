"""
On-Demand Adversarial Security Robot Package.
Provides:
    - ADVERSARIAL_ATTACK_SUITE: Curated dataset of multi-vector red-team prompts.
    - run_security_robot: Executes attack suite on demand and generates an audit scorecard.
"""

from tests.security_robot.attack_payloads import ADVERSARIAL_ATTACK_SUITE, AttackScenario

__all__ = [
    "ADVERSARIAL_ATTACK_SUITE",
    "AttackScenario",
]
