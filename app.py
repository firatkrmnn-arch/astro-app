import streamlit as st
import google.generativeai as genai
from kerykeion import AstrologicalSubject
from geopy.geocoders import Nominatim
from datetime import datetime, time
import pytz
from fpdf import FPDF # PDF oluşturma kütüphanesi

# --- AYARLAR ---
# DİKKAT: Bu anahtar GitHub'da görünüyor. Gerçek projen büyüdüğünde gizlenmeli.
GOOGLE_API_KEY = "AIzaSyCnUIQ2tBG8-Aq2DN-M7s4K3yV-mhgEsE0"
genai.configure(api_key=GOOGLE_API_KEY)

# --- ÇEVİRİ SÖZLÜKLERİ ---
BURC_CEVIRI = {
    "Ari": "Koç", "Tau": "Boğa", "Gem": "İkizler", "Can": "Yengeç",
    "Leo": "Aslan", "Vir": "Başak", "Lib": "Terazi", "Sco": "Akrep",
    "Sag": "Yay", "Cap": "Oğlak", "Aqu": "Kova", "Pis": "Balık"
}

EV_CEVIRI = {
    "First_House": "1. Ev (Yükselen)", "Second_House": "2. Ev", "Third_House": "3. Ev",
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
        # Saati 12:00'a sabitledik ki butona basınca sıfırlanmasın
        birth_time = st.time_input("Doğum Saati", value=time(12, 0)) 
    
    st.markdown("### 💭 Neyin Cevabını Arıyorsun?")
    question = st.text_area(
        "Aklındaki spesifik soruyu buraya yaz.",
        height=100
    )
    
    submitted = st.form_submit_button("Analiz Et ve Yanıtla 🚀")

if submitted:
    if not question:
        st.error("Lütfen bir soru yaz.")
    else:
        with st.spinner('Bağlantı ve harita hesaplanıyor...'):
            try:
                # 1. Konum Bulma (TIMEOUT FIX'İ BURADA)
                # 10 saniye bekleme süresi ekledik.
                geolocator = Nominatim(user_agent="astro_final_fix", timeout=10) 
                location = geolocator.geocode(city)
                
                if not location:
                    st.error("Şehir bulunamadı.")
                else:
                    # 2. DOĞRU SAAT HESAPLAMASI (pytz ile tarihsel DST hesaplama)
                    local_tz = pytz.timezone('Europe/Istanbul')
                    local_dt = datetime.combine(birth_date, birth_time)
                    local_dt = local_tz.localize(local_dt)
                    utc_dt = local_dt.astimezone(pytz.utc)
                    
                    # 3. Harita Hesapla (UTC Olarak)
                    user = AstrologicalSubject(
                        name, 
                        utc_dt.year, utc_dt.month, utc_dt.day,
                        utc_dt.hour, utc_dt.minute,
                        city, 
                        lat=location.latitude, 
                        lng=location.longitude,
                        tz_str="UTC" 
                    )

                    # 4. Verileri Hazırla
                    def tr(text): return BURC_CEVIRI.get(text, text)
                    def tr_house(text): return EV_CEVIRI.get(text, text)

                    planet_data = f"""
                    Kişi: {name}, Yer: {city}
                    Güneş: {tr(user.sun['sign'])} ({tr_house(user.sun['house'])}) ({user.sun['position']:.2f}°)
                    Ay: {tr(user.moon['sign'])} ({tr_house(user.moon['house'])}) ({user.moon['position']:.2f}°)
                    Yükselen: {tr(user.first_house['sign'])}
                    Merkür: {tr(user.mercury['sign'])}, Venüs: {tr(user.venus['sign'])}, Mars: {tr(user.mars['sign'])}
                    """

                    # 5. SENİN GEM PROMPTUN: Soruya Cevap Vermeye Odaklı
                    prompt = f"""
                    1. KİMLİK (ROLE): Sen "Astro Analist"sin. Dürüst, derin ve analitiksin.

                    2. GÖREV: Aşağıdaki harita verilerini kullanarak, kullanıcının sorduğu SPESİFİK SORUYA cevap ver. Genel yorum yapma.
                    
                    KULLANICI SORUSU: "{question}"
                    
                    HARİTA VERİLERİ:
                    {planet_data}
                    """

                    model = genai.GenerativeModel('gemini-2.5-flash')
                    response = model.generate_content(prompt)
                    
                    # 6. Ekrana Bas
                    st.success(f"✨ {name} için Cevap:")
                    st.markdown(response.text)
                    
                    # 7. PDF OLUŞTURMA VE İNDİRME BUTONU
                    pdf = PDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=12)
                    pdf.cell(0, 10, txt=f"Danisan: {name}", ln=1)
                    pdf.cell(0, 10, txt=f"Soru: {question}", ln=1)
                    pdf.ln(5)
                    # Not: Türkçe karakter sorunu olmaması için basit replace kullandık.
                    pdf_text = response.text.replace("ş","s").replace("ğ","g").replace("ı","i").replace("İ","I").replace("ç","c").replace("ö","o").replace("ü","u")
                    pdf.multi_cell(0, 5, txt=pdf_text)
                    
                    pdf_output = pdf.output(dest='S').encode('latin-1')
                    
                    st.download_button(
                        label="📄 Analizi PDF Olarak İndir",
                        data=pdf_output,
                        file_name=f"{name}_astro_analiz.pdf",
                        mime="application/pdf"
                    )

            except Exception as e:
                st.error(f"Beklenmedik bir hata oluştu: {e}")
