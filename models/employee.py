from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime

class EmploymentStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"
    TERMINATED = "terminated"

class SkillLevel(Enum):
    TRAINEE = "trainee"
    JUNIOR = "junior"
    SENIOR = "senior"
    EXPERT = "expert"
    def get_proficiency_score(self) -> float:
        """Convert skill level to numeric score"""
        scores = {
            SkillLevel.TRAINEE: 1.0,
            SkillLevel.JUNIOR: 2.0,
            SkillLevel.SENIOR: 3.0,
            SkillLevel.EXPERT: 4.0
        }
        return scores[self]


@dataclass
class EmployeeSkill:
    skill_name: str
    skill_category: str  # cleaning, maintenance, inspection, safety, etc.
    proficiency_level: SkillLevel
    years_experience: float
    certification_required: bool = False
    certification_date: Optional[datetime] = None

    def get_proficiency_score(self) -> float:
        """Convert skill level to numeric score"""
        scores = {
            SkillLevel.TRAINEE: 1.0,
            SkillLevel.JUNIOR: 2.0,
            SkillLevel.SENIOR: 3.0,
            SkillLevel.EXPERT: 4.0
        }
        return scores[self.proficiency_level]

@dataclass
class Employee:
    employee_id: str
    first_name: str
    last_name: str
    employment_status: EmploymentStatus = EmploymentStatus.ACTIVE
    hourly_rate: float = 20.0
    overtime_rate: float = 30.0
    skill_level: SkillLevel = SkillLevel.JUNIOR
    skills: List[EmployeeSkill] = field(default_factory=list)
    preferred_zones: List[str] = field(default_factory=list)
    shift_start: str = "08:00"
    shift_end: str = "17:00"
    performance_rating: float = 7.5  # 1-10 scale
    efficiency_rating: float = 7.5   # 1-10 scale
    quality_rating: float = 7.5      # 1-10 scale
    phone: Optional[str] = None
    hire_date: Optional[datetime] = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def get_skill_by_category(self, category: str) -> Optional[EmployeeSkill]:
        """Get best skill in a specific category"""
        category_skills = [s for s in self.skills if s.skill_category == category]
        if category_skills:
            return max(category_skills, key=lambda s: s.get_proficiency_score())
        return None

    def has_skill(self, skill_name: str, min_level: SkillLevel = SkillLevel.JUNIOR) -> bool:
        """Check if employee has required skill at minimum level"""
        for skill in self.skills:
            if skill.skill_name == skill_name:
                return skill.get_proficiency_score() >= min_level.get_proficiency_score()

        return False

    def get_cost_per_hour(self, is_overtime: bool = False) -> float:
        """Get hourly cost including overtime"""
        return self.overtime_rate if is_overtime else self.hourly_rate

    def calculate_efficiency_bonus(self) -> float:
        """Calculate efficiency-based rate bonus"""
        if self.efficiency_rating >= 9.0:
            return 1.2  # 20% bonus
        elif self.efficiency_rating >= 8.0:
            return 1.1  # 10% bonus
        return 1.0  # No bonus