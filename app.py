import json
from datetime import datetime
import streamlit as st

# إعداد الصفحة
st.set_page_config(
    page_title="بلانري الجميل 💖",
    page_icon="💖",
    layout="centered",
)

# ====== الألوان والتنسيق ======
st.markdown("""
<style>
body {
  background: linear-gradient(180deg, #fff8fb 0%, #ffeef5 100%);
  color: #444;
  font-family: "Tajawal", sans-serif;
}
h1, h2, h3 {
  text-align: center;
  color: #d63384;
  font-weight: 700;
}
.stButton>button {
  background-color: #ffb6c1;
  color: white;
  border: none;
  border-radius: 10px;
  padding: 8px 0;
  width: 100%;
  font-weight: bold;
}
.stButton>button:hover {
  background-color: #ff99b3;
}
[data-testid="stProgress"] > div > div {
  background-color: #ffb6c1;
}
textarea, input {
  background-color: #fff;
  border-radius: 10px;
  border: 1px solid #ffd6e0;
}
</style>
""", unsafe_allow_html=True)

# ====== البيانات الأساسية ======
MONTHS = {
    "jan": {"label": "يناير", "days": 31},
    "feb": {"label": "فبراير", "days": 29},
    "mar": {"label": "مارس", "days": 31},
    "apr": {"label": "أبريل", "days": 30},
    "may": {"label": "مايو", "days": 31},
    "jun": {"label": "يونيو", "days": 30},
    "jul": {"label": "يوليو", "days": 31},
    "aug": {"label": "أغسطس", "days": 31},
    "sep": {"label": "سبتمبر", "days": 30},
    "oct": {"label": "أكتوبر", "days": 31},
    "nov": {"label": "نوفمبر", "days": 30},
    "dec": {"label": "ديسمبر", "days": 31},
}

# حفظ البيانات في الجلسة
def init_state():
    if "data" not in st.session_state:
        st.session_state.data = {
            "meta": {"title": "بلانري الجميل 💖", "createdAt": datetime.utcnow().isoformat()},
            "months": {m: {"days": [False]*MONTHS[m]["days"], "note": ""} for m in MONTHS}
        }
    if "selected_month" not in st.session_state:
        st.session_state.selected_month = "jan"

init_state()

# ====== الواجهة ======
st.markdown("<h1>بلانري الجميل 💖</h1>", unsafe_allow_html=True)

# اختيار الشهر
month_keys = list(MONTHS.keys())
month_labels = [MONTHS[m]["label"] for m in month_keys]
current_index = month_keys.index(st.session_state.selected_month)
sel = st.selectbox("اختاري الشهر:", month_labels, index=current_index)
st.session_state.selected_month = month_keys[month_labels.index(sel)]

# حساب التقدم
mkey = st.session_state.selected_month
mobj = MONTHS[mkey]
mstate = st.session_state.data["months"][mkey]
done_count = sum(1 for d in mstate["days"] if d)
progress = int((done_count / mobj["days"]) * 100)

st.progress(progress / 100, text=f"تم إنجاز {progress}% ({done_count}/{mobj['days']})")

# شبكة الأيام
st.write("### الأيام")
cols = st.columns(7)
for day in range(1, mobj["days"] + 1):
    c = cols[(day - 1) % 7]
    done = mstate["days"][day - 1]
    if c.button(f"{day} {'💗' if done else ''}", key=f"{mkey}_{day}"):
        mstate["days"][day - 1] = not done

st.write("---")

# ملاحظة الشهر
st.write("### ملاحظات الشهر 🌷")
note = st.text_area("أضيفي ملاحظاتك أو أفكارك لهذا الشهر:", value=mstate["note"], height=100)
if note != mstate["note"]:
    mstate["note"] = note

# أزرار التحكم
c1, c2 = st.columns(2)
with c1:
    if st.button("تحديد كل الأيام 💕"):
        mstate["days"] = [True]*mobj["days"]
with c2:
    if st.button("مسح كل الأيام 🩶"):
        mstate["days"] = [False]*mobj["days"]

st.write("---")

# تنزيل ورفع النسخة الاحتياطية
col1, col2 = st.columns(2)
with col1:
    st.download_button(
        "تنزيل نسخة احتياطية 💾",
        data=json.dumps(st.session_state.data, ensure_ascii=False, indent=2),
        file_name="routine_backup.json",
        mime="application/json",
    )
with col2:
    file = st.file_uploader("استيراد نسخة", type=["json"])
    if file:
        st.session_state.data = json.load(file)
        st.success("تم الاستيراد بنجاح 🌸")

st.caption("✨ واجهة ناعمة وأنيقة لتتبع روتينك اليومي على مدار العام 💖")
