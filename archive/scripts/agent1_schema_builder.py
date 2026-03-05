"""
Agent 1: Schema Builder
Creates three lookup CSV files that define the custom Delta Sector taxonomy.
"""

import csv
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── File 1: lookup_sectors.csv ──────────────────────────────────────────────
SECTORS = [
    # Delta_Sector_ID, Delta_Sector, Delta_Sub_Industry, NAICS_Code, NAICS_Title, Mapping_Type
    (1, "Finance & Financial Services", "Commercial Banking", "52211", "Commercial Banking", "Direct"),
    (1, "Finance & Financial Services", "Retail Banking", "52212", "Savings Institutions", "Direct"),
    (1, "Finance & Financial Services", "Retail Banking", "52213", "Credit Unions", "Direct"),
    (1, "Finance & Financial Services", "Lending / Fintech (partial)", "5222", "Nondepository Credit Intermediation", "Direct"),
    (1, "Finance & Financial Services", "Financial Services", "5223", "Activities Related to Credit Intermediation", "Direct"),
    (1, "Finance & Financial Services", "Capital Markets", "5231", "Securities and Commodity Exchanges", "Direct"),
    (1, "Finance & Financial Services", "Investment Banking / Brokerage", "5232", "Securities and Commodity Contracts Brokerage", "Direct"),
    (1, "Finance & Financial Services", "Asset Mgmt / PE / VC / Hedge Funds", "5239", "Other Financial Investment Activities", "Direct"),
    (1, "Finance & Financial Services", "Insurance", "5241", "Insurance Carriers", "Direct"),
    (1, "Finance & Financial Services", "Insurance", "5242", "Insurance Agencies and Brokerages", "Direct"),
    (1, "Finance & Financial Services", "Insurance", "5251", "Insurance and Employee Benefit Funds", "Direct"),
    (2, "Technology & Software", "Software Publishers", "5112", "Software Publishers", "Direct"),
    (2, "Technology & Software", "Cloud Computing", "5182", "Computing Infrastructure Providers", "Direct"),
    (2, "Technology & Software", "Search / AI Platforms", "51822", "Web Search Portals and All Other Info Services", "Direct"),
    (2, "Technology & Software", "IT Services", "5415", "Computer Systems Design and Related Services", "Direct"),
    (2, "Technology & Software", "Semiconductor", "3344", "Semiconductor and Electronic Component Mfg", "Direct"),
    (2, "Technology & Software", "Telecommunications", "517", "Telecommunications", "Direct"),
    (3, "Healthcare & Life Sciences", "Pharmaceuticals", "3254", "Pharmaceutical and Medicine Manufacturing", "Direct"),
    (3, "Healthcare & Life Sciences", "Medical Devices", "3391", "Medical Equipment and Supplies Manufacturing", "Direct"),
    (3, "Healthcare & Life Sciences", "Life Sciences R&D", "54171", "R&D in Physical Engineering and Life Sciences", "Direct"),
    (3, "Healthcare & Life Sciences", "Health Insurance", "524114", "Direct Health and Medical Insurance Carriers", "Composite"),
    (3, "Healthcare & Life Sciences", "Healthcare Admin", "622", "Hospitals", "Composite"),
    (3, "Healthcare & Life Sciences", "Healthcare Admin", "621", "Ambulatory Health Care Services", "Composite"),
    (4, "Law Firms & Legal Services", "Law Practice", "5411", "Legal Services", "Direct"),
    (5, "Management Consulting Firms", "Management Consulting", "5416", "Management Scientific and Technical Consulting", "Direct"),
    (6, "Accounting & Tax Firms", "Accounting", "5412", "Accounting Tax Preparation Bookkeeping Payroll", "Direct"),
    (7, "Advertising & PR Agencies", "Advertising", "5418", "Advertising PR and Related Services", "Direct"),
    (7, "Advertising & PR Agencies", "Market Research", "54191", "Marketing Research and Public Opinion Polling", "Direct"),
    (8, "Staffing & Recruitment Agencies", "Staffing", "5613", "Employment Services", "Direct"),
    (9, "Real Estate & Property", "Real Estate", "531", "Real Estate", "Direct"),
    (10, "Education & Academia", "Higher Ed", "6113", "Colleges Universities and Professional Schools", "Direct"),
    (10, "Education & Academia", "K-12", "6111", "Elementary and Secondary Schools", "Composite"),
    (10, "Education & Academia", "Educational Support", "6117", "Educational Support Services", "Direct"),
    (11, "Government & Public Administration", "Federal Government", "921", "Executive Legislative and General Government", "Direct"),
    (11, "Government & Public Administration", "Justice", "922", "Justice Public Order and Safety Activities", "Direct"),
    (11, "Government & Public Administration", "Economic Programs", "926", "Administration of Economic Programs", "Direct"),
    (11, "Government & Public Administration", "National Security", "928", "National Security and International Affairs", "Direct"),
    (12, "Media Publishing & Entertainment", "Publishing", "5111", "Newspaper Periodical Book and Directory Publishers", "Direct"),
    (12, "Media Publishing & Entertainment", "Film & TV", "5121", "Motion Picture and Video Industries", "Direct"),
    (12, "Media Publishing & Entertainment", "Music", "5122", "Sound Recording Industries", "Direct"),
    (12, "Media Publishing & Entertainment", "Broadcasting", "516", "Broadcasting and Content Providers", "Direct"),
    (13, "Energy & Utilities", "Oil & Gas", "2111", "Oil and Gas Extraction", "Composite"),
    (13, "Energy & Utilities", "Electric Utilities", "2211", "Electric Power Generation Transmission Distribution", "Direct"),
    (13, "Energy & Utilities", "Gas Utilities", "2212", "Natural Gas Distribution", "Direct"),
    (14, "Architecture & Engineering Firms", "Architecture", "54131", "Architectural Services", "Direct"),
    (14, "Architecture & Engineering Firms", "Engineering", "54133", "Engineering Services", "Direct"),
    (14, "Architecture & Engineering Firms", "Testing", "54138", "Testing Laboratories and Services", "Direct"),
    # ── New Sectors 15-20 ──────────────────────────────────────────────────
    (15, "Manufacturing", "Food Manufacturing", "311", "Food Manufacturing", "Direct"),
    (15, "Manufacturing", "Beverage & Tobacco", "312", "Beverage and Tobacco Product Manufacturing", "Direct"),
    (15, "Manufacturing", "Chemical Manufacturing", "325", "Chemical Manufacturing", "Direct"),
    (15, "Manufacturing", "Plastics & Rubber", "326", "Plastics and Rubber Products Manufacturing", "Direct"),
    (15, "Manufacturing", "Primary Metals", "331", "Primary Metal Manufacturing", "Direct"),
    (15, "Manufacturing", "Fabricated Metals", "332", "Fabricated Metal Product Manufacturing", "Direct"),
    (15, "Manufacturing", "Machinery", "333", "Machinery Manufacturing", "Direct"),
    (15, "Manufacturing", "Electrical Equipment", "335", "Electrical Equipment Appliance and Component Mfg", "Direct"),
    (15, "Manufacturing", "Transportation Equipment", "336", "Transportation Equipment Manufacturing", "Direct"),
    (16, "Retail Trade", "Motor Vehicle Dealers", "441", "Motor Vehicle and Parts Dealers", "Direct"),
    (16, "Retail Trade", "Food & Beverage Retailers", "445", "Food and Beverage Retailers", "Direct"),
    (16, "Retail Trade", "General Merchandise", "452", "General Merchandise Stores", "Direct"),
    (16, "Retail Trade", "Health & Personal Care", "455", "Health and Personal Care Retailers", "Direct"),
    (16, "Retail Trade", "Clothing & Accessories", "456", "Clothing Clothing Accessories Shoe and Jewelry Retailers", "Direct"),
    (17, "Construction", "Building Construction", "236", "Construction of Buildings", "Direct"),
    (17, "Construction", "Heavy & Civil Engineering", "237", "Heavy and Civil Engineering Construction", "Direct"),
    (17, "Construction", "Specialty Trade Contractors", "238", "Specialty Trade Contractors", "Direct"),
    (18, "Transportation & Warehousing", "Air Transportation", "481", "Air Transportation", "Direct"),
    (18, "Transportation & Warehousing", "Rail Transportation", "482", "Rail Transportation", "Direct"),
    (18, "Transportation & Warehousing", "Truck Transportation", "484", "Truck Transportation", "Direct"),
    (18, "Transportation & Warehousing", "Transit & Ground Passenger", "485", "Transit and Ground Passenger Transportation", "Direct"),
    (18, "Transportation & Warehousing", "Support Activities", "488", "Support Activities for Transportation", "Direct"),
    (18, "Transportation & Warehousing", "Couriers & Messengers", "492", "Couriers and Messengers", "Direct"),
    (18, "Transportation & Warehousing", "Warehousing & Storage", "493", "Warehousing and Storage", "Direct"),
    (19, "Wholesale Trade", "Durable Goods", "423", "Merchant Wholesalers Durable Goods", "Direct"),
    (19, "Wholesale Trade", "Nondurable Goods", "424", "Merchant Wholesalers Nondurable Goods", "Direct"),
    (19, "Wholesale Trade", "Electronic Markets & Agents", "4251", "Wholesale Trade Agents and Brokers", "Direct"),
    (20, "Accommodation & Food Services", "Accommodation", "721", "Accommodation", "Direct"),
    (20, "Accommodation & Food Services", "Food Services & Drinking Places", "722", "Food Services and Drinking Places", "Direct"),
]

