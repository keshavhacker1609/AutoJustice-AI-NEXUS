/**
 * AutoJustice AI NEXUS — Phase 2: Internationalization (i18n)
 * Multi-language support for the Citizen Portal.
 *
 * Supported languages:
 *   en — English (default)
 *   hi — Hindi (हिंदी)
 *   ta — Tamil (தமிழ்)
 *   te — Telugu (తెలుగు)
 *   bn — Bengali (বাংলা)
 *   kn — Kannada (ಕನ್ನಡ)
 */

const TRANSLATIONS = {

  // ── English (default) ─────────────────────────────────────────────────────
  en: {
    lang_name: "English",
    page_title: "File a Cybercrime Complaint",

    // Nav + header
    track_case_nav: "Track Case",
    officer_login: "Officer Login",
    ministry: "Ministry of Home Affairs, Government of India",
    portal_name: "AutoJustice AI NEXUS",
    portal_tagline: "National Cyber Crime Complaint Management System",

    // Emergency + helpline
    emergency_label: "EMERGENCY?",
    emergency_msg: "Dial 112 immediately. This portal accepts non-emergency cybercrime complaints only.",
    hl_cyber_fraud: "Cyber Fraud Helpline",
    hl_emergency: "Emergency",
    hl_police: "Police",
    hl_women: "Women Helpline",

    // Page title bar
    file_complaint_heading: "File a Cybercrime Complaint",
    file_complaint_sub: "Complete all steps to submit your complaint and receive a Complaint Reference Number",
    system_active: "System Active",
    complaints_processed: "Complaints Processed",

    // Stats strip
    stat_total: "Complaints Filed",
    stat_firs: "Reports Generated",
    stat_today: "Filed Today",
    stat_fake: "False Complaints Detected",

    // Verified banner
    email_verified: "Email Verified",

    // Step labels
    step_your_details: "Your Details",
    step_incident: "Incident Details",
    step_evidence: "Upload Evidence",
    step_review: "Review & Submit",

    // Step 1 — Email OTP
    section_email_verify: "Email Verification — Verify your identity before filing",
    email_verify_notice: "You must verify your email address before submitting a complaint. A 6-digit One-Time Password (OTP) will be sent to your email. This ensures your complaint is traceable and legally actionable.",
    email_label: "Email Address",
    email_placeholder: "Enter your email address",
    otp_email_hint: "A verification code will be sent to this address",
    send_otp_btn: "Send OTP",
    otp_sent_title: "OTP sent to your email",
    otp_sent_sub: "Check your inbox and spam folder. Valid for 5 minutes.",
    enter_otp_label: "Enter 6-digit OTP",
    verify_otp_btn: "Verify OTP",
    resend_otp_btn: "Resend OTP",
    change_email_btn: "Change Email",

    // Step 2 — Complainant Details
    section_complainant: "Complainant Details",
    dpdp_notice: "Your personal information is protected under the DPDP Act 2023 and will only be shared with the assigned investigating officer.",
    full_name: "Full Name",
    full_name_placeholder: "As per Aadhaar / Government ID",
    mobile_label: "Mobile Number",
    mobile_placeholder: "10-digit mobile number",
    mobile_hint: "Investigating officer may contact you on this number",
    verified_otp_hint: "Verified via OTP",
    address_label: "Residential Address",
    address_placeholder: "Full address with city and PIN code",
    next_incident: "Next: Incident Details →",

    // Step 3 — Incident
    section_incident: "Incident Information",
    bns_warn: "Providing false information in a complaint is an offence under BNS Section 211. Please describe the incident truthfully and accurately.",
    incident_date_label: "Date of Incident",
    incident_location_label: "Incident Location / Platform",
    incident_location_placeholder: "e.g., WhatsApp, UPI App, Website URL",
    desc_label: "Description of Incident",
    desc_placeholder: "Describe exactly what happened: how you were contacted, what was said, what money or data was involved, names/numbers/links of the accused, and any other relevant details. Be as specific as possible.",
    min_chars_hint: "Minimum 20 characters required",
    back_btn: "← Back",
    next_upload: "Next: Upload Evidence →",

    // Step 4 — Evidence
    section_evidence: "Evidence Upload",
    evidence_notice: "Upload screenshots, PDFs, transaction records, conversation exports, or any other digital evidence. All files are hashed with SHA-256 for legal chain-of-custody integrity.",
    dropzone_title: "Drag files here or click to select",
    dropzone_sub: "Accepted: JPG, PNG, PDF, TXT — Max 25 MB per file",
    next_review: "Next: Review →",

    // Step 5 — Review
    section_review: "Review & Submit Complaint",
    review_notice: "Please review all details carefully before submission. Once submitted, the complaint will be analysed by our AI system and assigned to an investigating officer.",
    declaration: "By submitting this complaint, I declare that the information provided is true to the best of my knowledge. I understand that filing a false complaint is a punishable offence.",
    submit_btn: "Submit Complaint",

    // Result
    result_registered: "Complaint Registered",
    risk_classification: "Risk Classification",
    crime_category_label: "Crime Category",
    complaint_report_label: "Complaint Report",
    auth_score_label: "Authenticity Score",
    ai_summary_label: "AI Case Summary",
    integrity_hash_label: "Content Integrity Hash (SHA-256)",
    download_fir: "Download Complaint Report (PDF)",
    track_this_case: "Track This Case",
    file_another: "File Another Complaint",

    // Footer
    footer_portal: "AutoJustice AI NEXUS — National Cyber Crime Complaint Management System",

    // Risk
    risk_high: "HIGH RISK",
    risk_medium: "MEDIUM RISK",
    risk_low: "LOW RISK",

    // Validation
    err_email_required: "Please enter your email address.",
    err_email_invalid: "Please enter a valid email address.",
    err_name_required: "Please enter your full name.",
    err_desc_short: "Please describe the incident (minimum 20 characters).",
    err_otp_required: "Please enter the OTP.",
  },

  // ── Hindi ─────────────────────────────────────────────────────────────────
  hi: {
    lang_name: "हिंदी",
    page_title: "साइबर अपराध शिकायत दर्ज करें",

    track_case_nav: "केस ट्रैक करें",
    officer_login: "अधिकारी लॉगिन",
    ministry: "गृह मंत्रालय, भारत सरकार",
    portal_name: "ऑटोजस्टिस AI नेक्सस",
    portal_tagline: "राष्ट्रीय साइबर अपराध शिकायत प्रबंधन प्रणाली",

    emergency_label: "आपातकाल?",
    emergency_msg: "तुरंत 112 डायल करें। यह पोर्टल केवल गैर-आपातकालीन साइबर अपराध शिकायतों को स्वीकार करता है।",
    hl_cyber_fraud: "साइबर धोखाधड़ी हेल्पलाइन",
    hl_emergency: "आपातकाल",
    hl_police: "पुलिस",
    hl_women: "महिला हेल्पलाइन",

    file_complaint_heading: "साइबर अपराध शिकायत दर्ज करें",
    file_complaint_sub: "अपनी शिकायत दर्ज करने और शिकायत संदर्भ संख्या प्राप्त करने के लिए सभी चरण पूरे करें",
    system_active: "सिस्टम सक्रिय",
    complaints_processed: "शिकायतें प्रसंस्कृत",

    stat_total: "दर्ज शिकायतें",
    stat_firs: "रिपोर्ट उत्पन्न",
    stat_today: "आज दर्ज",
    stat_fake: "झूठी शिकायतें पहचानी गईं",

    email_verified: "ईमेल सत्यापित",

    step_your_details: "आपका विवरण",
    step_incident: "घटना विवरण",
    step_evidence: "साक्ष्य अपलोड",
    step_review: "समीक्षा और सबमिट",

    section_email_verify: "ईमेल सत्यापन — शिकायत दर्ज करने से पहले अपनी पहचान सत्यापित करें",
    email_verify_notice: "शिकायत सबमिट करने से पहले आपको अपना ईमेल पता सत्यापित करना होगा। आपके ईमेल पर एक 6-अंकीय OTP भेजा जाएगा। यह सुनिश्चित करता है कि आपकी शिकायत ट्रेस करने योग्य और कानूनी रूप से मान्य हो।",
    email_label: "ईमेल पता",
    email_placeholder: "अपना ईमेल पता दर्ज करें",
    otp_email_hint: "इस पते पर एक सत्यापन कोड भेजा जाएगा",
    send_otp_btn: "OTP भेजें",
    otp_sent_title: "आपके ईमेल पर OTP भेजा गया",
    otp_sent_sub: "अपना इनबॉक्स और स्पैम फ़ोल्डर जांचें। 5 मिनट के लिए मान्य।",
    enter_otp_label: "6-अंकीय OTP दर्ज करें",
    verify_otp_btn: "OTP सत्यापित करें",
    resend_otp_btn: "OTP दोबारा भेजें",
    change_email_btn: "ईमेल बदलें",

    section_complainant: "शिकायतकर्ता विवरण",
    dpdp_notice: "आपकी व्यक्तिगत जानकारी DPDP अधिनियम 2023 के तहत सुरक्षित है और केवल जांच अधिकारी के साथ साझा की जाएगी।",
    full_name: "पूरा नाम",
    full_name_placeholder: "आधार / सरकारी पहचान के अनुसार",
    mobile_label: "मोबाइल नंबर",
    mobile_placeholder: "10 अंकों का मोबाइल नंबर",
    mobile_hint: "जांच अधिकारी आपसे इस नंबर पर संपर्क कर सकते हैं",
    verified_otp_hint: "OTP से सत्यापित",
    address_label: "आवासीय पता",
    address_placeholder: "शहर और पिन कोड सहित पूरा पता",
    next_incident: "अगला: घटना विवरण →",

    section_incident: "घटना की जानकारी",
    bns_warn: "शिकायत में झूठी जानकारी देना BNS धारा 211 के तहत अपराध है। कृपया घटना का विवरण सच्चाई और सटीकता से दें।",
    incident_date_label: "घटना की तारीख",
    incident_location_label: "घटना स्थान / प्लेटफ़ॉर्म",
    incident_location_placeholder: "जैसे, WhatsApp, UPI ऐप, वेबसाइट URL",
    desc_label: "घटना का विवरण",
    desc_placeholder: "सटीक बताएं कि क्या हुआ: आपसे कैसे संपर्क किया गया, क्या कहा गया, कितना पैसा या डेटा शामिल था, आरोपी के नाम/नंबर/लिंक, और कोई अन्य प्रासंगिक विवरण।",
    min_chars_hint: "कम से कम 20 अक्षर आवश्यक",
    back_btn: "← वापस",
    next_upload: "अगला: साक्ष्य अपलोड करें →",

    section_evidence: "साक्ष्य अपलोड",
    evidence_notice: "स्क्रीनशॉट, PDF, लेनदेन रिकॉर्ड, बातचीत निर्यात, या कोई अन्य डिजिटल साक्ष्य अपलोड करें। सभी फ़ाइलों को कानूनी चेन-ऑफ़-कस्टडी के लिए SHA-256 से हैश किया जाता है।",
    dropzone_title: "फ़ाइलें यहाँ खींचें या चुनने के लिए क्लिक करें",
    dropzone_sub: "स्वीकृत: JPG, PNG, PDF, TXT — अधिकतम 25 MB प्रति फ़ाइल",
    next_review: "अगला: समीक्षा →",

    section_review: "शिकायत की समीक्षा और सबमिट करें",
    review_notice: "सबमिट करने से पहले सभी विवरणों की सावधानीपूर्वक समीक्षा करें। सबमिट होने के बाद, शिकायत का हमारी AI प्रणाली द्वारा विश्लेषण किया जाएगा और एक जांच अधिकारी को सौंपा जाएगा।",
    declaration: "इस शिकायत को सबमिट करके, मैं घोषणा करता/करती हूँ कि प्रदान की गई जानकारी मेरी जानकारी के अनुसार सत्य है। मैं समझता/समझती हूँ कि झूठी शिकायत दर्ज करना एक दंडनीय अपराध है।",
    submit_btn: "शिकायत दर्ज करें",

    result_registered: "शिकायत दर्ज की गई",
    risk_classification: "जोखिम वर्गीकरण",
    crime_category_label: "अपराध श्रेणी",
    complaint_report_label: "शिकायत रिपोर्ट",
    auth_score_label: "प्रामाणिकता स्कोर",
    ai_summary_label: "AI केस सारांश",
    integrity_hash_label: "सामग्री अखंडता हैश (SHA-256)",
    download_fir: "शिकायत रिपोर्ट डाउनलोड करें (PDF)",
    track_this_case: "इस केस को ट्रैक करें",
    file_another: "दूसरी शिकायत दर्ज करें",

    footer_portal: "ऑटोजस्टिस AI नेक्सस — राष्ट्रीय साइबर अपराध शिकायत प्रबंधन प्रणाली",

    risk_high: "उच्च जोखिम",
    risk_medium: "मध्यम जोखिम",
    risk_low: "कम जोखिम",

    err_email_required: "कृपया अपना ईमेल पता दर्ज करें।",
    err_email_invalid: "कृपया एक मान्य ईमेल पता दर्ज करें।",
    err_name_required: "कृपया अपना पूरा नाम दर्ज करें।",
    err_desc_short: "कृपया घटना का विवरण दें (न्यूनतम 20 अक्षर)।",
    err_otp_required: "कृपया OTP दर्ज करें।",
  },

  // ── Tamil ─────────────────────────────────────────────────────────────────
  ta: {
    lang_name: "தமிழ்",
    page_title: "இணைய குற்ற புகாரை தாக்கல் செய்யுங்கள்",
    track_case_nav: "வழக்கை கண்காணி",
    officer_login: "அதிகாரி உள்நுழை",
    ministry: "உள்துறை அமைச்சகம், இந்திய அரசு",
    portal_name: "ஆட்டோஜஸ்டிஸ் AI நெக்ஸஸ்",
    portal_tagline: "தேசிய இணைய குற்ற புகார் மேலாண்மை அமைப்பு",
    emergency_label: "அவசரமா?",
    emergency_msg: "உடனடியாக 112 ஐ அழைக்கவும். இந்த தளம் அவசரமற்ற இணையக் குற்ற புகார்களை மட்டுமே ஏற்கிறது.",
    hl_cyber_fraud: "இணைய மோசடி உதவி",
    hl_emergency: "அவசரம்",
    hl_police: "காவல்துறை",
    hl_women: "பெண்கள் உதவி",
    file_complaint_heading: "இணைய குற்ற புகாரை தாக்கல் செய்யுங்கள்",
    file_complaint_sub: "புகாரைத் தாக்கல் செய்து புகார் குறிப்பு எண்ணைப் பெற அனைத்து படிகளையும் முடிக்கவும்",
    stat_total: "தாக்கல் செய்யப்பட்ட புகார்கள்",
    stat_firs: "உருவாக்கப்பட்ட அறிக்கைகள்",
    stat_today: "இன்று தாக்கல் செய்யப்பட்டது",
    stat_fake: "கண்டறியப்பட்ட பொய்யான புகார்கள்",
    email_verified: "மின்னஞ்சல் சரிபார்க்கப்பட்டது",
    step_your_details: "உங்கள் விவரங்கள்",
    step_incident: "சம்பவ விவரங்கள்",
    step_evidence: "சான்றுகள் பதிவேற்றம்",
    step_review: "மதிப்பாய்வு மற்றும் சமர்ப்பிப்பு",
    section_email_verify: "மின்னஞ்சல் சரிபார்ப்பு — தாக்கல் செய்வதற்கு முன் உங்கள் அடையாளத்தை சரிபார்க்கவும்",
    email_label: "மின்னஞ்சல் முகவரி",
    email_placeholder: "உங்கள் மின்னஞ்சல் முகவரியை உள்ளிடவும்",
    send_otp_btn: "OTP அனுப்பு",
    enter_otp_label: "6-இலக்க OTP ஐ உள்ளிடவும்",
    verify_otp_btn: "OTP சரிபார்க்கவும்",
    resend_otp_btn: "OTP மீண்டும் அனுப்பு",
    change_email_btn: "மின்னஞ்சலை மாற்று",
    section_complainant: "புகார்தாரர் விவரங்கள்",
    full_name: "முழு பெயர்",
    mobile_label: "மொபைல் எண்",
    address_label: "குடியிருப்பு முகவரி",
    next_incident: "அடுத்தது: சம்பவ விவரங்கள் →",
    section_incident: "சம்பவ தகவல்",
    incident_date_label: "சம்பவத் தேதி",
    incident_location_label: "சம்பவ இடம் / தளம்",
    desc_label: "சம்பவ விளக்கம்",
    back_btn: "← பின்",
    next_upload: "அடுத்தது: சான்றுகள் பதிவேற்றம் →",
    section_evidence: "சான்று பதிவேற்றம்",
    dropzone_title: "கோப்புகளை இங்கே இழுக்கவும் அல்லது தேர்ந்தெடுக்க கிளிக் செய்யவும்",
    next_review: "அடுத்தது: மதிப்பாய்வு →",
    section_review: "புகாரை மதிப்பாய்வு செய்து சமர்ப்பிக்கவும்",
    submit_btn: "புகாரைத் தாக்கல் செய்",
    result_registered: "புகார் பதிவு செய்யப்பட்டது",
    risk_classification: "ஆபத்து வகைப்பாடு",
    crime_category_label: "குற்ற வகை",
    complaint_report_label: "புகார் அறிக்கை",
    auth_score_label: "நம்பகத்தன்மை மதிப்பெண்",
    ai_summary_label: "AI வழக்கு சுருக்கம்",
    download_fir: "புகார் அறிக்கையைப் பதிவிறக்கு (PDF)",
    track_this_case: "இந்த வழக்கை கண்காணி",
    file_another: "மற்றொரு புகாரை தாக்கல் செய்",
    footer_portal: "ஆட்டோஜஸ்டிஸ் AI நெக்ஸஸ் — தேசிய இணைய குற்ற புகார் மேலாண்மை அமைப்பு",
    risk_high: "உயர் ஆபத்து",
    risk_medium: "நடுத்தர ஆபத்து",
    risk_low: "குறைந்த ஆபத்து",
  },

  // ── Telugu ────────────────────────────────────────────────────────────────
  te: {
    lang_name: "తెలుగు",
    page_title: "సైబర్ నేర ఫిర్యాదు నమోదు చేయండి",
    track_case_nav: "కేసు ట్రాక్ చేయండి",
    officer_login: "అధికారి లాగిన్",
    ministry: "హోం మంత్రిత్వ శాఖ, భారత ప్రభుత్వం",
    portal_name: "ఆటోజస్టిస్ AI నెక్సస్",
    portal_tagline: "జాతీయ సైబర్ నేర ఫిర్యాదు నిర్వహణ వ్యవస్థ",
    emergency_label: "అత్యవసరమా?",
    emergency_msg: "వెంటనే 112 కి కాల్ చేయండి. ఈ పోర్టల్ అత్యవసరం కాని సైబర్ నేర ఫిర్యాదులను మాత్రమే అంగీకరిస్తుంది.",
    hl_cyber_fraud: "సైబర్ మోసం హెల్ప్‌లైన్",
    hl_emergency: "అత్యవసరం",
    hl_police: "పోలీసు",
    hl_women: "మహిళల హెల్ప్‌లైన్",
    file_complaint_heading: "సైబర్ నేర ఫిర్యాదు నమోదు చేయండి",
    file_complaint_sub: "మీ ఫిర్యాదును సమర్పించి ఫిర్యాదు రిఫరెన్స్ నంబర్ పొందడానికి అన్ని దశలను పూర్తి చేయండి",
    stat_total: "నమోదైన ఫిర్యాదులు",
    stat_firs: "రూపొందించిన నివేదికలు",
    stat_today: "నేడు నమోదైనవి",
    stat_fake: "గుర్తించిన తప్పుడు ఫిర్యాదులు",
    email_verified: "ఇమెయిల్ ధృవీకరించబడింది",
    step_your_details: "మీ వివరాలు",
    step_incident: "సంఘటన వివరాలు",
    step_evidence: "సాక్ష్యం అప్‌లోడ్",
    step_review: "సమీక్షించి సమర్పించండి",
    section_email_verify: "ఇమెయిల్ ధృవీకరణ — నమోదు చేయడానికి ముందు మీ గుర్తింపును ధృవీకరించండి",
    email_label: "ఇమెయిల్ చిరునామా",
    email_placeholder: "మీ ఇమెయిల్ చిరునామాను నమోదు చేయండి",
    send_otp_btn: "OTP పంపండి",
    enter_otp_label: "6-అంకెల OTP నమోదు చేయండి",
    verify_otp_btn: "OTP ధృవీకరించండి",
    resend_otp_btn: "OTP మళ్ళీ పంపండి",
    change_email_btn: "ఇమెయిల్ మార్చండి",
    section_complainant: "ఫిర్యాదుదారు వివరాలు",
    full_name: "పూర్తి పేరు",
    mobile_label: "మొబైల్ నంబర్",
    address_label: "నివాస చిరునామా",
    next_incident: "తదుపరి: సంఘటన వివరాలు →",
    section_incident: "సంఘటన సమాచారం",
    incident_date_label: "సంఘటన తేదీ",
    incident_location_label: "సంఘటన స్థలం / ప్లాట్‌ఫారమ్",
    desc_label: "సంఘటన వివరణ",
    back_btn: "← వెనుకకు",
    next_upload: "తదుపరి: సాక్ష్యం అప్‌లోడ్ →",
    section_evidence: "సాక్ష్యం అప్‌లోడ్",
    dropzone_title: "ఫైల్‌లను ఇక్కడ లాగండి లేదా ఎంచుకోవడానికి క్లిక్ చేయండి",
    next_review: "తదుపరి: సమీక్ష →",
    section_review: "ఫిర్యాదును సమీక్షించి సమర్పించండి",
    submit_btn: "ఫిర్యాదు సమర్పించండి",
    result_registered: "ఫిర్యాదు నమోదు చేయబడింది",
    risk_classification: "ప్రమాద వర్గీకరణ",
    crime_category_label: "నేర వర్గం",
    complaint_report_label: "ఫిర్యాదు నివేదిక",
    auth_score_label: "ప్రామాణికత స్కోర్",
    ai_summary_label: "AI కేసు సారాంశం",
    download_fir: "ఫిర్యాదు నివేదిక డౌన్‌లోడ్ (PDF)",
    track_this_case: "ఈ కేసును ట్రాక్ చేయండి",
    file_another: "మరొక ఫిర్యాదు నమోదు చేయండి",
    footer_portal: "ఆటోజస్టిస్ AI నెక్సస్ — జాతీయ సైబర్ నేర ఫిర్యాదు నిర్వహణ వ్యవస్థ",
    risk_high: "అధిక ప్రమాదం",
    risk_medium: "మధ్యమ ప్రమాదం",
    risk_low: "తక్కువ ప్రమాదం",
  },

  // ── Bengali ───────────────────────────────────────────────────────────────
  bn: {
    lang_name: "বাংলা",
    page_title: "সাইবার অপরাধ অভিযোগ দাখিল করুন",
    track_case_nav: "মামলা ট্র্যাক করুন",
    officer_login: "কর্মকর্তা লগইন",
    ministry: "স্বরাষ্ট্র মন্ত্রণালয়, ভারত সরকার",
    portal_name: "অটোজাস্টিস AI নেক্সাস",
    portal_tagline: "জাতীয় সাইবার অপরাধ অভিযোগ ব্যবস্থাপনা সিস্টেম",
    emergency_label: "জরুরি?",
    emergency_msg: "অবিলম্বে 112 ডায়াল করুন। এই পোর্টাল শুধুমাত্র অ-জরুরি সাইবার অপরাধ অভিযোগ গ্রহণ করে।",
    hl_cyber_fraud: "সাইবার জালিয়াতি হেল্পলাইন",
    hl_emergency: "জরুরি",
    hl_police: "পুলিশ",
    hl_women: "মহিলা হেল্পলাইন",
    file_complaint_heading: "সাইবার অপরাধ অভিযোগ দাখিল করুন",
    file_complaint_sub: "আপনার অভিযোগ জমা দিতে এবং অভিযোগ রেফারেন্স নম্বর পেতে সমস্ত ধাপ সম্পূর্ণ করুন",
    stat_total: "দাখিলকৃত অভিযোগ",
    stat_firs: "প্রস্তুত রিপোর্ট",
    stat_today: "আজ দাখিল",
    stat_fake: "সনাক্তকৃত মিথ্যা অভিযোগ",
    email_verified: "ইমেইল যাচাইকৃত",
    step_your_details: "আপনার বিবরণ",
    step_incident: "ঘটনার বিবরণ",
    step_evidence: "প্রমাণ আপলোড",
    step_review: "পর্যালোচনা ও জমা",
    section_email_verify: "ইমেইল যাচাইকরণ — দাখিল করার আগে আপনার পরিচয় যাচাই করুন",
    email_label: "ইমেইল ঠিকানা",
    email_placeholder: "আপনার ইমেইল ঠিকানা লিখুন",
    send_otp_btn: "OTP পাঠান",
    enter_otp_label: "6-সংখ্যার OTP লিখুন",
    verify_otp_btn: "OTP যাচাই করুন",
    resend_otp_btn: "OTP আবার পাঠান",
    change_email_btn: "ইমেইল পরিবর্তন করুন",
    section_complainant: "অভিযোগকারীর বিবরণ",
    full_name: "পূর্ণ নাম",
    mobile_label: "মোবাইল নম্বর",
    address_label: "আবাসিক ঠিকানা",
    next_incident: "পরবর্তী: ঘটনার বিবরণ →",
    section_incident: "ঘটনার তথ্য",
    incident_date_label: "ঘটনার তারিখ",
    incident_location_label: "ঘটনার স্থান / প্ল্যাটফর্ম",
    desc_label: "ঘটনার বিবরণ",
    back_btn: "← পেছনে",
    next_upload: "পরবর্তী: প্রমাণ আপলোড →",
    section_evidence: "প্রমাণ আপলোড",
    dropzone_title: "ফাইল এখানে টেনে আনুন বা নির্বাচন করতে ক্লিক করুন",
    next_review: "পরবর্তী: পর্যালোচনা →",
    section_review: "অভিযোগ পর্যালোচনা ও জমা দিন",
    submit_btn: "অভিযোগ দাখিল করুন",
    result_registered: "অভিযোগ নিবন্ধিত",
    risk_classification: "ঝুঁকি শ্রেণীবিভাগ",
    crime_category_label: "অপরাধ বিভাগ",
    complaint_report_label: "অভিযোগ রিপোর্ট",
    auth_score_label: "সত্যতা স্কোর",
    ai_summary_label: "AI মামলা সারাংশ",
    download_fir: "অভিযোগ রিপোর্ট ডাউনলোড (PDF)",
    track_this_case: "এই মামলা ট্র্যাক করুন",
    file_another: "আরেকটি অভিযোগ দাখিল করুন",
    footer_portal: "অটোজাস্টিস AI নেক্সাস — জাতীয় সাইবার অপরাধ অভিযোগ ব্যবস্থাপনা সিস্টেম",
    risk_high: "উচ্চ ঝুঁকি",
    risk_medium: "মাঝারি ঝুঁকি",
    risk_low: "কম ঝুঁকি",
  },

  // ── Kannada ───────────────────────────────────────────────────────────────
  kn: {
    lang_name: "ಕನ್ನಡ",
    page_title: "ಸೈಬರ್ ಅಪರಾಧ ದೂರು ಸಲ್ಲಿಸಿ",
    track_case_nav: "ಪ್ರಕರಣ ಟ್ರ್ಯಾಕ್ ಮಾಡಿ",
    officer_login: "ಅಧಿಕಾರಿ ಲಾಗಿನ್",
    ministry: "ಗೃಹ ಸಚಿವಾಲಯ, ಭಾರತ ಸರ್ಕಾರ",
    portal_name: "ಆಟೋಜಸ್ಟಿಸ್ AI ನೆಕ್ಸಸ್",
    portal_tagline: "ರಾಷ್ಟ್ರೀಯ ಸೈಬರ್ ಅಪರಾಧ ದೂರು ನಿರ್ವಹಣಾ ವ್ಯವಸ್ಥೆ",
    emergency_label: "ತುರ್ತು?",
    emergency_msg: "ತಕ್ಷಣ 112 ಕ್ಕೆ ಕರೆ ಮಾಡಿ. ಈ ಪೋರ್ಟಲ್ ತುರ್ತು-ಅಲ್ಲದ ಸೈಬರ್ ಅಪರಾಧ ದೂರುಗಳನ್ನು ಮಾತ್ರ ಸ್ವೀಕರಿಸುತ್ತದೆ.",
    hl_cyber_fraud: "ಸೈಬರ್ ವಂಚನೆ ಸಹಾಯವಾಣಿ",
    hl_emergency: "ತುರ್ತು",
    hl_police: "ಪೊಲೀಸ್",
    hl_women: "ಮಹಿಳಾ ಸಹಾಯವಾಣಿ",
    file_complaint_heading: "ಸೈಬರ್ ಅಪರಾಧ ದೂರು ಸಲ್ಲಿಸಿ",
    file_complaint_sub: "ನಿಮ್ಮ ದೂರು ಸಲ್ಲಿಸಲು ಮತ್ತು ದೂರು ಉಲ್ಲೇಖ ಸಂಖ್ಯೆಯನ್ನು ಪಡೆಯಲು ಎಲ್ಲಾ ಹಂತಗಳನ್ನು ಪೂರ್ಣಗೊಳಿಸಿ",
    stat_total: "ಸಲ್ಲಿಸಿದ ದೂರುಗಳು",
    stat_firs: "ರಚಿಸಿದ ವರದಿಗಳು",
    stat_today: "ಇಂದು ಸಲ್ಲಿಸಿದ್ದು",
    stat_fake: "ಪತ್ತೆಹಚ್ಚಿದ ಸುಳ್ಳು ದೂರುಗಳು",
    email_verified: "ಇಮೇಲ್ ಪರಿಶೀಲಿಸಲಾಗಿದೆ",
    step_your_details: "ನಿಮ್ಮ ವಿವರಗಳು",
    step_incident: "ಘಟನೆ ವಿವರಗಳು",
    step_evidence: "ಸಾಕ್ಷ್ಯ ಅಪ್‌ಲೋಡ್",
    step_review: "ಪರಿಶೀಲಿಸಿ ಮತ್ತು ಸಲ್ಲಿಸಿ",
    section_email_verify: "ಇಮೇಲ್ ಪರಿಶೀಲನೆ — ಸಲ್ಲಿಸುವ ಮೊದಲು ನಿಮ್ಮ ಗುರುತನ್ನು ಪರಿಶೀಲಿಸಿ",
    email_label: "ಇಮೇಲ್ ವಿಳಾಸ",
    email_placeholder: "ನಿಮ್ಮ ಇಮೇಲ್ ವಿಳಾಸ ನಮೂದಿಸಿ",
    send_otp_btn: "OTP ಕಳುಹಿಸಿ",
    enter_otp_label: "6-ಅಂಕಿಯ OTP ನಮೂದಿಸಿ",
    verify_otp_btn: "OTP ಪರಿಶೀಲಿಸಿ",
    resend_otp_btn: "OTP ಮತ್ತೆ ಕಳುಹಿಸಿ",
    change_email_btn: "ಇಮೇಲ್ ಬದಲಾಯಿಸಿ",
    section_complainant: "ದೂರುದಾರರ ವಿವರಗಳು",
    full_name: "ಪೂರ್ಣ ಹೆಸರು",
    mobile_label: "ಮೊಬೈಲ್ ಸಂಖ್ಯೆ",
    address_label: "ವಸತಿ ವಿಳಾಸ",
    next_incident: "ಮುಂದೆ: ಘಟನೆ ವಿವರಗಳು →",
    section_incident: "ಘಟನೆ ಮಾಹಿತಿ",
    incident_date_label: "ಘಟನೆಯ ದಿನಾಂಕ",
    incident_location_label: "ಘಟನೆ ಸ್ಥಳ / ಪ್ಲಾಟ್‌ಫಾರ್ಮ್",
    desc_label: "ಘಟನೆಯ ವಿವರಣೆ",
    back_btn: "← ಹಿಂದೆ",
    next_upload: "ಮುಂದೆ: ಸಾಕ್ಷ್ಯ ಅಪ್‌ಲೋಡ್ →",
    section_evidence: "ಸಾಕ್ಷ್ಯ ಅಪ್‌ಲೋಡ್",
    dropzone_title: "ಫೈಲ್‌ಗಳನ್ನು ಇಲ್ಲಿ ಎಳೆಯಿರಿ ಅಥವಾ ಆಯ್ಕೆ ಮಾಡಲು ಕ್ಲಿಕ್ ಮಾಡಿ",
    next_review: "ಮುಂದೆ: ಪರಿಶೀಲನೆ →",
    section_review: "ದೂರು ಪರಿಶೀಲಿಸಿ ಮತ್ತು ಸಲ್ಲಿಸಿ",
    submit_btn: "ದೂರು ಸಲ್ಲಿಸಿ",
    result_registered: "ದೂರು ನೋಂದಾಯಿಸಲಾಗಿದೆ",
    risk_classification: "ಅಪಾಯ ವರ್ಗೀಕರಣ",
    crime_category_label: "ಅಪರಾಧ ವರ್ಗ",
    complaint_report_label: "ದೂರು ವರದಿ",
    auth_score_label: "ಪ್ರಾಮಾಣಿಕತೆ ಸ್ಕೋರ್",
    ai_summary_label: "AI ಪ್ರಕರಣ ಸಾರಾಂಶ",
    download_fir: "ದೂರು ವರದಿ ಡೌನ್‌ಲೋಡ್ (PDF)",
    track_this_case: "ಈ ಪ್ರಕರಣವನ್ನು ಟ್ರ್ಯಾಕ್ ಮಾಡಿ",
    file_another: "ಮತ್ತೊಂದು ದೂರು ಸಲ್ಲಿಸಿ",
    footer_portal: "ಆಟೋಜಸ್ಟಿಸ್ AI ನೆಕ್ಸಸ್ — ರಾಷ್ಟ್ರೀಯ ಸೈಬರ್ ಅಪರಾಧ ದೂರು ನಿರ್ವಹಣಾ ವ್ಯವಸ್ಥೆ",
    risk_high: "ಹೆಚ್ಚಿನ ಅಪಾಯ",
    risk_medium: "ಮಧ್ಯಮ ಅಪಾಯ",
    risk_low: "ಕಡಿಮೆ ಅಪಾಯ",
  },
};

