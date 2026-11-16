"""Alias multilingues -> mots-clés français de la base (expansion de requête).

La base est rédigée en français. Pour qu'une question en anglais, en arabe ou en darija
retrouve les bons passages, on ajoute à la requête les mots-clés français correspondants.
"""
import re
from .textutil import normalize

_RAW = [
 (["absence", "absences", "absent", "absente", "غياب", "غيابات", "ghyab", "ghiab", "gheyab", "absenteeism", "missing class"],
  "absence absences APTUS justification seuil 50% rattrapage"),
 (["certificat", "medical", "medicale", "شهاده طبيه", "الطبيه", "طبيه", "الطبي", "doctor note", "sick note", "sick", "malade", "maladie", "mrid", "tibia", "chahada tibia"],
  "certificat médical Chef de Département Mdarbi 72 heures APTUS"),
 (["rattrapage", "ratrapage", "rattrapaj", "ratrapaj", "retake", "resit", "makeup exam", "make-up exam", "استدراك", "الاستدراك", "الاستدراكي"],
  "rattrapage note plafonnée 10/20"),
 (["examen", "examens", "exam", "exams", "ds", "controle", "امتحان", "امتحانات", "اختبار", "imtihan", "test"],
  "examen DS dates d'examens tableau d'affichage"),
 (["emploi du temps", "timetable", "schedule", "planning", "جدول", "جدول الحصص", "استعمال الزمن", "edt", "salle", "salles"],
  "emploi du temps tableau d'affichage salles changements"),
 (["attestation", "scolarite", "شهاده مدرسيه", "شهاده التمدرس", "school certificate", "enrollment certificate", "proof of enrollment", "certificate of enrollment"],
  "attestation de scolarité Bureau de la Scolarité Direction documents officiels"),
 (["releve", "releves", "كشف النقط", "كشف النقاط", "النقط", "النقاط", "transcript", "grades", "marks", "reclamation", "reclamations", "complaint", "شكايه"],
  "relevé de notes Bureau de la Scolarité Direction réclamations"),
 (["horaire", "horaires", "ouverture", "opening hours", "opening", "office hours", "ساعات العمل", "ساعات عمل", "اوقات", "مواعيد", "الاوقات", "wakt", "waqt", "sa3at"],
  "horaires administration lundi vendredi 8h30 17h30"),
 (["adresse", "address", "localisation", "location", "situe", "where is", "عنوان", "العنوان", "موقع", "fin kayna", "فين كاينه", "فين كاين", "كاينه", "map", "maps", "itineraire", "comment venir", "jadida"],
  "adresse localisation Route d'El Jadida KM 7 Oasis Casablanca"),
 (["contact", "contacter", "telephone", "tel", "phone", "email", "mail", "call", "joindre", "numero", "اتصال", "هاتف", "رقم", "بريد", "الايميل"],
  "contact téléphone email contact@estc.ma 0522230494 0522231560"),
 (["site", "website", "site web", "instagram", "facebook", "actualite", "actualites", "news", "announcements", "annonces", "اخبار", "reseaux sociaux", "social media"],
  "site web www.estc.ma Instagram Facebook actualités annonces"),
 (["bibliotheque", "library", "biblio", "مكتبه", "المكتبه", "maktaba"], "bibliothèque carte d'étudiant"),
 (["buvette", "restauration", "cafeteria", "canteen", "restaurant", "cantine", "manger", "food", "eat", "كافيتيريا", "مطعم", "الاكل", "cafet", "kfeteria"],
  "buvette restauration campus"),
 (["stage", "stages", "internship", "intern", "تدريب", "التدريب", "convention de stage", "sfe", "stagiaire"],
  "stage initiation fin d'études SFE convention de stage service des stages scolarité"),
 (["dut", "formation", "formations", "filieres", "diplome", "degree"], "formation DUT filières durée 2 ans bac+2"),
 (["bachelor", "باشلور"], "Bachelor en Technologie S5 S6 dossier candidature"),
 (["licence", "license", "licence pro", "اجازه", "الاجازه"], "licence professionnelle 1 an bac+2 présélection"),
 (["master", "masters", "formation continue", "continuing education", "evening classes", "cours du soir", "ماستر", "التكوين المستمر"],
  "formation continue masters spécialisés cours du soir week-end"),
 (["inscription", "inscrire", "inscrit", "apply", "application", "candidature", "candidat", "enroll", "register", "registration", "ecandidature", "e-candidature", "تسجيل", "التسجيل", "ترشح", "tsjil", "preinscription"],
  "inscription en ligne portail e-candidature candidature présélection"),
 (["departement", "department", "chef", "head of department", "قسم", "رئيس القسم", "mdarbi", "ined"],
  "département chef de département INED Mdarbi"),
 (["professeur", "professeurs", "prof", "profs", "teacher", "teachers", "who teaches", "enseigne", "enseignant", "استاذ", "الاستاذ", "ostad", "oustad", "ustad"],
  "professeur module semestre"),
 (["module", "modules", "matiere", "matieres", "course", "courses", "subject", "subjects", "مادة", "مواد", "المواد", "mawad", "mada"],
  "module semestre professeur"),
 (["campus", "amphi", "amphis", "amphitheatre", "vie etudiante", "student life", "conference", "conferences", "evenement", "evenements", "event", "events"],
  "amphithéâtres salles de conférences événements vie étudiante"),
 (["direction", "directeur", "director", "administration", "admin", "الاداره", "الادارة", "idara"], "Direction Générale administration Bureau de la Scolarité"),
 (["carte", "student card", "بطاقه"], "carte d'étudiant bibliothèque"),
 (["ai", "artificial intelligence", "ذكاء اصطناعي", "الذكاء الاصطناعي"], "Intelligence Artificielle IA"),
 (["law", "legal", "droit", "قانون", "القانون"], "droit commercial droit social système juridique"),
 (["accounting", "compta", "محاسبه", "المحاسبه"], "comptabilité financière Atlas Compta"),
 (["english", "anglais", "انجليزيه", "الانجليزيه"], "Business English"),
 (["math", "maths", "mathematics", "رياضيات"], "mathématiques appliquées financières"),
 (["statistics", "statistique", "stats", "احصاء"], "statistique descriptive probabiliste"),
 (["hr", "human resources", "grh", "ressources humaines", "الموارد البشريه"], "gestion des ressources humaines GRH E-GRH"),
 (["ecommerce", "e-commerce", "commerce electronique", "digital marketing"], "E-Commerce Marketing Digital"),
 (["entrepreneurship", "business plan", "entrepreneuriat", "مقاوله"], "Entrepreneuriat Business Plan"),
 (["tax", "taxes", "fiscalite", "ضرائب"], "Fiscalité"),
 (["logistics", "logistique"], "E-logistique"),
 (["economics", "economie", "اقتصاد"], "Économie générale"),
 (["french", "francais", "فرنسيه"], "Français"),
 (["vat", "tva", "value added tax", "ضريبه", "الضريبه على القيمه المضافه"], "TVA taxe valeur ajoutée HT TTC taux"),
 (["balance sheet", "bilan", "الميزانيه"], "Bilan actif passif patrimoine"),
 (["income statement", "profit and loss", "cpc", "compte de resultat"], "CPC compte de produits et charges résultat net"),
 (["depreciation", "amortissement", "amortissements", "الاهتلاك"], "amortissement linéaire dégressif annuité VNA"),
 (["provision", "provisions"], "provisions dotation reprise prudence"),
 (["mean", "average", "median", "moyenne", "mediane"], "moyenne médiane mode statistique descriptive"),
 (["standard deviation", "ecart type", "ecart-type", "variance"], "variance écart-type dispersion coefficient de variation"),
 (["probability", "probabilite", "probabilites", "احتمال", "احتمالات"], "probabilité conditionnelle Bayes loi"),
 (["binomial", "binomiale", "poisson", "normal distribution", "loi normale"], "loi binomiale Poisson normale"),
 (["supply and demand", "offre et demande", "market equilibrium", "العرض والطلب"], "marché offre demande équilibre prix"),
 (["employment contract", "work contract", "contrat de travail", "عقد الشغل"], "contrat de travail CDI CDD période d'essai"),
 (["probation", "trial period", "periode d'essai", "فتره التجربه"], "période d'essai cadres employés ouvriers"),
 (["dismissal", "fired", "licenciement", "resignation", "demission", "الطرد"], "licenciement démission préavis rupture"),
 (["limited liability", "sarl", "snc", "societe", "company types", "الشركات"], "SARL SA SNC société capital minimum associés"),
 (["separation of powers", "separation des pouvoirs", "decentralization", "decentralisation", "فصل السلط", "اللامركزيه"], "séparation des pouvoirs législatif exécutif judiciaire décentralisation"),
 (["swot", "pestel", "marketing mix", "4p", "segmentation"], "SWOT PESTEL SCP segmentation ciblage positionnement 4P"),
 (["sql", "database", "merise", "mcd", "mld", "erp", "base de donnees", "قاعده البيانات"], "SQL MERISE MCD MLD base de données ERP"),
 (["excel", "formula", "formule", "vlookup", "recherchev"], "Excel formule SOMME SI RECHERCHEV référence"),
 (["management", "fayol", "taylor", "weber", "mayo", "maslow", "podc"], "management PODC Fayol Taylor Weber Mayo Maslow"),
 (["herzberg", "recruitment", "recrutement", "gpec", "motivation"], "recrutement GPEC formation évaluation rémunération Herzberg"),
 (["cv", "cover letter", "lettre de motivation", "email professionnel", "professional email", "compte rendu", "note de service"], "e-mail professionnel CV lettre de motivation compte rendu note de service"),
 (["aida", "note de synthese", "argumentation"], "CAP AIDA STAR note de synthèse argumentation connecteurs"),
 (["keynes", "adam smith", "marx", "ricardo", "classical economics"], "classiques Smith Ricardo Marx Keynes courants de pensée"),
 (["compound interest", "simple interest", "interets composes", "interets simples", "annuity", "annuites", "escompte", "discount"], "intérêts simples composés escompte annuités valeur acquise"),

]

