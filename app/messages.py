"""Textes fixes du chatbot dans les 4 langues. Aucun montant n'est jamais donné."""

CONTACT_LINE = "contact@estc.ma, 0522230494 / 0522231560, www.estc.ma"

T = {
 "greeting": {
  "fr": "Bonjour ! Je suis l'assistant de la filière MDO à l'ESTC. Posez-moi vos questions sur les absences, les modules, les professeurs, les démarches, les formations ou la vie étudiante.",
  "en": "Hello! I am the assistant of the MDO program at ESTC. Ask me about absences, modules, professors, administrative procedures, programs or student life.",
  "ar": "مرحباً! أنا مساعد شعبة MDO في المدرسة العليا للتكنولوجيا بالدار البيضاء. يمكنك سؤالي عن الغياب والمواد والأساتذة والإجراءات الإدارية والتكوينات والحياة الطلابية.",
  "darija": "السلام! أنا المساعد ديال شعبة MDO فـ ESTC. سولني على الغياب، المواد، الأساتذة، الوثائق، التكوينات ولا الحياة الطلابية.",
 },
 "thanks": {
  "fr": "Avec plaisir ! N'hésitez pas si vous avez d'autres questions sur l'ESTC ou la filière MDO.",
  "en": "You're welcome! Feel free to ask if you have other questions about ESTC or the MDO program.",
  "ar": "عفواً! لا تتردد في طرح أي سؤال آخر حول المدرسة أو شعبة MDO.",
  "darija": "بلا ميزة! إلا كانت عندك شي أسئلة أخرى على ESTC ولا MDO، سولني.",
 },
 "not_found": {
  "fr": "Je ne trouve pas cette information dans ma base de données, et je ne veux pas vous donner une réponse inexacte. Pour une réponse fiable, contactez l'administration : " + CONTACT_LINE + ", ou le Chef de Département / la Direction. Je suis dédié à l'ESTC et à la filière MDO (modules, absences, démarches, formations, vie étudiante).",
  "en": "I can't find this information in my database, and I don't want to give you an inaccurate answer. For a reliable answer, please contact the administration: " + CONTACT_LINE + ", or the Head of Department / the Direction. I am dedicated to ESTC and the MDO program (modules, absences, procedures, programs, student life).",
  "ar": "لا أجد هذه المعلومة في قاعدة بياناتي ولا أريد أن أعطيك جواباً غير دقيق. للحصول على جواب موثوق، تواصل مع الإدارة: " + CONTACT_LINE + "، أو رئيس القسم / الإدارة. أنا مخصص للمدرسة وشعبة MDO (المواد، الغياب، المساطر، التكوينات، الحياة الطلابية).",
  "darija": "هاد المعلومة ما لقيتهاش فقاعدة المعطيات ديالي، وما بغيتش نعطيك جواب غالط. باش تعرف بالضبط، تواصل مع الإدارة: " + CONTACT_LINE + "، ولا مع رئيس القسم / الإدارة. أنا مخصص غير لـ ESTC وشعبة MDO (المواد، الغياب، الوثائق، التكوينات، الحياة الطلابية).",
 },
 "price": {
  "fr": "Ma base de données ne contient aucun montant ni tarif, et je ne donne jamais de chiffre estimé ni le prix d'une autre école. Pour les frais liés à l'ESTC (inscription, formation continue, etc.), contactez l'administration : " + CONTACT_LINE + ".",
  "en": "My database contains no amounts or fees, and I never give estimated figures or the prices of other schools. For ESTC-related fees (registration, continuing education, etc.), please contact the administration: " + CONTACT_LINE + ".",
  "ar": "قاعدة بياناتي لا تحتوي على أي مبلغ أو تعرفة، ولا أعطي أبداً أرقاماً تقديرية أو أسعار مؤسسات أخرى. بخصوص المصاريف المرتبطة بالمدرسة (التسجيل، التكوين المستمر...)، تواصل مع الإدارة: " + CONTACT_LINE + ".",
  "darija": "قاعدة المعطيات ديالي ما فيهاش حتى مبلغ ولا ثمن، وعمري نعطي رقم تقريبي ولا ثمن مدرسة أخرى. على المصاريف ديال ESTC (التسجيل، التكوين المستمر...)، تواصل مع الإدارة: " + CONTACT_LINE + ".",
 },
 "rate_limit": {
  "fr": "Trop de questions en peu de temps. Patientez quelques secondes puis réessayez.",
  "en": "Too many questions in a short time. Please wait a few seconds and try again.",
  "ar": "عدد كبير من الأسئلة في وقت قصير. انتظر بضع ثوان ثم حاول مجدداً.",
  "darija": "بزاف د الأسئلة فوقت قصير. تسنى شي ثواني وعاود.",
 },
 "llm_down": {
  "fr": "Le service d'IA est momentanément indisponible. Voici les informations trouvées directement dans la base :",
  "en": "The AI service is temporarily unavailable. Here is what was found directly in the database (in French):",
  "ar": "خدمة الذكاء الاصطناعي غير متاحة مؤقتاً. هذه هي المعلومات الموجودة مباشرة في القاعدة (بالفرنسية):",
  "darija": "خدمة الذكاء الاصطناعي ما خدامّاش دابا. هادي المعلومات اللي لقيت مباشرة فالقاعدة (بالفرنسية):",
 },
 "demo_intro": {
  "fr": "Réponse extraite de la base (mode démo, sans IA) :",
  "en": "Answer extracted from the database (demo mode, no AI; text is in French):",
  "ar": "جواب مستخرج من القاعدة (وضع تجريبي بدون ذكاء اصطناعي؛ النص بالفرنسية):",
  "darija": "جواب مستخرج من القاعدة (وضع تجريبي بلا ذكاء اصطناعي؛ النص بالفرنسية):",
 },
}


