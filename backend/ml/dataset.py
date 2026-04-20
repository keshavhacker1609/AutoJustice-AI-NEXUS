"""
AutoJustice AI NEXUS — Training Dataset Generator
Generates labeled synthetic datasets for the three ML models.
All samples are India-specific cybercrime complaint text.
"""
import random
from typing import List, Tuple

from features import extract_features

# ─── Random seed for reproducibility ─────────────────────────────────────────
random.seed(42)

# ─── Shared vocabulary pools ──────────────────────────────────────────────────
NAMES = [
    "Rahul Kumar Sharma", "Priya Mehta", "Amit Singh Rawat", "Neha Verma",
    "Vijay Krishnamurthy", "Sunita Patel", "Rajesh Gupta", "Kavita Nair",
    "Arun Mishra", "Deepa Iyer", "Suresh Reddy", "Anita Chauhan",
    "Manoj Tiwari", "Pooja Agarwal", "Sanjay Yadav", "Rekha Bhatt",
    "Dinesh Malhotra", "Usha Krishnan", "Naresh Pandey", "Geeta Joshi",
]
AMOUNTS = [
    "45000", "12500", "8750", "1,50,000", "23000", "67500", "2500",
    "18000", "95000", "3,25,000", "75000", "4500", "32000", "6,00,000",
    "15000", "88000", "21000", "55000", "1,10,000", "9999",
]
PHONES = [
    "9876543210", "8765432109", "7654321098", "9988776655", "8899001122",
    "9123456789", "7890123456", "8012345678", "9901234567", "7700112233",
]
DATES = [
    "15/03/2026", "22/01/2026", "08/02/2026", "30/11/2025", "14/12/2025",
    "05/04/2026", "19/09/2025", "27/07/2025", "03/10/2025", "11/06/2025",
]
BANKS = [
    "SBI", "HDFC Bank", "ICICI Bank", "Axis Bank", "PNB",
    "Kotak Mahindra Bank", "Bank of Baroda", "Canara Bank",
    "Union Bank of India", "IndusInd Bank",
]
PLATFORMS = [
    "WhatsApp", "Instagram", "Telegram", "Facebook", "Twitter",
    "Snapchat", "LinkedIn", "YouTube", "TikTok", "ShareChat",
]
CITIES = [
    "Delhi", "Mumbai", "Bengaluru", "Hyderabad", "Chennai",
    "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
]
RELATIONSHIPS = [
    "sister", "brother", "wife", "husband", "mother", "father",
    "daughter", "son", "friend", "colleague",
]
COMPANIES = [
    "TCS", "Infosys", "Wipro", "HCL Technologies", "Reliance Industries",
    "Amazon India", "Flipkart", "Google India", "Microsoft India", "IBM India",
]
SALARIES = [
    "35000", "50000", "75000", "1,20,000", "45000",
    "60000", "80000", "95000", "40000", "55000",
]
UPI_IDS = [
    "suspect@paytm", "fraud123@ybl", "scammer@okaxis", "unknown@oksbi",
    "hacker@okicici", "cheater@upi", "fraud@paytm", "thief@ybl",
]
TXN_IDS = [
    "TXN12345678901", "UPI20240315001", "IMPS9876543210", "NEFT20240101XYZ",
    "UPI20260108ABC", "TXN98765432100", "IMPS1234567890", "NEFT20251130DEF",
]
URLS = [
    "http://fraudjobs.in/apply", "https://fake-bank.com/login",
    "http://prize.win/claim", "https://gov-scheme.xyz/register",
    "http://crypto-profit.in/invest", "https://lottery-india.net/win",
]
EMAILS = [
    "fraudster@gmail.com", "scammer@yahoo.com", "hacker@hotmail.com",
    "unknown@protonmail.com", "suspect@outlook.com", "fake@tempmail.com",
]
CRYPTO_AMOUNTS = [
    "0.5 BTC", "2.3 ETH", "10000 USDT", "1.2 BTC", "500 USDT",
    "0.8 ETH", "5000 USDT", "3.0 BTC", "1500 USDT", "0.3 BTC",
]


def _r(pool):
    """Pick a random element from a pool."""
    return random.choice(pool)


