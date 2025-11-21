import streamlit as st
import google.generativeai as genai
from kerykeion import AstrologicalSubject
from geopy.geocoders import Nominatim
from datetime import datetime, time
import pytz

# --- AYARLAR ---
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
    "Fourth_House": "4. Ev (Dip)", "Fifth_House": "5. Ev", "Sixth_House": "6. Ev",
    "Seventh_House": "7. Ev (Alçalan)", "Eighth_House": "8. Ev", "Ninth_House": "9. Ev",
    "Tenth_House": "10. Ev (Tepe)", "Eleventh_House": "11. Ev", "Twelfth_House": "12. Ev"
}

# --- SAYFA YAPISI ---
st.set_page_config(page_title="Astro Analist AI", page_icon="🔮", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    h1 { color: #9d71e8; text-align: center; }
    .stButton>button { 
        width: 100%; background-color: #9d71e8; color: white; 
        border-radius: 12px; height: 55px; font-size: 20px; border: none;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔮 Astro Analist AI")
st.markdown("---")

# --- KULLANICI GİRİŞLERİ ---
with st.form("entry_form"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Adınız", "Fırat")
        city = st.text_input("Doğum Şehri", "Istanbul")
    with col2:
        # DÜZELTME 1: Saati 'now' yapmadık, 12:00'a sabitledik. Artık değişmez.
        birth_date = st.date_input("Doğum Tarihi", min_value=datetime(1920, 1, 1))
        birth_time = st.time_input("Doğum Saati", value=time(12, 00))
    
    submitted = st.form_submit_button("Haritamı Analiz Et 🚀")

# --- İŞLEM ---
if submitted:
    with st.spinner('Yıldız haritası çıkarılıyor...'):
        try:
            # 1. Konum Bul
            geolocator = Nominatim(user_agent="astro_fixed_final")
            location = geolocator.geocode(city)
            
            if not location:
                st.error("Şehir bulunamadı.")
            else:
                # DÜZELTME 2: Otomatik bulmayı kapattık. ZORLA ISTANBUL yaptık.
                # Bu sayede 1996 yılındaki +3 saatini sistem kendi veritabanından hatasız çekecek.
                local_tz = pytz.timezone('Europe/Istanbul')
                
                # Girdiğin saati İstanbul saatine göre ayarla
                local_dt = datetime.combine(birth_date, birth_time)
                local_dt = local_tz.localize(local_dt)
                
                # UTC'ye çevir
                utc_dt = local_dt.astimezone(pytz.utc)
                
                # 3. Harita Hesapla (UTC ile)
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
                Girdiğin Saat: {birth_time}
                Kullanılan Saat Dilimi: Europe/Istanbul (Otomatik Tarihsel Ayarlı)
                
                --- GEZEGEN KONUMLARI ---
                GÜNEŞ: {tr(user.sun['sign'])} - {tr_house(user.sun['house'])} ({user.sun['position']:.2f}°)
                AY: {tr(user.moon['sign'])} - {tr_house(user.moon['house'])} ({user.moon['position']:.2f}°)
                YÜKSELEN: {tr(user.first_house['sign'])} ({user.first_house['position']:.2f}°)
                
                Merkür: {tr(user.mercury['sign'])} ({tr_house(user.mercury['house'])})
                Venüs: {tr(user.venus['sign'])} ({tr_house(user.venus['house'])})
                Mars: {tr(user.mars['sign'])} ({tr_house(user.mars['house'])})
                Jüpiter: {tr(user.jupiter['sign'])} ({tr_house(user.jupiter['house'])})
                Satürn: {tr(user.saturn['sign'])} ({tr_house(user.saturn['house'])})
                Uranüs: {tr(user.uranus['sign'])} ({tr_house(user.uranus['house'])})
                Neptün: {tr(user.neptune['sign'])} ({tr_house(user.neptune['house'])})
                Plüton: {tr(user.pluto['sign'])} ({tr_house(user.pluto['house'])})
                """

                # 5. PROMPT
                prompt = f"""
                1. KİMLİK (ROLE):
                Sen "Astro Analist" adında uzman bir astroloğsun.

                2. GÖREV:
                Aşağıdaki harita verilerini kullanarak kişiye BÜTÜNSEL ve DERİN bir analiz yap.
                Gezegenlerin ev ve burç konumlarını sentezle.
                
                3. TON:
                Mistik, gerçekçi ve etkileyici.

                HARİTA VERİLERİ:
                {planet_data}
                """

                # Model
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content(prompt)
                
                st.success(f"✨ {name} için Analiz Hazır!")
                st.markdown(response.text)
                
                with st.expander("Teknik Verileri Kontrol Et"):
                    st.code(planet_data)

        except Exception as e:
            st.error(f"Hata: {e}")