def t(key: str, lang: str) -> str:
    return T[key].get(lang) or T[key]["fr"]


LANG_INSTRUCTION = {
 "fr": "Réponds en français.",
 "en": "Reply in English.",
 "ar": "أجب بالعربية الفصحى.",
 "darija": "Réponds en darija marocaine, avec la même écriture que l'étudiant (lettres arabes s'il écrit en arabe, lettres latines/arabizi s'il écrit en lettres latines).",
}

SYSTEM_PROMPT = """Tu es l'assistant officiel d'intégration des étudiants de 1re année de la filière MDO (Management Digital des Organisations) à l'ESTC Casablanca.

RÈGLES ABSOLUES :
1. Tu réponds UNIQUEMENT avec les informations du CONTEXTE ci-dessous (extraits de la base de données officielle). Tu n'inventes jamais une information (nom, date, prix, numéro, règle).
2. Si le CONTEXTE ne contient pas la réponse, dis-le clairement et oriente l'étudiant vers : contact@estc.ma, les téléphones 0522230494 / 0522231560, le site www.estc.ma, ou le Chef de Département / la Direction.
3. Tu restes dans le sujet : ESTC, filière MDO, vie scolaire, modules, démarches, formations. Pour tout autre sujet, explique poliment que tu es dédié à l'ESTC.
4. Prix et frais : la base ne contient aucun montant. Ne donne jamais de chiffre estimé ni le prix d'une autre école ; oriente vers l'administration.
5. Pour les règles importantes (absences, rattrapage, certificat médical), donne la règle exacte, sans l'adoucir ni l'interpréter.
6. Si un professeur n'est pas indiqué dans le CONTEXTE, dis que la base ne le précise pas. Ne devine jamais un nom.
7. Ton poli, clair et professionnel. Réponses courtes et structurées.
8. {lang_instruction}

CONTEXTE (base de données ESTC / MDO, version 3) :
{context}
"""

T["needs_ai"] = {
    "fr": "Cette demande (génération : QCM, résumé, plan, comparaison, exemple…) nécessite le mode IA, qui n'est pas activé. Voici les passages de la base utiles pour la traiter :",
    "en": "This request (generation: quiz, summary, plan, comparison, example...) requires AI mode, which is not enabled. Here are the relevant passages from the database (in French):",
    "ar": "هذا الطلب (توليد: أسئلة، ملخص، خطة، مقارنة، مثال...) يتطلب وضع الذكاء الاصطناعي غير المفعّل. إليك المقاطع المفيدة من القاعدة (بالفرنسية):",
    "darija": "هاد الطلب (QCM، ملخص، خطة، مقارنة، مثال...) خاصو الذكاء الاصطناعي اللي ما مفعّلش. هادي المقاطع المفيدة من القاعدة (بالفرنسية):",
}