# ─────────────────────────────────────────────────────────────────────────────
# GENUINE templates (specific, detailed, personal — authentic cybercrime reports)
# ─────────────────────────────────────────────────────────────────────────────
GENUINE_TEMPLATES = [
    # Financial fraud — OTP/UPI
    "On {date}, I received a call from {name} claiming to be from {bank}. "
    "They asked for my OTP and transferred Rs.{amount} from my account. "
    "The UPI transaction ID was {txn}. Their number was {phone}.",

    # Job fraud
    "My {relationship} {name} was approached by a fake recruiter on LinkedIn "
    "offering a job in {company} at Rs.{salary} per month. They paid Rs.{amount} "
    "as registration fees on {date} via UPI to {upi}.",

    # Fake social media profile / morphed photos
    "{name} created a fake profile on {platform} using my photos and is sending "
    "obscene messages to my contacts since {date}. Their profile URL is {url}.",

    # Sextortion
    "On {date} I was contacted on {platform} by someone using the name {name} "
    "who recorded our video call and is now demanding Rs.{amount} threatening "
    "to send the recording to my family. Their number is {phone}.",

    # Online shopping fraud
    "I ordered a mobile phone worth Rs.{amount} from a seller named {name} on "
    "an online marketplace. After paying via UPI ID {upi} on {date}, the seller "
    "blocked me and the product was never delivered.",

    # KYC fraud
    "I received a message asking me to update my KYC for {bank} account through "
    "a link {url}. When I entered my details on {date}, Rs.{amount} was debited "
    "from my account. The transaction number was {txn}.",

    # Investment / trading fraud
    "Someone added me to a {platform} group promising high returns on stock "
    "investments. I invested Rs.{amount} as advised by {name} between {date} "
    "and last week but when I tried to withdraw my profits, the app stopped "
    "working and {name} is now unreachable at {phone}.",

    # Cyber stalking
    "Since {date}, an unknown person using account {url} on {platform} has been "
    "harassing me with abusive messages and sharing my personal photos without "
    "consent. I have screenshots and their IP address if needed.",

    # Lottery / prize fraud
    "I received an email from {email} on {date} claiming I won a prize of "
    "Rs.{amount} from {company} lucky draw. When I paid Rs.{amount2} as "
    "processing fee via UPI to {upi}, they disappeared and the prize was never "
    "paid. The sender's number was {phone}.",

    # Impersonation of govt officer
    "On {date} a person called me from {phone} claiming to be a CBI officer and "
    "said my Aadhaar card was linked to illegal activities. They demanded "
    "Rs.{amount} to clear my name via UPI ID {upi}. I realized later it was fraud.",

    # Ransomware / hacking
    "My computer was hacked on {date} and all files were encrypted. A message "
    "appeared demanding {crypto} to restore access. The attacker's email is "
    "{email} and the Bitcoin wallet address was shown on screen.",

    # Aadhaar / identity misuse
    "I discovered on {date} that someone used my Aadhaar number to open a bank "
    "account in {bank} and took a loan of Rs.{amount}. The branch confirmed the "
    "account was opened fraudulently. Suspect's contact used was {phone}.",

    # Phishing — bank SMS
    "I received an SMS from a number {phone} on {date} claiming my {bank} "
    "account would be blocked. It contained a link {url}. I clicked and entered "
    "OTP after which Rs.{amount} was debited. Transaction ID: {txn}.",

    # Child safety / grooming
    "My {age}-year-old {child_rel} was contacted on {platform} by an adult "
    "posing as a teenager since {date}. The person's profile name is {handle} "
    "and they have been sending inappropriate messages. Their contact number "
    "is {phone}.",

    # Data breach / doxxing
    "{name} has posted my personal information including home address, phone "
    "number {phone}, and workplace details on {platform} on {date} without my "
    "consent. This is causing me and my family severe distress.",

    # Fake matrimony profile
    "I met a person using the name {name} on a matrimony website who claimed to "
    "work in {company} in {city}. After building trust over 3 months they asked "
    "for Rs.{amount} for a medical emergency on {date} via {bank} account and "
    "then blocked me. Their number was {phone}.",

    # Crypto investment scam
    "I was added to a {platform} group by {name} in {month} that promised "
    "guaranteed returns on cryptocurrency. I deposited {crypto} equivalent to "
    "Rs.{amount} to wallet {wallet} but when I tried to withdraw, they demanded "
    "more fees. Contact: {email}.",

    # Fake customer care
    "I searched for {bank} customer care number online and called {phone} on "
    "{date}. The person asked me to install a remote access app and then "
    "transferred Rs.{amount} from my account. Transaction ID: {txn}.",

    # Online loan fraud
    "I applied for a loan through an app called {app_name} and received Rs.{amount} "
    "on {date}. When I defaulted on one payment they started calling my contacts "
    "from {phone} with abusive messages and morphed photos.",

    # Defamation / fake reviews
    "My competitor {name} has been posting fake negative reviews about my business "
    "{company} on Google and Instagram since {date} using fake accounts. One of "
    "the accounts is {url}. This has cost me at least Rs.{amount} in lost business.",
]

# ─────────────────────────────────────────────────────────────────────────────
# FAKE templates (vague, keyword-stuffed, templated, or nonsensical)
# ─────────────────────────────────────────────────────────────────────────────
FAKE_TEMPLATES = [
    "Someone has done fraud with me please help me I need justice immediately",
    "I am writing to report that xyz person has done some illegal activity please take action",
    "Kindly take action against the unknown person who has been harassing me",
    "bomb hack kill murder rape threat extortion ransom blackmail sextortion kidnap",
    "please help please help please help I am victim please help",
    "I want to file a complaint against unknown person for cybercrime",
    "[victim name] was harassed by [suspect name] please take action against [suspect name]",
    "this is to inform you that some person is doing illegal things on internet",
    "I am writing to report that abc mobile has been misused kindly take action",
    "insert name here has committed a crime please arrest them",
    "cyber crime cyber crime cyber crime please help me cyber crime victim",
    "please help me I am victim of online fraud please do something",
    "I want justice please help someone did something wrong to me online",
    "kindly take action against the person who hacked me",
    "this is to inform you that I have been cheated please investigate",
    "bomb blast terrorist attack hack kill extort ransom threat kidnap murder",
    "xyz person did something bad please help me take action against them",
    "I am victim of fraud please help me file this complaint immediately",
    "someone is threatening me online please help please help please",
    "[victim name] needs help [suspect name] is criminal please arrest",
    "my money is gone please investigate fraud happened to me",
    "i am writing to report a serious crime please take immediate action",
    "kindly take action against all criminals in my area",
    "this is a very serious matter please help as soon as possible thank you",
    "I want to file a complaint against unknown person who is unknown",
]

