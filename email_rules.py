"""Junior Wings: kanıta dayalı e-posta kuralları. Harici LLM kullanılmaz.
Kural motoru güvenli olmayan veriden metin üretmez; gönderim gerçekleştirmez.
"""
import hashlib
import json
import re
from datetime import datetime, timezone

STAGE_NAMES = {"SINAV": "Genel Yetenek ve İngilizce Testi", "VIDEO": "Video Mülakat", "GRUP": "Grup Çalışması", "INGILIZCE": "İngilizce Görüşme", "IK_TEKNIK": "İK ve Birim Mülakatı"}
SUBCATEGORY = {
    "IFT-01": [("somut_katki", ("kendi katkı", "kişisel katkı", "attığı adım", "üstlendiği adım", "somutlaştır", "kendi rol", "sorumluluğ"), "Kendi katkısını ve uyguladığı adımları somut örneklerle anlatma")],
    "EKP-01": [("gorev_paylasimi", ("görev", "iş bölümü", "ortak", "katkı"), "Ortak görevlerde sorumluluk paylaşımını ve katkıyı somutlaştırma")],
    "PLN-01": [("bagimlilik_planlama", ("bağımlılı", "gecik", "sıralama", "iş planı"), "Görev bağımlılıklarını ve gecikmenin olası etkilerini açıklama")],
    "ANL-01": [("gerekcelendirme", ("gerekçe", "veri", "karar", "çözüm"), "Kararlarını somut verilerle gerekçelendirme")],
    "ING-01": [("anlama", ("anlama", "talimat", "ana fikir"), "Verilen talimatı ve ana fikri doğru anlama")],
}
GENERAL_CATEGORIES = [
    ("takip_sorusu", ("takip soru", "soruya", "sorulan", "yanıt", "cevap"), "Sorulara doğrudan ve açık yanıt verme"),
    ("zaman_aksiyon", ("zaman", "ne zaman", "aksiyon", "sonraki adım", "güncelleme"), "Zaman ve sonraki adım bilgisini açıklığa kavuşturma"),
    ("somut_ornek", ("somut", "örnek", "kendi katkı", "attığı adım"), "Somut örnek ve kişisel katkıyla açıklama yapma"),
    ("ekip_calismasi", ("ekip", "ortak", "görev", "iş bölümü"), "Ortak görevlerde rol ve katkıyı belirginleştirme"),
    ("gerekcelendirme", ("gerekçe", "veri", "çözüm"), "Karar ve çözüm tercihlerini gerekçelendirme"),
]


def sval(x):
    if x is None:
        return ""
    s = str(x).strip()
    return "" if s.lower() in ("nan", "none", "nat", "null") else s


def rows(data, sheet, bid=None):
    df = data.get(sheet)
    if df is None:
        return []
    if bid is not None and "Başvuru ID" in df.columns:
        df = df[df["Başvuru ID"].astype(str) == str(bid)]
    return df.where(df.notna(), None).to_dict("records")


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def application_hash(bid, data):
    payload = {s: rows(data, s, bid if s not in ("Beceri Tanımları", "Program Aşamaları", "Paylaşım Kuralları") else None) for s in (
        "Başvuru Kararları", "Başvuru Listesi", "Aşama Kayıtları", "Sınav Sonuçları", "İngilizce Görüşme Sonuçları", "İK Değerlendirme Notları", "Beceri Tanımları", "Program Aşamaları", "Paylaşım Kuralları")}
    return sha(payload)


def ids(x):
    return [v.strip() for v in sval(x).split(";") if v.strip()]


def current_records(records):
    replaced = {sval(r.get("Bu kaydın düzelttiği eski kayıt ID")) for r in records}
    return [r for r in records if sval(r.get("Kayıt ID")) not in replaced]


def is_shared(row):
    return sval(row.get("Bilginin adayla paylaşılma durumu (kod)")) == "PAYLASILABILIR"


def detect_category(skill, observation, justification):
    """Gözlem ve İK gerekçesi aynı somut alt kategoriye işaret etmedikçe eşleştirme yapmaz."""
    o, j = observation.casefold(), justification.casefold()
    pool = SUBCATEGORY.get(skill, GENERAL_CATEGORIES)
    for key, terms, advice in pool:
        if any(t in o for t in terms) and any(t in j for t in terms):
            return {"kod": key, "etiket": advice}
    return None


