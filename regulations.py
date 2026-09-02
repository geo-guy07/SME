"""
Real regulatory snippets for the SME Compliance Assistant MVP.
Sources: GST Act / CBIC, Udyam/MSME Ministry notifications, Shops & Establishments (model act).
These are paraphrased summaries of publicly available government provisions for use as
retrieval-ready knowledge base chunks (not verbatim legal text).
"""

REGULATIONS = [
    {
        "id": "GST-001",
        "category": "GST",
        "title": "GST Registration Threshold - Goods",
        "source": "CGST Act, 2017 - Section 22 / Notification 10/2019",
        "text": (
            "A business supplying goods must register for GST if its aggregate annual "
            "turnover exceeds Rs. 40 lakh in a financial year (Rs. 20 lakh for special "
            "category states such as Himachal Pradesh, Uttarakhand, and North-Eastern states). "
            "Registration is mandatory once this threshold is crossed, regardless of profit."
        ),
    },
    {
        "id": "GST-002",
        "category": "GST",
        "title": "GST Registration Threshold - Services",
        "source": "CGST Act, 2017 - Section 22",
        "text": (
            "A business supplying services must register for GST if its aggregate annual "
            "turnover exceeds Rs. 20 lakh in a financial year (Rs. 10 lakh for special "
            "category states). This threshold is lower than the goods threshold."
        ),
    },
    {
        "id": "GST-003",
        "category": "GST",
        "title": "Composition Scheme Eligibility",
        "source": "CGST Act, 2017 - Section 10",
        "text": (
            "Small businesses with aggregate turnover up to Rs. 1.5 crore (Rs. 75 lakh for "
            "special category states) can opt for the Composition Scheme, paying tax at a "
            "fixed lower rate and filing simplified quarterly returns, but cannot claim "
            "input tax credit or make inter-state outward supplies."
        ),
    },
    {
        "id": "MSME-001",
        "category": "MSME",
        "title": "Udyam Registration - Micro Enterprise Classification",
        "source": "Ministry of MSME Notification, Udyam Registration 2020",
        "text": (
            "An enterprise is classified as Micro if its investment in plant and machinery "
            "or equipment does not exceed Rs. 2.5 crore and annual turnover does not exceed "
            "Rs. 10 crore. Micro enterprises must register on the Udyam portal to access "
            "government schemes, priority lending, and delayed-payment protection."
        ),
    },
    {
        "id": "MSME-002",
        "category": "MSME",
        "title": "Udyam Registration - Small Enterprise Classification",
        "source": "Ministry of MSME Notification, Udyam Registration 2020",
        "text": (
            "An enterprise is classified as Small if its investment in plant and machinery "
            "or equipment does not exceed Rs. 25 crore and annual turnover does not exceed "
            "Rs. 100 crore. Small enterprises are eligible for Udyam registration and "
            "associated MSME benefits, including collateral-free loans under CGTMSE."
        ),
    },
    {
        "id": "MSME-003",
        "category": "MSME",
        "title": "Udyam Registration - Medium Enterprise Classification",
        "source": "Ministry of MSME Notification, Udyam Registration 2020",
        "text": (
            "An enterprise is classified as Medium if its investment in plant and machinery "
            "or equipment does not exceed Rs. 125 crore and annual turnover does not exceed "
            "Rs. 500 crore. Medium enterprises remain eligible for Udyam registration but "
            "receive fewer subsidy benefits than Micro or Small enterprises."
        ),
    },
    {
        "id": "SE-001",
        "category": "Shops & Establishments",
        "title": "Shops & Establishments Registration Requirement",
        "source": "State Shops and Establishments Act (Model Act, state-adopted)",
        "text": (
            "Any shop, commercial establishment, or business premises employing one or more "
            "persons must register under the applicable State Shops and Establishments Act "
            "within 30 days of commencing operations. This registration governs working "
            "hours, holidays, and employee record-keeping requirements."
        ),
    },
    {
        "id": "SE-002",
        "category": "Shops & Establishments",
        "title": "Employee Working Hours and Leave Requirements",
        "source": "State Shops and Establishments Act (Model Act, state-adopted)",
        "text": (
            "Establishments registered under the Shops and Establishments Act must not "
            "require employees to work more than 9 hours a day or 48 hours a week, and must "
            "provide at least one weekly holiday along with earned/annual leave as prescribed "
            "by the respective state rules."
        ),
    },
    {
        "id": "LAB-001",
        "category": "Labour Law",
        "title": "Provident Fund (PF) Applicability Threshold",
        "source": "Employees' Provident Funds and Miscellaneous Provisions Act, 1952",
        "text": (
            "Establishments employing 20 or more persons must register for and contribute "
            "to the Employees' Provident Fund (EPF). Both employer and employee contribute "
            "12% of basic wages plus dearness allowance to the fund each month."
        ),
    },
    {
        "id": "LAB-002",
        "category": "Labour Law",
        "title": "ESI (Employee State Insurance) Applicability Threshold",
        "source": "Employees' State Insurance Act, 1948",
        "text": (
            "Establishments employing 10 or more persons (in most states) with employees "
            "earning wages up to Rs. 21,000 per month must register under the ESI scheme, "
            "which provides medical and cash benefits to employees during sickness, "
            "maternity, or employment injury."
        ),
    },
]