# ─────────────────────────────────────────────────────────────────────────────
# REVIEW templates (some specifics but incomplete — borderline cases)
# ─────────────────────────────────────────────────────────────────────────────
REVIEW_TEMPLATES = [
    "Someone from {phone} has been calling me and threatening me. I am scared.",
    "I lost money through online fraud last month. Please investigate.",
    "A person on {platform} is misusing my photos. Please take action.",
    "I received suspicious messages asking for my bank details from {phone}.",
    "My {bank} account shows unauthorized transactions. Please look into this.",
    "Someone created a fake profile using my name on social media.",
    "I am being harassed by an unknown person via email {email}.",
    "Received a message on {date} claiming I won a lottery. Is this fraud?",
    "A person named {name} owes me Rs.{amount} and is not repaying.",
    "I clicked on a suspicious link and now I think my phone is hacked.",
    "Someone is using my photos without permission on various websites.",
    "I received abusive calls from an unknown number continuously for a week.",
    "My trading account was accessed by someone on {date} without my knowledge.",
    "I paid Rs.{amount} for a product online but never received it.",
    "An unknown person is blackmailing me. I have some screenshots.",
]

# Extra filler words for genuine templates that need substitution keys
_MONTHS = ["January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"]
_AGES = ["12", "13", "14", "15", "16"]
_CHILD_RELS = ["daughter", "son", "niece", "nephew"]
_HANDLES = ["@unknown_user", "@anon_profile", "@fake_person", "@anon123"]
_WALLETS = ["1A2B3C4D5E6F7G8H9I0J", "bc1qxxx", "0xABCDEF123456", "TXabc123"]
_APP_NAMES = ["QuickLoan", "CashNow", "EasyMoney", "FastCredit", "LoanApp"]
_AMOUNT2 = ["500", "1000", "2000", "1500", "750"]


def _fill_genuine(template: str) -> str:
    """Fill a genuine template with random realistic values."""
    try:
        return template.format(
            name=_r(NAMES),
            name2=_r(NAMES),
            date=_r(DATES),
            amount=_r(AMOUNTS),
            amount2=_r(_AMOUNT2),
            phone=_r(PHONES),
            bank=_r(BANKS),
            platform=_r(PLATFORMS),
            city=_r(CITIES),
            relationship=_r(RELATIONSHIPS),
            company=_r(COMPANIES),
            salary=_r(SALARIES),
            upi=_r(UPI_IDS),
            txn=_r(TXN_IDS),
            url=_r(URLS),
            email=_r(EMAILS),
            crypto=_r(CRYPTO_AMOUNTS),
            wallet=_r(_WALLETS),
            month=_r(_MONTHS),
            age=_r(_AGES),
            child_rel=_r(_CHILD_RELS),
            handle=_r(_HANDLES),
            app_name=_r(_APP_NAMES),
        )
    except KeyError:
        # Fallback: fill what we can with a format_map that ignores missing keys
        class _Default(dict):
            def __missing__(self, key):
                return _r(NAMES)
        return template.format_map(_Default(
            name=_r(NAMES), date=_r(DATES), amount=_r(AMOUNTS),
            phone=_r(PHONES), bank=_r(BANKS), platform=_r(PLATFORMS),
            city=_r(CITIES), relationship=_r(RELATIONSHIPS),
            company=_r(COMPANIES), salary=_r(SALARIES), upi=_r(UPI_IDS),
            txn=_r(TXN_IDS), url=_r(URLS), email=_r(EMAILS),
            crypto=_r(CRYPTO_AMOUNTS), wallet=_r(_WALLETS),
            month=_r(_MONTHS), age=_r(_AGES), child_rel=_r(_CHILD_RELS),
            handle=_r(_HANDLES), app_name=_r(_APP_NAMES),
            amount2=_r(_AMOUNT2),
        ))


def _fill_review(template: str) -> str:
    """Fill a review template with random values (partial specificity)."""
    class _Default(dict):
        def __missing__(self, key):
            defaults = {
                "phone": _r(PHONES), "platform": _r(PLATFORMS),
                "bank": _r(BANKS), "email": _r(EMAILS),
                "date": _r(DATES), "name": _r(NAMES),
                "amount": _r(AMOUNTS),
            }
            return defaults.get(key, "unknown")
    return template.format_map(_Default(
        phone=_r(PHONES), platform=_r(PLATFORMS), bank=_r(BANKS),
        email=_r(EMAILS), date=_r(DATES), name=_r(NAMES), amount=_r(AMOUNTS),
    ))


