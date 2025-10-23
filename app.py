
import json
from datetime import datetime
import streamlit as st

# =====================
# إعداد الصفحة و الثيم
# =====================
st.set_page_config(
    page_title="بلانر الروتين اليومي",
    page_icon="✅",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ثيم ألوان لطيفة (داكن + إيميرالد)
PRIMARY = "#10B981"   # Emerald
BG = "#0B1220"        # Very dark blue
PANEL = "#111827"     # Slate-900
TEXT = "#F8FAFC"      # Slate-50
MUTED = "#94A3B8"     # Slate-400

st.markdown(f"""
<style>
/* خلفية الصفحة */
[data-testid="stAppViewContainer"] {{
  background: radial-gradient(1200px 600px at 80% -10%, rgba(16,185,129,0.12), transparent 50%),
              radial-gradient(1000px 500px at -10% 10%, rgba(59,130,246,0.08), transparent 50%),
              {BG};
  color: {TEXT};
}}
/* لوحة المحتوى */
.block-container {{
  padding-top: 1.2rem;
  padding-bottom: 2.5rem;
}}
/* عناوين */
h1, h2, h3, h4 {{ color: {TEXT}; }}
/* أزرار */
.stButton>button {{
  background: linear-gradient(180deg, {PRIMARY}, #0ea371);
  color: #041015;
  border: 0;
  border-radius: 14px;
  padding: 0.6rem 0.9rem;
  font-weight: 700;
}}
.stButton>button:hover {{ filter: brightness(1.06); }}
/* حقول الإدخال */
.stTextInput>div>div>input,
.stTextArea textarea,
.stSelectbox>div>div>div {{
  background: {PANEL};
  color: {TEXT};
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.08);
}}
/* توغل */
.stToggle {{
  background: {PANEL};
  padding: 8px;
  border-radius: 12px;
}}
/* شريط التقدم */
[data-testid="stProgress"] > div > div {{ background: rgba(255,255,255,0.08); }}
[data-testid="stProgress"] > div > div > div {{ background: {PRIMARY}; }}
/* بطاقات الأيام */
.button-day {{
  width: 100%;
  padding: .9rem 0;
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,0.08);
  background: {PANEL};
  color: {TEXT};
  font-weight: 700;
}}
.button-day.done {{
  background: linear-gradient(180deg, {PRIMARY}, #0ea371);
  color: #041015;
}}
.caption-muted {{ color: {MUTED}; font-size: .85rem; }}
</style>
""", unsafe_allow_html=True)

# =====================
# البيانات الأساسية
# =====================
MONTHS = {
    "oct": {"label": "تشرين الأول", "days": 31},
    "nov": {"label": "تشرين الثاني", "days": 30},
    "dec": {"label": "كانون الأول", "days": 31},
}
DEFAULT_TITLE = "روتين يومي"

def init_state():
    if "data" not in st.session_state:
        st.session_state.data = {
            "meta": {"title": DEFAULT_TITLE, "createdAt": datetime.utcnow().isoformat()},
            "months": {
                m: {
                    "days": [False] * MONTHS[m]["days"],
                    "ratings": [0] * MONTHS[m]["days"],
                    "notes": {"__month": ""},
                }
                for m in MONTHS
            },
        }
    if "selected_month" not in st.session_state:
        st.session_state.selected_month = "oct"
    if "selected_day" not in st.session_state:
        st.session_state.selected_day = None

def calc_streak(days_list):
    current = 0
    longest = 0
    for done in days_list:
        if done:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return current, longest

def percent(a, b):
    return 0 if b == 0 else round((a / b) * 100)

init_state()

# =====================
# الهيدر البسيط
# =====================
c1, c2 = st.columns([2, 1])
with c1:
    st.markdown("#### بلانر الروتين اليومي")
    new_title = st.text_input("اسم الروتين", value=st.session_state.data["meta"].get("title", DEFAULT_TITLE"))
    if new_title != st.session_state.data["meta"].get("title", DEFAULT_TITLE):
        st.session_state.data["meta"]["title"] = new_title

with c2:
    month_keys = list(MONTHS.keys())
    month_labels = [MONTHS[m]["label"] for m in month_keys]
    idx = month_keys.index(st.session_state.selected_month)
    sel = st.selectbox("الشهر", month_labels, index=idx)
    st.session_state.selected_month = month_keys[month_labels.index(sel)]

mkey = st.session_state.selected_month
mobj = MONTHS[mkey]
mstate = st.session_state.data["months"][mkey]

total_done = sum(1 for d in mstate["days"] if d)
p = percent(total_done, mobj["days"])
current_streak, longest_streak = calc_streak(mstate["days"])

st.progress(p / 100, text=f"إنجاز {p}%  ({total_done}/{mobj['days']}) · سلسلة حالية {current_streak} · أطول سلسلة {longest_streak}")
st.markdown(f"<p class='caption-muted'>إضغطي على اليوم لفتح المحرّر.</p>", unsafe_allow_html=True)

# =====================
# شبكة الأيام (أزرار)
# =====================
cols = st.columns(7, gap="small")
for day in range(1, mobj["days"] + 1):
    c = cols[(day - 1) % 7]
    done = mstate["days"][day - 1]
    html = f\"\"\"\
    <button class="button-day {'done' if done else ''}" onclick="window.parent.postMessage({{'type':'select_day','day':{day}}}, '*')">
        {day} {'✅' if done else ''}
    </button>
    \"\"\"
    c.markdown(html, unsafe_allow_html=True)

# JS للتعامل مع ضغطات الأزرار (بسبب استخدام HTML داخل ماركداون)
st.components.v1.html(\"\"\"\
<script>
window.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'select_day') {
    const day = event.data.day;
    const data = {'day': day};
    const el = window.parent.document.querySelector('input[data-testid="stSessionState"]');
    if (el) { el.value = JSON.stringify(data); el.dispatchEvent(new Event('input', { bubbles: true })); }
  }
});
</script>
<input data-testid="stSessionState" style="display:none" />
\"\"\", height=0)

# إلتقاط قيمة اليوم المختار بطريقة بسيطة عبر نص مخفي
picked_json = st.text_input("hidden_state", value="", label_visibility="collapsed")
if picked_json:
    try:
        info = json.loads(picked_json)
        st.session_state.selected_day = int(info.get("day"))
    except Exception:
        pass

st.write("---")

# =====================
# محرر اليوم المحدّد
# =====================
if st.session_state.selected_day is not None:
    d = st.session_state.selected_day
    st.subheader(f"اليوم {d} · {MONTHS[mkey]['label']}")

    done = mstate["days"][d - 1]
    new_done = st.toggle("تم إنجاز الروتين لهذا اليوم", value=done)
    if new_done != done:
        mstate["days"][d - 1] = new_done

    rating = mstate["ratings"][d - 1]
    new_rating = st.slider("قيّمي يومك (0–5)", 0, 5, value=rating)
    if new_rating != rating:
        mstate["ratings"][d - 1] = new_rating

    day_note_key = f"day_{d}"
    day_note_val = mstate["notes"].get(day_note_key, "")
    new_note = st.text_area("ملاحظة لليوم (اختياري)", value=day_note_val, placeholder="كيف كان يومك؟ نقاط التحسين؟")
    if new_note != day_note_val:
        mstate["notes"][day_note_key] = new_note

    st.button("إغلاق محرر اليوم", on_click=lambda: st.session_state.update({"selected_day": None}))

# =====================
# ملاحظة الشهر + أزرار سريعة
# =====================
st.write("---")
st.markdown("#### ملاحظة عامة للشهر")
month_note = mstate["notes"].get("__month", "")
new_month_note = st.text_area("ملاحظة الشهر", value=month_note, placeholder="خطة الشهر، عادات تركيز، أهداف..")
if new_month_note != month_note:
    mstate["notes"]["__month"] = new_month_note

cc1, cc2 = st.columns(2)
with cc1:
    if st.button("تحديد كل الأيام"):
        mstate["days"] = [True] * mobj["days"]
        mstate["ratings"] = [5] * mobj["days"]
with cc2:
    if st.button("مسح الشهر"):
        mstate["days"] = [False] * mobj["days"]
        mstate["ratings"] = [0] * mobj["days"]
        mstate["notes"] = {"__month": ""}

st.write("---")
colx, coly = st.columns(2)
with colx:
    st.download_button(
        "تنزيل نسخة احتياطية (JSON)",
        data=json.dumps(st.session_state.data, ensure_ascii=False, indent=2),
        file_name="routine_backup.json",
        mime="application/json",
    )
with coly:
    up = st.file_uploader("استيراد نسخة (JSON)", type=["json"])
    if up is not None:
        try:
            st.session_state.data = json.loads(up.read().decode("utf-8"))
            st.success("تم الاستيراد بنجاح ✅")
        except Exception as e:
            st.error(f"ملف غير صالح: {e}")

st.caption("واجهة ملائمة للجوال · تحفظ تقدمك طالما جلسة التطبيق مفتوحة · للنشر عبر Streamlit Cloud اتبعي دليل README.")