def safe_observation(text):
    text = sval(text)
    for prefix in (
        "İnsan değerlendirici, kaydedilmiş yanıtı inceledi.",
        "Grup oturumunda verilen ortak görev gözlendi.",
        "İş birimi örnek görevinin yazılı insan değerlendirmesi.",
        "İngilizce yeterlilik görüşmesine ilişkin yazılı insan kaydı.",
        "Bu gözlem yalnız bu soru ve yanıtla sınırlıdır.",
        "Gözlem bu görüşmeyle sınırlıdır.",
    ):
        text = text.replace(prefix, "")
    return " ".join(text.split()).strip()


def verified_successes(bid, data, failed_stage):
    """Yalnız sınav GECTI veya önceki aşamadaki açık İK geçiş kararı başarıdır."""
    stages = rows(data, "Program Aşamaları")
    order = {sval(r.get("Aşama kodu")): int(r.get("Sıra")) for r in stages if sval(r.get("Sıra"))}
    cutoff = order.get(failed_stage, 999)
    evidence, issues = [], []
    exam = current_records(rows(data, "Sınav Sonuçları", bid))
    if order.get("SINAV", 999) < cutoff and exam:
        names = {"GENEL_YETENEK": "Genel Yetenek", "INGILIZCE": "İngilizce"}
        by_part = {}
        for r in exam:
            by_part.setdefault(sval(r.get("Sınav bölümü")), []).append(r)
        if all(len(by_part.get(k, [])) == 1 and sval(by_part[k][0].get("Sınav bölümünün sonucu (kod)")) == "GECTI" for k in names):
            if all(is_shared(by_part[k][0]) for k in names):
                evidence.append({"asama": "Sınav (her iki bölüm)", "kaynak": "; ".join(sval(by_part[k][0].get("Kayıt ID")) for k in names), "kanit": "Her iki bölüm GECTI"})
            else:
                issues.append("Geçilen sınavın başarı bilgisinde paylaşım izni eksik.")
    for r in rows(data, "Başvuru Kararları", bid):
        stage = sval(r.get("Aşama kodu"))
        decision = sval(r.get("İK’nın kaydettiği başvuru sonucu (kod)"))
        if stage in order and order[stage] < cutoff and stage != "SINAV" and decision == "DEVAM_EDIYOR" and sval(r.get("Kaydı oluşturan görevli (kod)")) == "IK_YETKILISI":
            evidence.append({"asama": STAGE_NAMES.get(stage, stage), "kaynak": sval(r.get("Kayıt ID")), "kanit": "Yetkili İK geçiş kararı"})
    return evidence, issues


