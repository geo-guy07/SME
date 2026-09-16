"""
Authoritative regulatory snippets for the SME Compliance & Audit Assistant.
Sources: CGST Act / CBIC, Ministry of MSME Notifications, State Shops & Establishments Acts,
EPFO, ESIC, Payment of Gratuity Act, State Professional Tax Acts, FSSAI regulations, Factories Act,
and Income Tax Act 1961 (including Sections 44AD, 44ADA, and 43B(h)).
Paraphrased summaries formatted as retrieval-ready knowledge base chunks for hybrid RAG.
"""

REGULATIONS = [
    # ---- 1. Goods and Services Tax (GST) ----
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
        "tags": ["gst", "turnover", "goods", "registration", "threshold"],
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
        "tags": ["gst", "turnover", "services", "registration", "threshold"],
    },
    {
        "id": "GST-003",
        "category": "GST",
        "title": "Composition Scheme Eligibility",
        "source": "CGST Act, 2017 - Section 10",
        "text": (
            "Small businesses with aggregate turnover up to Rs. 1.5 crore (Rs. 75 lakh for "
            "special category states) can opt for the Composition Scheme, paying tax at a "
            "fixed lower rate (1% for manufacturers/traders, 5% for restaurants) and filing "
            "simplified quarterly statements (CMP-08), but cannot claim input tax credit "
            "or make inter-state outward supplies."
        ),
        "tags": ["gst", "composition", "small business", "quarterly return"],
    },
    {
        "id": "GST-004",
        "category": "GST",
        "title": "Mandatory GST Registration - Inter-State & E-Commerce",
        "source": "CGST Act, 2017 - Section 24",
        "text": (
            "Threshold exemptions do not apply to businesses making inter-state taxable supplies "
            "or selling through e-commerce operator platforms (subject to notified threshold relief "
            "for unregistered e-commerce suppliers). Compulsory registration applies irrespective "
            "of turnover."
        ),
        "tags": ["gst", "inter-state", "ecommerce", "mandatory"],
    },
    {
        "id": "GST-005",
        "category": "GST",
        "title": "GST E-Invoicing Mandate",
        "source": "CBIC Notification No. 10/2023 - Central Tax",
        "text": (
            "Businesses whose aggregate annual turnover exceeds Rs. 5 crore in any preceding "
            "financial year from 2017-18 onwards are mandatorily required to generate e-invoices "
            "(IRN / QR code via Invoice Registration Portal) for B2B supplies and exports."
        ),
        "tags": ["gst", "e-invoicing", "b2b", "invoice"],
    },
    {
        "id": "GST-006",
        "category": "GST",
        "title": "Input Tax Credit (ITC) Matching & GSTR-2B Reconciliation",
        "source": "CGST Act, 2017 - Section 16(2)(aa) & Rule 36(4)",
        "text": (
            "Registered businesses can only avail Input Tax Credit (ITC) on inward supplies if the "
            "supplier has reported the invoice in their GSTR-1/IFF and it reflects in the buyer's "
            "auto-generated GSTR-2B. Unmatched ITC is disallowed and attracts interest if claimed."
        ),
        "tags": ["gst", "itc", "gstr-2b", "tax credit", "reconciliation"],
    },

    # ---- 2. MSME & Udyam Registration ----
    {
        "id": "MSME-001",
        "category": "MSME",
        "title": "Udyam Registration - Micro Enterprise Classification",
        "source": "Ministry of MSME Notification, Composite Criteria",
        "text": (
            "An enterprise is classified as Micro if its investment in plant and machinery "
            "or equipment does not exceed Rs. 1 crore and annual turnover does not exceed "
            "Rs. 5 crore. Micro enterprises must register on the official Udyam portal to access "
            "statutory protections, priority lending, and interest subsidies."
        ),
        "tags": ["msme", "udyam", "micro", "threshold", "classification"],
    },
    {
        "id": "MSME-002",
        "category": "MSME",
        "title": "Udyam Registration - Small Enterprise Classification",
        "source": "Ministry of MSME Notification, Composite Criteria",
        "text": (
            "An enterprise is classified as Small if its investment in plant and machinery "
            "or equipment does not exceed Rs. 10 crore and annual turnover does not exceed "
            "Rs. 50 crore. Small enterprises are eligible for Udyam registration and "
            "associated MSME benefits, including collateral-free loans under CGTMSE."
        ),
        "tags": ["msme", "udyam", "small", "threshold", "cgtmse"],
    },
    {
        "id": "MSME-003",
        "category": "MSME",
        "title": "Udyam Registration - Medium Enterprise Classification",
        "source": "Ministry of MSME Notification, Composite Criteria",
        "text": (
            "An enterprise is classified as Medium if its investment in plant and machinery "
            "or equipment does not exceed Rs. 50 crore and annual turnover does not exceed "
            "Rs. 250 crore. Medium enterprises remain eligible for Udyam registration and "
            "certain export incentive schemes."
        ),
        "tags": ["msme", "udyam", "medium", "threshold"],
    },
    {
        "id": "MSME-004",
        "category": "MSME",
        "title": "MSME Delayed Payment Protection - 45-Day Statutory Rule",
        "source": "MSMED Act, 2006 - Sections 15 & 16",
        "text": (
            "Buyers of goods or services from registered Micro and Small enterprises must make payment "
            "within the agreed period, not exceeding 45 days (or 15 days in the absence of an agreement). "
            "Delayed payments attract compound interest with monthly rests at 3 times the RBI Bank Rate."
        ),
        "tags": ["msme", "delayed payment", "45-day rule", "interest", "penalty"],
    },
    {
        "id": "MSME-005",
        "category": "MSME",
        "title": "Public Procurement Policy for MSEs",
        "source": "Ministry of MSME - Public Procurement Policy Order",
        "text": (
            "Central Ministries, Departments, and Public Sector Enterprises must procure a minimum "
            "of 25% of their total annual purchases of products and services from Micro and Small "
            "Enterprises, including sub-targets for SC/ST and women entrepreneurs."
        ),
        "tags": ["msme", "procurement", "tenders", "government"],
    },
    {
        "id": "MSME-006",
        "category": "MSME",
        "title": "Collateral-Free Credit Guarantee (CGTMSE Scheme)",
        "source": "Credit Guarantee Fund Trust for Micro and Small Enterprises",
        "text": (
            "Registered Micro and Small Enterprises can access collateral-free credit facilities "
            "(term loans and working capital) up to Rs. 5 crore through scheduled commercial banks "
            "and NBFCs with guarantee cover provided by CGTMSE."
        ),
        "tags": ["msme", "credit", "loan", "collateral-free", "cgtmse"],
    },

    # ---- 3. Shops & Establishments Acts ----
    {
        "id": "SE-001",
        "category": "Shops & Establishments",
        "title": "Shops & Establishments Registration Requirement",
        "source": "State Shops and Commercial Establishments Act (State Adopted)",
        "text": (
            "Any shop, commercial establishment, or business premises employing one or more "
            "persons must register under the applicable State Shops and Establishments Act "
            "within 30 days of commencing operations. This registration serves as foundational legal "
            "proof of commercial existence for opening bank accounts and obtaining local trade licenses."
        ),
        "tags": ["shops and establishments", "registration", "30 days", "commercial"],
    },
    {
        "id": "SE-002",
        "category": "Shops & Establishments",
        "title": "Employee Working Hours and Leave Requirements",
        "source": "State Shops and Establishments Act (State Adopted)",
        "text": (
            "Establishments registered under the Shops and Establishments Act must not "
            "require employees to work more than 9 hours a day or 48 hours a week, and must "
            "provide at least one weekly holiday along with earned, casual, and sick leave "
            "as prescribed by the respective state rules."
        ),
        "tags": ["working hours", "leave", "weekly off", "labor"],
    },
    {
        "id": "SE-003",
        "category": "Shops & Establishments",
        "title": "Display of Registration Certificate & Statutory Registers",
        "source": "State Shops and Commercial Establishments Rules",
        "text": (
            "The employer must conspicuously display the registration certificate at the premises, "
            "maintain employee muster rolls (Form A/B), overtime registers, and wage slips, and "
            "produce them upon inspection by the state Labour Officer."
        ),
        "tags": ["shops", "registers", "muster roll", "inspection"],
    },

    # ---- 4. Labour Laws & Social Security ----
    {
        "id": "LAB-001",
        "category": "Labour Law",
        "title": "Provident Fund (PF / EPFO) Applicability Threshold",
        "source": "Employees' Provident Funds and Miscellaneous Provisions Act, 1952",
        "text": (
            "Establishments employing 20 or more persons must register for and contribute "
            "to the Employees' Provident Fund (EPF). Both employer and employee contribute "
            "12% of basic wages plus dearness allowance to the fund each month, with voluntary "
            "registration permitted for smaller establishments."
        ),
        "tags": ["pf", "epfo", "provident fund", "20 employees", "contribution"],
    },
    {
        "id": "LAB-002",
        "category": "Labour Law",
        "title": "ESI (Employee State Insurance) Applicability Threshold",
        "source": "Employees' State Insurance Act, 1948",
        "text": (
            "Establishments employing 10 or more persons (in notified areas) where employees "
            "earn wages up to Rs. 21,000 per month (Rs. 25,000 for employees with disabilities) "
            "must register under ESI. Current contribution rates are 3.25% by employer and "
            "0.75% by employee."
        ),
        "tags": ["esi", "esic", "10 employees", "medical benefit", "insurance"],
    },
    {
        "id": "LAB-003",
        "category": "Labour Law",
        "title": "Payment of Gratuity Act Applicability",
        "source": "Payment of Gratuity Act, 1972",
        "text": (
            "Applies to every factory, mine, oilfield, plantation, port, railway company, and shop "
            "or establishment in which 10 or more persons are employed on any day of the preceding "
            "12 months. Gratuity is payable to an employee on separation after continuous service "
            "of not less than 5 years at the rate of 15 days wages per completed year."
        ),
        "tags": ["gratuity", "10 employees", "separation", "retirement"],
    },
    {
        "id": "LAB-004",
        "category": "Labour Law",
        "title": "Minimum Wages Act & Variable Dearness Allowance",
        "source": "Minimum Wages Act, 1948 / Code on Wages",
        "text": (
            "Every employer must pay wages not less than the statutory minimum wage rate "
            "notified by the appropriate Government (Central or State) for scheduled employments, "
            "categorized into unskilled, semi-skilled, skilled, and highly skilled categories, "
            "updated twice a year with Variable Dearness Allowance (VDA)."
        ),
        "tags": ["minimum wages", "vda", "statutory pay", "worker"],
    },
    {
        "id": "LAB-005",
        "category": "Labour Law",
        "title": "Equal Remuneration & Prevention of Workplace Discrimination",
        "source": "Equal Remuneration Act, 1976 / Code on Wages",
        "text": (
            "Employers are legally obligated to provide equal pay to male and female workers "
            "performing the same work or work of a similar nature. Employers must maintain "
            "registers in Form D showing employee particulars."
        ),
        "tags": ["equal pay", "gender equality", "wage parity", "labor"],
    },

    # ---- 5. Professional Tax (State Specific) ----
    {
        "id": "PT-001",
        "category": "Professional Tax",
        "title": "Professional Tax - Maharashtra (PTEC & PTRC)",
        "source": "Maharashtra State Tax on Professions, Trades, Callings and Employments Act, 1975",
        "text": (
            "Every business entity operating in Maharashtra must obtain a Professional Tax "
            "Enrollment Certificate (PTEC) and pay Rs. 2,500 annually. If employing staff with monthly "
            "salaries over Rs. 10,000 (men) or Rs. 25,000 (women), the employer must also obtain a "
            "Registration Certificate (PTRC) and deduct up to Rs. 200/month (Rs. 300 in February)."
        ),
        "tags": ["professional tax", "maharashtra", "ptec", "ptrc"],
    },
    {
        "id": "PT-002",
        "category": "Professional Tax",
        "title": "Professional Tax - Karnataka",
        "source": "Karnataka Tax on Professions, Trades, Callings and Employments Act, 1976",
        "text": (
            "Employers in Karnataka must register for Professional Tax within 30 days of hiring. "
            "Deduction of Rs. 200 per month applies to all employees drawing a gross salary of "
            "Rs. 25,000 or more per month. Self-employed individuals must pay annual tax of Rs. 2,500."
        ),
        "tags": ["professional tax", "karnataka", "salary threshold"],
    },
    {
        "id": "PT-003",
        "category": "Professional Tax",
        "title": "Professional Tax - West Bengal, MP, and Gujarat",
        "source": "Respective State Professional Tax Acts",
        "text": (
            "State laws in West Bengal, Madhya Pradesh, Gujarat, and Telangana mandate professional "
            "tax registration for both the enterprise entity and deduction from employee salaries "
            "above state-specific slabs (typically Rs. 10,000 to Rs. 15,000 monthly). Failure to enroll "
            "attracts penalty and compounding monthly interest."
        ),
        "tags": ["professional tax", "west bengal", "madhya pradesh", "gujarat"],
    },

    # ---- 6. Food Safety & Standards (FSSAI) ----
    {
        "id": "FSSAI-001",
        "category": "Food Safety",
        "title": "FSSAI Basic Registration - Petty Food Businesses",
        "source": "Food Safety and Standards (Licensing and Registration) Regulations, 2011",
        "text": (
            "All petty food business operators (FBOs) including small retail food shops, hawkers, "
            "cloud kitchens, and caterers with an annual turnover up to Rs. 12 lakh must obtain an "
            "FSSAI Basic Registration (14-digit registration number). Operating without registration "
            "is punishable with imprisonment up to 6 months and a fine up to Rs. 5 lakh."
        ),
        "tags": ["fssai", "food license", "petty food", "turnover 12 lakh"],
    },
    {
        "id": "FSSAI-002",
        "category": "Food Safety",
        "title": "FSSAI State Food License",
        "source": "Food Safety and Standards (Licensing and Registration) Regulations, 2011",
        "text": (
            "Food businesses with an annual turnover between Rs. 12 lakh and Rs. 20 crore (e.g. "
            "restaurants, hotels, food manufacturers, distributors) must obtain an FSSAI State License. "
            "Requires compliance with Schedule 4 sanitary and hygiene standards and annual return filing."
        ),
        "tags": ["fssai", "state license", "restaurants", "food safety"],
    },
    {
        "id": "FSSAI-003",
        "category": "Food Safety",
        "title": "FSSAI Central License - Large Scale & E-Commerce",
        "source": "Food Safety and Standards (Licensing and Registration) Regulations, 2011",
        "text": (
            "FBOs with an annual turnover exceeding Rs. 20 crore, 100% export-oriented units, "
            "importers, or businesses operating food delivery/e-commerce platforms across multiple "
            "states must obtain an FSSAI Central License from the designated Central Licensing Authority."
        ),
        "tags": ["fssai", "central license", "multi-state", "export"],
    },

    # ---- 7. Manufacturing & Factories Act ----
    {
        "id": "FAC-001",
        "category": "Factories Act",
        "title": "Factories Act Registration & License Threshold",
        "source": "Factories Act, 1948 - Section 2(m)",
        "text": (
            "Manufacturing premises where 10 or more workers are employed with the aid of power, "
            "or 20 or more workers without the aid of power, qualify as a 'Factory'. Such units "
            "must obtain factory plan approval, factory license from the Chief Inspector of Factories, "
            "and adhere to strict safety, health, and welfare norms."
        ),
        "tags": ["factories act", "manufacturing", "workers", "safety"],
    },
    {
        "id": "ENV-001",
        "category": "Pollution Control",
        "title": "State Pollution Control Board Consent (CTE / CTO)",
        "source": "Water Act 1974 / Air Act 1981 / CPCB Categorization",
        "text": (
            "Industrial and manufacturing units must obtain Consent to Establish (CTE) before "
            "construction and Consent to Operate (CTO) before commencing production from the State "
            "Pollution Control Board (SPCB). Non-polluting 'White category' units receive expedited "
            "or self-declaration exemptions, while Green and Orange categories require formal consent."
        ),
        "tags": ["pollution", "spcb", "consent to operate", "environment"],
    },

    # ---- 8. Income Tax & MSME Safeguards ----
    {
        "id": "IT-001",
        "category": "Income Tax",
        "title": "Presumptive Taxation for Small Businesses (Section 44AD)",
        "source": "Income Tax Act, 1961 - Section 44AD",
        "text": (
            "Eligible resident individuals, HUFs, and partnership firms with turnover up to Rs. 2 crore "
            "(increased to Rs. 3 crore if digital receipts exceed 95%) can declare profit at a presumptive "
            "rate of 8% (6% for digital receipts) and are exempt from maintaining formal books of accounts "
            "or undergoing mandatory tax audits under Section 44AB."
        ),
        "tags": ["income tax", "44ad", "presumptive tax", "small business"],
    },
    {
        "id": "IT-002",
        "category": "Income Tax",
        "title": "Presumptive Taxation for Professionals (Section 44ADA)",
        "source": "Income Tax Act, 1961 - Section 44ADA",
        "text": (
            "Specified professionals (legal, medical, engineering, accountancy, technical consultancy, "
            "interior decoration) with gross receipts up to Rs. 50 lakh (Rs. 75 lakh if 95% receipts "
            "are digital) can declare presumptive income at 50% of gross receipts without bookkeeping."
        ),
        "tags": ["income tax", "44ada", "professionals", "consultancy"],
    },
    {
        "id": "IT-003",
        "category": "Income Tax",
        "title": "Section 43B(h) - Disallowance of Overdue Payments to MSEs",
        "source": "Income Tax Act, 1961 - Section 43B(h) (Finance Act 2023)",
        "text": (
            "Any sum payable by an enterprise to a registered Micro or Small Enterprise beyond the "
            "time limit specified in Section 15 of the MSMED Act (within 15 or 45 days) will be "
            "disallowed as a business deduction in that financial year and taxed as income, eligible "
            "for deduction only in the year the actual payment is made."
        ),
        "tags": ["income tax", "43b(h)", "msme payment", "tax disallowance"],
    },
    {
        "id": "IT-004",
        "category": "Income Tax",
        "title": "TDS Obligations on Contractor and Professional Payments",
        "source": "Income Tax Act, 1961 - Sections 194C, 194J, 194Q",
        "text": (
            "Businesses liable for tax audit under Section 44AB must deduct TDS at 1%/2% under Section 194C "
            "on payments to contractors exceeding Rs. 30,000 single contract (or Rs. 1,00,000 annual aggregate), "
            "and 10% (or 2% for technical services) under Section 194J on professional fees exceeding Rs. 30,000."
        ),
        "tags": ["tds", "withholding tax", "194c", "194j", "contractor"],
    },
]