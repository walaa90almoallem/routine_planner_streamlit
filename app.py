import json
from datetime import datetime
import streamlit as st

# ========= إعداد الصفحة =========
st.set_page_config(page_title="بلانري الجميل 💖", page_icon="💖", layout="centered")

# ========= ألوان ناعمة (زهري + أبيض) =========
st.markdown("""
<style>
body {
  background: linear-gradient(180deg, #fff8fb 0%, #ffeef5 100%);
  color: #444;
  font-family: "Tajawal", sans-serif;
}
h1, h2, h3 { text-align:center; color:#d63384; font-weight:700; }
.stButton>button {
  background:#ffb6c1; color:#fff; border:0; border-radius:12px;
  padding:.6rem 1rem; font-weight:700;
}
.stButton>button:hover { filter:brightness(1.06); }
[data-testid="stProgress"]>div>div { background:#ffb6c1; }
textarea, input, select {
  background:#fff; border-radius:10px; border:1px solid #ffd6e0;
}
.task-badge { display:inline-block; padding:.25rem .6rem; background:#ffe3ea; border-radius:999px; color:#c2185b; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# ========= تعريف الشهور =========
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

# ========= تهيئة الجلسة =========
def init_state():
    if "data" not in st.session_state:
        # tasks: dict id -> name  | next_id: for unique task ids
        st.session_state.data = {
            "meta": {"createdAt": datetime.utcnow().isoformat()},
            "tasks": {},              # {"1":"رياضة", "2":"قراءة", ...}
            "next_id": 1,
            "months": {},            # per month: {"tasks": {"1":[bools], ...}, "note":""}
        }
    # تأكيد وجود بنية الشهور
    for m in MONTHS:
        if m not in st.session_state.data["months"]:
            st.session_state.data["months"][m] = {"tasks": {}, "note": ""}

    # اختيار الشهر الافتراضي = شهر اليوم
    if "selected_month" not in st.session_state:
        now = datetime.now()
        month_key = list(MONTHS.keys())[now.month - 1]
        st.session_state.selected_month = month_key

    # المهمة المختارة
    if "selected_task_id" not in st.session_state:
        st.session_state.selected_task_id = None

init_state()

# ========= عنوان =========
st.markdown("<h1>بلانري الجميل 💖</h1>", unsafe_allow_html=True)

# ========= إضافة مهمة جديدة =========
st.write("### ✨ أضيفي مهمة جديدة")
new_task = st.text_input("اسم المهمة", placeholder="مثال: رياضة صباحية، قراءة، تعلّم لغة...")
add_col1, add_col2 = st.columns([1,1])
with add_col1:
    if st.button("➕ إضافة مهمة"):
        name = new_task.strip()
        if name:
            tid = str(st.session_state.data["next_id"])
            st.session_state.data["tasks"][tid] = name
            st.session_state.data["next_id"] += 1
            st.session_state.selected_task_id = tid
            st.success(f"تمت إضافة المهمة: {name} 💗")
        else:
            st.warning("اكتبي اسم المهمة أولاً.")
with add_col2:
    # حذف المهمة المختارة
    if st.session_state.selected_task_id and st.button("🗑️ حذف المهمة الحالية"):
        tid = st.session_state.selected_task_id
        # احذف من قائمة المهام
        st.session_state.data["tasks"].pop(tid, None)
        # احذف بياناتها من كل الشهور
        for m in st.session_state.data["months"].values():
            if "tasks" in m and tid in m["tasks"]:
                m["tasks"].pop(tid, None)
        st.session_state.selected_task_id = None
        st.info("تم حذف المهمة.")

st.write("---")

# ========= اختيار الشهر الذي أنتِ فيه =========
month_keys = list(MONTHS.keys())
month_labels = [MONTHS[m]["label"] for m in month_keys]
cur_idx = month_keys.index(st.session_state.selected_month)
sel_label = st.selectbox("اختاري الشهر:", month_labels, index=cur_idx)
st.session_state.selected_month = month_keys[month_labels.index(sel_label)]

# ========= اختيار المهمة من قائمة =========
tasks_dict = st.session_state.data["tasks"]
task_ids_sorted = sorted(tasks_dict.keys(), key=lambda k: tasks_dict[k])
task_labels = [tasks_dict[tid] for tid in task_ids_sorted]

st.write("### 🌷 اختاري مهمة لتتبّعيها")
if task_labels:
    default_idx = 0
    if st.session_state.selected_task_id in task_ids_sorted:
        default_idx = task_ids_sorted.index(st.session_state.selected_task_id)
    chosen_label = st.selectbox("مهمتي:", task_labels, index=default_idx)
    chosen_tid = task_ids_sorted[task_labels.index(chosen_label)]
    st.session_state.selected_task_id = chosen_tid
    st.markdown(f"<span class='task-badge'>المهمة المختارة: {tasks_dict[chosen_tid]}</span>", unsafe_allow_html=True)
else:
    st.info("أضيفي مهمة من الأعلى، ثم اختاريها هنا لعرض البلانر.")
    st.stop()

st.write("---")
st.markdown("### مهام هذا الشهر")

# ========= بلانر المهمة المختارة لهذا الشهر =========
mkey = st.session_state.selected_month
mobj = MONTHS[mkey]
mstate = st.session_state.data["months"][mkey]

# أنشئ مصفوفة الأيام لهذه المهمة إن لم تكن موجودة
if "tasks" not in mstate:
    mstate["tasks"] = {}
if st.session_state.selected_task_id not in mstate["tasks"]:
    mstate["tasks"][st.session_state.selected_task_id] = [False] * mobj["days"]

days_list = mstate["tasks"][st.session_state.selected_task_id]
done_count = sum(1 for d in days_list if d)
progress = int((done_count / mobj["days"]) * 100)

st.subheader(tasks_dict[st.session_state.selected_task_id])
st.progress(progress/100, text=f"تم إنجاز {progress}% ({done_count}/{mobj['days']})")

# شبكة الأيام (كبسة واحدة تقلب حالة اليوم)
cols = st.columns(7)
for day in range(1, mobj["days"] + 1):
    c = cols[(day - 1) % 7]
    done = days_list[day - 1]
    if c.button(f"{day} {'💗' if done else ''}", key=f"{mkey}_{st.session_state.selected_task_id}_{day}"):
        days_list[day - 1] = not done

st.write("---")

# ========= ملاحظة للشهر (عامّة لكل المهام) =========
st.write("### 🩷 ملاحظات الشهر")
note = st.text_area("اكتبي ملاحظاتك أو أفكارك لهذا الشهر:", value=mstate.get("note", ""), height=100)
if note != mstate.get("note", ""):
    mstate["note"] = note

# ========= إجراءات سريعة على المهمة المختارة =========
a, b = st.columns(2)
with a:
    if st.button("تحديد كل الأيام للمهمة 💖"):
        for d in range(len(days_list)):
            days_list[d] = True
with b:
    if st.button("مسح كل الأيام للمهمة 🩶"):
        for d in range(len(days_list)):
            days_list[d] = False

st.write("---")

# ========= نسخ احتياطي/استيراد =========
c1, c2 = st.columns(2)
with c1:
    st.download_button(
        "تنزيل نسخة احتياطية 💾",
        data=json.dumps(st.session_state.data, ensure_ascii=False, indent=2),
        file_name="routine_backup.json",
        mime="application/json",
    )
with c2:
    up = st.file_uploader("استيراد نسخة", type=["json"])
    if up:
        try:
            st.session_state.data = json.load(up)
            st.success("تم الاستيراد بنجاح 🌸")
        except Exception:
            st.error("ملف غير صالح.")

st.caption("✨ أضيفي مهامك، اختاري الشهر الذي أنتِ فيه، وتابعي تقدّمك يومًا بيوم 💗")
