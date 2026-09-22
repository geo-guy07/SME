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
    owner: Optional[str] = None
    pan: Optional[str] = None
    gstin: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    activity: Optional[str] = None
    aadhaar: Optional[str] = None

    def as_dict(self):
        d = {
            "business_id": self.business_id,
            "name": self.name,
            "business_type": self.business_type,
            "turnover_lakh": self.turnover_lakh,
            "employee_count": self.employee_count,
            "state": self.state,
            "registration_status": self.registration_status,
            "special_category_state": self.special_category_state,
        }
        for field_name in ["owner", "pan", "gstin", "mobile", "email", "address", "activity", "aadhaar"]:
            val = getattr(self, field_name)
            if val is not None:
                d[field_name] = val
        return d


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
    BusinessProfile(
        business_id="B005",
        name="ABC Traders",
        business_type="goods",
        turnover_lakh=45,
        employee_count=4,
        state="Madhya Pradesh",
        owner="Rahul Sharma",
        address="Indore, Madhya Pradesh",
        activity="Wholesale trading",
        pan="ABCDE1234F",
        gstin="23ABCDE1234F1Z5",
        mobile="9876543210",
        email="rahul.sharma@example.com",
        aadhaar="987654321098",
    ),
]


def get_business(business_id: str) -> Optional[BusinessProfile]:
    """
    Retrieve a business profile by ID.
    Queries PostgreSQL database first; falls back seamlessly to in-memory
    SAMPLE_BUSINESSES if database is unreachable or record is not found.
    """
    try:
        from core.db_service import get_business_from_db
        db_data = get_business_from_db(business_id)
        if db_data:
            return BusinessProfile(
                business_id=db_data["business_id"],
                name=db_data["name"],
                business_type=db_data.get("business_type", "goods"),
                turnover_lakh=float(db_data.get("turnover_lakh") or 0.0),
                employee_count=int(db_data.get("employee_count") or 1),
                state=db_data.get("state", "Madhya Pradesh"),
                registration_status=db_data.get("registration_status", "unregistered"),
                special_category_state=bool(db_data.get("special_category_state", False)),
                owner=db_data.get("owner"),
                pan=db_data.get("pan"),
                gstin=db_data.get("gstin"),
                mobile=db_data.get("mobile"),
                email=db_data.get("email"),
                address=db_data.get("address"),
                activity=db_data.get("activity"),
                aadhaar=db_data.get("aadhaar"),
            )
    except Exception:
        pass

    # Fallback to static sample businesses
    for b in SAMPLE_BUSINESSES:
        if b.business_id == business_id:
            return b
    return None