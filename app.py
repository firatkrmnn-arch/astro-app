import streamlit as st
import google.generativeai as genai
from kerykeion import AstrologicalSubject
from geopy.geocoders import ArcGIS
from datetime import datetime, time
import pytz
from fpdf import FPDF
import base64

# --- AYARLAR VE GÜVENLİK ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("⚠️ API Anahtarı bulunamadı! Lütfen Streamlit Secrets ayarlarını kontrol et.")
except Exception as e:
    st.error(f"API Ayar Hatası: {e}")

# --- ARKA PLAN (Profil Fotosu) ---
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def set_background(png_file):
    try:
        bin_str = get_base64_of_bin_file(png_file)
        page_bg_img = f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpg;base64,{bin_str}");
            background-size: cover;
            background-position: center center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        h1, h2, h3, p, label {{
            color: white !important;
            text-shadow: 2px 2px 4px #000000;
        }}
        .stTextInput>div>div>input, .stTextArea>div>div>textarea {{
            background-color: rgba(0, 0, 0, 0.7) !important; 
            color: white !important;
            border: 1px solid #9d71e8;
        }}
        div[data-testid="stForm"] {{
            background-color: rgba(0, 0, 0, 0.85);
            padding: 30px;
            border-radius: 15px;
            border: 1px solid #9d71e8;
        }}
        .stButton>button {{ 
            width: 100%; background-color: #9d71e8; color: white; 
            border-radius: 12px; height: 55px; font-size: 18px; border: none; font-weight: bold;
        }}
        </style>
        """
        st.markdown(page_bg_img, unsafe_allow_html=True)
    except FileNotFoundError:
        pass # Resim yoksa hata verme, devam et

set_background("profil.jpg")

# --- YARDIMCI FONKSİYONLAR ---
def clean_text(text):
    if not text: return ""
    replacements = {
        "ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c",
        "İ": "I", "Ğ": "G", "Ü": "U", "Ş": "S", "Ö": "O", "Ç": "C",
        "â": "a", "î": "i", "û": "u"
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text.encode('latin-1', 'replace').decode('latin-1')

BURC_CEVIRI = {
    "Ari": "Koç", "Tau": "Boğa", "Gem": "İkizler", "Can": "Yengeç",
    "Leo": "Aslan", "Vir": "Başak", "Lib": "Terazi", "Sco": "Akrep",
    "Sag": "Yay", "Cap": "Oğlak", "Aqu": "Kova", "Pis": "Balık"
}

EV_CEVIRI = {
    "First_House": "1. Ev", "Second_House": "2. Ev", "Third_House": "3. Ev",
    "Fourth_House": "4. Ev", "Fifth_House": "5. Ev", "Sixth_House": "6. Ev",
    "Seventh_House": "7. Ev", "Eighth_House": "8. Ev", "Ninth_House": "9. Ev",
    "Tenth_House": "10. Ev", "Eleventh_House": "11. Ev", "Twelfth_House": "12. Ev"
}

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Astro Analist - Ozel Rapor', 0, 1, 'C')
        self.ln(10)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, 'Sayfa ' + str(self.page_no()), 0, 0, 'C')

# --- UYGULAMA ---
st.title("🔮 Astro Analist")
st.markdown("---")

with st.form("entry_form"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Adın", "Misafir")
        city = st.text_input("Doğum Şehri", "Istanbul")
    with col2:
        birth_date = st.date_input("Doğum Tarihi", min_value=datetime(1940, 1, 1))
        birth_time = st.time_input("Doğum Saati", value=time(12, 0)) 
    
    st.markdown("### 💭 Sorun Nedir?")
    question = st.text_area("Aklındaki spesifik soruyu buraya yaz.", height=100)
    
    submitted = st.form_submit_button("Analiz Et ve Yanıtla 🚀")

if submitted:
    if not question:
        st.error("Lütfen bir soru yaz.")
    else:
        with st.spinner('Gemini 3.0 Pro haritanı inceliyor...'):
            try:
                # 1. Konum
                geolocator = ArcGIS(user_agent="astro_gemini3", timeout=10) 
                location = geolocator.geocode(city)
                
                if not location:
                    st.error("Şehir bulunamadı.")
                else:
                    # 2. Saat
                    local_tz = pytz.timezone('Europe/Istanbul')
                    local_dt = datetime.combine(birth_date, birth_time)
                    local_dt = local_tz.localize(local_dt)
                    utc_dt = local_dt.astimezone(pytz.utc)
                    
                    # 3. Harita
                    user = AstrologicalSubject(
                        name, utc_dt.year, utc_dt.month, utc_dt.day,
                        utc_dt.hour, utc_dt.minute, city, 
                        lat=location.latitude, lng=location.longitude, tz_str="UTC" 
                    )

                    def tr(text): return BURC_CEVIRI.get(text, text)
                    def tr_house(text): return EV_CEVIRI.get(text, text)

                    planet_data = f"""
                    Kişi: {name}, Yer: {city}
                    Güneş: {tr(user.sun['sign'])} ({tr_house(user.sun['house'])})
                    Ay: {tr(user.moon['sign'])} ({tr_house(user.moon['house'])})
                    Yükselen: {tr(user.first_house['sign'])}
                    Merkür: {tr(user.mercury['sign'])}, Venüs: {tr(user.venus['sign'])}, Mars: {tr(user.mars['sign'])}
                    Jüpiter: {tr(user.jupiter['sign'])}, Satürn: {tr(user.saturn['sign'])}
                    """

                    # 4. GEMINI 3 PROMPTU
                    prompt = f"""
                    KİMLİK: Sen, dünyanın en gelişmiş astroloji yapay zekası "Astro Analist"sin.
                    MODEL: Gemini 3 Pro yeteneklerini kullanarak derin, katmanlı ve psikolojik analiz yap.
                    GÖREV: Kullanıcının doğum haritasını ve sorusunu sentezleyerek cevap ver.
                    
                    KULLANICI SORUSU: "{question}"
                    
                    HARİTA VERİLERİ:
                    {planet_data}
                    """

                    # --- KRİTİK GÜNCELLEME: SENİN GEMINI 3 MODELİN ---
                    model = genai.GenerativeModel('gemini-3-pro-preview')
                    response = model.generate_content(prompt)
                    
                    st.success(f"✨ {name} için Cevap (Gemini 3.0):")
                    
                    st.markdown(
                        f"""
                        <div style="background-color: rgba(0,0,0,0.7); padding: 20px; border-radius: 10px; border: 1px solid #9d71e8;">
                        {response.text}
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                    
                    # 5. PDF
                    pdf = PDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=12)
                    clean_name = clean_text(name)
                    clean_question = clean_text(question)
                    clean_response = clean_text(response.text)
                    
                    pdf.cell(0, 10, txt=f"Danisan: {clean_name}", ln=1)
                    pdf.cell(0, 10, txt=f"Soru: {clean_question}", ln=1)
                    pdf.ln(5)
                    pdf.multi_cell(0, 5, txt=clean_response)
                    pdf_output = pdf.output(dest='S').encode('latin-1')
                    
                    st.download_button(
                        label="📄 Analizi PDF Olarak İndir",
                        data=pdf_output,
                        file_name="astro_analiz_v3.pdf",
                        mime="application/pdf"
                    )

            except Exception as e:
                st.error(f"Hata: {e}")