def evaluate(bid, data):
    failures = []
    decisions = rows(data, "Başvuru Kararları", bid)
    if len(decisions) != 1:
        failures.append("Karar kaydı eksik veya birden fazla; güncel karar İK tarafından netleştirilmeli.")
    decision = decisions[-1] if decisions else {}
    stage = sval(decision.get("Aşama kodu"))
    status = sval(decision.get("İK’nın kaydettiği başvuru sonucu (kod)"))
    base = ids(decision.get("Kararın dayandığı kayıt ID’leri"))
    context = {"basvuru_id": bid, "asama": stage, "karar": status, "dayanak_ids": base, "ik_aciklama": sval(decision.get("İK’nın karar / süreç açıklaması")), "gozlemler": [], "beceri": "", "alt_kategori": None, "ret_turu": "", "ik_gerekce": "", "paylasim": [], "puanlar": [], "basarilar": []}
    if status not in ("OLUMSUZ", "KABUL", "DEVAM_EDIYOR"):
        failures.append("Başvuru kararı bilinmiyor.")
    if stage not in STAGE_NAMES:
        failures.append("Aşama kodu tanınmıyor.")
    if not base and status == "OLUMSUZ":
        failures.append("Olumsuz kararın kaynak kayıt ID'leri eksik.")
    successes, success_issues = verified_successes(bid, data, stage)
    context["basarilar"] = successes
    failures.extend(success_issues)
    if status in ("KABUL", "DEVAM_EDIYOR"):
        # Bu statüler ayrı akışta; tek başına otomatik karar metni üretilmez.
        return {"basvuru_id": bid, "karar": status, "asama": stage, "kuyruk": "AYRI_ILETISIM_AKISI" if not failures else "IK_INCELEME", "hatalar": failures, "context": context, "sablon": f"{status}_AYRI_AKIS"}
    if status != "OLUMSUZ":
        return {"basvuru_id": bid, "karar": status, "asama": stage, "kuyruk": "IK_INCELEME", "hatalar": failures, "context": context, "sablon": "YOK"}
    if stage == "SINAV":
        all_exam = rows(data, "Sınav Sonuçları", bid)
        active = current_records(all_exam)
        for did in base:
            match = [r for r in active if sval(r.get("Kayıt ID")) == did]
            if len(match) != 1 or sval(match[0].get("Sınav bölümünün sonucu (kod)")) != "GECEMEDI":
                failures.append(f"{did}: güncel ve başarısız sınav dayanağı doğrulanamadı.")
        for r in active:
            rid = sval(r.get("Kayıt ID"))
            if not is_shared(r):
                failures.append(f"{rid}: sınav sonucu paylaşım izni yok.")
            try:
                counts = [int(r[k]) for k in ("Soru sayısı", "Doğru sayısı", "Yanlış sayısı", "Boş sayısı")]
                if sum(counts[1:]) != counts[0] or min(counts) < 0:
                    failures.append(f"{rid}: soru sayıları tutarsız.")
                score = counts[1]
            except (TypeError, ValueError, KeyError):
                failures.append(f"{rid}: puan bilgisi eksik.")
                score = None
            context["puanlar"].append({"bolum": sval(r.get("Sınav bölümü")), "dogru": score, "toplam": r.get("Soru sayısı"), "sonuc": sval(r.get("Sınav bölümünün sonucu (kod)")), "kaynak": rid})
            context["paylasim"].append({"kaynak": rid, "izin": is_shared(r)})
        context["ret_turu"] = "SINAV_BOLUM_SONUCU"
        context["ik_gerekce"] = ", ".join(p["bolum"] for p in context["puanlar"] if p["kaynak"] in base)
        template = "OLUMSUZ_SINAV_" + "_".join(sorted({p["bolum"] for p in context["puanlar"] if p["kaynak"] in base}))
    elif stage == "INGILIZCE":
        ir = rows(data, "İngilizce Görüşme Sonuçları", bid)
        if len(ir) != 1 or not base or any(sval(r.get("Kayıt ID")) not in base for r in ir) or len(base) != 1:
            failures.append("İngilizce görüşmesinin güncel karar dayanağı benzersiz değil.")
        if ir:
            r = ir[-1]
            if sval(r.get("İngilizce görüşmesinin sonucu (kod)")) != "GECEMEDI":
                failures.append("İngilizce görüşmesi sonucu GECEMEDI değil.")
            if not is_shared(r):
                failures.append("İngilizce görüşmesi paylaşım izni bulunmuyor.")
            observation = safe_observation(r.get("Değerlendiricinin gözlemi / süreç notu"))
            if len(observation) < 12:
                failures.append("İngilizce görüşmesinde somut gözlem eksik.")
            context["gozlemler"].append({"kaynak": sval(r.get("Kayıt ID")), "metin": observation})
            context["paylasim"].append({"kaynak": sval(r.get("Kayıt ID")), "izin": is_shared(r)})
            context["puanlar"].append({"bolum": "Sözlü İngilizce", "dogru": r.get("İngilizce görüşme puanı"), "toplam": r.get("Alınabilecek en yüksek puan"), "kaynak": sval(r.get("Kayıt ID"))})
            # Ret gerekçesi sonuç kaydıdır; alt kategori ancak gözlemle gerekçenin aynı konuyu desteklediği ölçüde belirlenir.
            context["ik_gerekce"] = "İngilizce görüşme sonucunun GECEMEDI olarak kaydedilmesi"
            context["alt_kategori"] = None
            context["ret_turu"] = "INGILIZCE_GORUSME"
        template = "OLUMSUZ_INGILIZCE_GORUSME"
    elif stage in ("VIDEO", "GRUP", "IK_TEKNIK"):
        notes = rows(data, "İK Değerlendirme Notları", bid)
        notes = [r for r in notes if sval(r.get("Aşama kodu")) == stage]
        if len(notes) != 1:
            failures.append("İlgili aşamanın son İK gerekçesi tekil değil; İK incelemesi gerekir.")
        note = notes[-1] if notes else {}
        typ = sval(note.get("İK ret gerekçesinin türü (kod)"))
        reason = sval(note.get("İK tarafından kaydedilen ret gerekçesi"))
        skill = sval(note.get("Beceri kodu"))
        context.update({"ret_turu": typ, "ik_gerekce": reason, "beceri": skill, "ik_kayit": sval(note.get("Kayıt ID"))})
        if typ not in ("GEREKLILIK_KARSILANMADI", "KONTENJAN_KISITI"):
            failures.append("İK ret türü eksik veya geçersiz.")
        if not reason:
            failures.append("İK ret gerekçesi boş.")
        if sval(note.get("Gerekçenin paylaşımı için İK teyidi (kod)")) != "EVET":
            failures.append("İK gerekçesinin paylaşım teyidi bulunmuyor.")
        if set(ids(note.get("Gerekçenin dayandığı kayıt ID’leri"))) != set(base):
            failures.append("Son İK gerekçesinin kaynak ID'leri ile karar dayanakları uyuşmuyor.")
        context["paylasim"].append({"kaynak": sval(note.get("Kayıt ID")), "izin": sval(note.get("Gerekçenin paylaşımı için İK teyidi (kod)")) == "EVET"})
        active_stages = current_records(rows(data, "Aşama Kayıtları", bid))
        for did in base:
            matches = [r for r in active_stages if sval(r.get("Kayıt ID")) == did and sval(r.get("Aşama kodu")) == stage]
            if len(matches) != 1:
                failures.append(f"{did}: güncel aşama kaydı bulunamadı veya düzeltildi.")
                continue
            r = matches[0]
            observation = safe_observation(r.get("Değerlendiricinin gözlemi / süreç notu"))
            if not observation:
                failures.append(f"{did}: doğrulanabilir gözlem yok.")
            if any(bad in observation.casefold() for bad in ("kişiliği", "içine kapanık", "kişilik envanteri", "uyum sağlayamaz", "somut soru, yanıt veya davranış örneği kaydedilmedi")):
                failures.append(f"{did}: kişilik çıkarımı veya kanıtsız öznel yargı içeriyor.")
            if not is_shared(r):
                failures.append(f"{did}: gözlemin adayla paylaşım izni yok.")
            if skill and sval(r.get("Beceri kodu")) != skill and typ != "KONTENJAN_KISITI":
                failures.append(f"{did}: İK beceri kodu ile kaynak beceri kodu çelişiyor.")
            context["gozlemler"].append({"kaynak": did, "metin": observation})
            context["paylasim"].append({"kaynak": did, "izin": is_shared(r)})
        if typ == "GEREKLILIK_KARSILANMADI":
            skill_defs = [r for r in rows(data, "Beceri Tanımları") if sval(r.get("Beceri kodu")) == skill]
            if len(skill_defs) != 1:
                failures.append("Beceri kodu tanım tablosunda doğrulanamadı.")
            else:
                context["beceri_tanimi"] = sval(skill_defs[0].get("Beceri Tanımı"))
            cats = [detect_category(skill, item["metin"], reason) for item in context["gozlemler"]]
            if not cats or any(c is None for c in cats) or len(set(c["kod"] for c in cats if c)) != 1:
                failures.append("Beceri, somut gözlem ve İK gerekçesi için ortak alt kategori doğrulanamadı.")
            else:
                context["alt_kategori"] = cats[0]
            joined = " ".join(x["metin"].casefold() for x in context["gozlemler"])
            if "farklı sonuç içeriyor" in joined or "ortak değerlendirme notu henüz girilmedi" in joined or "beklentisini karşılayan" in joined:
                failures.append("Dayanak gözlemlerinde çelişki veya netleşmemiş değerlendirme var.")
        template = "OLUMSUZ_KONTENJAN" if typ == "KONTENJAN_KISITI" else f"OLUMSUZ_{stage}_{skill}_{context['alt_kategori']['kod'] if context['alt_kategori'] else 'BELIRSIZ'}"
    else:
        template = "YOK"
        failures.append("Olumsuz karara ilişkin desteklenen aşama yok.")
    return {"basvuru_id": bid, "karar": status, "asama": stage, "kuyruk": "IK_INCELEME" if failures else "TASLAK_UYGUN", "hatalar": sorted(set(failures)), "context": context, "sablon": template}


