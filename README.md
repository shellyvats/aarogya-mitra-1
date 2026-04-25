# 🌿 Aarogya Mitra — Rural Health Access Navigator v2

AI-powered health assistant with animated UI, ML symptom classifier,
BMI calculator, interactive maps, admin dashboard, and WhatsApp integration.

---

## 🚀 Quick Start

```bash
# 1. Open terminal in this folder
cd rural-health-bot-v3

# 2. Create virtual environment
python -m venv venv

# 3. Activate
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac/Linux

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run
python app.py
```

**Chat UI   →  http://127.0.0.1:5000**
**Dashboard →  http://127.0.0.1:5000/admin**

---

## ✨ New Features in v2

| Feature | Description |
|---|---|
| 🌿 Aarogya Mitra | Named AI assistant with animated personality |
| 🎨 Dark animated UI | Floating particles, glowing effects, smooth animations |
| 🔊 Text to Speech | Click the 🔊 button to hear replies aloud |
| 🤖 ML Symptom Classifier | AI handles complex multi-symptom descriptions |
| ⚖️ BMI Calculator | Health assessment with Indian ICMR standards |
| 🗺️ Interactive Map | OpenStreetMap shows real hospital locations |
| 📊 Admin Dashboard | Live charts of queries, activity, conversations |
| 📱 WhatsApp Guide | Step-by-step WhatsApp deployment instructions |

---

## 📁 Project Structure

```
rural-health-bot-v3/
├── app.py                   ← Flask server (main entry point)
├── bot.py                   ← AIML engine
├── db.py                    ← SQLite database
├── requirements.txt
├── aiml/
│   ├── greetings.aiml
│   ├── triage.aiml
│   ├── schemes.aiml
│   └── facilities.aiml
├── ml/
│   ├── symptom_classifier.py ← scikit-learn ML model
│   ├── bmi.py               ← BMI calculator
│   └── whatsapp.py          ← Twilio WhatsApp handler
├── data/
│   └── health.db            ← Auto-created SQLite database
└── templates/
    ├── index.html           ← Main chat UI
    └── admin.html           ← Analytics dashboard
```

---

## 💬 Sample Queries

| Type this | What happens |
|---|---|
| `Hello` | Aarogya Mitra greets you |
| `I have high fever with chills` | ML classifier identifies Malaria |
| `chest pain left arm sweating` | ML identifies Heart Attack — CRITICAL |
| `Hospital in Jaipur` | Shows hospitals on map + list |
| `Ayushman Bharat` | Full PMJAY scheme details |
| `Emergency` | All helpline numbers |
| BMI tab | Enter weight + height for health assessment |

---

## 📱 WhatsApp Setup (Optional)

1. Sign up free at twilio.com
2. Enable WhatsApp Sandbox
3. Install: `pip install twilio`
4. Run ngrok: `ngrok http 5000`
5. Set webhook: `https://YOUR_NGROK_URL/whatsapp`

---

## 🛠️ Tech Stack

- AIML 2.0 · Python Flask · SQLite
- scikit-learn (Naive Bayes classifier)
- Leaflet.js + OpenStreetMap (free, no API key needed)
- Chart.js (admin dashboard)
- Web Speech API (text to speech)
- HTML5 · CSS3 · Vanilla JavaScript

---

Built for Dell AI Lab Project Submission 🏥