def generate_fake_detection_dataset() -> Tuple[List[List[float]], List[int]]:
    """
    Generate labeled training data for the fake detection classifier.
    Returns (X, y) where:
      y = 1  →  genuine report
      y = 0  →  fake/spam report
      y = 2  →  review (borderline) — encoded as 2 in y but kept for balance
    Total: 800 genuine + 800 fake + 400 review = 2000+ samples.
    """
    X: List[List[float]] = []
    y: List[int] = []

    # ── Genuine samples (label = 1) ───────────────────────────────────────────
    genuine_count = 0
    while genuine_count < 800:
        template = _r(GENUINE_TEMPLATES)
        text = _fill_genuine(template)
        X.append(extract_features(text))
        y.append(1)
        genuine_count += 1

    # ── Fake samples (label = 0) ──────────────────────────────────────────────
    fake_count = 0
    while fake_count < 800:
        template = _r(FAKE_TEMPLATES)
        # Occasionally add minor variations
        if random.random() < 0.3:
            template = template + " " + _r([
                "please help", "urgent", "immediate action required",
                "please investigate", "I am suffering",
            ])
        X.append(extract_features(template))
        y.append(0)
        fake_count += 1

    # ── Review samples (label = 2) ────────────────────────────────────────────
    review_count = 0
    while review_count < 400:
        template = _r(REVIEW_TEMPLATES)
        text = _fill_review(template)
        X.append(extract_features(text))
        y.append(2)
        review_count += 1

    return X, y


# ─────────────────────────────────────────────────────────────────────────────
# Crime Category Dataset
# ─────────────────────────────────────────────────────────────────────────────