// ── Language Manager ────────────────────────────────────────────────────────

const SUPPORTED_LANGS = Object.keys(TRANSLATIONS);
const LANG_KEY        = 'aj_lang';

let _currentLang = 'en';

/**
 * Get a translated string by key.
 * Falls back to English if key not found in current language.
 */
export function t(key) {
  const lang = TRANSLATIONS[_currentLang] || TRANSLATIONS['en'];
  return lang[key] || TRANSLATIONS['en'][key] || key;
}

/** Return current language code. */
export function getLang() { return _currentLang; }

/** Return all supported language codes. */
export function getSupportedLangs() {
  return SUPPORTED_LANGS.map(code => ({
    code,
    name: TRANSLATIONS[code].lang_name,
  }));
}

/**
 * Switch language and re-render all i18n-annotated elements.
 * Persists selection to localStorage.
 */
export function setLang(langCode) {
  if (!SUPPORTED_LANGS.includes(langCode)) {
    console.warn('[i18n] Unsupported language:', langCode);
    return;
  }
  _currentLang = langCode;
  try { localStorage.setItem(LANG_KEY, langCode); } catch (_) {}
  applyTranslations();
  document.documentElement.lang = langCode;
}

/**
 * Apply translations to all elements with [data-i18n="key"] attribute.
 * Also updates [data-i18n-placeholder] and [data-i18n-title] attributes.
 */