# ── File 2: lookup_functions.csv ────────────────────────────────────────────
FUNCTIONS = [
    # Function_ID, Function_Name, SOC_Code, SOC_Title, Shared
    (1, "Executive & General Management", "11-1011", "Chief Executives", False),
    (1, "Executive & General Management", "11-1021", "General and Operations Managers", False),
    (1, "Executive & General Management", "11-1031", "Legislators", False),
    (2, "Finance Accounting & FP&A", "11-3031", "Financial Managers", False),
    (2, "Finance Accounting & FP&A", "13-2011", "Accountants and Auditors", False),
    (2, "Finance Accounting & FP&A", "13-2051", "Financial and Investment Analysts", False),
    (2, "Finance Accounting & FP&A", "13-2061", "Financial Examiners", False),
    (2, "Finance Accounting & FP&A", "13-2082", "Tax Preparers", False),
    (2, "Finance Accounting & FP&A", "13-2041", "Credit Analysts", False),
    (3, "Legal & Compliance", "23-1011", "Lawyers", False),
    (3, "Legal & Compliance", "23-1012", "Judicial Law Clerks", False),
    (3, "Legal & Compliance", "23-2011", "Paralegals and Legal Assistants", False),
    (3, "Legal & Compliance", "13-1041", "Compliance Officers", False),
    (4, "Human Resources & People Ops", "11-3121", "Human Resources Managers", False),
    (4, "Human Resources & People Ops", "13-1071", "Human Resources Specialists", False),
    (4, "Human Resources & People Ops", "13-1075", "Labor Relations Specialists", False),
    (4, "Human Resources & People Ops", "13-1151", "Training and Development Specialists", False),
    (5, "Marketing & Communications", "11-2021", "Marketing Managers", False),
    (5, "Marketing & Communications", "11-2031", "Public Relations Managers", False),
    (5, "Marketing & Communications", "13-1161", "Market Research Analysts and Marketing Specialists", False),
    (5, "Marketing & Communications", "27-3031", "Public Relations Specialists", False),
    (6, "Sales & Business Development", "11-2022", "Sales Managers", False),
    (6, "Sales & Business Development", "41-3091", "Sales Representatives Services All Other", False),
    (6, "Sales & Business Development", "41-4012", "Sales Representatives Wholesale and Manufacturing Technical", False),
    (6, "Sales & Business Development", "41-9031", "Sales Engineers", False),
    (7, "Information Technology", "15-1211", "Computer Systems Analysts", False),
    (7, "Information Technology", "15-1212", "Information Security Analysts", False),
    (7, "Information Technology", "15-1221", "Computer and Information Research Scientists", False),
    (7, "Information Technology", "15-1232", "Computer User Support Specialists", False),
    (7, "Information Technology", "15-1241", "Computer Network Architects", False),
    (7, "Information Technology", "15-1244", "Network and Computer Systems Administrators", False),
    (7, "Information Technology", "15-1251", "Computer Programmers", False),
    (7, "Information Technology", "15-1252", "Software Developers", False),
    (7, "Information Technology", "15-1253", "Software Quality Assurance Analysts and Testers", False),
    (7, "Information Technology", "15-1254", "Web Developers", False),
    (7, "Information Technology", "15-1255", "Web and Digital Interface Designers", False),
    (7, "Information Technology", "15-1299", "Computer Occupations All Other", False),
    (8, "Data Analytics & Research", "15-2051", "Data Scientists", False),
    (8, "Data Analytics & Research", "15-2041", "Statisticians", False),
    (8, "Data Analytics & Research", "13-1111", "Management Analysts", True),   # Shared with Function 10
    (8, "Data Analytics & Research", "19-3011", "Economists", False),
    (8, "Data Analytics & Research", "15-2031", "Operations Research Analysts", False),
    (9, "Supply Chain Procurement & Operations", "11-3071", "Transportation Storage and Distribution Managers", False),
    (9, "Supply Chain Procurement & Operations", "13-1023", "Purchasing Agents Except Wholesale Retail and Farm", False),
    (9, "Supply Chain Procurement & Operations", "13-1081", "Logisticians", False),
    (9, "Supply Chain Procurement & Operations", "13-1082", "Project Management Specialists", False),
    (10, "Strategy & Corporate Development", "13-1111", "Management Analysts", True),   # Shared with Function 8
    (10, "Strategy & Corporate Development", "13-1199", "Business Operations Specialists All Other", False),
]