CRIME_TEMPLATES = {
    "Financial Crime": [
        "On {date} I received a call from someone claiming to be {bank} executive. "
        "They asked me to share OTP and Rs.{amount} was debited from my account. "
        "UPI transaction ID: {txn}.",

        "My {bank} account was hacked on {date} and Rs.{amount} was transferred "
        "without my knowledge to UPI ID {upi}. I never shared my PIN or OTP.",

        "I received an SMS with a link to update {bank} KYC. After clicking {url} "
        "on {date} and entering details, Rs.{amount} was withdrawn. Phone: {phone}.",

        "A person {name} called on {phone} saying my debit card will be blocked. "
        "They asked for card details and on {date} Rs.{amount} was debited via {txn}.",

        "I transferred Rs.{amount} on {date} to UPI {upi} for online purchase but "
        "received no goods. The seller's number {phone} is now switched off.",

        "Fake {bank} customer care number {phone} was found online. They asked me "
        "to install AnyDesk and stole Rs.{amount} on {date}.",

        "I received a QR code from {email} claiming it was a payment receipt. When "
        "I scanned it on {date}, Rs.{amount} was deducted from my account instead.",

        "Someone used my credit card details to make purchases worth Rs.{amount} on "
        "{date}. Transactions appeared from {city} which I never visited.",

        "A person on {platform} offered to buy my product and sent a fake payment "
        "screenshot for Rs.{amount} on {date}. Phone used: {phone}.",

        "I was added to a {platform} trading group promising 3x returns. I invested "
        "Rs.{amount} as instructed by {name} but cannot withdraw. Contact: {phone}.",

        "Received email from {email} on {date} saying I won a lottery of Rs.{amount}. "
        "They asked for Rs.500 processing fee. This appears to be a scam.",

        "A person posing as Income Tax officer called from {phone} on {date} demanding "
        "Rs.{amount} to avoid arrest. Threatened legal action if not paid.",

        "I paid Rs.{amount} via {upi} to {name} for a job placement on {date}. "
        "After payment they stopped responding. Their number: {phone}.",

        "Fraudulent NEFT transfer of Rs.{amount} from my {bank} account on {date}. "
        "Transaction reference: {txn}. Account holder details changed without my consent.",

        "Investment fraud: {name} convinced me to invest Rs.{amount} in a fake mutual "
        "fund scheme promising 40% returns. After {date} they vanished. Phone: {phone}.",
    ],

    "Online Harassment": [
        "An unknown person on {platform} using account {url} has been sending me "
        "abusive and threatening messages since {date}. I have screenshots.",

        "I am being cyberstalked by {name} who knows my daily routine and posts "
        "my location on {platform}. Started on {date}. Their number is {phone}.",

        "Someone created a fake account using my name on {platform} and is contacting "
        "my friends and colleagues with defamatory content since {date}.",

        "I have been receiving death threats via {platform} from an account {url} "
        "since {date}. The person also called me from {phone}.",

        "My ex-partner {name} is continuously harassing me on {platform} with abusive "
        "messages and sharing my personal photos since {date}.",

        "{name} from {city} has been making fake reviews about me online and sending "
        "harassing emails to my workplace since {date}. Email: {email}.",

        "I am receiving unsolicited vulgar images and videos from {phone} on {platform} "
        "multiple times per day since {date}. Blocking does not help as they use new accounts.",

        "An anonymous account on {platform} started a hate campaign against me on {date} "
        "sharing false information about my personal life to my {relationship}.",

        "A group of people on {platform} are coordinating harassment against me including "
        "doxxing my home address. It started on {date} after I posted an opinion online.",

        "I am being blackmailed on {platform} by someone who claims to have hacked my "
        "account on {date}. They demand I share more personal content or they will expose me.",

        "{name} has been posting morphed images of me on {platform} since {date} and "
        "tagging my contacts. I am deeply distressed. Their phone: {phone}.",

        "Received threatening calls from {phone} every night since {date}. The caller "
        "uses abusive language and threatens physical harm to me and my family.",

        "Someone is impersonating me on {platform} since {date} using my photo and "
        "asking my contacts for money, causing reputational damage.",

        "A person at {email} has been sending me hateful emails threatening to share "
        "my private information since {date}. I want immediate action.",

        "I am being targeted by organized trolling on {platform} since {date}. Multiple "
        "fake accounts posting my personal details and threatening messages.",
    ],

    "Identity Theft": [
        "{name} created a fake profile on {platform} using my Aadhaar photo and "
        "personal details to commit fraud. I discovered this on {date}.",

        "My Aadhaar number was used to open a {bank} account and take a loan of "
        "Rs.{amount} without my knowledge. I found out on {date}.",

        "Someone used my PAN card to file a fraudulent income tax return on {date} "
        "claiming refund of Rs.{amount} to their bank account.",

        "My identity was stolen and used to register multiple SIM cards. I found "
        "two unknown numbers {phone} linked to my Aadhaar on {date}.",

        "A fraudster used my driving license to get a loan of Rs.{amount} from {name} "
        "finance company. I received collection calls on {date}.",

        "My {platform} account was hacked on {date}. The attacker changed the profile "
        "name to {name} and is now impersonating me to my contacts.",

        "I discovered on {date} that my photographs are being used to create fake "
        "profiles on multiple matrimony websites. Phone linked: {phone}.",

        "Someone forged my signatures and used my identity documents to purchase "
        "property worth Rs.{amount} in {city} on {date}.",

        "My email account {email} was compromised on {date} and used to send "
        "phishing emails to my contacts requesting money transfers.",

        "Received a notice that a credit card with Rs.{amount} limit was issued in "
        "my name on {date} using forged documents. Card billed from {city}.",

        "{name} is using my company ID and credentials to access client systems since "
        "{date}. I have logs and evidence of unauthorized access.",

        "My social media accounts on {platform} were accessed without authorization on "
        "{date} and used to post offensive content under my name.",

        "Someone filed a police complaint using my identity in {city} on {date}. "
        "I received summons for a crime I did not commit.",

        "Fraudulent electricity connection was taken in my name using forged documents "
        "in {city}. Bill of Rs.{amount} accumulated by {date}.",

        "My GST registration details were stolen and used to issue fake invoices worth "
        "Rs.{amount} by {date}. Business email used was {email}.",
    ],

    "Extortion": [
        "A person from {phone} is blackmailing me with screenshots of private "
        "conversations demanding Rs.{amount} by {date}. I have their email {email}.",

        "I am being extorted by someone who recorded a video call on {platform} on "
        "{date}. They demand Rs.{amount} or will share the recording. Contact: {phone}.",

        "After meeting someone on {platform} who introduced themselves as {name}, "
        "they sent intimate images and are now demanding Rs.{amount} threatening "
        "to share them with my family. Date of first contact: {date}.",

        "I received a ransom email from {email} on {date} stating they have hacked "
        "my computer and have compromising material demanding Rs.{amount} in crypto.",

        "{name} from {city} is threatening to release edited videos of me on {platform} "
        "unless I pay Rs.{amount}. They first contacted me on {date} from {phone}.",

        "My ex-partner is sending me sextortion messages from {phone} demanding "
        "Rs.{amount} in exchange for deleting intimate photos taken during our "
        "relationship. The deadline given is {date}.",

        "A criminal gang contacted me via {platform} on {date} claiming to have "
        "illegal content under my IP address. Demanded Rs.{amount} to close the case.",

        "I am receiving threats from unknown callers on {phone} to pay Rs.{amount} "
        "or face physical violence. First call received on {date}.",

        "Ransomware installed on my computer on {date} encrypted all files. "
        "Attacker demands {crypto} payment to {wallet} for decryption key.",

        "A person claiming to be police officer called from {phone} on {date} saying "
        "my number is linked to drugs case and demanded Rs.{amount} to clear my name.",

        "Extortion via {platform}: {name} claims to have hacked my accounts and demands "
        "Rs.{amount} weekly. First demand was on {date}. Email: {email}.",

        "I received threatening messages from {email} demanding Rs.{amount} claiming "
        "they have data about my browsing history. Date: {date}.",

        "Someone is extorting me using deepfake videos. They created a fake video of "
        "me and demand Rs.{amount} to delete it. Contact: {phone} since {date}.",

        "A gang from {city} is running online extortion. They collected my data from "
        "{platform} and are demanding Rs.{amount} threatening to post it. Phone: {phone}.",

        "I was lured into a fake online relationship on {platform} by {name} since "
        "{date}. After gaining trust they are now demanding Rs.{amount} via UPI {upi}.",
    ],

    "Child Safety": [
        "An adult posing as a teenager on {platform} has been grooming my {age}-year-old "
        "child since {date}. Their account is {url}. Child's device shows chats from {phone}.",

        "I discovered that my child was sent inappropriate sexual content on {platform} "
        "by an unknown adult on {date}. Screenshots saved. Account: {url}.",

        "A person using the handle {handle} on {platform} has been asking my minor child "
        "for photos since {date}. The child is {age} years old.",

        "CSAM content was sent to my {age}-year-old via {platform} on {date}. The sender's "
        "account was {url} and the number linked was {phone}.",

        "My child was asked by a person on {platform} to meet in {city} on {date}. "
        "They claim to be {age} years old but profile seems fake. Contact: {phone}.",

        "An unknown person is sharing child pornography in a {platform} group. The group "
        "link is {url} and it was discovered on {date}. Admin's number: {phone}.",

        "My {age}-year-old was asked to perform acts on video call by a stranger on "
        "{platform} on {date}. The account email is {email}.",

        "A person named {name} from {city} has been communicating with my minor child "
        "aged {age} on {platform} sending inappropriate messages. Contact: {phone}.",

        "A child exploitation website {url} was found in my child's browser on {date}. "
        "Content includes material that violates POCSO Act.",

        "Unknown adult offered money Rs.{amount} to my {age}-year-old on {platform} for "
        "sharing private photos. Conversation started on {date}. Account: {url}.",

        "A person using {email} has been sending sexual content to children in school "
        "group on {platform}. Discovered on {date}. Multiple parents affected.",

        "My minor child was blackmailed with intimate photos on {platform} by {name} "
        "demanding Rs.{amount}. Incident started on {date}. Their number: {phone}.",

        "A fake coaching institute {company} in {city} has been targeting minor girls "
        "online since {date}. Their website is {url} and contact is {phone}.",

        "Person {handle} on {platform} asked my {age}-year-old child to download a "
        "suspicious app on {date} and sent inappropriate images thereafter.",

        "My child received a video call from {phone} on {platform} on {date} where "
        "the caller showed obscene content. This is POCSO violation.",
    ],

    "Data Breach": [
        "My company database was accessed without authorization on {date}. Customer "
        "data of {amount} records was exfiltrated. IP address traced to {city}.",

        "I received an email from {email} on {date} containing my personal data "
        "including Aadhaar number, PAN and bank details — likely from a data breach.",

        "A hacker group emailed from {email} claiming to have our company's employee "
        "database and demands {crypto} ransom by {date}. Our CISO was notified.",

        "My email account {email} was hacked on {date} and all contacts and emails "
        "were accessed. Unauthorized login detected from {city}.",

        "Personal data of our hospital patients was posted on dark web forum on {date}. "
        "This includes names, addresses, medical records. Over Rs.{amount} impact.",

        "Insider threat detected: employee {name} at {company} copied confidential "
        "customer data to personal drive on {date}. HR has been informed.",

        "My phone was hacked using a zero-day exploit on {date}. All messages and "
        "contacts were accessed. I received notification from {email} about the breach.",

        "Unauthorized API access to our payment system occurred on {date}. Customer "
        "card data may have been compromised. Attacker IP tracked to {city}.",

        "A competitor obtained our proprietary software code through a data breach on "
        "{date}. Inside source identified as {name} at {company}. Contact: {phone}.",

        "Government portal with my Aadhaar data was breached on {date}. I received "
        "SMS from {phone} with details only the government should have.",

        "Someone posted my private email conversations on {platform} on {date} "
        "proving they accessed my email account {email} without permission.",

        "My cloud storage was breached on {date} and private files including documents "
        "and photos were downloaded. Notified by service at {email}.",

        "An unknown party from {city} accessed our company server on {date} and "
        "installed malware. Rs.{amount} worth of proprietary data stolen.",

        "Banking credentials of multiple customers including myself were leaked on "
        "{platform} on {date}. My {bank} account was compromised. Ref: {txn}.",

        "Phishing website {url} captured my login credentials on {date}. "
        "My accounts were then accessed from {city} without authorization.",
    ],

    "Cyber Fraud": [
        "I received an SMS saying I won a prize and to click {url}. On {date} I "
        "entered my details and Rs.{amount} was debited from my {bank} account.",

        "A person calling from {phone} on {date} said my {bank} account was being "
        "used for money laundering. They transferred Rs.{amount} to investigate.",

        "Fake government scheme website {url} collected Rs.{amount} from me on {date} "
        "promising PM housing scheme benefits. Contact number given was {phone}.",

        "Phishing email from {email} pretending to be {company} HR asked me to verify "
        "my salary account on {date}. My {bank} credentials were stolen.",

        "I was scammed in a fake online job interview on {date}. Paid Rs.{amount} "
        "for training material via {upi} to {name}. No job materialized.",

        "Vishing scam: caller from {phone} on {date} pretended to be RBI officer and "
        "convinced me to install an app. Rs.{amount} vanished from my account.",

        "Smishing: SMS from spoofed number {phone} on {date} with link {url} to claim "
        "electricity bill refund. Entered bank details and lost Rs.{amount}.",

        "Fake online marketplace ad for second-hand iPhone at Rs.{amount}. Paid advance "
        "via {upi} on {date} to {name}. Product never delivered. Contact: {phone}.",

        "Investment fraud app {url} promised 200% returns. I invested Rs.{amount} on "
        "{date} recommended by {name} in a {platform} group. App now shows zero balance.",

        "Romance fraud: met {name} on dating app claiming to be NRI in {city}. After "
        "months of conversation asked for Rs.{amount} on {date} for emergency. Scam.",

        "Fake tech support from {email} accessed my computer on {date} and transferred "
        "Rs.{amount} from my {bank} account while I watched helplessly.",

        "Task-based fraud on {platform}: paid Rs.{amount} on {date} to unlock earnings "
        "from completing online tasks. Organizer {name} disappeared after payment.",

        "Pig butchering scam: {name} befriended me on {platform} since {date} and "
        "introduced me to crypto investment. I lost Rs.{amount} total. Contact: {email}.",

        "Ad fraud: I paid Rs.{amount} for Google Ads managed by agency {name}. "
        "On {date} I discovered no ads were ever run. Email: {email}.",

        "Ponzi scheme: {name} collected Rs.{amount} from me on {date} promising "
        "monthly 10% returns. Paid 2 months then disappeared. Phone: {phone}.",
    ],

    "Impersonation": [
        "A person called me from {phone} on {date} claiming to be CBI Director and "
        "demanded Rs.{amount} to resolve a fabricated case against me.",

        "Someone impersonating {bank} MD sent email from {email} on {date} instructing "
        "me to transfer Rs.{amount} to a vendor account immediately.",

        "{name} is impersonating a government officer on {platform} and collecting "
        "fees for fake schemes since {date}. Contact number: {phone}.",

        "I received a WhatsApp message from {phone} on {date} from someone claiming "
        "to be Prime Minister's office asking for donation of Rs.{amount}.",

        "Fake CBI officer called me from {phone} on {date} saying my Aadhaar was used "
        "in drug trafficking case. Demanded Rs.{amount} to settle the matter.",

        "Someone is impersonating our company {company} online via {url} and collecting "
        "money from customers. Fake site found on {date}. Losses: Rs.{amount}.",

        "A person using my officer friend {name}'s photo on {platform} is impersonating "
        "them and asking their contacts for money since {date}. Phone: {phone}.",

        "Received email from {email} impersonating Income Tax Department on {date} "
        "with demand for Rs.{amount} tax clearance to avoid arrest.",

        "Fake Enforcement Directorate officer called from {phone} on {date} asking "
        "me to keep Rs.{amount} ready for verification of my accounts.",

        "An impersonator is using my doctor {name}'s credentials on {platform} to "
        "provide fake medical advice and charge fees since {date}.",

        "Someone impersonating TRAI official called from {phone} on {date} saying my "
        "phone will be disconnected for misuse unless I pay Rs.{amount}.",

        "Fake RBI governor email from {email} on {date} requested me to transfer "
        "Rs.{amount} to a regulatory account to unlock frozen funds.",

        "A person is impersonating a judge on {platform} and offering to close cases "
        "for Rs.{amount} each since {date}. Contact: {phone}.",

        "Cyber criminal impersonated my {company} CEO via email {email} on {date} "
        "ordering me to process urgent payment of Rs.{amount} to vendor.",

        "Fake Aadhaar enrollment officer visited my area on {date} collecting biometrics "
        "and Rs.{amount} fees illegally. Their ID showed UIDAI but was fake. Phone: {phone}.",
    ],

    "Other Cybercrime": [
        "Someone published defamatory content about me on {url} on {date} with false "
        "allegations. This has damaged my reputation in {city}. Contact: {email}.",

        "A competitor is leaving fake 1-star reviews on my business page using fake "
        "accounts since {date}. One account is {url}. This is causing Rs.{amount} loss.",

        "I was scammed in a cryptocurrency exchange {url} on {date}. Lost {crypto} "
        "equivalent to Rs.{amount}. Operator's email: {email}.",

        "Someone hacked my {platform} account on {date} and posted defamatory content "
        "under my name. The posts went viral and I have received threats since.",

        "An NFT marketplace {url} accepted Rs.{amount} from me on {date} but the "
        "digital assets were never transferred. Contact: {email}.",

        "Fake online gaming platform {url} convinced me to deposit Rs.{amount} on {date}. "
        "The winnings were never paid out and the site is now inaccessible.",

        "I received a deepfake video of me in a compromising situation on {date} via "
        "{platform}. Someone is using AI to create defamatory content. Email: {email}.",

        "Cyber squatting: someone registered domain {url} using my company name on "
        "{date} and is directing customers to a fake site. Loss: Rs.{amount}.",

        "I discovered on {date} that my intellectual property was stolen and sold on "
        "{url} without permission. Revenue loss estimated at Rs.{amount}.",

        "A rogue former employee {name} from {company} is accessing our systems on "
        "{date} and leaking information to competitors. Their email: {email}.",

        "Fake donation campaign using my NGO name on {platform} collected Rs.{amount} "
        "from donors since {date}. Account used: {upi}.",

        "Someone is selling fake government certificates on {url} using my organization's "
        "name since {date}. Victims paid Rs.{amount} each.",

        "Digital piracy: my copyrighted content worth Rs.{amount} is being distributed "
        "freely on {url} since {date}. Operator contact: {email}.",

        "A viral false rumor about me was started on {platform} on {date} by {name} "
        "claiming I was involved in criminal activity. Screenshots available.",

        "Malware distributed via {platform} on {date} stole data from my computer. "
        "The malicious file was sent from {email} and is linked to group in {city}.",
    ],
}


