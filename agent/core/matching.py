"""
Interest-based matching algorithm
"""
from typing import Dict, List


class MatchingEngine:
    """Calculate compatibility scores between users"""

    def __init__(self, high_match_threshold: float = 0.75):
        self.high_match_threshold = high_match_threshold

    def calculate_match_score(self, user1_profile: Dict, user2_profile: Dict) -> float:
        """
        Calculate compatibility score between two users

        Args:
            user1_profile: First user's profile data
            user2_profile: Second user's profile data

        Returns:
            float between 0 and 1 indicating match quality
        """
        score = 0.0
        weights_sum = 0.0

        # Interest overlap (weight: 0.4)
        interest_score = self._calculate_interest_overlap(
            user1_profile.get('interests', []),
            user2_profile.get('interests', [])
        )
        score += interest_score * 0.4
        weights_sum += 0.4

        # Industry/field match (weight: 0.3)
        industry_score = self._calculate_industry_match(
            user1_profile.get('industry', ''),
            user2_profile.get('industry', '')
        )
        score += industry_score * 0.3
        weights_sum += 0.3

        # Role/seniority compatibility (weight: 0.2)
        role_score = self._calculate_role_compatibility(
            user1_profile.get('role', ''),
            user2_profile.get('role', ''),
            user1_profile.get('seniority', ''),
            user2_profile.get('seniority', '')
        )
        score += role_score * 0.2
        weights_sum += 0.2

        # Goals alignment (weight: 0.1)
        goals_score = self._calculate_goals_alignment(
            user1_profile.get('goals', []),
            user2_profile.get('goals', [])
        )
        score += goals_score * 0.1
        weights_sum += 0.1

        # Normalize score
        return score / weights_sum if weights_sum > 0 else 0.0

    def _calculate_interest_overlap(self, interests1: List[str], interests2: List[str]) -> float:
        """Calculate overlap between interest lists"""
        if not interests1 or not interests2:
            return 0.0

        set1 = set(i.lower() for i in interests1)
        set2 = set(i.lower() for i in interests2)

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    def _calculate_industry_match(self, industry1: str, industry2: str) -> float:
        """Calculate industry match score"""
        if not industry1 or not industry2:
            return 0.0

        # Exact match
        if industry1.lower() == industry2.lower():
            return 1.0

        # Uses keyword matching to find related industries
        keywords1 = set(industry1.lower().split())
        keywords2 = set(industry2.lower().split())

        overlap = len(keywords1 & keywords2)
        return min(overlap / 3, 0.7) if overlap > 0 else 0.0

    def _calculate_role_compatibility(
        self,
        role1: str,
        role2: str,
        seniority1: str,
        seniority2: str
    ) -> float:
        """Calculate role and seniority compatibility"""
        score = 0.0

        # Same role type gets points
        if role1 and role2:
            if role1.lower() == role2.lower():
                score += 0.5
            elif any(word in role2.lower() for word in role1.lower().split()):
                score += 0.3

        # Similar seniority gets points (peer networking)
        seniority_levels = ['junior', 'mid', 'senior', 'lead', 'manager', 'director', 'vp', 'c-level']

        if seniority1 and seniority2:
            level1 = next((i for i, level in enumerate(seniority_levels) if level in seniority1.lower()), -1)
            level2 = next((i for i, level in enumerate(seniority_levels) if level in seniority2.lower()), -1)

            if level1 >= 0 and level2 >= 0:
                diff = abs(level1 - level2)
                if diff == 0:
                    score += 0.5
                elif diff == 1:
                    score += 0.3
                elif diff == 2:
                    score += 0.1

        return min(score, 1.0)

    def _calculate_goals_alignment(self, goals1: List[str], goals2: List[str]) -> float:
        """Calculate alignment between user goals"""
        if not goals1 or not goals2:
            return 0.0

        # Simple keyword overlap
        set1 = set(' '.join(goals1).lower().split())
        set2 = set(' '.join(goals2).lower().split())

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    def is_high_match(self, score: float) -> bool:
        """Determine if a match score is high enough for autonomous action"""
        return score >= self.high_match_threshold

    def get_match_reason(self, user1_profile: Dict, user2_profile: Dict, score: float) -> str:
        """
        Generate a human-readable explanation of why users match

        Args:
            user1_profile: First user's profile
            user2_profile: Second user's profile
            score: Match score

        Returns:
            String explanation of the match
        """
        reasons = []

        # Check interests
        interests1 = set(i.lower() for i in user1_profile.get('interests', []))
        interests2 = set(i.lower() for i in user2_profile.get('interests', []))
        common_interests = interests1 & interests2

        if common_interests:
            reasons.append(f"shared interests in {', '.join(list(common_interests)[:3])}")

        # Check industry
        if user1_profile.get('industry', '').lower() == user2_profile.get('industry', '').lower():
            reasons.append(f"both work in {user1_profile.get('industry')}")

        # Check role
        if user1_profile.get('role') and user2_profile.get('role'):
            if user1_profile['role'].lower() == user2_profile['role'].lower():
                reasons.append(f"similar roles as {user1_profile['role']}")

        if not reasons:
            return "potential synergy based on your profiles"

        return " and ".join(reasons[:2])