def make_email(result):
    if result["kuyruk"] != "TASLAK_UYGUN" or result["karar"] != "OLUMSUZ":
        raise ValueError("İnceleme veya ayrı iletişim akışındaki kayıttan e-posta üretilemez.")
    ctx = result["context"]
    bid, stage, typ = result["basvuru_id"], result["asama"], ctx["ret_turu"]
    text = ["Konu: Junior Wings Başvurunuz Hakkında Bilgilendirme", "", "Sayın Adayımız,", "", f"Junior Wings programına gösterdiğiniz ilgi ve {STAGE_NAMES[stage]} aşamasına katılımınız için teşekkür ederiz. Başvurunuzun bu aşamadaki değerlendirmesi olumsuz sonuçlanmıştır."]
    if ctx["basarilar"]:
        names = ", ".join(s["asama"] for s in ctx["basarilar"])
        text.append(f"Önceki değerlendirme sürecinizde {names} aşamasını başarıyla tamamladığınız doğrulanmıştır. Bu emeğiniz için ayrıca teşekkür ederiz.")
    if typ == "SINAV_BOLUM_SONUCU":
        failed = [p for p in ctx["puanlar"] if p["kaynak"] in ctx["dayanak_ids"]]
        names = {"GENEL_YETENEK": "Genel Yetenek", "INGILIZCE": "İngilizce"}
        text.append("Kararın dayanağı, " + ", ".join(names.get(p["bolum"], p["bolum"]) for p in failed) + " bölümünde kayıtlı sonucun geçiş koşulunu karşılamamasıdır.")
        for p in ctx["puanlar"]:
            text.append(f"{names.get(p['bolum'], p['bolum'])}: {p['toplam']} soruda {p['dogru']} doğru (Sonuç: {'Geçti' if p['sonuc'] == 'GECTI' else 'Geçemedi'}).")
        # Sayısal baraj ve bilinmeyen soru konuları asla paylaşılmaz.
        text.append("İlgili bölümde soru çözüm pratiği yaparak doğru yanıt oranınızı geliştirmeye odaklanabilirsiniz.")
    elif typ == "INGILIZCE_GORUSME":
        p = ctx["puanlar"][0]
        text.append(f"İngilizce görüşmesi için kayıtlı sonucunuz {p['toplam']} üzerinden {p['dogru']} puandır; bu aşamanın geçiş koşulu karşılanmamıştır.")
        # Gözlemle aynı alt kategori doğrulanmadıkça gelişim önerisi eklenmez.
    elif typ == "KONTENJAN_KISITI":
        text.append("Herhangi bir yetkinlik eksikliğine dayanmamakla birlikte sonucunuz olumsuz olmuştur.")
        text.append("Bu karar kontenjan planlamasıyla ilgilidir; bireysel yetkinliklerinizin yetersiz olduğuna ilişkin bir değerlendirme değildir.")
    else:
        text.append(f"Kararın kayıtlı gerekçesi: {ctx['ik_gerekce'].rstrip('.')}.")
        if ctx["alt_kategori"] and ctx["gozlemler"]:
            text.append("Değerlendirme kaydında, ilgili aşamada " + ctx["alt_kategori"]["etiket"].lower() + " alanına ilişkin bir gözlem yer almaktadır.")
            text.append("Gelişim önerisi: Benzer değerlendirmelerde " + ctx["alt_kategori"]["etiket"].lower() + " üzerine örneklerle pratik yapabilirsiniz.")
    text += ["", "Değerlendirme yalnızca ilgili başvuru aşamasına ilişkindir. Kariyer yolculuğunuzda başarılar dileriz.", "", "Saygılarımızla,", "Türk Hava Yolları İnsan Kaynakları"]
    draft = "\n\n".join(v for v in text if v != "")
    if re.search(r"geçme barajı\s*[:=]\s*\d|geçiş barajı\s*[:=]\s*\d", draft, re.I):
        raise ValueError("Gizli baraj bilgisi metne sızdı.")
    return draft