_ALIASES = [([normalize(t) for t in triggers], exp) for triggers, exp in _RAW]


def _hit(trigger: str, text: str) -> bool:
    if re.search(r"[a-z]", trigger):
        return re.search(r"(?<!\w)" + re.escape(trigger) + r"(?!\w)", text) is not None
    return trigger in text


def expansions(query: str) -> str:
    q = normalize(query)
    out = []
    for triggers, exp in _ALIASES:
        if any(_hit(t, q) for t in triggers):
            out.append(exp)
    return " ".join(out)


_PRICE_RE = re.compile(
    r"(?<!\w)(prix|tarif|tarifs|frais|montant|montants|combien|payer|paiement|payant|gratuit|tuition|fee|fees|price|prices|pricing|how much|"
    r"coute|coutent|cout d|"
    r"ثمن|سعر|اسعار|تكلفه|مصاريف|رسوم|بشحال|bchhal|taman|tmn|tmen|flous|فلوس|الثمن)(?!\w)"
)


def is_price_question(query: str) -> bool:
    return _PRICE_RE.search(normalize(query)) is not None


_GREET = re.compile(r"^(bonjour|bonsoir|salut|coucou|hello|hi|hey|salam|salam alaykum|assalam|slm|سلام|السلام عليكم|مرحبا|اهلا|صباح الخير|مساء الخير|labas|lbas)\W*$")
_THANKS = re.compile(r"^(merci|merci beaucoup|thanks|thank you|thx|chokran|shukran|choukran|شكرا|شكرا جزيلا|barakallah|بارك الله فيك)\W*$")


def small_talk(query: str):
    q = normalize(query).strip()
    if _GREET.match(q):
        return "greeting"
    if _THANKS.match(q):
        return "thanks"
    return None