def generate_crime_dataset() -> Tuple[List[str], List[str]]:
    """
    Generate labeled crime category training data.
    Returns (descriptions, labels) with 100+ samples per category.
    Total: 9 categories × 100+ samples = 900+ samples.
    """
    descriptions: List[str] = []
    labels: List[str] = []

    for category, templates in CRIME_TEMPLATES.items():
        count = 0
        target = 120  # 120 per category = 1080 total
        while count < target:
            template = _r(templates)
            # Use the genuine fill helper with safe fallbacks
            class _Default(dict):
                def __missing__(self, key):
                    _fallbacks = {
                        "name": _r(NAMES), "date": _r(DATES),
                        "amount": _r(AMOUNTS), "phone": _r(PHONES),
                        "bank": _r(BANKS), "platform": _r(PLATFORMS),
                        "city": _r(CITIES), "relationship": _r(RELATIONSHIPS),
                        "company": _r(COMPANIES), "salary": _r(SALARIES),
                        "upi": _r(UPI_IDS), "txn": _r(TXN_IDS),
                        "url": _r(URLS), "email": _r(EMAILS),
                        "crypto": _r(CRYPTO_AMOUNTS), "wallet": _r(_WALLETS),
                        "month": _r(_MONTHS), "age": _r(_AGES),
                        "child_rel": _r(_CHILD_RELS), "handle": _r(_HANDLES),
                        "app_name": _r(_APP_NAMES), "amount2": _r(_AMOUNT2),
                    }
                    return _fallbacks.get(key, "unknown")

            try:
                text = template.format_map(_Default(
                    name=_r(NAMES), date=_r(DATES), amount=_r(AMOUNTS),
                    phone=_r(PHONES), bank=_r(BANKS), platform=_r(PLATFORMS),
                    city=_r(CITIES), relationship=_r(RELATIONSHIPS),
                    company=_r(COMPANIES), salary=_r(SALARIES),
                    upi=_r(UPI_IDS), txn=_r(TXN_IDS), url=_r(URLS),
                    email=_r(EMAILS), crypto=_r(CRYPTO_AMOUNTS),
                    wallet=_r(_WALLETS), month=_r(_MONTHS), age=_r(_AGES),
                    child_rel=_r(_CHILD_RELS), handle=_r(_HANDLES),
                    app_name=_r(_APP_NAMES), amount2=_r(_AMOUNT2),
                ))
            except Exception:
                text = template
            descriptions.append(text)
            labels.append(category)
            count += 1

    return descriptions, labels


