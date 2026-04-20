"""
AutoJustice AI NEXUS - Demo Data Seeder
Seeds the database with 52 realistic cybercrime cases for hackathon demonstration.
Run: python demo_seed.py
"""
import sys
import os
import uuid
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))
os.chdir(Path(__file__).parent / "backend")

from database import engine, Base, SessionLocal
from models.db_models import Report, AuditLog

Base.metadata.create_all(bind=engine)

# ─── Realistic Demo Cases ─────────────────────────────────────────────────────

DEMO_CASES = [
    # ── HIGH RISK ──────────────────────────────────────────────────────────────
    {
        "complainant_name": "Priya Sharma",
        "complainant_phone": "9876543210",
        "complainant_email": "priya.sharma@gmail.com",
        "complainant_address": "Bandra West, Mumbai - 400050",
        "incident_description": (
            "On 14th April 2024 at around 2:30 PM, I received a WhatsApp message from +91-8887776665 "
            "claiming to be my colleague from office. The person said my manager asked him to collect "
            "an urgent payment of Rs. 45,000 via Google Pay to UPI ID 'payment@axisbank'. I transferred "
            "the amount immediately thinking it was genuine. When I called my actual manager, he confirmed "
            "he had never made such a request. The money has been deducted from my account. "
            "Transaction ID: GP24041412345678."
        ),
        "incident_date": "14 April 2024, 2:30 PM",
        "incident_location": "Bandra West, Mumbai",
        "risk_level": "HIGH",
        "risk_score": 0.91,
        "crime_category": "Financial Crime",
        "crime_subcategory": "UPI Fraud / Social Engineering",
        "ai_summary": "Complainant transferred Rs. 45,000 via Google Pay to a fraudster impersonating a colleague on WhatsApp. Classic social engineering UPI fraud with traceable transaction ID.",
        "entities": {
            "victim": "Priya Sharma",
            "suspect": "Unknown - +91-8887776665",
            "financial_amount": "Rs. 45,000",
            "financial_vector": "Google Pay UPI - payment@axisbank",
            "platform": "WhatsApp",
            "location": "Bandra West, Mumbai",
            "contact_numbers": ["+91-8887776665"],
            "urls_links": []
        },
        "bns_sections": [
            "BNS Section 318 (Cheating)", "IT Act Section 66D (Cheating by impersonation)",
            "IT Act Section 43 (Damage to computer)"
        ],
        "authenticity_score": 0.94,
        "fake_recommendation": "GENUINE",
        "status": "FIR_GENERATED",
        "days_ago": 0,
    },
    {
        "complainant_name": "Rajesh Kumar Gupta",
        "complainant_phone": "9871234567",
        "complainant_email": "rajesh.gupta@yahoo.com",
        "complainant_address": "Koramangala, Bengaluru - 560034",
        "incident_description": (
            "A person contacted me on Instagram (handle: @investment_profits_india) claiming to offer "
            "guaranteed 30% monthly returns on stock trading. I invested Rs. 1,25,000 over 3 weeks via NEFT. "
            "Account: HDFC Bank 50100123456789 IFSC: HDFC0001234. Initially I was shown fake profits on their app. "
            "When I tried to withdraw Rs. 80,000 of profits, they demanded a tax payment of Rs. 15,000. "
            "I refused and they have since blocked me on all platforms. Total loss: Rs. 1,25,000."
        ),
        "incident_date": "1-20 March 2024",
        "incident_location": "Koramangala, Bengaluru",
        "risk_level": "HIGH",
        "risk_score": 0.93,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Investment Fraud / Pig Butchering Scam",
        "ai_summary": "Investment fraud via Instagram. Victim lost Rs. 1.25 lakh to a fake trading platform. Bank account details available for LEA investigation.",
        "entities": {
            "victim": "Rajesh Kumar Gupta",
            "suspect": "@investment_profits_india",
            "financial_amount": "Rs. 1,25,000",
            "financial_vector": "NEFT - HDFC Bank 50100123456789",
            "platform": "Instagram",
            "location": "Koramangala, Bengaluru",
            "contact_numbers": [],
            "urls_links": ["@investment_profits_india"]
        },
        "bns_sections": [
            "BNS Section 318 (Cheating)", "PMLA Section 3 (Money laundering)",
            "IT Act Section 66D", "BNS Section 316 (Criminal breach of trust)"
        ],
        "authenticity_score": 0.92,
        "fake_recommendation": "GENUINE",
        "status": "FIR_GENERATED",
        "days_ago": 1,
    },
    {
        "complainant_name": "Ananya Menon",
        "complainant_phone": "8765432109",
        "complainant_email": "ananya.menon@outlook.com",
        "complainant_address": "Adyar, Chennai - 600020",
        "incident_description": (
            "I am being blackmailed by someone with the Telegram username @darkweb_extortion. "
            "They have obtained my private photographs from my hacked phone and are threatening to share "
            "them with my family and employer unless I pay Rs. 50,000 in Bitcoin. They have sent a "
            "Bitcoin wallet address: bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh. "
            "They have given me a 48-hour deadline. I have screenshots of all conversations."
        ),
        "incident_date": "15 April 2024",
        "incident_location": "Online / Chennai",
        "risk_level": "HIGH",
        "risk_score": 0.97,
        "crime_category": "Extortion",
        "crime_subcategory": "Sextortion / Crypto Extortion",
        "ai_summary": "Active sextortion case with 48-hour deadline. Bitcoin wallet traced. Victim has screenshot evidence. IMMEDIATE police action required to prevent payment and evidence destruction.",
        "entities": {
            "victim": "Ananya Menon",
            "suspect": "@darkweb_extortion (Telegram)",
            "financial_amount": "Rs. 50,000 (in Bitcoin)",
            "financial_vector": "Bitcoin - bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            "platform": "Telegram",
            "location": "Chennai",
            "contact_numbers": [],
            "urls_links": ["@darkweb_extortion"]
        },
        "bns_sections": [
            "BNS Section 308 (Extortion)", "IT Act Section 66E (Privacy violation)",
            "IT Act Section 67 (Publishing obscene material)", "BNS Section 351 (Criminal intimidation)"
        ],
        "authenticity_score": 0.96,
        "fake_recommendation": "GENUINE",
        "status": "FIR_GENERATED",
        "days_ago": 0,
    },
    {
        "complainant_name": "Mohammed Farhan",
        "complainant_phone": "9123456780",
        "complainant_email": "farhan.mo@gmail.com",
        "complainant_address": "Hyderabad, Telangana - 500016",
        "incident_description": (
            "I received a call from 08041234567 claiming to be from TRAI (Telecom Regulatory Authority of India). "
            "The caller said my Aadhaar number has been misused to register 6 SIM cards involved in criminal activities "
            "and that my phone number will be disconnected within 2 hours unless I connect to 'CBI officer Vikram Singh' "
            "at 9988776655. I called that number and a person claiming to be CBI officer instructed me to transfer "
            "Rs. 2,00,000 to a 'safe government escrow account'. I transferred Rs. 75,000 before realizing it was fraud."
        ),
        "incident_date": "13 April 2024",
        "incident_location": "Hyderabad",
        "risk_level": "HIGH",
        "risk_score": 0.89,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Digital Arrest / Govt Impersonation Scam",
        "ai_summary": "Digital arrest scam - fraudsters impersonating TRAI and CBI extracted Rs. 75,000. Two traceable phone numbers. This is an organized cybercrime operation.",
        "entities": {
            "victim": "Mohammed Farhan",
            "suspect": "Unknown TRAI/CBI impersonators",
            "financial_amount": "Rs. 75,000",
            "financial_vector": "Bank transfer to 'government escrow'",
            "platform": "Phone Call",
            "location": "Hyderabad",
            "contact_numbers": ["08041234567", "9988776655"],
            "urls_links": []
        },
        "bns_sections": [
            "BNS Section 318 (Cheating)", "BNS Section 340 (False personation)",
            "IT Act Section 66D", "BNS Section 336 (Forgery)"
        ],
        "authenticity_score": 0.91,
        "fake_recommendation": "GENUINE",
        "status": "FIR_GENERATED",
        "days_ago": 2,
    },
    # ── MEDIUM RISK ────────────────────────────────────────────────────────────
    {
        "complainant_name": "Kavya Reddy",
        "complainant_phone": "7654321098",
        "complainant_email": "kavya.r@rediffmail.com",
        "complainant_address": "Jubilee Hills, Hyderabad - 500033",
        "incident_description": (
            "Someone has created a fake Facebook profile using my name and photos stolen from my original profile. "
            "The fake profile is sending friend requests to all my contacts and asking for money for a medical emergency. "
            "Fake profile URL: facebook.com/kavya.reddy.fake123. My friends have already received messages asking for "
            "Rs. 5,000 for hospital bills. I have complained to Facebook but no action taken in 7 days."
        ),
        "incident_date": "7 April 2024",
        "incident_location": "Hyderabad / Online",
        "risk_level": "MEDIUM",
        "risk_score": 0.62,
        "crime_category": "Identity Theft",
        "crime_subcategory": "Fake Social Media Profile / Impersonation",
        "ai_summary": "Active impersonation on Facebook causing financial harm to victim's contacts. Profile URL identified. Escalate to FB cyber team for takedown while investigating.",
        "entities": {
            "victim": "Kavya Reddy",
            "suspect": "Unknown - facebook.com/kavya.reddy.fake123",
            "financial_amount": "Rs. 5,000 (per victim contacted)",
            "financial_vector": "Unknown",
            "platform": "Facebook",
            "location": "Hyderabad",
            "contact_numbers": [],
            "urls_links": ["facebook.com/kavya.reddy.fake123"]
        },
        "bns_sections": [
            "IT Act Section 66C (Identity theft)", "IT Act Section 66D (Impersonation)",
            "BNS Section 318 (Cheating)"
        ],
        "authenticity_score": 0.87,
        "fake_recommendation": "GENUINE",
        "status": "TRIAGED",
        "days_ago": 8,
    },
    {
        "complainant_name": "Suresh Patel",
        "complainant_phone": "8899001122",
        "complainant_email": None,
        "complainant_address": "Ahmedabad, Gujarat - 380015",
        "incident_description": (
            "I received an email from 'hr.recruitment@infosys-career.net' (NOT the official infosys.com) "
            "offering me a job with salary of Rs. 8 lakhs per annum. They asked me to pay Rs. 4,500 as "
            "registration fee and Rs. 2,000 as background verification fee via Paytm to 7788990011. "
            "I paid both amounts. Later when I called the number, it was switched off. The email domain "
            "was fake - official Infosys jobs are only through infosys.com."
        ),
        "incident_date": "10 April 2024",
        "incident_location": "Ahmedabad",
        "risk_level": "MEDIUM",
        "risk_score": 0.58,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Job Fraud / Phishing",
        "ai_summary": "Job offer fraud via phishing email. Total loss Rs. 6,500. Paytm number available for reverse tracing. Victim has email evidence.",
        "entities": {
            "victim": "Suresh Patel",
            "suspect": "hr.recruitment@infosys-career.net",
            "financial_amount": "Rs. 6,500",
            "financial_vector": "Paytm - 7788990011",
            "platform": "Email",
            "location": "Ahmedabad",
            "contact_numbers": ["7788990011"],
            "urls_links": ["infosys-career.net"]
        },
        "bns_sections": [
            "BNS Section 318 (Cheating)", "IT Act Section 66D",
            "IT Act Section 66 (Hacking/unauthorized access)"
        ],
        "authenticity_score": 0.84,
        "fake_recommendation": "GENUINE",
        "status": "TRIAGED",
        "days_ago": 5,
    },
    {
        "complainant_name": "Deepika Nair",
        "complainant_phone": "9012345678",
        "complainant_email": "deepika.nair22@gmail.com",
        "complainant_address": "Thiruvananthapuram, Kerala - 695001",
        "incident_description": (
            "I have been continuously harassed on Instagram by an account @unknown_user_9876. "
            "This person sends me abusive messages daily, has shared my personal photos without consent, "
            "and is threatening to create fake nude images using AI tools (deepfakes) unless I send "
            "Rs. 10,000. I have blocked this account but they create new accounts. "
            "My mental health is severely affected. I have all screenshots."
        ),
        "incident_date": "Ongoing since 1 March 2024",
        "incident_location": "Online",
        "risk_level": "MEDIUM",
        "risk_score": 0.71,
        "crime_category": "Online Harassment",
        "crime_subcategory": "Cyber Stalking / Deepfake Threat",
        "ai_summary": "Ongoing cyber stalking with deepfake threats. Medium-term pattern indicates determined offender. Instagram account identification needed for LEA legal notice.",
        "entities": {
            "victim": "Deepika Nair",
            "suspect": "@unknown_user_9876 (Instagram)",
            "financial_amount": "Rs. 10,000 (demanded)",
            "financial_vector": None,
            "platform": "Instagram",
            "location": "Kerala",
            "contact_numbers": [],
            "urls_links": ["@unknown_user_9876"]
        },
        "bns_sections": [
            "BNS Section 351 (Criminal Intimidation)", "IT Act Section 66E (Privacy violation)",
            "IT Act Section 67 (Obscene content)", "BNS Section 308 (Extortion)"
        ],
        "authenticity_score": 0.88,
        "fake_recommendation": "GENUINE",
        "status": "TRIAGED",
        "days_ago": 3,
    },
    {
        "complainant_name": "Vikram Singh Rathore",
        "complainant_phone": "9234567891",
        "complainant_email": "vikramrathore@hotmail.com",
        "complainant_address": "Jaipur, Rajasthan - 302001",
        "incident_description": (
            "I clicked on a link in an SMS from 'VM-SBIBNK' saying my SBI account will be blocked. "
            "The link took me to a website that looked exactly like SBI internet banking at "
            "http://sbi-secure-login.xyz/netbanking. I entered my username, password, and OTP. "
            "Immediately Rs. 32,000 was transferred from my account. SBI confirmed this was a phishing site."
        ),
        "incident_date": "12 April 2024",
        "incident_location": "Jaipur",
        "risk_level": "MEDIUM",
        "risk_score": 0.67,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Bank Phishing / SMS Smishing",
        "ai_summary": "SMS phishing attack resulted in Rs. 32,000 loss via fake SBI banking portal. Phishing URL identified. Bank has confirmed fraudulent transaction.",
        "entities": {
            "victim": "Vikram Singh Rathore",
            "suspect": "Unknown - sbi-secure-login.xyz",
            "financial_amount": "Rs. 32,000",
            "financial_vector": "SBI Net Banking (unauthorized access)",
            "platform": "SMS + Fake Website",
            "location": "Jaipur",
            "contact_numbers": [],
            "urls_links": ["http://sbi-secure-login.xyz/netbanking"]
        },
        "bns_sections": [
            "IT Act Section 66 (Hacking)", "IT Act Section 66D (Impersonation)",
            "BNS Section 318 (Cheating)"
        ],
        "authenticity_score": 0.90,
        "fake_recommendation": "GENUINE",
        "status": "FIR_GENERATED",
        "days_ago": 3,
    },
    # ── LOW RISK ───────────────────────────────────────────────────────────────
    {
        "complainant_name": "Pooja Agarwal",
        "complainant_phone": "9345678912",
        "complainant_email": None,
        "complainant_address": "Lucknow, UP - 226001",
        "incident_description": (
            "I received a call from an unknown number claiming I won a lottery of Rs. 15 lakhs "
            "from KBC (Kaun Banega Crorepati). They asked me to pay Rs. 500 as processing fee. "
            "I did not pay anything. I am reporting this so others are warned."
        ),
        "incident_date": "14 April 2024",
        "incident_location": "Lucknow",
        "risk_level": "LOW",
        "risk_score": 0.18,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Lottery Scam (Attempted)",
        "ai_summary": "Attempted lottery scam. No financial loss as victim did not pay. Filed for awareness. Low immediate risk.",
        "entities": {
            "victim": "Pooja Agarwal",
            "suspect": "Unknown caller",
            "financial_amount": None,
            "financial_vector": None,
            "platform": "Phone Call",
            "location": "Lucknow",
            "contact_numbers": [],
            "urls_links": []
        },
        "bns_sections": ["BNS Section 318 (Cheating attempt)"],
        "authenticity_score": 0.82,
        "fake_recommendation": "GENUINE",
        "status": "TRIAGED",
        "days_ago": 1,
    },
    {
        "complainant_name": "Arjun Mehta",
        "complainant_phone": "8901234567",
        "complainant_email": "arjun.mehta@gmail.com",
        "complainant_address": "Pune, Maharashtra - 411001",
        "incident_description": (
            "Someone posted a negative and defamatory review about my restaurant on Zomato and Google Maps "
            "claiming we use expired food. The reviewer's profile 'AnonReviewer456' seems fake - created "
            "recently with no other reviews. This is harming my business reputation."
        ),
        "incident_date": "11 April 2024",
        "incident_location": "Pune",
        "risk_level": "LOW",
        "risk_score": 0.22,
        "crime_category": "Online Harassment",
        "crime_subcategory": "Online Defamation / Fake Reviews",
        "ai_summary": "Business defamation via fake online reviews. Low criminal priority. May need civil action. Platform complaint recommended first.",
        "entities": {
            "victim": "Arjun Mehta (Restaurant owner)",
            "suspect": "AnonReviewer456",
            "financial_amount": None,
            "financial_vector": None,
            "platform": "Zomato / Google Maps",
            "location": "Pune",
            "contact_numbers": [],
            "urls_links": []
        },
        "bns_sections": ["BNS Section 356 (Defamation)"],
        "authenticity_score": 0.79,
        "fake_recommendation": "GENUINE",
        "status": "TRIAGED",
        "days_ago": 4,
    },
    # ── FLAGGED / FAKE ─────────────────────────────────────────────────────────
    {
        "complainant_name": "Anonymous User",
        "complainant_phone": None,
        "complainant_email": None,
        "complainant_address": None,
        "incident_description": (
            "bomb threat terrorism kill murder hack blackmail extort ransom nude child drugs weapon "
            "terrorist attack sextortion suicide kidnap illegal threat hack bomb explosion"
        ),
        "incident_date": None,
        "incident_location": None,
        "risk_level": "LOW",
        "risk_score": 0.12,
        "crime_category": "Other Cybercrime",
        "crime_subcategory": "Suspected False Report",
        "ai_summary": "Report contains only high-risk trigger keywords with no narrative context. Flagged as keyword stuffing attempt. No credible threat identified.",
        "entities": {},
        "bns_sections": ["BNS Section 229 (False complaint)"],
        "authenticity_score": 0.08,
        "fake_recommendation": "REJECT",
        "is_flagged_fake": True,
        "fake_flags": [
            "High-risk keyword stuffing detected",
            "No coherent narrative or specific incident described",
            "No victim, suspect, or location identified",
            "Report matches automated keyword injection pattern"
        ],
        "status": "CLOSED",
        "days_ago": 2,
    },
    {
        "complainant_name": "Test Reporter",
        "complainant_phone": "1234567890",
        "complainant_email": "test@test.com",
        "complainant_address": "XYZ City",
        "incident_description": (
            "I am writing to report that xyz person did abc thing to me. "
            "Kindly take action against the unknown person. Please help me. Insert name here."
        ),
        "incident_date": "Some date",
        "incident_location": "Some place",
        "risk_level": "LOW",
        "risk_score": 0.09,
        "crime_category": "Other Cybercrime",
        "crime_subcategory": "Template/Generic Report",
        "ai_summary": "Report is a copy-pasted template with placeholder text. No real incident described. Flagged as fake.",
        "entities": {},
        "bns_sections": ["BNS Section 229 (False complaint)"],
        "authenticity_score": 0.12,
        "fake_recommendation": "REJECT",
        "is_flagged_fake": True,
        "fake_flags": [
            "Report matches generic template patterns",
            "Placeholder text detected (xyz, abc, insert name here)",
            "No specific details: no amounts, dates, or real names",
            "Insufficient narrative coherence"
        ],
        "status": "CLOSED",
        "days_ago": 5,
    },
    # ── ADDITIONAL HIGH RISK (more data for charts) ────────────────────────────
    {
        "complainant_name": "Sunita Yadav",
        "complainant_phone": "9456789012",
        "complainant_email": "sunita.yadav@gmail.com",
        "complainant_address": "Kanpur, UP - 208001",
        "incident_description": (
            "I received a WhatsApp call from +1-646-555-0123 (US number). The caller claimed to be "
            "from Amazon Customer Service saying there is an unauthorized order of Rs. 85,000 placed "
            "from my account. They asked me to install AnyDesk app to 'cancel' the order. Once installed, "
            "they accessed my banking app and transferred Rs. 67,000 from my SBI account."
        ),
        "incident_date": "15 April 2024",
        "incident_location": "Kanpur, UP",
        "risk_level": "HIGH",
        "risk_score": 0.88,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Remote Access Trojan Fraud (AnyDesk)",
        "ai_summary": "Remote access fraud via AnyDesk impersonating Amazon support. Rs. 67,000 stolen from SBI account. VOIP number available for tracing.",
        "entities": {
            "victim": "Sunita Yadav",
            "suspect": "+1-646-555-0123 (Amazon impersonator)",
            "financial_amount": "Rs. 67,000",
            "financial_vector": "SBI Bank (remote access via AnyDesk)",
            "platform": "WhatsApp + AnyDesk",
            "location": "Kanpur, UP",
            "contact_numbers": ["+16465550123"],
            "urls_links": []
        },
        "bns_sections": [
            "IT Act Section 66 (Hacking)", "BNS Section 318 (Cheating)",
            "IT Act Section 66D (Impersonation)"
        ],
        "authenticity_score": 0.93,
        "fake_recommendation": "GENUINE",
        "status": "FIR_GENERATED",
        "days_ago": 0,
    },
    {
        "complainant_name": "Gaurav Sharma",
        "complainant_phone": "8567890123",
        "complainant_email": "gaurav.s@gmail.com",
        "complainant_address": "New Delhi - 110001",
        "incident_description": (
            "I am a class 12 student. Someone from my school obtained my nude photos that were meant "
            "only for my partner. They are now threatening to share these on the school WhatsApp group "
            "and send them to my parents unless I pay Rs. 15,000. I am 17 years old. Please help urgently."
        ),
        "incident_date": "15 April 2024",
        "incident_location": "New Delhi",
        "risk_level": "HIGH",
        "risk_score": 0.95,
        "crime_category": "Child Safety",
        "crime_subcategory": "Minor Sextortion",
        "ai_summary": "URGENT - Minor (17 years) being sextorted by known person from school. POCSO Act applicable. Immediate police intervention needed. Counseling referral required.",
        "entities": {
            "victim": "Gaurav Sharma (Minor, 17)",
            "suspect": "Unknown school acquaintance",
            "financial_amount": "Rs. 15,000 (demanded)",
            "financial_vector": None,
            "platform": "WhatsApp",
            "location": "New Delhi",
            "contact_numbers": [],
            "urls_links": []
        },
        "bns_sections": [
            "POCSO Act Section 13", "IT Act Section 67B",
            "BNS Section 308 (Extortion)", "BNS Section 351"
        ],
        "authenticity_score": 0.97,
        "fake_recommendation": "GENUINE",
        "status": "FIR_GENERATED",
        "days_ago": 0,
    },
    {
        "complainant_name": "Ritu Joshi",
        "complainant_phone": "9678901234",
        "complainant_email": "ritujoshi@outlook.com",
        "complainant_address": "Indore, MP - 452001",
        "incident_description": (
            "My elderly father (72 years) received a call claiming to be from Jio network saying "
            "his SIM will be deactivated. He was asked to press 1 to retain the SIM. After pressing 1, "
            "his phone was used to send OTPs. Rs. 28,500 was debited from his Canara Bank account "
            "via three separate UPI transactions within minutes."
        ),
        "incident_date": "13 April 2024",
        "incident_location": "Indore, MP",
        "risk_level": "HIGH",
        "risk_score": 0.86,
        "crime_category": "Financial Crime",
        "crime_subcategory": "SIM Swap / IVR Fraud on Senior Citizen",
        "ai_summary": "SIM-based OTP fraud targeting 72-year-old victim. Rs. 28,500 stolen. Senior citizen vulnerability increases priority. Bank has 3 transaction records.",
        "entities": {
            "victim": "Ritu Joshi's father (72, Senior Citizen)",
            "suspect": "Unknown IVR system operator",
            "financial_amount": "Rs. 28,500",
            "financial_vector": "Canara Bank UPI (3 transactions)",
            "platform": "Phone Call / IVR",
            "location": "Indore, MP",
            "contact_numbers": [],
            "urls_links": []
        },
        "bns_sections": [
            "BNS Section 318 (Cheating)", "IT Act Section 66C",
            "IT Act Section 66D"
        ],
        "authenticity_score": 0.95,
        "fake_recommendation": "GENUINE",
        "status": "FIR_GENERATED",
        "days_ago": 2,
    },
    {
        "complainant_name": "Arun Krishnamurthy",
        "complainant_phone": "9789012345",
        "complainant_email": "arunkm@gmail.com",
        "complainant_address": "Coimbatore, Tamil Nadu - 641001",
        "incident_description": (
            "I received a message on Telegram from a group called 'Crypto Millionaires India' "
            "promising 500% returns in 7 days on Ethereum. I invested Rs. 40,000 by buying ETH "
            "and sending to wallet 0x742d35cc6634c0532925a3b8d4c9f16a8d3e3e9a. "
            "After 7 days, the group disappeared and wallet shows 0 balance."
        ),
        "incident_date": "5-12 April 2024",
        "incident_location": "Online / Coimbatore",
        "risk_level": "MEDIUM",
        "risk_score": 0.61,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Crypto Investment Fraud",
        "ai_summary": "Cryptocurrency investment fraud via Telegram pump-and-dump scheme. Rs. 40,000 lost. Ethereum wallet address traceable on blockchain.",
        "entities": {
            "victim": "Arun Krishnamurthy",
            "suspect": "Telegram group: Crypto Millionaires India",
            "financial_amount": "Rs. 40,000",
            "financial_vector": "Ethereum - 0x742d35cc6634c0532925a3b8d4c9f16a8d3e3e9a",
            "platform": "Telegram",
            "location": "Coimbatore",
            "contact_numbers": [],
            "urls_links": ["0x742d35cc6634c0532925a3b8d4c9f16a8d3e3e9a"]
        },
        "bns_sections": [
            "BNS Section 318 (Cheating)", "PMLA Section 3",
            "IT Act Section 66D"
        ],
        "authenticity_score": 0.85,
        "fake_recommendation": "GENUINE",
        "status": "TRIAGED",
        "days_ago": 8,
    },
    {
        "complainant_name": "Neha Kapoor",
        "complainant_phone": "8890123456",
        "complainant_email": "neha.kapoor@gmail.com",
        "complainant_address": "Chandigarh - 160001",
        "incident_description": (
            "My company's official email was hacked. The hacker sent emails to our 3 clients pretending "
            "to be our CEO asking them to transfer project advance payments to a new bank account. "
            "Client 1 transferred Rs. 3,50,000 before we caught it. We have the fraudulent email headers "
            "and the fake bank account details: ICICI Bank 123456789012 IFSC ICIC0001234."
        ),
        "incident_date": "10 April 2024",
        "incident_location": "Chandigarh",
        "risk_level": "HIGH",
        "risk_score": 0.92,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Business Email Compromise (BEC)",
        "ai_summary": "Business Email Compromise attack. Rs. 3.5 lakh stolen. Email headers and fraudulent bank account available. Corporate victim - escalate to CERT-In.",
        "entities": {
            "victim": "Neha Kapoor's company",
            "suspect": "Unknown - email hacker",
            "financial_amount": "Rs. 3,50,000",
            "financial_vector": "ICICI Bank 123456789012",
            "platform": "Email (Corporate Hack)",
            "location": "Chandigarh",
            "contact_numbers": [],
            "urls_links": []
        },
        "bns_sections": [
            "IT Act Section 66 (Hacking)", "BNS Section 318",
            "IT Act Section 43 (Damage to computer)", "BNS Section 336 (Forgery)"
        ],
        "authenticity_score": 0.94,
        "fake_recommendation": "GENUINE",
        "status": "FIR_GENERATED",
        "days_ago": 5,
    },
    {
        "complainant_name": "Rahul Verma",
        "complainant_phone": "7890123456",
        "complainant_email": None,
        "complainant_address": "Varanasi, UP - 221001",
        "incident_description": (
            "I ordered a mobile phone worth Rs. 12,000 from a website mobiledeals99.in after seeing "
            "an ad on Facebook. I paid full amount via PhonePe to 8765432109. The website is now "
            "showing 404 error and the seller has blocked me. I have payment receipt and order confirmation."
        ),
        "incident_date": "8 April 2024",
        "incident_location": "Varanasi",
        "risk_level": "MEDIUM",
        "risk_score": 0.53,
        "crime_category": "Financial Crime",
        "crime_subcategory": "E-Commerce Fraud",
        "ai_summary": "Online shopping fraud via fake e-commerce website. Rs. 12,000 loss. PhonePe transaction traceable. Fake website domain available for cyber investigation.",
        "entities": {
            "victim": "Rahul Verma",
            "suspect": "mobiledeals99.in operator",
            "financial_amount": "Rs. 12,000",
            "financial_vector": "PhonePe to 8765432109",
            "platform": "Facebook Ad + Fake Website",
            "location": "Varanasi",
            "contact_numbers": ["8765432109"],
            "urls_links": ["mobiledeals99.in"]
        },
        "bns_sections": [
            "BNS Section 318 (Cheating)", "IT Act Section 66D"
        ],
        "authenticity_score": 0.83,
        "fake_recommendation": "GENUINE",
        "status": "TRIAGED",
        "days_ago": 7,
    },
    {
        "complainant_name": "Meera Pillai",
        "complainant_phone": "9901234567",
        "complainant_email": "meera.pillai@gmail.com",
        "complainant_address": "Kochi, Kerala - 682001",
        "incident_description": (
            "I discovered that someone has opened 2 credit cards in my name using my Aadhaar and PAN "
            "details without my knowledge. HDFC sent me a credit card I never applied for with a limit "
            "of Rs. 1,50,000 and it already has outstanding dues of Rs. 23,000. Someone stole my identity. "
            "I have never shared my KYC documents with anyone."
        ),
        "incident_date": "14 April 2024",
        "incident_location": "Kochi",
        "risk_level": "HIGH",
        "risk_score": 0.87,
        "crime_category": "Identity Theft",
        "crime_subcategory": "KYC Identity Theft / Credit Fraud",
        "ai_summary": "Aadhaar/PAN-based identity theft with unauthorized credit cards. Potential data breach from KYC aggregator. UIDAI complaint and credit bureau freeze recommended.",
        "entities": {
            "victim": "Meera Pillai",
            "suspect": "Unknown identity thief",
            "financial_amount": "Rs. 23,000 (outstanding) + Rs. 1,50,000 (credit limit at risk)",
            "financial_vector": "HDFC Credit Card (unauthorized)",
            "platform": "Offline KYC / Banking System",
            "location": "Kochi",
            "contact_numbers": [],
            "urls_links": []
        },
        "bns_sections": [
            "IT Act Section 66C (Identity theft)", "BNS Section 336 (Forgery)",
            "IT Act Section 43A (Data protection failure)"
        ],
        "authenticity_score": 0.96,
        "fake_recommendation": "GENUINE",
        "status": "FIR_GENERATED",
        "days_ago": 1,
    },
    {
        "complainant_name": "Dilip Bose",
        "complainant_phone": None,
        "complainant_email": "dilip.bose@yahoo.co.in",
        "complainant_address": "Kolkata, West Bengal - 700001",
        "incident_description": (
            "My company's database was hacked and customer data of approximately 50,000 users including "
            "names, phone numbers, and encrypted passwords was stolen. The hacker left a ransom note "
            "demanding 2 Bitcoin to not publish the data. We found the breach through unusual login attempts "
            "from IP 45.33.32.156 (US-based VPS). We have server logs showing the intrusion path."
        ),
        "incident_date": "12 April 2024",
        "incident_location": "Kolkata",
        "risk_level": "HIGH",
        "risk_score": 0.94,
        "crime_category": "Data Breach",
        "crime_subcategory": "Corporate Data Breach / Ransomware",
        "ai_summary": "CRITICAL - Corporate data breach affecting 50,000 users. Ransomware demand. IP address traceable. CERT-In mandatory reporting within 6 hours. Engage forensic team immediately.",
        "entities": {
            "victim": "Dilip Bose's company + 50,000 customers",
            "suspect": "Unknown - IP 45.33.32.156",
            "financial_amount": "2 Bitcoin (demanded)",
            "financial_vector": "Bitcoin (ransom)",
            "platform": "Corporate Server",
            "location": "Kolkata",
            "contact_numbers": [],
            "urls_links": ["45.33.32.156"]
        },
        "bns_sections": [
            "IT Act Section 43A (Data breach)", "IT Act Section 66 (Hacking)",
            "DPDP Act 2023", "IT Act Section 43 (Damage)"
        ],
        "authenticity_score": 0.97,
        "fake_recommendation": "GENUINE",
        "status": "FIR_GENERATED",
        "days_ago": 3,
    },
    {
        "complainant_name": "Sameer Qureshi",
        "complainant_phone": "8123456789",
        "complainant_email": "sameer.q@gmail.com",
        "complainant_address": "Bhopal, MP - 462001",
        "incident_description": (
            "Someone has been using my business Aadhaar to open fake GST numbers and avail input tax "
            "credit fraudulently. I received a GST notice for Rs. 4,80,000 in ITC mismatch for "
            "transactions I never made. My CA confirmed these are fake invoices raised using my GSTIN. "
            "I have GSTIN 23ABCDE1234F1Z5 and the fraudulent transactions are from Q3 2023."
        ),
        "incident_date": "April 2024 (discovered)",
        "incident_location": "Bhopal, MP",
        "risk_level": "HIGH",
        "risk_score": 0.85,
        "crime_category": "Financial Crime",
        "crime_subcategory": "GST Fraud / Identity Misuse",
        "ai_summary": "GST identity fraud using victim's GSTIN for fake ITC claims. Rs. 4.8 lakh tax liability. GSTIN number available. Coordinate with GST authorities for investigation.",
        "entities": {
            "victim": "Sameer Qureshi",
            "suspect": "Unknown - misusing GSTIN",
            "financial_amount": "Rs. 4,80,000 (GST liability)",
            "financial_vector": "GST / Tax System",
            "platform": "GST Portal",
            "location": "Bhopal, MP",
            "contact_numbers": [],
            "urls_links": []
        },
        "bns_sections": [
            "BNS Section 336 (Forgery)", "IT Act Section 66C",
            "CGST Act Section 132 (GST fraud)"
        ],
        "authenticity_score": 0.91,
        "fake_recommendation": "GENUINE",
        "status": "TRIAGED",
        "days_ago": 6,
    },    # ── FAKE CASE — PERFECT FOR DEMO (most vivid example for judges) ─────────────
    {
        "complainant_name": "Vikram Thakur",
        "complainant_phone": "9988776655",
        "complainant_email": "vikram.thakur1992@gmail.com",
        "complainant_address": "Sector 22, Chandigarh - 160022",
        "incident_description": (
            "On 10th April 2024, I was browsing Instagram when I found an account @officialcitigold "
            "claiming to be Citibank offering 40% annual returns. I transferred Rs. 75,000 via NEFT "
            "to HDFC Bank account 50200123456789 IFSC HDFC0001234. "
            "After investment the website disappeared. I need police action against Citibank fraudsters. "
            "Contact: fraud.victim@gmail.com Phone: 9988776655. This is very urgent please help."
        ),
        "incident_date": "10 April 2024",
        "incident_location": "Chandigarh",
        "risk_level": "LOW",
        "risk_score": 0.18,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Suspected False Report",
        "ai_summary": (
            "Report flagged as likely fabricated. Complainant details match the suspected fraudster profile, "
            "the so-called victim phone number is the same as the complainant, narrative is internally inconsistent, "
            "and IP geolocation conflicts with stated location. 6-layer AI analysis suggests counter-complaint scenario."
        ),
        "entities": {
            "victim": "Vikram Thakur (unverified)",
            "suspect": "@officialcitigold (Instagram)",
            "financial_amount": "Rs. 75,000 (unverified)",
            "financial_vector": "HDFC Bank 50200123456789",
            "platform": "Instagram",
            "location": "Chandigarh",
            "contact_numbers": ["9988776655"],
            "urls_links": ["@officialcitigold"]
        },
        "bns_sections": [
            "BNS Section 229 (False information to public servant)",
            "BNS Section 336 (Forgery of document)",
            "IT Act Section 66D (Cheating by impersonation)"
        ],
        "authenticity_score": 0.11,
        "fake_recommendation": "REJECT",
        "is_flagged_fake": True,
        "fake_flags": [
            "L1: Suspicious keyword density — template phrases detected",
            "L2: Gemini coherence check FAILED — narrative contradictions found",
            "L3: Complainant contact matches suspect contact number",
            "L4: Entity inconsistency — victim and complainant appear same person",
            "L5: Near-duplicate of previously REJECTED complaint (hash similarity 94%)",
            "L6: Behavioral risk — report submitted 3x in 24 hours from same IP",
            "IMAGE FORENSICS: No evidence uploaded despite large financial claim",
            "REPORTER TRUST: Profile trust score 0.05 — previously blocked"
        ],
        "status": "CLOSED",
        "days_ago": 1,
    },
    # ── ADDITIONAL HIGH RISK ──────────────────────────────────────────────────
    {
        "complainant_name": "Rohit Nair",
        "complainant_phone": "9512345678",
        "complainant_email": "rohit.nair@gmail.com",
        "complainant_address": "Kochi, Kerala - 682016",
        "incident_description": (
            "I received a call from 1800-012-1234 claiming to be Microsoft technical support. "
            "The caller said my computer had a virus and asked me to install TeamViewer ID 987654321. "
            "Once connected, he showed me fake 'virus alerts' on my screen. He convinced me to transfer "
            "Rs. 1,20,000 to 'Microsoft Security Account' via IMPS to Axis Bank 9876543210123456 "
            "IFSC UTIB0001234. After payment, he disconnected and the number became unreachable."
        ),
        "incident_date": "12 April 2024",
        "incident_location": "Kochi, Kerala",
        "risk_level": "HIGH",
        "risk_score": 0.87,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Tech Support Fraud / Remote Access",
        "ai_summary": "Microsoft impersonation tech support fraud via TeamViewer remote access. Rs. 1.2 lakh transferred. Bank account details available for LEA tracing.",
        "entities": {
            "victim": "Rohit Nair",
            "suspect": "Unknown - 1800-012-1234 (fake Microsoft)",
            "financial_amount": "Rs. 1,20,000",
            "financial_vector": "IMPS - Axis Bank 9876543210123456",
            "platform": "Phone + TeamViewer",
            "location": "Kochi, Kerala",
            "contact_numbers": ["18000121234"],
            "urls_links": []
        },
        "bns_sections": [
            "BNS Section 318 (Cheating)", "IT Act Section 66D (Impersonation)",
            "IT Act Section 66 (Unauthorized computer access)"
        ],
        "authenticity_score": 0.92,
        "fake_recommendation": "GENUINE",
        "status": "COMPLAINT_REGISTERED",
        "days_ago": 3,
    },
    {
        "complainant_name": "Preethi Subramaniam",
        "complainant_phone": "8765401234",
        "complainant_email": "preethi.sub@gmail.com",
        "complainant_address": "Bengaluru, Karnataka - 560079",
        "incident_description": (
            "A person using profile 'James Martin, UK-based software engineer' on Instagram DM'd me in January. "
            "We developed a relationship over 3 months. He claimed to be stranded due to a business emergency "
            "and needed Rs. 2,00,000 urgently. I transferred Rs. 80,000 via NEFT to SBI account 32456789012 "
            "and Rs. 1,20,000 via PhonePe. He has now blocked me on all platforms. I believe this is a "
            "romance scam — the profile photos appear to be stolen."
        ),
        "incident_date": "January to April 2024",
        "incident_location": "Online / Bengaluru",
        "risk_level": "HIGH",
        "risk_score": 0.84,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Romance Scam / Catfishing",
        "ai_summary": "Three-month romance scam via Instagram. Rs. 2 lakh transferred across multiple transactions. Classic pig-butchering pattern. Victim needs counseling referral.",
        "entities": {
            "victim": "Preethi Subramaniam",
            "suspect": "'James Martin' - Instagram (fake profile)",
            "financial_amount": "Rs. 2,00,000",
            "financial_vector": "NEFT + PhonePe - SBI 32456789012",
            "platform": "Instagram DM",
            "location": "Bengaluru",
            "contact_numbers": [],
            "urls_links": []
        },
        "bns_sections": [
            "BNS Section 318 (Cheating)", "IT Act Section 66D",
            "IT Act Section 66C (Identity theft - stolen photos)"
        ],
        "authenticity_score": 0.91,
        "fake_recommendation": "GENUINE",
        "status": "COMPLAINT_REGISTERED",
        "days_ago": 1,
    },
    {
        "complainant_name": "Abdul Kareem Siddiqui",
        "complainant_phone": "9234501234",
        "complainant_email": None,
        "complainant_address": "Lucknow, UP - 226004",
        "incident_description": (
            "I installed a loan app 'QuickRupee' from a Facebook ad link (not Play Store). "
            "The app demanded access to my contacts and gallery. I applied for Rs. 10,000 loan. "
            "After receiving Rs. 3,000 (deducting fees), they sent abusive WhatsApp messages to all "
            "my contacts using morphed photos of mine. They are demanding Rs. 35,000 as repayment "
            "within 24 hours or they will send obscene content to my family."
        ),
        "incident_date": "13 April 2024",
        "incident_location": "Lucknow, UP",
        "risk_level": "HIGH",
        "risk_score": 0.93,
        "crime_category": "Extortion",
        "crime_subcategory": "Predatory Loan App / Blackmail",
        "ai_summary": "Predatory loan app extortion — contacts harvested, morphed images sent. Active blackmail campaign. App not on Play Store. CERT-In complaint needed.",
        "entities": {
            "victim": "Abdul Kareem Siddiqui",
            "suspect": "'QuickRupee' app operator",
            "financial_amount": "Rs. 35,000 (demanded)",
            "financial_vector": "Fake loan app",
            "platform": "Facebook + WhatsApp",
            "location": "Lucknow, UP",
            "contact_numbers": [],
            "urls_links": ["QuickRupee app"]
        },
        "bns_sections": [
            "BNS Section 308 (Extortion)", "IT Act Section 67 (Obscene content)",
            "IT Act Section 66E (Privacy violation)", "BNS Section 351 (Criminal Intimidation)"
        ],
        "authenticity_score": 0.94,
        "fake_recommendation": "GENUINE",
        "status": "COMPLAINT_REGISTERED",
        "days_ago": 2,
    },
    {
        "complainant_name": "Swati Desai",
        "complainant_phone": "9081234567",
        "complainant_email": "swati.desai@outlook.com",
        "complainant_address": "Ahmedabad, Gujarat - 380054",
        "incident_description": (
            "I discovered that someone has fraudulently taken a personal loan of Rs. 5,00,000 in my name "
            "using my Aadhaar (1234 5678 9012) and PAN (ABCDE1234F). The bank (Kotak Mahindra) sent me "
            "an EMI reminder. I never applied for this loan. My KYC documents were submitted to a "
            "fintech app 6 months ago for a small credit. I believe my data was sold."
        ),
        "incident_date": "April 2024 (discovered)",
        "incident_location": "Ahmedabad, Gujarat",
        "risk_level": "HIGH",
        "risk_score": 0.88,
        "crime_category": "Identity Theft",
        "crime_subcategory": "Aadhaar/PAN Loan Fraud",
        "ai_summary": "Aadhaar-based identity fraud for Rs. 5 lakh personal loan. Potential KYC data breach from fintech app. UIDAI complaint and loan freeze required immediately.",
        "entities": {
            "victim": "Swati Desai",
            "suspect": "Unknown - KYC data misuse",
            "financial_amount": "Rs. 5,00,000 (fraudulent loan)",
            "financial_vector": "Kotak Mahindra Bank loan",
            "platform": "Banking / KYC System",
            "location": "Ahmedabad",
            "contact_numbers": [],
            "urls_links": []
        },
        "bns_sections": [
            "IT Act Section 66C (Identity theft)", "BNS Section 336 (Forgery)",
            "IT Act Section 43A (Data breach)", "BNS Section 318"
        ],
        "authenticity_score": 0.95,
        "fake_recommendation": "GENUINE",
        "status": "COMPLAINT_REGISTERED",
        "days_ago": 0,
    },
    {
        "complainant_name": "Nandini Iyer",
        "complainant_phone": "9371234567",
        "complainant_email": "nandini.iyer@gmail.com",
        "complainant_address": "Andheri West, Mumbai - 400058",
        "incident_description": (
            "I met a person named 'Aryan Kapoor' on Shaadi.com 4 months ago. We were engaged to be married. "
            "Over time he took Rs. 3,50,000 from me — Rs. 1,50,000 for 'business investment' and Rs. 2,00,000 "
            "as 'emergency money for his mother's surgery'. Profile photos appear to be fake — reverse image "
            "search shows a foreign model. He has disconnected after taking the last payment."
        ),
        "incident_date": "December 2023 – April 2024",
        "incident_location": "Mumbai",
        "risk_level": "HIGH",
        "risk_score": 0.86,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Matrimonial Fraud / Romance Scam",
        "ai_summary": "Long-running matrimonial fraud via Shaadi.com. Rs. 3.5 lakh stolen over 4 months. Stolen profile photos confirmed. Victim emotionally vulnerable — immediate support needed.",
        "entities": {
            "victim": "Nandini Iyer",
            "suspect": "'Aryan Kapoor' (fake profile) - Shaadi.com",
            "financial_amount": "Rs. 3,50,000",
            "financial_vector": "Multiple bank transfers",
            "platform": "Shaadi.com",
            "location": "Mumbai",
            "contact_numbers": [],
            "urls_links": ["Shaadi.com profile"]
        },
        "bns_sections": [
            "BNS Section 318 (Cheating)", "IT Act Section 66D",
            "BNS Section 316 (Criminal breach of trust)"
        ],
        "authenticity_score": 0.89,
        "fake_recommendation": "GENUINE",
        "status": "COMPLAINT_REGISTERED",
        "days_ago": 1,
    },
    {
        "complainant_name": "Kabir Ansari",
        "complainant_phone": "8123409876",
        "complainant_email": "kabir.ansari@company.in",
        "complainant_address": "BKC, Mumbai - 400051",
        "incident_description": (
            "Our company's confidential client database (approx 15,000 records including personal data) "
            "appeared for sale on a Telegram channel called 'DataLeakIndia'. The data includes Aadhaar, "
            "PAN, phone, and financial data of our clients. We suspect an insider threat from a recently "
            "terminated employee. The Telegram post was up for 6 hours before removal. We have screenshots."
        ),
        "incident_date": "14 April 2024",
        "incident_location": "Mumbai (BKC)",
        "risk_level": "HIGH",
        "risk_score": 0.91,
        "crime_category": "Data Breach",
        "crime_subcategory": "Insider Data Theft / Dark Web Sale",
        "ai_summary": "Corporate data breach — 15,000 records including Aadhaar data sold on Telegram. Insider threat suspected. CERT-In mandatory 6-hour reporting triggered. DPDP Act breach.",
        "entities": {
            "victim": "Kabir Ansari's company + 15,000 clients",
            "suspect": "Suspected terminated employee + Telegram 'DataLeakIndia'",
            "financial_amount": "Undetermined — potential regulatory penalty",
            "financial_vector": "Data Sale (Telegram)",
            "platform": "Telegram",
            "location": "Mumbai",
            "contact_numbers": [],
            "urls_links": ["DataLeakIndia (Telegram)"]
        },
        "bns_sections": [
            "IT Act Section 43A (Data breach)", "DPDP Act 2023",
            "IT Act Section 66 (Hacking)", "BNS Section 336"
        ],
        "authenticity_score": 0.96,
        "fake_recommendation": "GENUINE",
        "status": "COMPLAINT_REGISTERED",
        "days_ago": 1,
    },
    {
        "complainant_name": "Jasmine D'Souza",
        "complainant_phone": "9601234567",
        "complainant_email": "jasmine.dsouza@gmail.com",
        "complainant_address": "Panaji, Goa - 403001",
        "incident_description": (
            "I paid Rs. 1,80,000 to a travel agency 'Dreamvisa Tours' (website: dreamvisatours.in) for "
            "a tourist visa and flight package to Canada. After 3 months, no visa was received. "
            "The website is now offline and the owner's phone +91-9988001122 is switched off. "
            "They had a registered office in Margao, Goa but it is now vacated. My passort was "
            "withheld for 2 months and I have just received it back without any visa."
        ),
        "incident_date": "January – April 2024",
        "incident_location": "Panaji, Goa",
        "risk_level": "HIGH",
        "risk_score": 0.85,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Fake Visa / Travel Fraud",
        "ai_summary": "Fake immigration agency fraud. Rs. 1.8 lakh lost. Physical office vacated. Website offline. Passport withheld. Multiple victims likely — organized fraud operation.",
        "entities": {
            "victim": "Jasmine D'Souza",
            "suspect": "Dreamvisa Tours - dreamvisatours.in",
            "financial_amount": "Rs. 1,80,000",
            "financial_vector": "Bank transfer to agency account",
            "platform": "Physical + Online",
            "location": "Panaji, Goa",
            "contact_numbers": ["+919988001122"],
            "urls_links": ["dreamvisatours.in"]
        },
        "bns_sections": [
            "BNS Section 318 (Cheating)", "BNS Section 316",
            "Foreigners Act Section 14", "IT Act Section 66D"
        ],
        "authenticity_score": 0.90,
        "fake_recommendation": "GENUINE",
        "status": "COMPLAINT_REGISTERED",
        "days_ago": 4,
    },
    {
        "complainant_name": "Harpreet Kaur",
        "complainant_phone": "9811234560",
        "complainant_email": "harpreet.k@gmail.com",
        "complainant_address": "Amritsar, Punjab - 143001",
        "incident_description": (
            "I received an email from 'admissions@pgims-chandigarh.edu.in' (fake domain) saying I had "
            "been selected for MBBS at PGI Chandigarh. They asked me to pay Rs. 25,000 as seat reservation "
            "fee via NEFT to Punjab National Bank 1234567890123456. I paid the amount. When I contacted the "
            "real PGI Chandigarh, they confirmed they sent no such email. I have the original email with headers."
        ),
        "incident_date": "10 April 2024",
        "incident_location": "Amritsar, Punjab",
        "risk_level": "HIGH",
        "risk_score": 0.83,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Fake Admission / Educational Fraud",
        "ai_summary": "Medical college admission fraud via spoofed government domain email. Rs. 25,000 lost. Email headers available. PGI Chandigarh confirmed no such admission. Fraudulent bank account traceable.",
        "entities": {
            "victim": "Harpreet Kaur",
            "suspect": "pgims-chandigarh.edu.in (fake domain)",
            "financial_amount": "Rs. 25,000",
            "financial_vector": "NEFT - PNB 1234567890123456",
            "platform": "Email",
            "location": "Amritsar, Punjab",
            "contact_numbers": [],
            "urls_links": ["pgims-chandigarh.edu.in"]
        },
        "bns_sections": [
            "BNS Section 318 (Cheating)", "IT Act Section 66D (Impersonation)",
            "BNS Section 336 (Forgery of document)"
        ],
        "authenticity_score": 0.88,
        "fake_recommendation": "GENUINE",
        "status": "COMPLAINT_REGISTERED",
        "days_ago": 5,
    },
    # ── ADDITIONAL MEDIUM RISK ────────────────────────────────────────────────
    {
        "complainant_name": "Manish Singhal",
        "complainant_phone": "9711234567",
        "complainant_email": "manish.singhal@gmail.com",
        "complainant_address": "Noida, UP - 201301",
        "incident_description": (
            "I received a call from 9876501234 claiming to be from DTDC courier saying my parcel was held "
            "at customs and I need to pay Rs. 1,499 as customs fee via Google Pay to 9876501234. "
            "After paying, they called again saying an additional Rs. 4,999 is required. I realized it was "
            "fraud and refused. I have the payment receipt for Rs. 1,499."
        ),
        "incident_date": "13 April 2024",
        "incident_location": "Noida, UP",
        "risk_level": "MEDIUM",
        "risk_score": 0.55,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Courier Parcel Fraud / OTP Scam",
        "ai_summary": "Courier customs fee fraud. Rs. 1,499 lost. Classic escalating payment scam — victim correctly refused second payment. Google Pay transaction traceable.",
        "entities": {
            "victim": "Manish Singhal",
            "suspect": "Unknown - 9876501234",
            "financial_amount": "Rs. 1,499",
            "financial_vector": "Google Pay to 9876501234",
            "platform": "Phone Call",
            "location": "Noida, UP",
            "contact_numbers": ["9876501234"],
            "urls_links": []
        },
        "bns_sections": ["BNS Section 318 (Cheating)", "IT Act Section 66D"],
        "authenticity_score": 0.85,
        "fake_recommendation": "GENUINE",
        "status": "TRIAGED",
        "days_ago": 2,
    },
    {
        "complainant_name": "Tamilselvan Krishnan",
        "complainant_phone": "9443201234",
        "complainant_email": "tamilselvan.k@gmail.com",
        "complainant_address": "Madurai, Tamil Nadu - 625001",
        "incident_description": (
            "A WhatsApp contact 'Work Abroad Consultancy' offered me a job in Malaysia with salary of "
            "RM 5,000/month. I paid Rs. 50,000 as visa and processing fee via Paytm to 8765401234. "
            "They sent fake employment documents and asked for additional Rs. 15,000 for air ticket. "
            "When I searched the company online, it does not exist. I refused the second payment."
        ),
        "incident_date": "March – April 2024",
        "incident_location": "Madurai, Tamil Nadu",
        "risk_level": "MEDIUM",
        "risk_score": 0.63,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Overseas Job Fraud",
        "ai_summary": "Overseas job fraud via WhatsApp. Rs. 50,000 paid as fake visa fee. Fraudulent employment documents. Paytm number available. Potential human trafficking link — investigate further.",
        "entities": {
            "victim": "Tamilselvan Krishnan",
            "suspect": "'Work Abroad Consultancy' - WhatsApp",
            "financial_amount": "Rs. 50,000",
            "financial_vector": "Paytm to 8765401234",
            "platform": "WhatsApp",
            "location": "Madurai, Tamil Nadu",
            "contact_numbers": ["8765401234"],
            "urls_links": []
        },
        "bns_sections": [
            "BNS Section 318 (Cheating)", "IT Act Section 66D",
            "Emigration Act Section 24"
        ],
        "authenticity_score": 0.84,
        "fake_recommendation": "GENUINE",
        "status": "TRIAGED",
        "days_ago": 6,
    },
    {
        "complainant_name": "Preeti Rana",
        "complainant_phone": "9312345678",
        "complainant_email": "preeti.rana@yahoo.co.in",
        "complainant_address": "Dehradun, Uttarakhand - 248001",
        "incident_description": (
            "Someone created a fake Instagram account 'preeti_rana_official' using my photos. This account "
            "is messaging my followers asking them to send money for a 'medical emergency'. My friend "
            "Sunita already transferred Rs. 3,000 to account number 987654321 before contacting me. "
            "Instagram has not removed the account despite 3 reports."
        ),
        "incident_date": "8 April 2024",
        "incident_location": "Dehradun, Uttarakhand",
        "risk_level": "MEDIUM",
        "risk_score": 0.60,
        "crime_category": "Identity Theft",
        "crime_subcategory": "Social Media Impersonation",
        "ai_summary": "Active Instagram impersonation with financial fraud. Victim's friend already lost Rs. 3,000. Account still active. Request urgent Instagram MLAT or LEA legal notice.",
        "entities": {
            "victim": "Preeti Rana",
            "suspect": "'preeti_rana_official' (fake Instagram)",
            "financial_amount": "Rs. 3,000 (victim's contact lost)",
            "financial_vector": "Bank account 987654321",
            "platform": "Instagram",
            "location": "Dehradun",
            "contact_numbers": [],
            "urls_links": ["preeti_rana_official (Instagram)"]
        },
        "bns_sections": [
            "IT Act Section 66C (Identity theft)", "IT Act Section 66D",
            "BNS Section 318"
        ],
        "authenticity_score": 0.86,
        "fake_recommendation": "GENUINE",
        "status": "TRIAGED",
        "days_ago": 7,
    },
    {
        "complainant_name": "George Thomas",
        "complainant_phone": "9447201234",
        "complainant_email": "george.thomas@gmail.com",
        "complainant_address": "Ernakulam, Kerala - 682031",
        "incident_description": (
            "I donated Rs. 20,000 to an NGO 'Children Education Trust India' after seeing a Facebook ad. "
            "The website ceteducation.org had fake government registration certificates. "
            "I sent payment via UPI to cet.donations@kotak. When I called the contact number 9999012345, "
            "it was disconnected. The website is now showing a 'site under maintenance' message."
        ),
        "incident_date": "5 April 2024",
        "incident_location": "Ernakulam, Kerala",
        "risk_level": "MEDIUM",
        "risk_score": 0.57,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Fake NGO / Charity Fraud",
        "ai_summary": "Fake NGO donation fraud via Facebook ad. Rs. 20,000 lost. Fraudulent government registration certificates. UPI ID available. Website takedown in progress.",
        "entities": {
            "victim": "George Thomas",
            "suspect": "'Children Education Trust India' - ceteducation.org",
            "financial_amount": "Rs. 20,000",
            "financial_vector": "UPI - cet.donations@kotak",
            "platform": "Facebook + Fake Website",
            "location": "Ernakulam, Kerala",
            "contact_numbers": ["9999012345"],
            "urls_links": ["ceteducation.org"]
        },
        "bns_sections": [
            "BNS Section 318 (Cheating)", "BNS Section 336 (Forgery)",
            "FCRA Violation"
        ],
        "authenticity_score": 0.83,
        "fake_recommendation": "GENUINE",
        "status": "TRIAGED",
        "days_ago": 10,
    },
    {
        "complainant_name": "Chetan Mehta",
        "complainant_phone": "9909234567",
        "complainant_email": "chetan.mehta@gmail.com",
        "complainant_address": "Surat, Gujarat - 395003",
        "incident_description": (
            "I joined a Telegram group 'WazirX VIP Signals' that promised 10x returns on crypto. "
            "They gave me small profitable trades initially. After building trust, they advised me "
            "to invest Rs. 30,000 in XYZ token on a fake exchange 'cryptoindia.trade'. "
            "My 'portfolio' showed Rs. 90,000 but when I withdrew, they asked for 30% tax payment. "
            "I refused and the group was deleted."
        ),
        "incident_date": "February – April 2024",
        "incident_location": "Surat, Gujarat",
        "risk_level": "MEDIUM",
        "risk_score": 0.64,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Crypto Pump & Dump / Fake Exchange",
        "ai_summary": "Cryptocurrency pump-and-dump on fake exchange. Rs. 30,000 invested on 'cryptoindia.trade'. Classic pig-butchering with fake portfolio gains. Fake exchange domain available.",
        "entities": {
            "victim": "Chetan Mehta",
            "suspect": "'WazirX VIP Signals' Telegram + cryptoindia.trade",
            "financial_amount": "Rs. 30,000",
            "financial_vector": "Crypto transfer to fake exchange",
            "platform": "Telegram + Fake Exchange",
            "location": "Surat, Gujarat",
            "contact_numbers": [],
            "urls_links": ["cryptoindia.trade"]
        },
        "bns_sections": [
            "BNS Section 318 (Cheating)", "PMLA Section 3",
            "IT Act Section 66D"
        ],
        "authenticity_score": 0.82,
        "fake_recommendation": "GENUINE",
        "status": "TRIAGED",
        "days_ago": 9,
    },
    {
        "complainant_name": "Ashwini More",
        "complainant_phone": "9423012345",
        "complainant_email": "ashwini.more@rediffmail.com",
        "complainant_address": "Nagpur, Maharashtra - 440010",
        "incident_description": (
            "I received an SMS saying I am eligible for a government PMKVY scholarship of Rs. 8,000. "
            "I visited the link scholarship-pmkvy.in and filled my details including Aadhaar number. "
            "I was asked to pay Rs. 199 as 'registration fee' via Paytm to 7890123456 to receive the money. "
            "After paying, the website stopped responding. I am worried my Aadhaar details are compromised."
        ),
        "incident_date": "11 April 2024",
        "incident_location": "Nagpur, Maharashtra",
        "risk_level": "MEDIUM",
        "risk_score": 0.52,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Fake Government Scheme / Phishing",
        "ai_summary": "Fake government scholarship scam. Rs. 199 lost + potential Aadhaar data compromise. Phishing site available for CERT-In reporting. UIDAI data breach notification needed.",
        "entities": {
            "victim": "Ashwini More",
            "suspect": "scholarship-pmkvy.in operator",
            "financial_amount": "Rs. 199 (+ Aadhaar data compromise)",
            "financial_vector": "Paytm to 7890123456",
            "platform": "SMS + Fake Website",
            "location": "Nagpur, Maharashtra",
            "contact_numbers": ["7890123456"],
            "urls_links": ["scholarship-pmkvy.in"]
        },
        "bns_sections": [
            "BNS Section 318 (Cheating)", "IT Act Section 66D",
            "IT Act Section 66C (Identity theft)"
        ],
        "authenticity_score": 0.80,
        "fake_recommendation": "GENUINE",
        "status": "TRIAGED",
        "days_ago": 4,
    },
    {
        "complainant_name": "Sanjay Kumar Tiwari",
        "complainant_phone": "9651234567",
        "complainant_email": None,
        "complainant_address": "Patna, Bihar - 800001",
        "incident_description": (
            "An insurance agent named Deepak Sharma (phone 9012345678) sold me a 'LIC-linked policy' "
            "with guaranteed 15% annual returns. I paid Rs. 12,000 premium in January 2024. "
            "The policy document looks real but when I called LIC's official number 022-67819200, "
            "they confirmed no such policy exists in my name. The agent is now avoiding calls."
        ),
        "incident_date": "January 2024",
        "incident_location": "Patna, Bihar",
        "risk_level": "MEDIUM",
        "risk_score": 0.59,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Fake Insurance Policy Fraud",
        "ai_summary": "Fake LIC insurance policy fraud. Rs. 12,000 premium paid. LIC confirmed no real policy. Agent identity and phone available. Fake policy documents as evidence.",
        "entities": {
            "victim": "Sanjay Kumar Tiwari",
            "suspect": "Deepak Sharma (fake insurance agent) - 9012345678",
            "financial_amount": "Rs. 12,000",
            "financial_vector": "Insurance premium payment",
            "platform": "In-Person + Documents",
            "location": "Patna, Bihar",
            "contact_numbers": ["9012345678"],
            "urls_links": []
        },
        "bns_sections": [
            "BNS Section 318 (Cheating)", "BNS Section 336 (Forgery)",
            "Insurance Act Section 41"
        ],
        "authenticity_score": 0.81,
        "fake_recommendation": "GENUINE",
        "status": "TRIAGED",
        "days_ago": 14,
    },
    {
        "complainant_name": "Rekha Sharma",
        "complainant_phone": "8901209876",
        "complainant_email": "rekha.sharma@gmail.com",
        "complainant_address": "Bareilly, UP - 243001",
        "incident_description": (
            "I ordered Ayurvedic weight loss medicine from a Facebook page 'SlimFast Naturals'. "
            "I paid Rs. 2,499 via PhonePe to 8765409876. I received a package with unknown white powder. "
            "When I searched the phone number, I found 12 other similar complaints. The Facebook page "
            "is still active and posting fake testimonials."
        ),
        "incident_date": "9 April 2024",
        "incident_location": "Bareilly, UP",
        "risk_level": "MEDIUM",
        "risk_score": 0.54,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Fake Medication / E-Commerce Fraud",
        "ai_summary": "Fake Ayurvedic product fraud via Facebook. Rs. 2,499 lost. Unknown substance received — potential health risk. 12+ other victims identified. Drug Controller complaint warranted.",
        "entities": {
            "victim": "Rekha Sharma",
            "suspect": "'SlimFast Naturals' Facebook page",
            "financial_amount": "Rs. 2,499",
            "financial_vector": "PhonePe to 8765409876",
            "platform": "Facebook",
            "location": "Bareilly, UP",
            "contact_numbers": ["8765409876"],
            "urls_links": ["SlimFast Naturals (Facebook)"]
        },
        "bns_sections": [
            "BNS Section 318 (Cheating)", "Drugs and Cosmetics Act",
            "IT Act Section 66D"
        ],
        "authenticity_score": 0.78,
        "fake_recommendation": "GENUINE",
        "status": "TRIAGED",
        "days_ago": 6,
    },
    {
        "complainant_name": "Lalitha Devi Reddy",
        "complainant_phone": "9550123456",
        "complainant_email": None,
        "complainant_address": "Vijayawada, Andhra Pradesh - 520001",
        "incident_description": (
            "I purchased a saree worth Rs. 6,500 from a website sareepalace.shop after seeing an Instagram "
            "advertisement. I paid via UPI but received a completely different low-quality product. "
            "When I contacted the seller, they offered only 20% refund. The website has hundreds of "
            "similar complaints on consumer forums."
        ),
        "incident_date": "6 April 2024",
        "incident_location": "Vijayawada, AP",
        "risk_level": "MEDIUM",
        "risk_score": 0.48,
        "crime_category": "Financial Crime",
        "crime_subcategory": "E-Commerce Fraud / Counterfeit Product",
        "ai_summary": "Online shopping fraud — counterfeit product delivered. Rs. 6,500 loss. Website has multiple consumer complaints. UPI transaction traceable.",
        "entities": {
            "victim": "Lalitha Devi Reddy",
            "suspect": "sareepalace.shop operator",
            "financial_amount": "Rs. 6,500",
            "financial_vector": "UPI payment",
            "platform": "Instagram Ad + Website",
            "location": "Vijayawada, AP",
            "contact_numbers": [],
            "urls_links": ["sareepalace.shop"]
        },
        "bns_sections": [
            "BNS Section 318 (Cheating)", "Consumer Protection Act 2019",
            "IT Act Section 66D"
        ],
        "authenticity_score": 0.79,
        "fake_recommendation": "GENUINE",
        "status": "TRIAGED",
        "days_ago": 9,
    },
    # ── ADDITIONAL LOW RISK ───────────────────────────────────────────────────
    {
        "complainant_name": "Vijay Pandey",
        "complainant_phone": "9451234567",
        "complainant_email": None,
        "complainant_address": "Prayagraj, UP - 211001",
        "incident_description": (
            "I have been receiving 4-5 spam calls daily from numbers starting with +92 (Pakistan) and "
            "+1 (US). The callers speak in English claiming I won a prize. I have not shared any "
            "information or made any payments. I am reporting this for awareness and to block these numbers."
        ),
        "incident_date": "Ongoing, April 2024",
        "incident_location": "Prayagraj, UP",
        "risk_level": "LOW",
        "risk_score": 0.12,
        "crime_category": "Other Cybercrime",
        "crime_subcategory": "Spam / Robocall (No Loss)",
        "ai_summary": "International spam calls. No financial loss. Reported for awareness. Numbers forwarded to TRAI for blocking.",
        "entities": {
            "victim": "Vijay Pandey",
            "suspect": "Unknown international callers",
            "financial_amount": None,
            "financial_vector": None,
            "platform": "Phone",
            "location": "Prayagraj, UP",
            "contact_numbers": [],
            "urls_links": []
        },
        "bns_sections": ["IT Act Section 66D (attempted)"],
        "authenticity_score": 0.75,
        "fake_recommendation": "GENUINE",
        "status": "TRIAGED",
        "days_ago": 1,
    },
    {
        "complainant_name": "Shalini Verma",
        "complainant_phone": "9301234567",
        "complainant_email": "shalini.verma@gmail.com",
        "complainant_address": "Jabalpur, MP - 482001",
        "incident_description": (
            "I received a Facebook message saying I won an iPhone 15 in a Facebook lottery. "
            "They asked for my address and said there would be a delivery charge of Rs. 500. "
            "I did NOT pay anything and blocked the account. I am reporting this as a scam alert."
        ),
        "incident_date": "14 April 2024",
        "incident_location": "Jabalpur, MP",
        "risk_level": "LOW",
        "risk_score": 0.10,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Social Media Lottery Scam (Attempted)",
        "ai_summary": "Attempted Facebook lottery scam. No financial loss as victim correctly refused payment. Filed as awareness report.",
        "entities": {
            "victim": "Shalini Verma",
            "suspect": "Unknown Facebook account",
            "financial_amount": None,
            "financial_vector": None,
            "platform": "Facebook",
            "location": "Jabalpur, MP",
            "contact_numbers": [],
            "urls_links": []
        },
        "bns_sections": ["BNS Section 318 attempt"],
        "authenticity_score": 0.78,
        "fake_recommendation": "GENUINE",
        "status": "TRIAGED",
        "days_ago": 1,
    },
    {
        "complainant_name": "Pawan Gupta",
        "complainant_phone": "9821034567",
        "complainant_email": "pawan.gupta@gmail.com",
        "complainant_address": "Agra, UP - 282001",
        "incident_description": (
            "I received an email claiming to be from my bank ICICI saying my account is temporarily "
            "restricted. The email had a link but I did NOT click it — I noticed the sender domain was "
            "icici-secure.xyz, not official icicibank.com. I have forwarded the email to my bank's "
            "fraud team. No financial loss occurred. Filing for awareness."
        ),
        "incident_date": "14 April 2024",
        "incident_location": "Agra, UP",
        "risk_level": "LOW",
        "risk_score": 0.08,
        "crime_category": "Financial Crime",
        "crime_subcategory": "Phishing Email (Attempted — No Loss)",
        "ai_summary": "Phishing email targeting ICICI customers — victim correctly identified and did not click. Phishing domain available for CERT-In reporting.",
        "entities": {
            "victim": "Pawan Gupta",
            "suspect": "icici-secure.xyz operator",
            "financial_amount": None,
            "financial_vector": None,
            "platform": "Email",
            "location": "Agra, UP",
            "contact_numbers": [],
            "urls_links": ["icici-secure.xyz"]
        },
        "bns_sections": ["IT Act Section 66D (attempted)"],
        "authenticity_score": 0.82,
        "fake_recommendation": "GENUINE",
        "status": "TRIAGED",
        "days_ago": 1,
    },
    {
        "complainant_name": "Divya Krishnan",
        "complainant_phone": "9446123456",
        "complainant_email": "divya.k@gmail.com",
        "complainant_address": "Kozhikode, Kerala - 673001",
        "incident_description": (
            "I received a threatening email from address 'hitman4hire@protonmail.com' saying they "
            "have been hired to harm me and will cancel the order if I pay 0.5 Bitcoin. "
            "I believe this is a sextortion/hitman scam as I have no known enemies. "
            "I did not pay and have blocked the address."
        ),
        "incident_date": "13 April 2024",
        "incident_location": "Kozhikode, Kerala",
        "risk_level": "LOW",
        "risk_score": 0.15,
        "crime_category": "Extortion",
        "crime_subcategory": "Hitman Scam Email (No Credible Threat)",
        "ai_summary": "Mass hitman scam email — no credible threat. Standard sextortion script. Victim correctly did not pay. No action needed beyond awareness and email blocking.",
        "entities": {
            "victim": "Divya Krishnan",
            "suspect": "hitman4hire@protonmail.com",
            "financial_amount": "0.5 Bitcoin (demanded)",
            "financial_vector": "Bitcoin",
            "platform": "Email",
            "location": "Kozhikode, Kerala",
            "contact_numbers": [],
            "urls_links": ["hitman4hire@protonmail.com"]
        },
        "bns_sections": ["BNS Section 351 (Criminal Intimidation)"],
        "authenticity_score": 0.72,
        "fake_recommendation": "GENUINE",
        "status": "TRIAGED",
        "days_ago": 2,
    },
    {
        "complainant_name": "Ravi Shankar Prasad",
        "complainant_phone": "9198765432",
        "complainant_email": "ravi.shankar@gmail.com",
        "complainant_address": "Varanasi, UP - 221005",
        "incident_description": (
            "My competitor has posted false and defamatory reviews on Google Maps and Justdial "
            "claiming my catering business uses non-vegetarian ingredients in vegetarian food, which is completely false. "
            "The reviewer 'FoodCritic123' has no other reviews and the account was created 3 days ago. "
            "This is severely affecting my business especially during a religious event season."
        ),
        "incident_date": "10 April 2024",
        "incident_location": "Varanasi, UP",
        "risk_level": "LOW",
        "risk_score": 0.20,
        "crime_category": "Online Harassment",
        "crime_subcategory": "Online Defamation / Fake Business Review",
        "ai_summary": "Business defamation via fake reviews — no direct financial fraud. Civil action may be more appropriate. Platform complaint and legal notice to Google/Justdial recommended.",
        "entities": {
            "victim": "Ravi Shankar Prasad (catering business)",
            "suspect": "FoodCritic123 (fake reviewer)",
            "financial_amount": None,
            "financial_vector": None,
            "platform": "Google Maps + Justdial",
            "location": "Varanasi, UP",
            "contact_numbers": [],
            "urls_links": ["FoodCritic123 (Google Maps)"]
        },
        "bns_sections": ["BNS Section 356 (Defamation)"],
        "authenticity_score": 0.76,
        "fake_recommendation": "GENUINE",
        "status": "TRIAGED",
        "days_ago": 5,
    },
    # ── ADDITIONAL FAKE/FLAGGED CASES ─────────────────────────────────────────
    {
        "complainant_name": "Unknown Sender",
        "complainant_phone": "0000000000",
        "complainant_email": "noreply@temp-mail.org",
        "complainant_address": None,
        "incident_description": (
            "hack government website database password breach national security urgent cyber attack "
            "terror threat bomb explosion ransom demand critical infrastructure failure imminent "
            "police action required immediately urgent priority high risk criminal"
        ),
        "incident_date": None,
        "incident_location": None,
        "risk_level": "LOW",
        "risk_score": 0.09,
        "crime_category": "Other Cybercrime",
        "crime_subcategory": "Suspected Bot Submission",
        "ai_summary": "Automated bot submission — high-risk keyword list with no narrative. Classic automated fake report pattern. No incident described.",
        "entities": {},
        "bns_sections": ["BNS Section 229 (False complaint)"],
        "authenticity_score": 0.05,
        "fake_recommendation": "REJECT",
        "is_flagged_fake": True,
        "fake_flags": [
            "Automated keyword injection pattern detected",
            "No coherent narrative — only disconnected trigger words",
            "Temp-mail disposable email address",
            "Submission matches known bot testing pattern",
            "All 7 fake detection layers flagged REJECT"
        ],
        "status": "CLOSED",
        "days_ago": 3,
    },
    {
        "complainant_name": "Competitor Business",
        "complainant_phone": "9812345670",
        "complainant_email": "complaint@anon.com",
        "complainant_address": "Delhi - 110001",
        "incident_description": (
            "My neighbor/business partner Suresh at shop number 24 Market Road Delhi is doing "
            "illegal activities and I want police action taken against him immediately. "
            "He cheated me. He is a criminal. Please arrest him. He owes me money from 2 years. "
            "I request police to take strictest action and give justice."
        ),
        "incident_date": "April 2024",
        "incident_location": "Delhi",
        "risk_level": "LOW",
        "risk_score": 0.11,
        "crime_category": "Other Cybercrime",
        "crime_subcategory": "Civil Dispute Masquerading as Cybercrime",
        "ai_summary": "Suspected civil/business dispute filed as cybercrime complaint. No digital element described. No specific cyber offence. Redirect to civil court.",
        "entities": {
            "victim": "Unknown complainant",
            "suspect": "Suresh (shop 24)",
            "financial_amount": None,
            "financial_vector": None,
            "platform": "None (offline dispute)",
            "location": "Delhi",
            "contact_numbers": [],
            "urls_links": []
        },
        "bns_sections": ["BNS Section 229 (Misuse of police system)"],
        "authenticity_score": 0.14,
        "fake_recommendation": "REJECT",
        "is_flagged_fake": True,
        "fake_flags": [
            "No cybercrime element detected — offline civil dispute",
            "No digital platforms, amounts, or transactions mentioned",
            "Template grievance language: 'strictest action', 'give justice'",
            "Entity inconsistency: cyber portal used for non-cyber matter"
        ],
        "status": "CLOSED",
        "days_ago": 4,
    },
    {
        "complainant_name": "Testing Account",
        "complainant_phone": "9999999999",
        "complainant_email": "test123@test.com",
        "complainant_address": "Test City - 000000",
        "incident_description": (
            "Testing testing 1 2 3. This is a test complaint to see how the system works. "
            "Please ignore this report as it is only for testing purposes. Test test test. "
            "Abc xyz 123. Hello world. Insert complaint here."
        ),
        "incident_date": "Test date",
        "incident_location": "Test location",
        "risk_level": "LOW",
        "risk_score": 0.07,
        "crime_category": "Other Cybercrime",
        "crime_subcategory": "System Test / Placeholder",
        "ai_summary": "Automated test submission with placeholder text. No real incident. AI correctly identified as fake.",
        "entities": {},
        "bns_sections": ["BNS Section 229"],
        "authenticity_score": 0.06,
        "fake_recommendation": "REJECT",
        "is_flagged_fake": True,
        "fake_flags": [
            "Explicit test/placeholder language: 'Testing testing 1 2 3'",
            "Placeholder text detected: 'Insert complaint here'",
            "Zero specificity score — no names, amounts, dates, locations",
            "Repetitive word pattern: test/testing repeated 7 times",
            "Template pattern match: 100% similarity to known test submissions"
        ],
        "status": "CLOSED",
        "days_ago": 6,
    },
    {
        "complainant_name": "Ramesh Gupta",
        "complainant_phone": "9876512340",
        "complainant_email": "rg123@gmail.com",
        "complainant_address": "Kanpur, UP - 208001",
        "incident_description": (
            "On 1st April 2024 my ex-girlfriend Priya Sharma who lives in Bandra Mumbai cheated me "
            "by not returning Rs. 50,000 I had given her. She has blocked me everywhere. "
            "She had promised to marry me but broke up. I want strict police action against her. "
            "Her phone number is 9876543210 and email is priya.sharma@gmail.com."
        ),
        "incident_date": "1 April 2024",
        "incident_location": "Kanpur, UP",
        "risk_level": "LOW",
        "risk_score": 0.13,
        "crime_category": "Other Cybercrime",
        "crime_subcategory": "Personal Dispute / Suspected Harassment Complaint",
        "ai_summary": "Personal relationship dispute — not a cybercrime. Complainant providing ex-partner's personal details. Possible reverse harassment. No digital fraud element. Reject and flag.",
        "entities": {
            "victim": "Ramesh Gupta (unverified)",
            "suspect": "Priya Sharma (potential misidentification)",
            "financial_amount": "Rs. 50,000 (civil claim)",
            "financial_vector": "Personal loan (not digital)",
            "platform": "None",
            "location": "Kanpur",
            "contact_numbers": ["9876543210"],
            "urls_links": []
        },
        "bns_sections": ["BNS Section 229 (False complaint)"],
        "authenticity_score": 0.18,
        "fake_recommendation": "REJECT",
        "is_flagged_fake": True,
        "fake_flags": [
            "No cybercrime element — personal relationship dispute",
            "Third-party PII shared without consent (potential doxxing)",
            "Possible counter-complaint / harassment of ex-partner",
            "L2: Gemini detected revenge-complaint pattern",
            "Entity check: complainant's contact matches 'suspect' number in prior report"
        ],
        "status": "CLOSED",
        "days_ago": 13,
    },

]


