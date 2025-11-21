import streamlit as st
import google.generativeai as genai
from kerykeion import AstrologicalSubject
from geopy.geocoders import ArcGIS
from datetime import datetime, time
import pytz
from fpdf import FPDF

# --- AYARLAR VE GÜVENLİK ---
# Şifreyi kodun içine YAZMIYORUZ. Streamlit Secrets'tan çekiyoruz.
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("⚠️ API Anahtarı bulunamadı! Lütfen Streamlit Cloud panelinde 'Secrets' ayarını yaptığından emin ol.")
except Exception as e:
    st.error(f"API Ayar Hatası: {e}")

# --- TÜRKÇE KARAKTER TEMİZLEYİCİ (PDF İÇİN) ---
def clean_text(text):
    if not text:
        return ""
    replacements = {
        "ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c",
        "İ": "I", "Ğ": "G", "Ü": "U", "Ş": "S", "Ö": "O", "Ç": "C",
        "â": "a", "î": "i", "û": "u"
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text.encode('latin-1', 'replace').decode('latin-1')

# --- ÇEVİRİ SÖZLÜKLERİ ---
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

# --- PDF SINIFI ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Astro Analist - Ozel Rapor', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, 'Sayfa ' + str(self.page_no()), 0, 0, 'C')

# --- SAYFA YAPISI ---
st.set_page_config(page_title="Astro Analist", page_icon="🔮", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    h1 { color: #9d71e8; text-align: center; font-family: sans-serif; }
    .stButton>button { 
        width: 100%; background-color: #9d71e8; color: white; 
        border-radius: 12px; height: 55px; font-size: 18px; border: none;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔮 Astro Analist")
st.markdown("---")

# --- GİRİŞ FORMU ---
with st.form("entry_form"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Adın", "Misafir")
        city = st.text_input("Doğum Şehri", "Istanbul")
    with col2:
        birth_date = st.date_input("Doğum Tarihi", min_value=datetime(1940, 1, 1))
        birth_time = st.time_input("Doğum Saati", value=time(12, 0)) 
    
    st.markdown("### 💭 Neyin Cevabını Arıyorsun?")
    question = st.text_area("Aklındaki spesifik soruyu buraya yaz.", height=100)
    
    submitted = st.form_submit_button("Analiz Et ve Yanıtla 🚀")

if submitted:
    if not question:
        st.error("Lütfen bir soru yaz.")
    else:
        with st.spinner('Yıldızlar hizalanıyor...'):
            try:
                # 1. Konum Bulma (ArcGIS)
                geolocator = ArcGIS(user_agent="astro_secure_v1", timeout=10) 
                location = geolocator.geocode(city)
                
                if not location:
                    st.error("Şehir bulunamadı.")
                else:
                    # 2. Saat Hesaplama
                    local_tz = pytz.timezone('Europe/Istanbul')
                    local_dt = datetime.combine(birth_date, birth_time)
                    local_dt = local_tz.localize(local_dt)
                    utc_dt = local_dt.astimezone(pytz.utc)
                    
                    # 3. Harita Hesapla
                    user = AstrologicalSubject(
                        name, 
                        utc_dt.year, utc_dt.month, utc_dt.day,
                        utc_dt.hour, utc_dt.minute,
                        city, 
                        lat=location.latitude, 
                        lng=location.longitude,
                        tz_str="UTC" 
                    )

                    def tr(text): return BURC_CEVIRI.get(text, text)
                    def tr_house(text): return EV_CEVIRI.get(text, text)

                    planet_data = f"""
                    Kişi: {name}, Yer: {city}
                    Güneş: {tr(user.sun['sign'])} ({tr_house(user.sun['house'])})
                    Ay: {tr(user.moon['sign'])} ({tr_house(user.moon['house'])})
                    Yükselen: {tr(user.first_house['sign'])}
                    Merkür: {tr(user.mercury['sign'])}, Venüs: {tr(user.venus['sign'])}, Mars: {tr(user.mars['sign'])}
                    """

                    # 4. AI Prompt
                    prompt = f"""
                    KİMLİK: Sen "Astro Analist"sin.
                    GÖREV: Aşağıdaki harita verilerini kullanarak, kullanıcının sorduğu SORUYA cevap ver.
                    
                    KULLANICI SORUSU: "{question}"
                    
                    HARİTA VERİLERİ:
                    {planet_data}
                    """

                    model = genai.GenerativeModel('gemini-2.5-flash')
                    response = model.generate_content(prompt)
                    
                    st.success(f"✨ {name} için Cevap:")
                    st.markdown(response.text)
                    
                    # 5. PDF OLUŞTURMA
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
                        file_name="astro_analiz.pdf",
                        mime="application/pdf"
                    )

            except Exception as e:
                st.error(f"Beklenmedik bir hata oluştu: {e}")