# ─────────────────────────────────────────────────────────────────────────────
# Risk Level Dataset
# ─────────────────────────────────────────────────────────────────────────────

def generate_risk_dataset() -> Tuple[List[List[float]], List[str]]:
    """
    Generate labeled risk level training data.
    Reuses the fake detection feature vectors with risk labels applied.

    Returns (X, y) where y is "HIGH", "MEDIUM", or "LOW".
    """
    X_raw, y_fake = generate_fake_detection_dataset()

    X: List[List[float]] = []
    y: List[str] = []

    # Feature indices from FEATURE_NAMES
    IDX_WORD_COUNT          = 0   # word_count
    IDX_HAS_AMOUNT          = 3   # has_financial_amount
    IDX_SPECIFICITY         = 10  # specificity_score

    for features in X_raw:
        word_count   = features[IDX_WORD_COUNT]
        has_amount   = features[IDX_HAS_AMOUNT]
        specificity  = features[IDX_SPECIFICITY]

        if has_amount == 1.0 and word_count > 0.4 and specificity > 0.5:
            risk = "HIGH"
        elif has_amount == 1.0 and specificity > 0.25:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        X.append(features)
        y.append(risk)

    return X, y


if __name__ == "__main__":
    # Quick sanity check
    X_fake, y_fake = generate_fake_detection_dataset()
    print(f"Fake detection dataset: {len(X_fake)} samples, {len(set(y_fake))} classes")
    print(f"  Genuine: {y_fake.count(1)}, Fake: {y_fake.count(0)}, Review: {y_fake.count(2)}")

    X_crime, y_crime = generate_crime_dataset()
    from collections import Counter
    print(f"\nCrime dataset: {len(X_crime)} samples, {len(set(y_crime))} categories")
    for cat, cnt in sorted(Counter(y_crime).items()):
        print(f"  {cat}: {cnt}")

    X_risk, y_risk = generate_risk_dataset()
    print(f"\nRisk dataset: {len(X_risk)} samples")
    for level, cnt in sorted(Counter(y_risk).items()):
        print(f"  {level}: {cnt}")
