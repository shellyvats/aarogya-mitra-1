from flask import Flask, render_template, request, jsonify
from bot import HealthBot
from db import init_db, search_facilities, get_all_schemes, get_emergency_contacts
import logging, sqlite3, os, re, sys
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "aarogya_mitra_secret_2024"

init_db()
bot = HealthBot()

classifier = None
try:
    sys.path.insert(0, os.path.dirname(__file__))
    from ml.symptom_classifier import SymptomClassifier
    classifier = SymptomClassifier()
except Exception as e:
    logger.warning(f"ML not available: {e}")

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "health.db")

KNOWN_DISTRICTS = [
    "agra","lucknow","varanasi","kanpur","gorakhpur","meerut","mathura","aligarh",
    "patna","gaya","muzaffarpur","bhagalpur","darbhanga",
    "jaipur","jodhpur","udaipur","kota","ajmer","bikaner","alwar",
    "bhopal","indore","gwalior","jabalpur","ujjain",
    "pune","mumbai","nashik","nagpur","aurangabad","solapur",
    "chennai","madurai","coimbatore","trichy","salem","vellore",
    "bengaluru","bangalore","mysuru","mysore","hubballi","mangaluru","belagavi",
    "ahmedabad","surat","vadodara","rajkot","junagadh","bhavnagar",
    "kolkata","howrah","darjeeling","malda",
    "bhubaneswar","cuttack","sambalpur",
    "visakhapatnam","vizag","vijayawada","guntur","tirupati",
    "hyderabad","warangal","nizamabad",
    "thiruvananthapuram","trivandrum","kochi","kozhikode","thrissur",
    "gurugram","gurgaon","faridabad","ambala","rohtak","hisar",
    "amritsar","ludhiana","patiala","jalandhar",
    "shimla","dehradun","haridwar","nainital",
    "ranchi","dhanbad","jamshedpur",
    "guwahati","raipur","bilaspur",
    "delhi","new delhi",
]