# ── File 3: lookup_jobs.csv ─────────────────────────────────────────────────
JOBS = [
    # Custom_Title, Delta_Sector_ID, SOC_Code, SOC_Title, Mapping_Notes
    ("Investment Banker", "1", "13-2051", "Financial and Investment Analysts", "Closest match"),
    ("Financial Analyst", "1", "13-2051", "Financial and Investment Analysts", "Direct"),
    ("Portfolio Manager", "1", "11-3031", "Financial Managers", "Closest match"),
    ("Quantitative Analyst", "1", "15-2051", "Data Scientists", "Closest for quant roles"),
    ("Risk Analyst", "1", "13-2051", "Financial and Investment Analysts", "Subspecialty"),
    ("Actuary", "1", "15-2011", "Actuaries", "Direct"),
    ("Insurance Underwriter", "1", "13-2053", "Insurance Underwriters", "Direct"),
    ("Compliance Officer", "1", "13-1041", "Compliance Officers", "Direct"),
    ("Wealth Advisor", "1", "13-2052", "Personal Financial Advisors", "Direct"),
    ("Credit Analyst", "1", "13-2041", "Credit Analysts", "Direct"),
    ("Loan Officer", "1", "13-2072", "Loan Officers", "Direct"),
    ("Claims Adjuster", "1", "13-1031", "Claims Adjusters Examiners and Investigators", "Direct"),
    ("Financial Planner", "1", "13-2052", "Personal Financial Advisors", "Same SOC"),
    ("Treasury Analyst", "1", "13-2051", "Financial and Investment Analysts", "Subspecialty"),
    ("Fund Accountant", "1", "13-2011", "Accountants and Auditors", "Closest"),
    ("Software Engineer", "2", "15-1252", "Software Developers", "Direct"),
    ("DevOps Engineer", "2", "15-1244", "Network and Computer Systems Administrators", "Closest"),
    ("Data Scientist", "2", "15-2051", "Data Scientists", "Direct"),
    ("Machine Learning Engineer", "2", "15-1252", "Software Developers", "No specific SOC"),
    ("Product Manager", "2", "11-2021", "Marketing Managers", "Common mapping"),
    ("UX/UI Designer", "2", "15-1255", "Web and Digital Interface Designers", "Direct"),
    ("Cybersecurity Analyst", "2", "15-1212", "Information Security Analysts", "Direct"),
    ("Cloud Architect", "2", "15-1241", "Computer Network Architects", "Closest"),
    ("Solutions Architect", "2", "15-1241", "Computer Network Architects", "Closest"),
    ("QA Engineer", "2", "15-1253", "Software Quality Assurance Analysts and Testers", "Direct"),
    ("Site Reliability Engineer", "2", "15-1244", "Network and Computer Systems Administrators", "Closest"),
    ("Frontend Developer", "2", "15-1254", "Web Developers", "Closest"),
    ("Backend Developer", "2", "15-1252", "Software Developers", "Closest"),
    ("Data Engineer", "2", "15-1252", "Software Developers", "Closest"),
    ("Systems Analyst", "2", "15-1211", "Computer Systems Analysts", "Direct"),
    ("IT Support Specialist", "2", "15-1232", "Computer User Support Specialists", "Direct"),
    ("Network Engineer", "2", "15-1241", "Computer Network Architects", "Closest"),
    ("Database Administrator", "2", "15-1242", "Database Administrators", "Direct"),
    ("Telecom Engineer", "2", "17-2072", "Electronics Engineers Except Computer", "Closest"),
    ("Healthcare Administrator", "3", "11-9111", "Medical and Health Services Managers", "Direct"),
    ("Regulatory Affairs Manager", "3", "11-9199", "Managers All Other", "Closest"),
    ("Clinical Research Associate", "3", "19-1042", "Medical Scientists", "Closest"),
    ("Biostatistician", "3", "15-2041", "Statisticians", "Direct"),
    ("Medical Science Liaison", "3", "19-1042", "Medical Scientists", "Closest"),
    ("Pharmacovigilance Specialist", "3", "19-1042", "Medical Scientists", "Closest"),
    ("Health Informatics Analyst", "3", "15-2051", "Data Scientists", "Closest"),
    ("Clinical Data Manager", "3", "15-2051", "Data Scientists", "Closest"),
    ("Attorney", "4", "23-1011", "Lawyers", "Direct"),
    ("Paralegal", "4", "23-2011", "Paralegals and Legal Assistants", "Direct"),
    ("Legal Secretary", "4", "43-6012", "Legal Secretaries and Administrative Assistants", "Direct"),
    ("Contract Manager", "4", "23-2011", "Paralegals and Legal Assistants", "Closest"),
    ("Management Consultant", "5", "13-1111", "Management Analysts", "Direct"),
    ("Strategy Consultant", "5", "13-1111", "Management Analysts", "Same SOC"),
    ("Business Analyst", "5", "13-1111", "Management Analysts", "Same SOC"),
    ("IT Consultant", "5", "15-1211", "Computer Systems Analysts", "Closest"),
    ("Operations Consultant", "5", "13-1111", "Management Analysts", "Same SOC"),
    ("Auditor", "6", "13-2011", "Accountants and Auditors", "Direct"),
    ("CPA", "6", "13-2011", "Accountants and Auditors", "Direct"),
    ("Controller", "6", "11-3031", "Financial Managers", "Closest"),
    ("Tax Advisor", "6", "13-2082", "Tax Preparers", "Closest"),
    ("Bookkeeper", "6", "43-3031", "Bookkeeping Accounting and Auditing Clerks", "Direct"),
    ("Forensic Accountant", "6", "13-2011", "Accountants and Auditors", "Subspecialty"),
    ("Marketing Manager", "7", "11-2021", "Marketing Managers", "Direct"),
    ("Growth Marketer", "7", "13-1161", "Market Research Analysts and Marketing Specialists", "Closest"),
    ("Brand Manager", "7", "11-2021", "Marketing Managers", "Closest"),
    ("SEO Specialist", "7", "13-1161", "Market Research Analysts and Marketing Specialists", "Closest"),
    ("PR Manager", "7", "11-2031", "Public Relations Managers", "Direct"),
    ("Content Strategist", "7", "27-3043", "Writers and Authors", "Closest"),
    ("Social Media Manager", "7", "13-1161", "Market Research Analysts and Marketing Specialists", "Closest"),
    ("Copywriter", "7", "27-3043", "Writers and Authors", "Closest"),
    ("Media Planner", "7", "13-1161", "Market Research Analysts and Marketing Specialists", "Closest"),
    ("Creative Director", "7", "11-2021", "Marketing Managers", "Closest"),
    ("Graphic Designer", "7", "27-1024", "Graphic Designers", "Direct"),
    ("Recruiter", "8", "13-1071", "Human Resources Specialists", "Direct"),
    ("Staffing Coordinator", "8", "43-4161", "Human Resources Assistants", "Closest"),
    ("Talent Acquisition Specialist", "8", "13-1071", "Human Resources Specialists", "Direct"),
    ("Real Estate Broker", "9", "41-9021", "Real Estate Brokers", "Direct"),
    ("Real Estate Agent", "9", "41-9022", "Real Estate Sales Agents", "Direct"),
    ("Property Manager", "9", "11-9141", "Property Real Estate and Community Association Managers", "Direct"),
    ("Real Estate Appraiser", "9", "13-2020", "Property Appraisers and Assessors", "Direct"),
    ("Professor", "10", "25-1199", "Postsecondary Teachers All Other", "Direct"),
    ("Academic Administrator", "10", "11-9032", "Education Administrators Postsecondary", "Direct"),
    ("K-12 Teacher", "10", "25-2031", "Secondary School Teachers", "Closest"),
    ("School Counselor", "10", "21-1012", "Educational Vocational and School Counselors", "Direct"),
    ("Instructional Designer", "10", "25-9031", "Instructional Coordinators", "Direct"),
    ("Policy Analyst", "11", "13-1111", "Management Analysts", "Closest"),
    ("Urban Planner", "11", "19-3051", "Urban and Regional Planners", "Direct"),
    ("Government Program Manager", "11", "13-1082", "Project Management Specialists", "Closest"),
    ("Budget Analyst", "11", "13-2031", "Budget Analysts", "Direct"),
    ("Intelligence Analyst", "11", "33-3021", "Detectives and Criminal Investigators", "Closest"),
    ("Editor", "12", "27-3041", "Editors", "Direct"),
    ("Producer", "12", "27-2012", "Producers and Directors", "Direct"),
    ("Journalist", "12", "27-3023", "News Analysts Reporters and Journalists", "Direct"),
    ("Film Editor", "12", "27-4032", "Film and Video Editors", "Direct"),
    ("Sound Engineer", "12", "27-4011", "Audio and Video Technicians", "Closest"),
    ("Broadcast Technician", "12", "27-4012", "Broadcast Technicians", "Direct"),
    ("Energy Analyst", "13", "13-2051", "Financial and Investment Analysts", "Closest"),
    ("Petroleum Engineer", "13", "17-2171", "Petroleum Engineers", "Direct"),
    ("Power Plant Operator", "13", "51-8013", "Power Plant Operators", "Direct"),
    ("Utility Manager", "13", "11-3071", "Transportation Storage and Distribution Managers", "Closest"),
    ("Architect", "14", "17-1011", "Architects Except Landscape and Naval", "Direct"),
    ("Civil Engineer", "14", "17-2051", "Civil Engineers", "Direct"),
    ("Structural Engineer", "14", "17-2051", "Civil Engineers", "Same SOC"),
    ("Environmental Engineer", "14", "17-2081", "Environmental Engineers", "Direct"),
    ("Mechanical Engineer", "14", "17-2141", "Mechanical Engineers", "Direct"),
    ("Drafter", "14", "17-3011", "Architectural and Civil Drafters", "Direct"),
    # Cross-industry roles — assigned to highest-employment industry per NIOEM
    ("Account Executive", "2", "41-3091", "Sales Representatives Services All Other", "Cross-industry; primary: Technology"),
    ("Sales Director", "5", "11-2022", "Sales Managers", "Cross-industry; primary: Consulting"),
    ("VP of Sales", "2", "11-2022", "Sales Managers", "Cross-industry; primary: Technology"),
    ("CEO", "3", "11-1011", "Chief Executives", "Cross-industry; primary: Healthcare"),
    ("COO", "3", "11-1021", "General and Operations Managers", "Cross-industry; primary: Healthcare"),
    ("CFO", "1", "11-3031", "Financial Managers", "Cross-industry; primary: Finance"),
    ("CTO", "2", "11-3021", "Computer and Information Systems Managers", "Cross-industry; primary: Technology"),
    ("CISO", "2", "15-1212", "Information Security Analysts", "Cross-industry; primary: Technology"),
    ("HR Manager", "3", "11-3121", "Human Resources Managers", "Cross-industry; primary: Healthcare"),
    ("HR Director", "11", "11-3121", "Human Resources Managers", "Cross-industry; primary: Government"),
    ("VP of Engineering", "2", "11-3021", "Computer and Information Systems Managers", "Cross-industry; primary: Technology"),
    ("Project Manager", "2", "13-1082", "Project Management Specialists", "Cross-industry; primary: Technology"),
    ("Scrum Master", "2", "13-1082", "Project Management Specialists", "Cross-industry; primary: Technology"),
    ("Business Development Manager", "5", "11-2022", "Sales Managers", "Cross-industry; primary: Consulting"),
    ("Training Manager", "3", "13-1151", "Training and Development Specialists", "Cross-industry; primary: Healthcare"),
    ("Compensation Analyst", "11", "13-1141", "Compensation Benefits and Job Analysis Specialists", "Cross-industry; primary: Government"),
    ("Data Analyst", "2", "15-2051", "Data Scientists", "Cross-industry; primary: Technology"),
    ("Business Intelligence Analyst", "1", "15-2051", "Data Scientists", "Cross-industry; primary: Finance"),
    ("Supply Chain Manager", "15", "11-3071", "Transportation Storage and Distribution Managers", "Cross-industry; primary: Manufacturing"),
    ("Procurement Specialist", "15", "13-1023", "Purchasing Agents Except Wholesale Retail and Farm", "Cross-industry; primary: Manufacturing"),
    ("Logistics Coordinator", "18", "13-1081", "Logisticians", "Cross-industry; primary: Transportation"),
    ("Operations Analyst", "5", "13-1111", "Management Analysts", "Cross-industry; primary: Consulting"),
    ("Corporate Strategist", "5", "13-1199", "Business Operations Specialists All Other", "Cross-industry; primary: Consulting"),
    # ── Representative jobs for new sectors 15-20 ─────────────────────────
    ("Plant Manager", "15", "11-1021", "General and Operations Managers", "Manufacturing context"),
    ("Quality Assurance Manager", "15", "11-3051", "Industrial Production Managers", "Direct"),
    ("Manufacturing Engineer", "15", "17-2112", "Industrial Engineers", "Direct"),
    ("Production Supervisor", "15", "51-1011", "First-Line Supervisors of Production Workers", "Direct"),
    ("Safety Manager", "15", "19-5011", "Occupational Health and Safety Specialists", "Direct"),
    ("Retail Store Manager", "16", "11-1021", "General and Operations Managers", "Retail context"),
    ("Retail Buyer", "16", "13-1020", "Buyers and Purchasing Agents", "Direct"),
    ("Merchandising Manager", "16", "11-2021", "Marketing Managers", "Retail context"),
    ("Loss Prevention Manager", "16", "33-9099", "Protective Service Workers All Other", "Closest"),
    ("Construction Manager", "17", "11-9021", "Construction Managers", "Direct"),
    ("Construction Estimator", "17", "13-1051", "Cost Estimators", "Direct"),
    ("Site Superintendent", "17", "47-1011", "First-Line Supervisors of Construction Trades Workers", "Direct"),
    ("Fleet Manager", "18", "11-3071", "Transportation Storage and Distribution Managers", "Direct"),
    ("Logistics Manager", "18", "11-3071", "Transportation Storage and Distribution Managers", "Transport context"),
    ("Warehouse Manager", "18", "11-3071", "Transportation Storage and Distribution Managers", "Warehouse context"),
    ("Dispatch Coordinator", "18", "43-5032", "Dispatchers Except Police Fire and Ambulance", "Direct"),
    ("Wholesale Account Manager", "19", "41-4012", "Sales Representatives Wholesale and Manufacturing Technical", "Direct"),
    ("Distribution Manager", "19", "11-3071", "Transportation Storage and Distribution Managers", "Wholesale context"),
    ("Hotel General Manager", "20", "11-9081", "Lodging Managers", "Direct"),
    ("Restaurant Manager", "20", "11-9051", "Food Service Managers", "Direct"),
    ("Event Coordinator", "20", "13-1121", "Meeting Convention and Event Planners", "Direct"),
    ("Catering Manager", "20", "11-9051", "Food Service Managers", "Catering context"),
]