STAGE_NAMES_EN = {
    "SINAV": "General Aptitude and English Test",
    "VIDEO": "Video Interview",
    "GRUP": "Group Exercise",
    "INGILIZCE": "English Interview",
    "IK_TEKNIK": "HR and Department Interview",
}
SUCCESS_NAMES_EN = {
    "Sınav (her iki bölüm)": "both sections of the General Aptitude and English Test",
    "Video Mülakat": "the Video Interview",
    "Grup Çalışması": "the Group Exercise",
    "İngilizce Görüşme": "the English Interview",
    "İK ve Birim Mülakatı": "the HR and Department Interview",
}
CATEGORY_EN = {
    "somut_katki": "explaining your individual contributions and specific actions with concrete examples",
    "gorev_paylasimi": "clarifying the division of responsibilities and your contribution to shared tasks",
    "bagimlilik_planlama": "explaining task dependencies and the possible effects of delays",
    "gerekcelendirme": "supporting decisions with concrete evidence and clear reasoning",
    "anlama": "understanding instructions and the main point accurately",
    "takip_sorusu": "responding directly and clearly to follow-up questions",
    "zaman_aksiyon": "clarifying timelines and next steps",
    "somut_ornek": "using concrete examples to explain your personal contribution",
    "ekip_calismasi": "making your role and contribution to shared tasks clear",
}