REMEDIES = {
    "fever": {
        "title": "Fever — Bukhar",
        "ayurvedic": [
            "🌿 Tulsi Kadha — Boil 10 tulsi leaves + ginger + black pepper in 2 cups water. Drink warm twice daily.",
            "🌿 Giloy (Amruta) — Boil giloy stem in water and drink. Highly effective for viral fever.",
            "🌿 Neem leaves — Boil neem leaves, use water to sponge body. Reduces temperature naturally.",
            "🌿 Turmeric milk — 1 tsp haldi in warm milk at night. Fights infection from inside.",
            "🌿 Dry ginger (Sonth) — Mix sonth powder with honey. Take twice daily.",
        ],
        "home": [
            "💧 Stay very hydrated — water, coconut water, nimbu pani, ORS every 30 minutes.",
            "🧊 Cold compress — Wet cloth on forehead, armpits, wrists to reduce temperature.",
            "🍋 Lemon water with honey — Vitamin C boosts immunity.",
            "🧅 Onion on feet — Place onion slices on feet under socks overnight. Traditional remedy.",
            "🍚 Light food only — Rice kanji, dal khichdi, moong soup. No heavy oily food.",
            "😴 Rest completely — Do not exert yourself. Stay in cool room.",
        ],
        "warning": "⚠️ Visit PHC if fever exceeds 103°F or lasts more than 3 days."
    },
    "cough": {
        "title": "Cough — Khansi",
        "ayurvedic": [
            "🌿 Tulsi-Ginger-Honey Kadha — Boil tulsi, ginger, black pepper. Add honey when warm. Drink 3 times daily.",
            "🌿 Mulethi (Licorice) — Chew mulethi stick or boil in water. Soothes throat instantly.",
            "🌿 Pippali with honey — Long pepper powder + honey. For dry cough and congestion.",
            "🌿 Sitopaladi Churna — Classical Ayurvedic powder for cough. Available at medical stores.",
            "🌿 Vasa leaves — Adhatoda leaf juice with honey. Clears mucus from chest.",
        ],
        "home": [
            "🍯 Honey + ginger juice — 1 tsp ginger juice + 1 tsp honey. Take 3-4 times a day.",
            "🧂 Salt water gargle — Warm salt water gargle 3-4 times daily for throat relief.",
            "🌶️ Haldi-Doodh — Turmeric milk at night. Anti-inflammatory for airways.",
            "💨 Steam inhalation — Eucalyptus oil in hot water. Inhale for 10 minutes.",
            "🍋 Warm lemon water — Clears mucus and soothes throat.",
            "🚫 Avoid cold drinks, ice cream, sour food during cough.",
        ],
        "warning": "⚠️ Cough lasting more than 2 weeks with blood or weight loss — visit PHC immediately for TB test."
    },
    "cold": {
        "title": "Common Cold — Sardi Zukam",
        "ayurvedic": [
            "🌿 Nasya with sesame oil — 2 drops warm sesame oil in each nostril morning and night.",
            "🌿 Trikatu (Ginger + Pepper + Pippali) — Mix powders with honey for blocked nose.",
            "🌿 Tulsi steam — Add tulsi leaves to hot water for steam. Clears nasal congestion.",
            "🌿 Chyawanprash — 1-2 tsp daily. Classic immunity booster. Take with warm milk.",
        ],
        "home": [
            "💧 Warm fluids all day — warm water, soups, ginger tea, herbal kadha.",
            "🧄 Raw garlic — 2-3 raw garlic cloves daily. Natural antiviral.",
            "💨 Nasal saline rinse — Salt water in each nostril to clear congestion.",
            "🛌 Sleep 8 hours — Immunity is built during sleep.",
            "🌡️ Stay warm — Wear warm clothes, avoid cold wind and AC.",
        ],
        "warning": "⚠️ If cold with high fever lasts more than 10 days, see a doctor."
    },
    "diabetes": {
        "title": "Diabetes — Madhumeh",
        "ayurvedic": [
            "🌿 Karela juice — 30ml bitter gourd juice on empty stomach every morning. Lowers blood sugar.",
            "🌿 Methi seeds — Soak 2 tsp overnight. Drink water and eat seeds on empty stomach daily.",
            "🌿 Jamun seed powder — 1 tsp twice daily. Proven to reduce blood sugar levels.",
            "🌿 Gurmar leaves — Chew fresh leaves or take powder. Reduces sugar absorption.",
            "🌿 Vijaysar wooden glass — Soak in water overnight. Drink water every morning.",
            "🌿 Neem leaves — Drink neem leaf juice on empty stomach. Improves insulin sensitivity.",
        ],
        "home": [
            "🥗 Strict diet — Whole grains, vegetables, dal. NO rice, white bread, sugar, sweets, fried food.",
            "🚶 Walk 30-45 minutes daily — Most effective natural blood sugar control.",
            "⏰ Small meals every 3-4 hours — Never skip meals, especially breakfast.",
            "🍌 Avoid high glycemic foods — banana, mango, potato, white rice, sugary drinks.",
            "💧 Drink 8-10 glasses water daily — Helps kidneys flush excess sugar.",
            "🧘 Kapalbhati pranayama — 15 minutes daily helps improve insulin function.",
        ],
        "warning": "⚠️ Always monitor blood sugar. Never stop prescribed medicines without doctor advice."
    },
    "hypertension": {
        "title": "High Blood Pressure — Uchcha Raktachap",
        "ayurvedic": [
            "🌿 Arjuna bark — Boil in milk (Arjuna Ksheer Pak). Strengthens heart, reduces BP.",
            "🌿 Brahmi — Brahmi powder or ghee. Calms nervous system, reduces stress BP.",
            "🌿 Garlic — 2 raw garlic cloves daily on empty stomach. Natural BP reducer.",
            "🌿 Triphala — Take at night with warm water. Supports heart and circulation.",
            "🌿 Ashwagandha — Reduces stress-induced BP. Take with warm milk at night.",
        ],
        "home": [
            "🧂 Reduce salt drastically — Less than 1 tsp total per day including in tea.",
            "🍌 Eat potassium foods — banana, coconut water, spinach, sweet potato.",
            "🚶 Walk 30 minutes daily — Most effective natural BP reducer.",
            "😌 Stress management — Deep breathing and meditation 10-15 minutes daily.",
            "🚫 Quit smoking and alcohol — Both significantly raise blood pressure.",
            "⚖️ Lose excess weight — Even 5kg loss can reduce BP significantly.",
        ],
        "warning": "⚠️ Never stop BP medicines without doctor advice. Monitor BP daily at home."
    },
    "malaria": {
        "title": "Malaria — Malarial Fever",
        "ayurvedic": [
            "🌿 Chirayata (Swertia chirata) — Decoction of chirayata for malarial fever.",
            "🌿 Giloy kadha — Boil giloy stem and drink twice daily. Known as Amruta for fevers.",
            "🌿 Tulsi-Black pepper kadha — Immunity booster during malarial fever.",
            "🌿 Kutki — Classical anti-malarial Ayurvedic herb with doctor's guidance.",
        ],
        "home": [
            "💧 Stay very well hydrated — ORS, coconut water, nimbu pani frequently.",
            "🦟 Use mosquito nets every night — Treated nets are most effective prevention.",
            "🧴 Apply neem or eucalyptus oil on skin to repel mosquitoes.",
            "💊 Complete full course of anti-malarial medicines given by PHC.",
            "🍲 Light diet — khichdi, moong dal, soups. Avoid heavy food.",
        ],
        "warning": "⚠️ MUST visit PHC for blood test. Ayurvedic remedies are supportive only. Free anti-malarial at PHC."
    },
    "dengue": {
        "title": "Dengue Fever",
        "ayurvedic": [
            "🌿 Papaya leaf juice — Most researched remedy for dengue. Increases platelet count. 30ml twice daily.",
            "🌿 Giloy juice — Boosts immunity during dengue fever recovery.",
            "🌿 Guduchi — Anti-viral herb for dengue and viral fevers.",
            "🌿 Tulsi kadha — 2-3 times daily to boost immunity.",
        ],
        "home": [
            "💧 Drink 3-4 litres fluid daily — water, coconut water, ORS, juices. Critical.",
            "🚫 NO aspirin, ibuprofen, brufen — Can cause dangerous bleeding in dengue.",
            "🛏️ Complete bed rest — Do not exert yourself at all.",
            "🌡️ Watch for warning signs — severe pain, vomiting blood, bleeding — go to hospital.",
            "🦟 Prevent mosquito bites even while sick — wear full sleeves, use nets.",
        ],
        "warning": "⚠️ Visit PHC same day for platelet count test. Platelet monitoring is critical in dengue."
    },
    "tuberculosis": {
        "title": "Tuberculosis — TB",
        "ayurvedic": [
            "🌿 Vasaka (Adhatoda) — Vasa leaf juice with honey. Traditional respiratory TB herb.",
            "🌿 Ashwagandha — Regains strength and weight during TB recovery. Take with milk.",
            "🌿 Chyawanprash — 2 tsp twice daily with warm milk. Lung strength booster.",
            "🌿 Giloy + Shatavari — Immune support combination during TB treatment.",
            "🌿 Turmeric in warm milk — Anti-inflammatory, supports lung tissue healing.",
        ],
        "home": [
            "🥛 High protein diet — milk, eggs, dal, paneer, soya. TB causes severe protein loss.",
            "☀️ Morning sunlight — 30 minutes daily. Natural Vitamin D for immunity.",
            "😷 Cover mouth while coughing. Separate utensils. Ventilate your room well.",
            "💊 NEVER skip DOTS doses — even when feeling better. Incomplete treatment = drug resistance.",
            "📋 Get family members tested — TB is contagious to close contacts.",
        ],
        "warning": "⚠️ Visit PHC immediately. Free DOTS treatment for 6 months. Rs 500/month nutrition support under Nikshay Yojana."
    },
    "diarrhoea": {
        "title": "Diarrhoea — Atisaar",
        "ayurvedic": [
            "🌿 Bael (Wood apple) — Ripe bael pulp with warm water. Most effective Ayurvedic remedy.",
            "🌿 Kutajghan Vati — Classical Ayurvedic tablet for loose motions. Available at stores.",
            "🌿 Pomegranate peel tea — Boil pomegranate peel in water. Traditional astringent.",
            "🌿 Isabgol — Mix in water or buttermilk. Absorbs excess water in intestines.",
        ],
        "home": [
            "💧 ORS immediately — 1 litre water + 6 tsp sugar + half tsp salt. Drink every 15 minutes.",
            "🍚 Rice kanji — Boil rice in excess water, drink the starchy water with salt.",
            "🍌 Banana with curd — Easy on stomach, replenishes potassium.",
            "🧄 Ginger + cumin water — Boil jeera and ginger. Anti-diarrhoeal.",
            "🥣 Light diet — Khichdi, curd rice, dal water. Avoid spicy and oily food.",
            "🚫 Avoid dairy, raw vegetables, and fruits except banana.",
        ],
        "warning": "⚠️ Visit PHC if diarrhoea lasts more than 2 days or if there is blood in stool."
    },
    "typhoid": {
        "title": "Typhoid — Maiyad Bukhar",
        "ayurvedic": [
            "🌿 Chirayata decoction — Strong anti-bacterial for typhoid fever.",
            "🌿 Kutki — Ayurvedic hepatoprotective herb. Supports liver during typhoid.",
            "🌿 Giloy kadha — Reduces fever and boosts immunity during typhoid.",
            "🌿 Turmeric with honey in warm water — Anti-bacterial. Twice daily.",
        ],
        "home": [
            "💧 High fluid intake — water, coconut water, ORS, soups, fruit juices.",
            "🥣 Soft easily digestible food — khichdi, rice, boiled vegetables, curd, banana.",
            "🧼 Strict hygiene — Wash hands before eating. Drink only boiled or filtered water.",
            "🛏️ Complete rest — Typhoid is very draining. Do not exert yourself.",
            "🍽️ Separate utensils — Typhoid spreads through contaminated food and water.",
        ],
        "warning": "⚠️ Visit PHC for Widal test and antibiotics. Typhoid MUST be treated with prescribed antibiotics."
    },
    "asthma": {
        "title": "Asthma — Dama",
        "ayurvedic": [
            "🌿 Vasaka leaves — Juice of Adulsa leaves with honey. Opens airways.",
            "🌿 Black pepper + honey — 3-4 black peppercorns crushed with honey daily.",
            "🌿 Ginger tea with honey — Natural bronchodilator. 2-3 cups daily.",
            "🌿 Turmeric in warm milk — Reduces airway inflammation at night.",
            "🌿 Pushkarmool — Classical herb for respiratory conditions with honey.",
        ],
        "home": [
            "💨 Steam inhalation — Eucalyptus oil in hot water. Inhale 10 min twice daily.",
            "🧘 Pranayama daily — Anulom-Vilom and Bhramari. Strengthens lungs over time.",
            "🚫 Identify and avoid triggers — dust, smoke, pollen, perfumes, cold air.",
            "🏠 Keep home dust-free — Damp mop floors, avoid carpets.",
            "💊 Always carry inhaler — Never go out without rescue inhaler.",
            "🌙 Sleep with head elevated — Extra pillow prevents nighttime attacks.",
        ],
        "warning": "⚠️ Always follow prescribed inhaler medication. In severe attack, call 108 immediately."
    },
    "anaemia": {
        "title": "Anaemia — Raktalpta",
        "ayurvedic": [
            "🌿 Punarnava juice — Juice of fresh leaves improves haemoglobin levels.",
            "🌿 Shatavari — Builds blood and strength. Especially for women.",
            "🌿 Raisins (Draksha) — Soak overnight and eat with water every morning.",
            "🌿 Amla — Highest natural Vitamin C. Greatly enhances iron absorption.",
            "🌿 Lauh Bhasma — Ayurvedic iron supplement. Use under doctor's guidance.",
        ],
        "home": [
            "🥬 Iron-rich foods daily — spinach, methi, beetroot, lentils, rajma, chana, jaggery.",
            "🍋 Eat Vitamin C with iron — lemon, amla, orange alongside iron foods boosts absorption.",
            "🚫 Avoid tea and coffee with meals — Tannins block iron absorption significantly.",
            "🫙 Cook in iron vessels — Traditional iron kadhai increases food iron content.",
            "💊 Free iron tablets at PHC — Take regularly as prescribed.",
            "🥩 Non-veg iron — eggs, chicken liver, fish are most easily absorbed iron sources.",
        ],
        "warning": "⚠️ Pregnant women and children with anaemia must visit PHC. Free iron supplements available."
    },
    "jaundice": {
        "title": "Jaundice — Piliya",
        "ayurvedic": [
            "🌿 Kutki — Most effective Ayurvedic herb for liver in jaundice treatment.",
            "🌿 Bhumyamalaki (Phyllanthus) — Protects against viral hepatitis. Classical liver herb.",
            "🌿 Punarnava — Reduces liver inflammation and promotes bile flow.",
            "🌿 Arogyavardhini Vati — Classical tablet for liver conditions.",
            "🌿 Turmeric in warm water — Anti-inflammatory liver protectant daily.",
        ],
        "home": [
            "🧃 Sugarcane juice — 2 glasses daily. Traditional and effective for jaundice.",
            "🍋 Warm lemon water — Stimulates liver function every morning.",
            "🥥 Coconut water — Rehydrates and supports liver recovery.",
            "🚫 Avoid completely — alcohol, oil, ghee, fried food, spices, non-veg.",
            "🥗 Light diet — boiled vegetables, khichdi, fruits (not sour).",
            "🛏️ Complete rest — Liver heals only with rest. No exertion.",
        ],
        "warning": "⚠️ Visit PHC for Hepatitis test immediately. Hepatitis B jaundice needs medical treatment."
    },
    "headache": {
        "title": "Headache — Sir Dard",
        "ayurvedic": [
            "🌿 Brahmi oil massage — Gently massage brahmi oil on scalp and forehead.",
            "🌿 Peppermint oil — Apply diluted on temples and forehead. Cool and soothing.",
            "🌿 Shirobhyanga — Head massage with warm sesame oil. Most effective Ayurvedic remedy.",
            "🌿 Ashwagandha with warm milk — For chronic stress and tension headaches at night.",
        ],
        "home": [
            "🌡️ Cold compress — Cold wet cloth on forehead for tension headache.",
            "♨️ Warm compress — Warm cloth on face and forehead for sinus headache.",
            "💧 Drink 2 glasses water first — Many headaches are simply dehydration.",
            "🌑 Rest in dark quiet room — Essential for migraine headaches.",
            "☕ Ginger tea — Anti-inflammatory. Effective for migraine and tension headache.",
            "🧘 Deep slow breathing for 5 minutes — Relieves tension headache naturally.",
        ],
        "warning": "⚠️ Sudden severe headache or headache with vision problems needs immediate hospital visit."
    },
    "skin": {
        "title": "Skin Problems — Twacha Rog",
        "ayurvedic": [
            "🌿 Neem paste — Apply neem leaf paste on rashes, acne, and skin infections.",
            "🌿 Turmeric paste — Mix turmeric + rose water. Apply on affected area.",
            "🌿 Manjistha — Blood purifier herb. Very effective for chronic skin conditions.",
            "🌿 Aloe vera gel — Apply fresh aloe vera gel directly. Cooling and healing.",
            "🌿 Kumkumadi oil — For skin healing and reducing dark spots.",
        ],
        "home": [
            "🧼 Keep skin clean — Wash with mild soap and clean water twice daily.",
            "🌿 Coconut oil — Virgin coconut oil for dry skin, rashes, and mild infections.",
            "🍯 Honey — Natural antibacterial. Apply raw honey on wounds and skin infections.",
            "💧 Stay hydrated — 8-10 glasses water daily for clear healthy skin.",
            "🥗 Skin-friendly diet — fruits, vegetables, avoid oily and spicy food.",
            "☀️ Limit direct sun exposure — Use light cotton clothes to cover skin.",
        ],
        "warning": "⚠️ For scabies, chickenpox, or spreading infections, visit PHC for proper treatment."
    },
}