def write_csv(filename, headers, rows):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"  Created {filename}: {len(rows)} rows")
    return path


def main():
    print("=" * 60)
    print("AGENT 1: Schema Builder")
    print("=" * 60)

    # File 1: lookup_sectors.csv
    print("\n1. Building lookup_sectors.csv...")
    write_csv(
        "lookup_sectors.csv",
        ["Delta_Sector_ID", "Delta_Sector", "Delta_Sub_Industry", "NAICS_Code", "NAICS_Title", "Mapping_Type"],
        SECTORS,
    )

    # File 2: lookup_functions.csv
    print("\n2. Building lookup_functions.csv...")
    write_csv(
        "lookup_functions.csv",
        ["Function_ID", "Function_Name", "SOC_Code", "SOC_Title", "Shared"],
        FUNCTIONS,
    )

    # File 3: lookup_jobs.csv
    print("\n3. Building lookup_jobs.csv...")
    write_csv(
        "lookup_jobs.csv",
        ["Custom_Title", "Delta_Sector_ID", "SOC_Code", "SOC_Title", "Mapping_Notes"],
        JOBS,
    )

    # Verification
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    print(f"\nSectors: {len(set(s[0] for s in SECTORS))} unique Delta Sectors, {len(SECTORS)} NAICS mappings")
    print(f"Functions: {len(set(f[0] for f in FUNCTIONS))} unique Functions, {len(FUNCTIONS)} SOC mappings")
    print(f"  Shared SOC codes: {sum(1 for f in FUNCTIONS if f[4])}")
    print(f"Jobs: {len(JOBS)} custom job titles")
    print(f"  Industry-assigned: {sum(1 for j in JOBS if 'Cross-industry' not in str(j[4]))}")
    print(f"  Cross-industry: {sum(1 for j in JOBS if 'Cross-industry' in str(j[4]))}")

    # Print sector summary
    print("\nDelta Sectors:")
    seen = set()
    for s in SECTORS:
        if s[0] not in seen:
            naics_count = sum(1 for x in SECTORS if x[0] == s[0])
            print(f"  {s[0]:2d}. {s[1]:<45s} ({naics_count} NAICS codes)")
            seen.add(s[0])

    print("\nDelta Functions:")
    seen = set()
    for f in FUNCTIONS:
        if f[0] not in seen:
            soc_count = sum(1 for x in FUNCTIONS if x[0] == f[0])
            print(f"  {f[0]:2d}. {f[1]:<45s} ({soc_count} SOC codes)")
            seen.add(f[0])

    print("\nAgent 1 complete.")


if __name__ == "__main__":
    main()