def make_email_en(result):
    """Create an independent evidence-based English draft, not a free-form translation.

    Internal HR notes and candidate-specific unverified claims are never copied.
    """
    if result["kuyruk"] != "TASLAK_UYGUN" or result["karar"] != "OLUMSUZ":
        raise ValueError("An English draft cannot be created for an unapproved data status.")
    ctx = result["context"]
    bid, stage, typ = result["basvuru_id"], result["asama"], ctx["ret_turu"]
    parts = [
        "Subject: Update on Your Junior Wings Application",
        "Dear Applicant,",
        f"Thank you for your interest in the Junior Wings program and for participating in the {STAGE_NAMES_EN[stage]} stage. We regret to inform you that your application was unsuccessful at this stage.",
    ]
    if ctx["basarilar"]:
        successes = [SUCCESS_NAMES_EN.get(item["asama"]) for item in ctx["basarilar"]]
        if any(v is None for v in successes):
            raise ValueError("An earlier verified stage cannot be represented safely in English.")
        parts.append("Our records confirm that you successfully passed " + ", ".join(successes) + " in the earlier stages of the selection process. We appreciate your effort and achievement.")
    if typ == "SINAV_BOLUM_SONUCU":
        failed = [v for v in ctx["puanlar"] if v["kaynak"] in ctx["dayanak_ids"]]
        name = {"GENEL_YETENEK": "General Aptitude", "INGILIZCE": "English"}
        if not failed or any(v["bolum"] not in name for v in ctx["puanlar"]):
            raise ValueError("Unsupported exam section in English draft.")
        parts.append("The decision is based on the recorded result in the " + ", ".join(name[v["bolum"]] for v in failed) + " section(s), which did not meet the progression requirements.")
        for v in ctx["puanlar"]:
            outcome = "Passed" if v["sonuc"] == "GECTI" else "Not passed"
            parts.append(f"{name[v['bolum']]}: {v['dogru']} correct answers out of {v['toplam']} questions (Result: {outcome}).")
        parts.append("You may wish to improve your accuracy through further practice in the relevant test section(s).")
    elif typ == "INGILIZCE_GORUSME":
        v = ctx["puanlar"][0]
        parts.append(f"Your recorded score for the English Interview was {v['dogru']} out of {v['toplam']}. This result did not meet the requirements to progress beyond this stage.")
    elif typ == "KONTENJAN_KISITI":
        parts.append("Although the outcome of your application was unsuccessful, this decision was not based on any deficiency in your competencies.")
        parts.append("The decision was related to position availability and capacity planning; it should not be interpreted as an assessment that your individual competencies are insufficient.")
    elif typ == "GEREKLILIK_KARSILANMADI":
        cat = ctx.get("alt_kategori")
        if not cat or cat["kod"] not in CATEGORY_EN:
            raise ValueError("No verified English subcategory template is available.")
        label = CATEGORY_EN[cat["kod"]]
        parts.append(f"According to the recorded assessment, the requirements relating to {label} were not sufficiently demonstrated at this stage.")
        parts.append(f"Development suggestion: You may find it helpful to practice {label}, using specific examples from your own experience.")
    else:
        raise ValueError("Unsupported rejection reason for English draft.")
    parts.extend([
        "This assessment relates only to the relevant stage of your application. We wish you success in your future career.",
        "Kind regards,\nTurkish Airlines Human Resources",
    ])
    return "\n\n".join(parts)