FITNESS_DATA = {
    "morning": {
        "title": "Morning Routine",
        "icon": "🌅",
        "duration": "30-45 minutes",
        "water": "Drink 2 glasses of warm water before starting",
        "exercises": [
            {"name": "Surya Namaskar", "reps": "5-10 rounds", "benefit": "Full body workout, flexibility and strength", "icon": "🧘"},
            {"name": "Brisk Walking", "reps": "20-30 minutes", "benefit": "Best exercise for heart, diabetes and BP control", "icon": "🚶"},
            {"name": "Kapalbhati Pranayama", "reps": "5 minutes", "benefit": "Cleanses lungs, improves digestion, reduces belly fat", "icon": "💨"},
            {"name": "Anulom-Vilom Breathing", "reps": "5 minutes", "benefit": "Reduces stress, lowers BP, calms mind", "icon": "🌬️"},
            {"name": "Tadasana (Mountain Pose)", "reps": "Hold 30 sec × 5", "benefit": "Improves posture, strengthens spine", "icon": "🏔️"},
        ],
        "tip": "Morning exercise on empty stomach burns more fat and boosts metabolism for the entire day."
    },
    "strength": {
        "title": "Strength Training",
        "icon": "💪",
        "duration": "30-40 minutes",
        "water": "Drink water before, during, and after workout",
        "exercises": [
            {"name": "Squats (Utkatasana)", "reps": "3 sets of 15", "benefit": "Strengthens legs, glutes, and core", "icon": "🏋️"},
            {"name": "Push-ups", "reps": "3 sets of 10-15", "benefit": "Upper body strength, chest and arms", "icon": "💪"},
            {"name": "Plank", "reps": "Hold 30-60 sec × 3", "benefit": "Core strength, reduces back pain", "icon": "🏄"},
            {"name": "Lunges", "reps": "3 sets of 12 each leg", "benefit": "Balance, leg strength", "icon": "🦵"},
            {"name": "Jumping Jacks", "reps": "3 sets of 20", "benefit": "Cardio, full body warmup", "icon": "⭐"},
        ],
        "tip": "Strength training 3 days a week prevents muscle loss, bone weakness, and diabetes."
    },
    "yoga": {
        "title": "Yoga & Flexibility",
        "icon": "🧘",
        "duration": "20-30 minutes",
        "water": "Drink water 30 minutes before yoga",
        "exercises": [
            {"name": "Trikonasana (Triangle)", "reps": "Hold 30 sec each side × 3", "benefit": "Stretches spine, reduces back pain", "icon": "📐"},
            {"name": "Bhujangasana (Cobra)", "reps": "Hold 20 sec × 5", "benefit": "Strengthens back, opens chest", "icon": "🐍"},
            {"name": "Paschimottanasana", "reps": "Hold 30 sec × 3", "benefit": "Stretches hamstrings, relieves sciatica", "icon": "🙇"},
            {"name": "Vrikshasana (Tree Pose)", "reps": "Hold 1 min each leg × 2", "benefit": "Balance, focus, strong ankles", "icon": "🌳"},
            {"name": "Shavasana (Rest)", "reps": "5-10 minutes at end", "benefit": "Complete relaxation, stress relief", "icon": "💤"},
        ],
        "tip": "21 days of daily yoga creates lasting improvement in flexibility and mental peace."
    },
    "water": {
        "title": "Water Intake Guide",
        "icon": "💧",
        "total": "8-10 glasses (2-2.5 litres) daily",
        "schedule": [
            {"time": "6:00 AM — Wake up",         "amount": "2 glasses warm water",  "benefit": "Activates organs, flushes toxins"},
            {"time": "8:00 AM — Before breakfast", "amount": "1 glass",              "benefit": "Improves digestion and metabolism"},
            {"time": "10:30 AM",                   "amount": "1 glass",              "benefit": "Keeps energy levels stable"},
            {"time": "12:30 PM — Before lunch",    "amount": "1 glass",              "benefit": "Prepares stomach for digestion"},
            {"time": "3:00 PM",                    "amount": "1 glass",              "benefit": "Prevents afternoon fatigue"},
            {"time": "5:00 PM — Evening",          "amount": "1 glass",              "benefit": "Hydrates before activity"},
            {"time": "7:00 PM — Before dinner",    "amount": "1 glass",              "benefit": "Aids digestion"},
            {"time": "9:00 PM — Before bed",       "amount": "1 glass warm water",   "benefit": "Prevents dehydration overnight"},
        ],
        "tips": [
            "💡 Drink water before meals, not during — avoids diluting digestive enzymes.",
            "💡 Warm water is better than cold — easier for body to process.",
            "💡 Check urine colour — pale yellow means well-hydrated, dark means drink more.",
            "💡 Increase intake in summer, during illness, and after exercise.",
            "💡 Use steel or copper vessel — avoid plastic in hot conditions.",
        ]
    },
    "diet": {
        "title": "Healthy Diet Tips",
        "icon": "🥗",
        "meals": [
            {"meal": "Early Morning",   "suggestion": "2 glasses warm water + 5 soaked almonds + 1 tsp honey with ginger", "icon": "🌅"},
            {"meal": "Breakfast 7-9AM", "suggestion": "Poha / Upma / Oats with vegetables + 1 fruit + 1 glass milk", "icon": "🍳"},
            {"meal": "Mid-Morning",     "suggestion": "Seasonal fruit or handful of nuts and seeds", "icon": "🍎"},
            {"meal": "Lunch 12-2PM",    "suggestion": "2 chapati + dal + sabzi + curd + salad. Biggest meal of day.", "icon": "🍽️"},
            {"meal": "Evening Snack",   "suggestion": "Chana chaat / roasted makhana / sprouts / buttermilk", "icon": "🌆"},
            {"meal": "Dinner 7-8PM",    "suggestion": "Light meal — khichdi or 1-2 chapati with dal or soup. No heavy food.", "icon": "🌙"},
        ],
        "tips": [
            "🚫 Avoid packaged and processed food — high in salt, sugar, unhealthy fats.",
            "🌾 Eat whole grains — brown rice, whole wheat chapati, millets like bajra, jowar, ragi.",
            "🥗 Half your plate should be vegetables and salad at every meal.",
            "🚫 Limit sugar to 5 teaspoons maximum per day including in tea and milk.",
            "🧂 Reduce salt — less than 1 teaspoon daily. Excess salt causes hypertension.",
            "🫙 Cook at home — restaurant food has 3-5x more oil, salt, and calories.",
        ]
    },
    "sleep": {
        "title": "Sleep & Recovery",
        "icon": "😴",
        "duration": "Adults: 7-8 hours. Children: 9-10 hours.",
        "tips": [
            {"tip": "Fixed sleep schedule", "detail": "Sleep and wake at same time every day, even weekends.", "icon": "⏰"},
            {"tip": "No screens 1 hour before bed", "detail": "Mobile and TV blue light disrupts melatonin hormone.", "icon": "📵"},
            {"tip": "Warm turmeric milk", "detail": "Milk has tryptophan. Add turmeric or nutmeg for better sleep.", "icon": "🥛"},
            {"tip": "Cool dark room", "detail": "Ideal sleep temp is 18-22°C. Use thin curtains.", "icon": "🌑"},
            {"tip": "Avoid caffeine after 3 PM", "detail": "Tea and coffee stay in system for 6 hours.", "icon": "☕"},
            {"tip": "Brahmi or Ashwagandha", "detail": "Natural herbs for stress and improved sleep quality.", "icon": "🌿"},
        ]
    }
}