export function applyTranslations() {
  // Text content
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    const val = t(key);
    if (val && val !== key) el.textContent = val;
  });

  // Placeholder attributes
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    const val = t(key);
    if (val && val !== key) el.placeholder = val;
  });

  // Title / aria-label attributes
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    const key = el.getAttribute('data-i18n-title');
    const val = t(key);
    if (val && val !== key) el.title = val;
  });

  // [data-i18n-html] — allows inline HTML (e.g. <strong> inside a notice)
  document.querySelectorAll('[data-i18n-html]').forEach(el => {
    const key = el.getAttribute('data-i18n-html');
    const val = t(key);
    if (val && val !== key) el.innerHTML = val;
  });

  // Page title
  const pageTitle = t('page_title');
  if (pageTitle && pageTitle !== 'page_title') {
    document.title = `${pageTitle} — AutoJustice AI NEXUS`;
  }
}

/**
 * Initialise i18n from saved preference or browser language.
 * Call once on page load.
 */
export function initI18n() {
  let saved = null;
  try { saved = localStorage.getItem(LANG_KEY); } catch (_) {}

  if (saved && SUPPORTED_LANGS.includes(saved)) {
    _currentLang = saved;
  } else {
    const browserLang = (navigator.language || 'en').split('-')[0].toLowerCase();
    _currentLang = SUPPORTED_LANGS.includes(browserLang) ? browserLang : 'en';
  }

  applyTranslations();
  renderLanguageSwitcher();
  document.documentElement.lang = _currentLang;
}

/**
 * Render the language switcher dropdown in #lang-switcher container (if present).
 */
export function renderLanguageSwitcher() {
  const container = document.getElementById('lang-switcher');
  if (!container) return;

  const select = document.createElement('select');
  select.className   = 'lang-select';
  select.title       = 'Change Language / भाषा बदलें';
  select.setAttribute('aria-label', 'Language selector');

  getSupportedLangs().forEach(({ code, name }) => {
    const opt = document.createElement('option');
    opt.value    = code;
    opt.textContent = name;
    opt.selected = code === _currentLang;
    select.appendChild(opt);
  });

  select.addEventListener('change', (e) => setLang(e.target.value));

  container.innerHTML = '';
  container.appendChild(select);
}