def classify_reply(message):
    m = message.casefold()
    labels = [("ITIRAZ", ("itiraz", "yeniden değerlendir", "karara katılm")), ("PUAN_SORUSU", ("puan", "sonuç", "notum")), ("GEREKCE_SORUSU", ("neden", "gerekçe", "sebep")), ("YENIDEN_BASVURU", ("yeniden başvur", "tekrar başvur")), ("SUREC_SORUSU", ("ne zaman", "süreç", "sonraki aşama"))]
    return next((code for code, words in labels if any(w in m for w in words)), "DIGER")


def reply_suggestion(bid, category, approved_email):
    if category == "ITIRAZ":
        body = "İtirazınızın ilgili kayıtlar çerçevesinde İK tarafından değerlendirilmesi için talebiniz alınmıştır. İnceleme tamamlanmadan karar değişikliği veya sonuç garantisi veremeyiz."
    elif category == "PUAN_SORUSU":
        body = "Paylaşılmasına izin verilen puan ve bölüm bilgileri, daha önce onaylanan bildirimdeki kapsamla sınırlıdır. Ek bilgi talebiniz İK tarafından incelenecektir."
    elif category == "GEREKCE_SORUSU":
        body = "Gerekçe hakkında paylaşabileceğimiz bilgiler, İK tarafından onaylanan bildirimin kapsamıyla sınırlıdır. İletiniz incelenmek üzere kayda alınmıştır."
    else:
        body = "Sorunuz İK ekibimizin incelemesine sunulmuştur. Kesinleşmemiş süreç veya gelecek başvurular hakkında taahhütte bulunamıyoruz."
    return f"Konu: Junior Wings Başvurunuz Hakkındaki Mesajınız\n\nSayın Adayımız,\n\nMesajınız için teşekkür ederiz. {body}\n\nSaygılarımızla,\nTürk Hava Yolları İnsan Kaynakları"


def validate_edit(bid, text):
    """İK tarafından düzenlenen metin için otomatik asgari koruma; insan incelemesinin yerini almaz."""
    issues = []
    # Başvuru ID aday e-postasının zorunlu bir alanı değildir.
    # Kayıt/taslak eşleştirmesi ve İK onayı app.py içerisinde başvuru ID,
    # kaynak veri parmak izi ve iki e-posta metninin hash'i ile yürütülür.
    if re.search(r"(?:baraj|eşik|geçmek için gereken)[^\n.!?]{0,60}\d|\d+[^\n.!?]{0,35}(?:baraj|geçmek için gereken)", text, flags=re.I):
        issues.append("Sayısal geçme barajı/puan eşiği paylaşımı şüphesi var.")
    if re.search(r"(?:kesin kabul|garanti ed|iş teklifi sunuyoruz|bir sonraki başvurunuzda kabul|guaranteed acceptance|guarantee(?:d)? (?:admission|acceptance|employment)|we guarantee)", text, flags=re.I):
        issues.append("Kanıtlanmamış kabul/gelecek vaadi tespit edildi.")
    if re.search(r"(?:kişilik envanterine göre|kişilik tipiniz|liderlik kişiliğiniz|based on your personality inventory|your personality type)", text, flags=re.I):
        issues.append("Kişilik envanteri üzerinden paylaşılması yasak çıkarım var.")
    if re.search(r"(?:passing|pass|minimum|required) (?:score|threshold|mark)[^\n.!?]{0,30}\d|\d+[^\n.!?]{0,30}(?:passing threshold|minimum passing score)", text, flags=re.I):
        issues.append("Possible disclosure of a confidential numeric passing threshold in English.")
    return issues
