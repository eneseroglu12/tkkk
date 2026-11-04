"""Junior Wings MVP | Güvenli e-posta ve İK onay paneli."""
import csv
import io
import os
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st

from ai_assist import bilingual_check, polish_via_groq, suggestion_issues
from email_rules import (
    application_hash,
    classify_reply,
    evaluate,
    make_email,
    make_email_en,
    reply_suggestion,
    sha,
    validate_edit,
)

st.set_page_config(
    page_title="Junior Wings | İK Onay Paneli",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

REQUIRED = [
    "Başvuru Kararları",
    "Başvuru Listesi",
    "Program Aşamaları",
    "Aşama Kayıtları",
    "Sınav Sonuçları",
    "İngilizce Görüşme Sonuçları",
    "İK Değerlendirme Notları",
    "Beceri Tanımları",
]
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"



def inject_theme() -> None:
    st.markdown(
        f"""
        <style>
            :root {{
                --thy-red: #c8102e;
                --thy-red-dark: #8f0c21;
                --thy-black: #111111;
                --thy-cream: #f7f1e7;
                --thy-soft: #fffaf3;
                --thy-white: #ffffff;
                --thy-text: #231f20;
                --thy-border: #e8d8c4;
                --thy-shadow: rgba(108, 32, 45, 0.08);
            }}
            .stApp {{
                background: radial-gradient(circle at 92% 0%, rgba(200,16,46,.035), transparent 33%), linear-gradient(180deg, #fffcf7 0%, #f7f0e6 100%);
                color: var(--thy-text);
            }}
            [data-testid="stSidebar"] {{
                background: linear-gradient(180deg, #fbf6ef 0%, #f2e6d4 100%);
                border-right: 1px solid var(--thy-border);
            }}
            .block-container {{
                padding-top: 1.55rem;
                padding-bottom: 2.2rem;
                max-width: 1380px;
            }}
            div[data-testid="stMetric"] {{
                background: var(--thy-white);
                border: 1px solid var(--thy-border);
                border-radius: 18px;
                padding: 14px 16px;
                box-shadow: 0 10px 24px var(--thy-shadow);
            }}
            .sidebar-brand-box {{
                background: linear-gradient(180deg, #fffdfa 0%, #f6eee2 100%);
                border: 1px solid var(--thy-border);
                border-radius: 18px;
                padding: 14px;
                box-shadow: 0 10px 24px var(--thy-shadow);
                margin-bottom: 14px;
                text-align: center;
            }}
            .sidebar-brand-box p {{
                margin: 8px 0 0 0;
                font-size: .92rem;
                color: #3a3132;
            }}
            .stButton > button, .stDownloadButton > button {{
                border-radius: 12px;
                border: 1px solid var(--thy-red);
                background: #b80f2c;
                color: #fffdfb;
                font-weight: 600;
                padding: 0.55rem 1rem;
            }}
            .stButton > button:hover, .stDownloadButton > button:hover {{
                border-color: var(--thy-red-dark);
                background: #970d25;
                color: #fffdfb;
            }}
            .stTabs [data-baseweb="tab-list"] {{
                gap: 8px;
                padding-bottom: 6px;
            }}
            .stTabs [data-baseweb="tab"] {{
                background: #fffdf9;
                border-radius: 12px;
                border: 1px solid var(--thy-border);
                padding: 10px 18px;
                height: auto;
                box-shadow: 0 2px 8px rgba(90, 40, 48, 0.035);
            }}
            .stTabs [aria-selected="true"] {{
                background: #fbecee !important;
                border-color: #f0b6bf !important;
                color: var(--thy-red-dark) !important;
                font-weight: 700;
            }}
            .stTextArea textarea,
            .stTextInput input,
            .stSelectbox [data-baseweb="select"] > div,
            .stFileUploader > div {{
                border-radius: 14px !important;
            }}
            div[data-testid="stExpander"] {{
                border: 1px solid var(--thy-border);
                border-radius: 16px;
                background: rgba(255,251,246,.84);
            }}

            /* Minimal, responsive business dashboard */
            .jw-stats-grid {{
                display: grid;
                grid-template-columns: repeat(5, minmax(0, 1fr));
                gap: 13px;
                margin: 0 0 23px 0;
            }}
            .jw-stat {{
                --accent: #171717;
                --soft: #f4f0eb;
                background: #fffdfa;
                border: 1px solid #e7ddd1;
                border-radius: 17px;
                padding: 17px 18px 15px;
                position: relative;
                overflow: hidden;
                box-shadow: 0 5px 17px rgba(28, 23, 25, 0.035);
                min-height: 158px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
            }}
            .jw-stat::before {{
                content: "";
                position: absolute;
                height: 4px;
                top: 0;
                left: 0;
                right: 0;
                background: var(--accent);
            }}
            .jw-stat-total {{ --accent: #171717; --soft: #eeeeea; }}
            .jw-stat-negative {{ --accent: #c8102e; --soft: #fbe8ec; }}
            .jw-stat-positive {{ --accent: #246c50; --soft: #e5f3e9; }}
            .jw-stat-progress {{ --accent: #99763b; --soft: #f6eddf; }}
            .jw-stat-review {{ --accent: #5e5269; --soft: #eee9f3; }}
            .jw-stat-head {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 8px;
            }}
            .jw-stat-label {{ color: #514a45; font-size: .82rem; font-weight: 600; line-height: 1.2; }}
            .jw-stat-icon {{
                display: inline-flex;
                justify-content: center;
                align-items: center;
                width: 31px;
                height: 31px;
                border-radius: 10px;
                background: var(--soft);
                color: var(--accent);
                font-size: .95rem;
                font-weight: 800;
                flex: 0 0 31px;
            }}
            .jw-stat-value {{
                font-size: clamp(2rem, 3vw, 2.8rem);
                letter-spacing: -.06em;
                font-weight: 780;
                line-height: 1.05;
                color: var(--accent);
                font-variant-numeric: tabular-nums;
                margin: 10px 0 12px;
            }}
            .jw-stat-track {{ height: 5px; border-radius: 999px; background: var(--soft); overflow: hidden; }}
            .jw-stat-fill {{ height: 100%; background: var(--accent); border-radius: inherit; }}
            .jw-stat-foot {{ display: flex; justify-content: space-between; gap: 6px; color: #786f69; font-size: .72rem; margin-top: 8px; }}
            .jw-stat-foot strong {{ font-weight: 750; color: var(--accent); }}
            .jw-stats-caption {{ color: #746e66; font-size: .77rem; margin-top: -10px; margin-bottom: 15px; }}
            @media (max-width: 1050px) {{
                .jw-stats-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
            }}
            @media (max-width: 670px) {{
                .jw-stats-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
                .jw-stat {{ padding: 13px; min-height: 140px; }}
                .jw-stat-value {{ font-size: 2.05rem; }}
                .jw-stat-label {{ font-size: .78rem; }}
            }}
            .stTabs [data-baseweb="tab-highlight"] {{ background: #c8102e; }}
            .stTabs [data-baseweb="tab-border"] {{ background: #e9dfd4; }}
            .stSelectbox label, .stTextInput label {{ font-weight: 650; }}
            .stTextInput input:focus, .stTextArea textarea:focus {{ border-color: #c8102e; }}
            div[data-testid="stDataFrame"] {{ border-radius: 12px; overflow: hidden; }}

            .tip-list {{ margin: 0; padding-left: 18px; }}
            .tip-list li {{ margin-bottom: 6px; }}
        </style>
        """,
        unsafe_allow_html=True,
    )



def render_sidebar_branding() -> None:
    thy = ASSETS_DIR / "thy_logo.png"
    st.markdown('<div class="sidebar-brand-box">', unsafe_allow_html=True)
    if thy.is_file():
        st.image(str(thy), use_container_width=True)
    st.markdown(
        "<p><strong>Kurumsal Tema</strong><br/>Kırmızı · Siyah · Krem</p></div>",
        unsafe_allow_html=True,
    )




@st.cache_data(show_spinner="Veriler kontrol ediliyor...")
def load_excel(contents):
    source = io.BytesIO(contents)
    xlsx = pd.ExcelFile(source)
    return {
        name: pd.read_excel(
            xlsx, sheet_name=name, dtype={"Başvuru ID": str, "Kayıt ID": str}
        )
        for name in xlsx.sheet_names
    }


inject_theme()
for key, default in {
    "drafts": {},
    "answers": {},
    "period_done": {},
    "batch": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

with st.sidebar:
    render_sidebar_branding()
    st.header("📂 Veri kaynağı")
    file = st.file_uploader("02_Veriler.xlsx dosyasını yükleyin", type="xlsx")
    st.caption("İK onayları yalnızca bu oturumda saklanır. Gerçek e-posta gönderimi yapılmaz.")
    with st.expander("İsteğe bağlı Groq AI", expanded=False):
        groq_key = st.text_input("Groq API anahtarı", type="password", key="groq_key")
        groq_model = st.text_input("Groq model adı", value="llama-3.3-70b-versatile", key="groq_model")
        groq_consent = st.checkbox("Taslak metninin Groq'a gönderilmesini kabul ediyorum.", key="groq_consent")
        st.caption("Yalnızca görüntülenen taslak metinleri gönderilir. API anahtarı ve metinler üçüncü taraf hizmete iletilir; kurumunuzun veri politikalarına uygun kullanın.")

if file:
    file_bytes = file.getvalue()
elif os.path.isfile("02_Veriler.xlsx"):
    with open("02_Veriler.xlsx", "rb") as fh:
        file_bytes = fh.read()
else:
    st.info("Devam etmek için sol taraftan Excel dosyasını yükleyin.")
    st.stop()

try:
    data = load_excel(file_bytes)
except Exception as exc:
    st.error(f"Veri dosyası açılamadı: {exc}")
    st.stop()

missing = [s for s in REQUIRED if s not in data]
if missing:
    st.error("Gerekli sekmeler eksik: " + ", ".join(missing))
    st.stop()

bids = data["Başvuru Kararları"]["Başvuru ID"].dropna().astype(str).unique().tolist()
if not bids:
    st.warning("Başvuru kaydı yok.")
    st.stop()

results = {bid: evaluate(bid, data) for bid in bids}
counts = data["Başvuru Kararları"]["İK’nın kaydettiği başvuru sonucu (kod)"].astype(str).value_counts()
# Özet kartları: İK inceleme, karar türlerinden bağımsız bir inceleme kuyruğudur.
total_count = len(bids)
negative_count = int(counts.get("OLUMSUZ", 0))
positive_count = int(counts.get("KABUL", 0))
progress_count = int(counts.get("DEVAM_EDIYOR", 0))
review_count = sum(r["kuyruk"] == "IK_INCELEME" for r in results.values())


def stat_card(label, value, tone, symbol, foot_label):
    percent = (value / total_count * 100) if total_count else 0
    return (
        f'<div class="jw-stat jw-stat-{tone}">'
        f'<div class="jw-stat-head"><span class="jw-stat-label">{label}</span>'
        f'<span class="jw-stat-icon" aria-hidden="true">{symbol}</span></div>'
        f'<div class="jw-stat-value">{value:,}</div>'
        f'<div class="jw-stat-track" aria-hidden="true"><div class="jw-stat-fill" style="width:{min(percent,100):.1f}%"></div></div>'
        f'<div class="jw-stat-foot"><span>{foot_label}</span><strong>%{percent:.0f}</strong></div>'
        '</div>'
    )


st.markdown(
    '<div class="jw-stats-grid">'
    + stat_card("Toplam başvuru", total_count, "total", "≡", "Tüm kayıtlar")
    + stat_card("Olumsuz", negative_count, "negative", "−", "Başvuruların")
    + stat_card("Kabul", positive_count, "positive", "✓", "Başvuruların")
    + stat_card("Devam ediyor", progress_count, "progress", "↗", "Başvuruların")
    + stat_card("İK incelemesi", review_count, "review", "!", "Başvuruların")
    + '</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="jw-stats-caption">İK incelemesi ayrı bir karar türü değil, mevcut başvurular içindeki kontrol kuyruğudur.</p>',
    unsafe_allow_html=True,
)


tabs = st.tabs(
    [
        "📩 Taslak ve İK onayı",
        "📦 Toplu gönderime hazırlık",
        "💬 Gelen yanıtlar",
        "📊 Kayıt ve rapor",
    ]
)

with tabs[0]:
    # Filtreler kayıtların karar ve aşama alanlarını kullanır; e-posta metnine dayanmaz.
    st.subheader("Aday bul")
    filter_col1, filter_col2, filter_col3 = st.columns([1, 1.3, 1.3])
    with filter_col1:
        decision_filter = st.selectbox(
            "Başvuru kararı",
            ["Tümü", "OLUMSUZ", "KABUL", "DEVAM_EDIYOR"],
            format_func=lambda value: {
                "Tümü": "Tüm kararlar", "OLUMSUZ": "Olumsuz",
                "KABUL": "Kabul", "DEVAM_EDIYOR": "Devam ediyor",
            }.get(value, value),
            key="candidate_decision_filter",
        )
    with filter_col2:
        stage_options = sorted({r["asama"] for r in results.values() if r["asama"]})
        stage_filter = st.selectbox(
            "Değerlendirme aşaması",
            ["Tümü"] + stage_options,
            format_func=lambda value: "Tüm aşamalar" if value == "Tümü" else value.replace("_", " ").title(),
            key="candidate_stage_filter",
        )
    with filter_col3:
        id_search = st.text_input(
            "Başvuru veya anonim aday ID ile ara",
            placeholder="Örn. BSV-078, 078 veya ADY-078",
            key="candidate_id_search",
        ).strip().casefold()

    anonymous_by_bid = {}
    applicant_frame = data.get("Başvuru Listesi")
    if applicant_frame is not None and {"Başvuru ID", "Anonim aday ID"}.issubset(applicant_frame.columns):
        anon_rows = applicant_frame.dropna(subset=["Başvuru ID"]).drop_duplicates("Başvuru ID", keep="last")
        anonymous_by_bid = {str(row["Başvuru ID"]): str(row["Anonim aday ID"]) for _, row in anon_rows.iterrows() if pd.notna(row["Anonim aday ID"])}

    filtered_bids = [
        bid for bid in bids
        if (decision_filter == "Tümü" or results[bid]["karar"] == decision_filter)
        and (stage_filter == "Tümü" or results[bid]["asama"] == stage_filter)
        and (not id_search or id_search in bid.casefold() or id_search in anonymous_by_bid.get(bid, "").casefold())
    ]
    st.caption(f"{len(filtered_bids)} / {len(bids)} başvuru bulundu")
    if filtered_bids:
        with st.expander("Filtrelenmiş başvuruları listele", expanded=False):
            st.dataframe(
                pd.DataFrame([
                    {
                        "Başvuru ID": bid,
                        "Anonim aday ID": anonymous_by_bid.get(bid, "—"),
                        "Karar": results[bid]["karar"],
                        "Aşama": results[bid]["asama"],
                        "İşlem": results[bid]["kuyruk"],
                    }
                    for bid in filtered_bids
                ]),
                hide_index=True,
                use_container_width=True,
            )
    else:
        st.info("Bu filtrelere uygun başvuru bulunamadı. Karar, aşama veya arama metnini değiştirin.")

    if filtered_bids:
        col1, col2 = st.columns([1, 2])
        with col1:
            selected = st.selectbox(
                "Başvuru ID",
                filtered_bids,
                index=filtered_bids.index("BSV-002") if "BSV-002" in filtered_bids else 0,
            )
            result = results[selected]
            st.write("**Karar:**", result["karar"])
            st.write("**Aşama:**", result["asama"])
            st.write("**Şablon:**", result["sablon"])
            st.write("**İşlem:**", result["kuyruk"])
            st.write("**Dayanak kayıtlar:**", ", ".join(result["context"]["dayanak_ids"]) or "—")
            if result["hatalar"]:
                st.error("İK incelemesi gerekli; aday taslağı oluşturulamaz.")
                for issue in result["hatalar"]:
                    st.write("• " + issue)
            elif result["kuyruk"] == "AYRI_ILETISIM_AKISI":
                st.info(
                    "Bu karar için ret mesajı üretilmez. Kabul veya süreç iletişimi ayrı İK akışında hazırlanmalıdır."
                )
            else:
                st.success("Kaynak denetimi tamamlandı; e-posta taslağı üretilebilir.")
        with col2:
            ctx = result["context"]
            st.subheader("İK kanıt ekranı")
            with st.expander("Önceki başarıların dayanakları", expanded=True):
                if ctx["basarilar"]:
                    st.dataframe(pd.DataFrame(ctx["basarilar"]), hide_index=True, use_container_width=True)
                else:
                    st.caption(
                        "İK tarafından doğrulanmış önceki aşama başarısı kaydı bulunmuyor; başarı iddiası eklenmeyecek."
                    )
            x, y = st.columns(2)
            with x:
                st.write("**İK ret gerekçesi:**", ctx["ik_gerekce"] or "—")
                st.write("**Ret türü:**", ctx["ret_turu"] or "—")
                st.write("**Beceri kodu:**", ctx["beceri"] or "—")
                st.write(
                    "**Alt kategori:**",
                    ctx["alt_kategori"]["kod"] if ctx["alt_kategori"] else "—",
                )
            with y:
                st.write("**Paylaşım izinleri**")
                if ctx["paylasim"]:
                    st.dataframe(pd.DataFrame(ctx["paylasim"]), hide_index=True, use_container_width=True)
                else:
                    st.caption("Paylaşılabilir kaynak bilgisi yok.")
            with st.expander("Kaynak gözlemler (yalnızca İK)"):
                if ctx["gozlemler"]:
                    st.dataframe(pd.DataFrame(ctx["gozlemler"]), hide_index=True, use_container_width=True)
                else:
                    st.caption("Kayıtlı bir değerlendirme gözlemi yok.")
            with st.expander("Sınav/bölüm sonuçları (gizli barajlar gösterilmez)"):
                if ctx["puanlar"]:
                    st.dataframe(pd.DataFrame(ctx["puanlar"]), hide_index=True, use_container_width=True)
                else:
                    st.caption("Puan kaydı yok.")

        fingerprint = application_hash(selected, data)
        stored = st.session_state["drafts"].get(selected)
        if stored and (stored["source_hash"] != fingerprint or "edited_en" not in stored):
            del st.session_state["drafts"][selected]
            stored = None
            st.warning("Kaynak kayıt değişti: eski taslak ve İK onayı geçersiz bırakıldı.")

        if result["kuyruk"] == "TASLAK_UYGUN":
            st.divider()
            st.subheader("Aday e-postası")
            if st.button("Kanıta dayalı e-posta taslağı üret", type="primary"):
                draft = make_email(result)
                draft_en = make_email_en(result)
                st.session_state["drafts"][selected] = {
                    "source_hash": fingerprint,
                    "original": draft,
                    "edited": draft,
                    "original_en": draft_en,
                    "edited_en": draft_en,
                    "approved": False,
                    "approval_hash": None,
                    "approved_at": None,
                    "template": result["sablon"],
                    "stage": result["asama"],
                    "status": result["karar"],
                }
                st.success("Yeni taslak oluşturuldu. İK onayı bekliyor.")

            stored = st.session_state["drafts"].get(selected)
            if stored:
                new_text = st.text_area(
                    "🇹🇷 Türkçe e-posta taslağı (düzenlenebilir)",
                    value=stored["edited"],
                    height=320,
                    key=f"draft_input_{selected}_{fingerprint}",
                )
                if new_text != stored["edited"]:
                    stored["edited"] = new_text
                    stored["approved"] = False
                    stored["approval_hash"] = None
                    stored["approved_at"] = None
                    st.warning("Taslak değiştirildi; önceki İK onayı sıfırlandı.")

                new_text_en = st.text_area(
                    "🇬🇧 English email draft (editable)",
                    value=stored["edited_en"],
                    height=320,
                    key=f"draft_en_input_{selected}_{fingerprint}",
                )
                if new_text_en != stored["edited_en"]:
                    stored["edited_en"] = new_text_en
                    stored["approved"] = False
                    stored["approval_hash"] = None
                    stored["approved_at"] = None
                    st.warning("İngilizce taslak değiştirildi; önceki İK onayı sıfırlandı.")

                st.caption(
                    "Önemli: Düzenlenen metin otomatik olarak semantik denetlenmez. İK, gizli baraj veya kanıtsız iddia eklenmediğini kontrol etmelidir."
                )
                with st.expander("Türkçe–İngilizce tutarlılık kontrolü", expanded=False):
                    parity_issues = bilingual_check(new_text, new_text_en, ctx["ret_turu"])
                    if parity_issues:
                        for issue in parity_issues:
                            st.warning(issue)
                    else:
                        st.success("Temel sayı, kimlik kodu ve karar işaretleri uyumlu görünüyor.")
                    st.caption("Bu otomatik kontrol anlamsal eşdeğerliği garanti etmez. İK iki metni de incelemelidir.")

                with st.expander("Groq AI ile dil düzenleme önerisi (isteğe bağlı)", expanded=False):
                    st.caption("Groq yalnızca görüntülenen aday e-posta metnini alır; Excel kaynakları aktarılmaz. AI yanıtları otomatik olarak onaylı taslağın yerine geçmez.")
                    if st.button("İki dilde AI önerisi üret", key=f"groq_{selected}", disabled=not groq_key or not groq_consent):
                        try:
                            with st.spinner("Groq taslakları düzenliyor..."):
                                tr_ai = polish_via_groq(new_text, "tr", groq_key, groq_model)
                                en_ai = polish_via_groq(new_text_en, "en", groq_key, groq_model)
                            st.session_state["ai_suggestions"] = {
                                "bid": selected, "source_hash": fingerprint, "draft_hash": sha([new_text, new_text_en]),
                                "tr": tr_ai, "en": en_ai,
                            }
                        except Exception as exc:
                            st.error(f"Groq isteği başarısız: {exc}. Mevcut taslaklar değişmedi.")
                    ai = st.session_state.get("ai_suggestions")
                    if ai and ai["bid"] == selected and ai["source_hash"] == fingerprint and ai["draft_hash"] == sha([new_text, new_text_en]):
                        tr_flags = suggestion_issues(new_text, ai["tr"], validate_edit, selected, ctx["ret_turu"], "tr")
                        en_flags = suggestion_issues(new_text_en, ai["en"], validate_edit, selected, ctx["ret_turu"], "en")
                        parity_flags = bilingual_check(ai["tr"], ai["en"], ctx["ret_turu"])
                        if tr_flags or en_flags or parity_flags:
                            st.error("AI önerilerinde otomatik kontrol uyarıları var; doğrudan kullanmayın.")
                            for issue in tr_flags + en_flags + parity_flags:
                                st.warning(issue)
                        else:
                            st.info("Temel kontroller geçti. İçeriğin doğruluğu ve gizlilik için İK incelemesi yine zorunlu.")
                        st.text_area("AI Türkçe öneri (salt okunur)", ai["tr"], height=240, disabled=True, key=f"ai_tr_{selected}")
                        st.text_area("AI English suggestion (read-only)", ai["en"], height=240, disabled=True, key=f"ai_en_{selected}")
                        st.caption("Uygun bulduğunuz metni yukarıdaki düzenlenebilir taslaklara elle taşıyın; mevcut İK onayı değişiklikle sıfırlanır.")

                edited_issues = validate_edit(selected, new_text) + validate_edit(selected, new_text_en)
                for issue in edited_issues:
                    st.error(issue)

                checked = st.checkbox(
                    "Kaynak kayıtlarını, paylaşım izinlerini ve Türkçe/İngilizce taslakların ikisini de kontrol ettim.",
                    key=f"approve_check_{selected}_{sha([new_text, new_text_en])}",
                )
                if st.button(
                    "İK ONAYI VER",
                    disabled=not checked or not new_text.strip() or not new_text_en.strip() or bool(edited_issues),
                ):
                    stored["approval_hash"] = sha(
                        {
                            "source": fingerprint,
                            "text": new_text,
                            "text_en": new_text_en,
                            "template": stored["template"],
                        }
                    )
                    stored["approved"] = True
                    stored["approved_at"] = datetime.now().isoformat(timespec="seconds")
                    st.success("Bireysel İK onayı kaydedildi. E-posta gönderilmedi.")
                if stored["approved"]:
                    st.success("Onaylı: " + str(stored["approved_at"]))
        elif stored:
            del st.session_state["drafts"][selected]
            st.warning("Artık uygun olmayan kaydın taslağı/onayı kaldırıldı.")

with tabs[1]:
    st.subheader("Aşama bazlı gönderim hazırlığı")
    st.caption(
        "Bireysel İK onayı + kesinleşmiş aşama koşulu sağlanmadan satır toplu listeye alınmaz. Bu ekran gerçek gönderim yapmaz."
    )
    stages = list(dict.fromkeys(r["asama"] for r in results.values() if r["karar"] == "OLUMSUZ"))
    stage = st.selectbox("Sonuçları kesinleşen aşama", stages)
    done = st.checkbox(
        "Bu aşamadaki tüm sonuçların kesinleştiğini İK olarak doğruluyorum",
        key=f"done_{stage}",
    )
    approved, blocked = [], []
    for bid, r in results.items():
        if r["asama"] != stage or r["karar"] != "OLUMSUZ":
            continue
        d = st.session_state["drafts"].get(bid)
        if r["kuyruk"] != "TASLAK_UYGUN":
            blocked.append({"Başvuru ID": bid, "Neden": "İK incelemesi gerekli"})
        elif not d or not d.get("approved"):
            blocked.append({"Başvuru ID": bid, "Neden": "Bireysel onay yok"})
        elif validate_edit(bid, d["edited"]) or validate_edit(bid, d["edited_en"]):
            blocked.append({"Başvuru ID": bid, "Neden": "Taslak güvenlik denetimi geçersiz"})
        elif d["source_hash"] != application_hash(bid, data) or d.get("approval_hash") != sha(
            {
                "source": d["source_hash"],
                "text": d["edited"],
                "text_en": d["edited_en"],
                "template": d["template"],
            }
        ):
            blocked.append({"Başvuru ID": bid, "Neden": "Veri/taslak değişmiş; onay geçersiz"})
        else:
            approved.append(
                {
                    "Başvuru ID": bid,
                    "Karar": r["karar"],
                    "Aşama": stage,
                    "Şablon": d["template"],
                    "İK onay zamanı": d["approved_at"],
                    "Türkçe E-posta Taslağı": d["edited"],
                    "İngilizce E-posta Taslağı": d["edited_en"],
                }
            )

    a, b = st.columns(2)
    a.metric("Bireysel onaylı", len(approved))
    b.metric("Bekleyen / inceleme", len(blocked))
    if blocked:
        with st.expander("Gönderime alınmayan kayıtlar"):
            st.dataframe(pd.DataFrame(blocked), hide_index=True, use_container_width=True)
    if done and approved:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(approved[0]), delimiter=";")
        writer.writeheader()
        writer.writerows(approved)
        st.download_button(
            "Onaylı bildirimleri CSV olarak indir (gönderim yok)",
            output.getvalue().encode("utf-8-sig"),
            file_name=f"junior_wings_onayli_{stage.lower()}.csv",
            mime="text/csv",
            type="primary",
        )
    elif not done:
        st.info("Aşama sonuçlarının kesinleşmesi onaylanmadan toplu liste hazırlanamaz.")
    else:
        st.info("Bu aşamada güncel bireysel İK onaylı bildirim bulunmuyor.")

with tabs[2]:
    st.subheader("Aday yanıtı / itiraz incelemesi")
    st.caption(
        "Gelen kutusuyla entegrasyon yoktur. Adayın mesajı İK tarafından buraya girilir; yanıtlar İK onayından önce dışarı gönderilmez."
    )
    rbid = st.selectbox("İletinin başvuru ID'si", bids, key="incoming_bid")
    incoming = st.text_area("Adayın gelen mesajı", height=130, key="incoming_message")
    if st.button("Mesajı sınıflandır ve yanıt öner"):
        if not incoming.strip():
            st.warning("Önce gelen mesajı girin.")
        else:
            cat = classify_reply(incoming)
            key = sha({"bid": rbid, "incoming": incoming})
            proposal = reply_suggestion(
                rbid,
                cat,
                st.session_state["drafts"].get(rbid, {}).get("edited", ""),
            )
            st.session_state["answers"][key] = {
                "bid": rbid,
                "category": cat,
                "incoming": incoming,
                "text": proposal,
                "approved": False,
                "approved_at": None,
            }
    matching = [(k, v) for k, v in st.session_state["answers"].items() if v["bid"] == rbid]
    for key, reply in matching:
        st.write("**Tür:**", reply["category"])
        st.caption("Kaynak ileti: " + reply["incoming"][:240])
        edited_reply = st.text_area(
            "İK yanıt önerisi (manuel düzenlenebilir)",
            value=reply["text"],
            key=f"reply_{key}",
            height=180,
        )
        if edited_reply != reply["text"]:
            reply["text"] = edited_reply
            reply["approved"] = False
            reply["approved_at"] = None
        if st.button(
            "Yanıt taslağını İK olarak onayla",
            key=f"approve_reply_{key}",
            disabled=not reply["text"].strip(),
        ):
            reply["approved"] = True
            reply["approved_at"] = datetime.now().isoformat(timespec="seconds")
            st.success("Yanıt onaylandı (gönderilmedi).")
        if reply["approved"]:
            st.success("İK onaylı yanıt — " + reply["approved_at"])

with tabs[3]:
    st.subheader("Karar ve taslak raporu")
    report = []
    for bid, r in results.items():
        d = st.session_state["drafts"].get(bid)
        valid = bool(
            d
            and d.get("approved")
            and d["source_hash"] == application_hash(bid, data)
            and d["approval_hash"]
            == sha(
                {
                    "source": d["source_hash"],
                    "text": d["edited"],
                    "text_en": d["edited_en"],
                    "template": d["template"],
                }
            )
            and not validate_edit(bid, d["edited"])
            and not validate_edit(bid, d["edited_en"])
        )
        report.append(
            {
                "Başvuru ID": bid,
                "Karar": r["karar"],
                "Aşama": r["asama"],
                "Şablon": r["sablon"],
                "Kuyruk": r["kuyruk"],
                "İK onayı": "GEÇERLİ" if valid else "YOK",
                "İnceleme nedeni": "; ".join(r["hatalar"]),
            }
        )
    st.dataframe(pd.DataFrame(report), hide_index=True, use_container_width=True)
    if st.session_state["answers"]:
        freq = (
            pd.Series([x["category"] for x in st.session_state["answers"].values()])
            .value_counts()
            .rename_axis("Soru türü")
            .reset_index(name="Adet")
        )
        st.write("**Tekrarlanan soru türleri**")
        st.dataframe(freq, hide_index=True, use_container_width=True)
    st.caption(
        "Bu çalışma bir gönderim servisi, kullanıcı yetkilendirme veya kalıcı kayıt altyapısı içermez. Üretim kullanımı öncesi bunlar ayrıca kurulmalıdır."
    )