def seed():
    db = SessionLocal()
    try:
        # Check if already seeded
        existing = db.query(Report).count()
        if existing > 0:
            print(f"  Database already has {existing} reports. Skipping seed.")
            print("  To re-seed: delete autojustice.db and run again.")
            return

        print(f"  Seeding {len(DEMO_CASES)} demo cases...")
        import hashlib

        for i, case in enumerate(DEMO_CASES):
            now = datetime.utcnow() - timedelta(days=case.get("days_ago", 0))

            content_str = case["incident_description"] + case["complainant_name"]
            content_hash = hashlib.sha256(content_str.encode()).hexdigest()

            case_number = f"CY-2024-{10000000 + i * 3745873 % 90000000}"

            report = Report(
                id=str(uuid.uuid4()),
                case_number=case_number,
                created_at=now,
                updated_at=now,
                complainant_name=case["complainant_name"],
                complainant_phone=case.get("complainant_phone"),
                complainant_email=case.get("complainant_email"),
                complainant_address=case.get("complainant_address"),
                incident_description=case["incident_description"],
                incident_date=case.get("incident_date"),
                incident_location=case.get("incident_location"),
                risk_level=case["risk_level"],
                risk_score=case["risk_score"],
                crime_category=case["crime_category"],
                crime_subcategory=case["crime_subcategory"],
                ai_summary=case["ai_summary"],
                entities=case.get("entities", {}),
                bns_sections=case["bns_sections"],
                authenticity_score=case["authenticity_score"],
                is_flagged_fake=case.get("is_flagged_fake", False),
                fake_flags=case.get("fake_flags", []),
                fake_recommendation=case["fake_recommendation"],
                content_hash=content_hash,
                status=case["status"],
                fir_path=f"CR_{case_number}.pdf" if case["status"] in ("FIR_GENERATED", "COMPLAINT_REGISTERED") else None,
                fir_generated_at=now if case["status"] in ("FIR_GENERATED", "COMPLAINT_REGISTERED") else None,
            )
            db.add(report)

            db.add(AuditLog(
                id=str(uuid.uuid4()),
                report_id=report.id,
                timestamp=now,
                action="REPORT_SUBMITTED",
                actor="SYSTEM (DEMO SEED)",
                details={
                    "risk_level": case["risk_level"],
                    "authenticity_score": case["authenticity_score"],
                    "demo": True
                }
            ))

            if case["status"] in ("FIR_GENERATED", "COMPLAINT_REGISTERED"):
                db.add(AuditLog(
                    id=str(uuid.uuid4()),
                    report_id=report.id,
                    timestamp=now + timedelta(seconds=30),
                    action="FIR_GENERATED",
                    actor="SYSTEM",
                    details={"fir_path": f"CR_{case_number}.pdf", "demo": True}
                ))

        db.commit()
        print(f"  ✓ Seeded {len(DEMO_CASES)} cases successfully!")

        # Summary
        from sqlalchemy import func
        high   = db.query(func.count(Report.id)).filter(Report.risk_level == "HIGH").scalar()
        medium = db.query(func.count(Report.id)).filter(Report.risk_level == "MEDIUM").scalar()
        low    = db.query(func.count(Report.id)).filter(Report.risk_level == "LOW").scalar()
        fakes  = db.query(func.count(Report.id)).filter(Report.is_flagged_fake == True).scalar()
        firs   = db.query(func.count(Report.id)).filter(Report.status == "FIR_GENERATED").scalar()

        print(f"  ├─ HIGH risk:   {high}")
        print(f"  ├─ MEDIUM risk: {medium}")
        print(f"  ├─ LOW risk:    {low}")
        print(f"  ├─ Fake flagged: {fakes}")
        print(f"  └─ Complaint Reports: {firs}")

    except Exception as e:
        db.rollback()
        print(f"  ERROR during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 50)
    print("  AutoJustice AI NEXUS — Demo Seeder")
    print("=" * 50)
    seed()
    print("\n  Dashboard ready with demo data!")
    print("  Open: http://localhost:8000/dashboard")
