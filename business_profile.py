"""
Business Profile — SME Compliance Assistant

Structured representation of a business, replacing the hardcoded dict
that was previously inline in agent_demo.py. Used by the rules engine
to evaluate which compliance requirements apply.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BusinessProfile:
    business_id: str
    name: str
    business_type: str          # "goods" or "services" (affects GST threshold)
    turnover_lakh: float        # annual turnover in Rs. lakh
    employee_count: int
    state: str
    registration_status: str = "unregistered"
    special_category_state: bool = False  # HP, Uttarakhand, NE states etc. -> lower GST threshold

    def as_dict(self):
        return {
            "business_id": self.business_id,
            "name": self.name,
            "business_type": self.business_type,
            "turnover_lakh": self.turnover_lakh,
            "employee_count": self.employee_count,
            "state": self.state,
            "registration_status": self.registration_status,
            "special_category_state": self.special_category_state,
        }


# ---- Sample businesses used for testing the rules engine ----
SAMPLE_BUSINESSES = [
    BusinessProfile(
        business_id="B001",
        name="Sharma Textiles",
        business_type="goods",
        turnover_lakh=50,
        employee_count=8,
        state="Madhya Pradesh",
        registration_status="unregistered",
    ),
    BusinessProfile(
        business_id="B002",
        name="Verma Consulting Services",
        business_type="services",
        turnover_lakh=15,
        employee_count=3,
        state="Madhya Pradesh",
        registration_status="unregistered",
    ),
    BusinessProfile(
        business_id="B003",
        name="Rao Manufacturing Pvt Ltd",
        business_type="goods",
        turnover_lakh=180,
        employee_count=25,
        state="Karnataka",
        registration_status="Udyam registered (Small)",
    ),
    BusinessProfile(
        business_id="B004",
        name="Thapa Handicrafts",
        business_type="goods",
        turnover_lakh=12,
        employee_count=2,
        state="Himachal Pradesh",
        registration_status="unregistered",
        special_category_state=True,
    ),
]


def get_business(business_id: str) -> Optional[BusinessProfile]:
    for b in SAMPLE_BUSINESSES:
        if b.business_id == business_id:
            return b
    return None