def init_logs():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS chat_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT, user_msg TEXT, bot_reply TEXT, source TEXT DEFAULT 'web'
    )""")
    conn.commit()
    conn.close()

init_logs()

def log_chat(user_msg, bot_reply, source="web"):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO chat_logs (timestamp,user_msg,bot_reply,source) VALUES (?,?,?,?)",
                     (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_msg, bot_reply, source))
        conn.commit(); conn.close()
    except Exception as e:
        logger.error(f"Log error: {e}")

def detect_district(text):
    t = text.lower()
    for pat in [r"hospital in (\w+)", r"phc in (\w+)", r"clinic in (\w+)", r"hospital near (\w+)"]:
        m = re.search(pat, t)
        if m: return m.group(1)
    for d in KNOWN_DISTRICTS:
        if d in t: return d
    return None

def detect_remedy_query(text):
    t = text.lower()
    disease_keywords = {
        "fever":          ["fever","bukhar","temperature","body heat","tap"],
        "cough":          ["cough","khansi","coughing","dry cough"],
        "cold":           ["cold","runny nose","nasal","sardi","zukam","blocked nose"],
        "diabetes":       ["diabetes","sugar","blood sugar","diabetic","madhumeh"],
        "hypertension":   ["hypertension","blood pressure","high bp","bp high","raktachap"],
        "malaria":        ["malaria","malarial fever","chills fever"],
        "dengue":         ["dengue","dengue fever","platelet"],
        "tuberculosis":   ["tuberculosis","tb ","kshay rog"],
        "diarrhoea":      ["diarrhoea","diarrhea","loose motions","loose motion","atisaar"],
        "typhoid":        ["typhoid","enteric fever","maiyad"],
        "asthma":         ["asthma","breathlessness","wheezing","dama"],
        "anaemia":        ["anaemia","anemia","haemoglobin","hemoglobin","pale","raktalpta"],
        "jaundice":       ["jaundice","yellow eyes","yellow skin","piliya"],
        "headache":       ["headache","head pain","migraine","sir dard","sar dard"],
        "skin":           ["skin","rash","itching","eczema","acne","khujli","twacha"],
    }
    for disease, keywords in disease_keywords.items():
        for kw in keywords:
            if kw in t: return disease
    return None

def format_facilities(facilities, district):
    if not facilities:
        return f"No facilities found for {district.title()}. Call 104 for help or visit nhm.gov.in"
    lines = [f"Health Facilities in {district.title()}:\n"]
    for i, f in enumerate(facilities, 1):
        em = "Emergency Available" if f["emergency_available"] == "Yes" else "OPD Only"
        lines.append(f"{i}. {f['facility_name']} [{f['facility_type']}]\n   {f['address']}\n   Phone: {f['phone']} | {em}\n")
    lines.append("For emergency, call 108 (Free ambulance, 24x7)")
    return "\n".join(lines)

# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_msg = data.get("message", "").strip()
    if not user_msg:
        return jsonify({"reply": "Please type something so I can help you.", "type": "text"})

    district = detect_district(user_msg)
    if district:
        fac = search_facilities(district)
        reply = format_facilities(fac, district)
        log_chat(user_msg, reply)
        fac_data = [{"name": f["facility_name"], "type": f["facility_type"],
                     "lat": f["latitude"], "lng": f["longitude"],
                     "phone": f["phone"], "address": f["address"],
                     "emergency": f["emergency_available"]} for f in fac]
        return jsonify({"reply": reply, "type": "facilities", "facilities": fac_data})

    remedy_disease = detect_remedy_query(user_msg)

    ml_result = None
    if classifier:
        try: ml_result = classifier.predict(user_msg)
        except: pass

    aiml_reply = bot.respond(user_msg)
    is_fallback = "didn't understand" in aiml_reply.lower() or "not sure" in aiml_reply.lower()

    if ml_result and is_fallback:
        reply = (f"Based on your symptoms, this looks like: {ml_result['disease']}\n"
                 f"Confidence: {ml_result['confidence']}%\n"
                 f"Severity: {ml_result['severity']}\n"
                 f"Recommended: {ml_result['facility']}\n\n"
                 f"{ml_result['action']}")
        log_chat(user_msg, reply)
        ml_d = ml_result['disease'].lower()
        r_key = ml_d if ml_d in REMEDIES else remedy_disease
        return jsonify({"reply": reply, "type": "ml_result", "ml": ml_result,
                        "remedy_available": r_key is not None, "remedy_disease": r_key})

    log_chat(user_msg, aiml_reply)
    return jsonify({"reply": aiml_reply, "type": "text",
                    "remedy_available": remedy_disease is not None,
                    "remedy_disease": remedy_disease})

@app.route("/api/remedies/<disease>")
def get_remedies(disease):
    d = disease.lower()
    if d in REMEDIES: return jsonify({"found": True, "data": REMEDIES[d]})
    return jsonify({"found": False}), 404

@app.route("/api/remedies")
def list_remedies():
    return jsonify({"diseases": list(REMEDIES.keys()), "count": len(REMEDIES)})

@app.route("/api/fitness")
def fitness_overview():
    return jsonify({"categories": [
        {"id": "morning",  "title": "Morning Routine",    "icon": "🌅", "duration": "30-45 min"},
        {"id": "strength", "title": "Strength Training",  "icon": "💪", "duration": "30-40 min"},
        {"id": "yoga",     "title": "Yoga & Flexibility", "icon": "🧘", "duration": "20-30 min"},
        {"id": "water",    "title": "Water Intake Guide", "icon": "💧", "duration": "All day"},
        {"id": "diet",     "title": "Healthy Diet Tips",  "icon": "🥗", "duration": "Daily"},
        {"id": "sleep",    "title": "Sleep & Recovery",   "icon": "😴", "duration": "7-8 hrs"},
    ]})

@app.route("/api/fitness/<category>")
def get_fitness(category):
    c = category.lower()
    if c in FITNESS_DATA: return jsonify({"found": True, "data": FITNESS_DATA[c]})
    return jsonify({"found": False}), 404

@app.route("/api/bmi", methods=["POST"])
def bmi():
    data = request.get_json()
    try:
        from ml.bmi import calculate_bmi
        result = calculate_bmi(float(data.get("weight", 0)), float(data.get("height", 0)))
        if result: return jsonify(result)
        return jsonify({"error": "Invalid values"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/facilities")
def api_facilities():
    district = request.args.get("district", "")
    if not district: return jsonify({"error": "Provide a district name"}), 400
    return jsonify({"district": district, "count": len(search_facilities(district)),
                    "facilities": search_facilities(district)})

@app.route("/api/schemes")
def api_schemes():
    return jsonify({"schemes": get_all_schemes()})

@app.route("/api/emergency")
def api_emergency():
    return jsonify({"contacts": get_emergency_contacts()})

@app.route("/api/admin/stats")
def admin_stats():
    try:
        conn = sqlite3.connect(DB_PATH)
        total  = conn.execute("SELECT COUNT(*) FROM chat_logs").fetchone()[0]
        today  = conn.execute("SELECT COUNT(*) FROM chat_logs WHERE timestamp LIKE ?",
                              (f"{datetime.now().strftime('%Y-%m-%d')}%",)).fetchone()[0]
        recent = conn.execute("SELECT user_msg,bot_reply,timestamp FROM chat_logs ORDER BY id DESC LIMIT 10").fetchall()
        top    = conn.execute("SELECT user_msg,COUNT(*) c FROM chat_logs GROUP BY LOWER(user_msg) ORDER BY c DESC LIMIT 8").fetchall()
        hourly = conn.execute("SELECT substr(timestamp,12,2) hr,COUNT(*) c FROM chat_logs GROUP BY hr ORDER BY hr").fetchall()
        conn.close()
        return jsonify({"total_messages": total, "today_messages": today,
                        "recent_chats":   [{"user": r[0], "bot": r[1][:80], "time": r[2]} for r in recent],
                        "top_queries":    [{"query": r[0], "count": r[1]} for r in top],
                        "hourly_activity":[{"hour": r[0], "count": r[1]} for r in hourly]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/whatsapp/setup")
def whatsapp_setup():
    try:
        from ml.whatsapp import get_whatsapp_setup_instructions
        return jsonify(get_whatsapp_setup_instructions())
    except Exception:
        return jsonify({"status": "WhatsApp module available. Install twilio to activate."})

if __name__ == "__main__":
    print("\n" + "="*55)
    print("  Aarogya Mitra — Upgraded Version")
    print("  Chat UI   →  http://127.0.0.1:5000")
    print("  Dashboard →  http://127.0.0.1:5000/admin")
    print("="*55 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
