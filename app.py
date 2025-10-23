# app.py
# -*- coding: utf-8 -*-

import json
from datetime import datetime
import streamlit as st

# مكتبة Supabase v2
from supabase import create_client, Client

# ========================= إعداد الصفحة والستايل =========================
st.set_page_config(page_title="بلانري الجميل 💖", page_icon="💖", layout="centered")

st.markdown(
    """
<style>
/* خلفية وردية ناعمة */
body { background: linear-gradient(180deg,#fff8fb 0%,#ffeef5 100%); }
* { font-family: "Tajawal", system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", "Helvetica Neue", Arial, "Apple Color Emoji", "Segoe UI Emoji"; }
h1,h2,h3 { text-align:center; color:#d63384; font-weight:800; }

/* أزرار */
.stButton>button { background:#ffb6c1; color:#fff; border:0; border-radius:12px; padding:.6rem 1rem; font-weight:700; }
.stButton>button:hover { filter:brightness(1.06); }

/* حقول */
textarea,input,select { background:#fff; border-radius:10px; border:1px solid #ffd6e0; }

/* شارات صغيرة */
.task-badge{display:inline-block;padding:.25rem .6rem;background:#ffe3ea;border-radius:999px;color:#c2185b;font-weight:700;}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown("<h1>بلانري الجميل 💖</h1>", unsafe_allow_html=True)

# ========================= ثوابت الشهور =========================
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

# ========================= تهيئة الجلسة =========================
def _blank_state():
    return {
        "meta": {"createdAt": datetime.utcnow().isoformat()},
        "tasks": {},             # {"1":"رياضة", ...}
        "next_id": 1,
        "months": {k: {"tasks": {}, "note": ""} for k in MONTHS.keys()},
    }

if "data" not in st.session_state:
    st.session_state.data = _blank_state()
if "selected_month" not in st.session_state:
    month_key = list(MONTHS.keys())[datetime.now().month - 1]
    st.session_state.selected_month = month_key
if "selected_task_id" not in st.session_state:
    st.session_state.selected_task_id = None
if "user" not in st.session_state:
    st.session_state.user = None
if "cloud_loaded" not in st.session_state:
    st.session_state.cloud_loaded = False

# ========================= Supabase =========================
def _get_client() -> Client:
    """
    يُنشئ عميل Supabase من Secrets
    """
    try:
        url = st.secrets["supabase_url"].strip()
        key = st.secrets["supabase_anon_key"].strip()
    except Exception:
        st.error("لم يتم ضبط مفاتيح Supabase في Secrets.")
        st.stop()
    return create_client(url, key)

SUPA: Client | None = _get_client()

def supa_sign_up(email: str, password: str):
    """تسجيل حساب جديد"""
    return SUPA.auth.sign_up({"email": email, "password": password})

def supa_sign_in(email: str, password: str):
    """تسجيل الدخول (إصدار v2: لا نستخدم .data)"""
    return SUPA.auth.sign_in_with_password({"email": email, "password": password})

def supa_get_user():
    """جلب المستخدم الحالي (قد يُرجع None)"""
    try:
        return SUPA.auth.get_user()
    except Exception:
        return None

def _safe_get_data_field(resp):
    """
    بعض استجابات supabase-py ترجع كائن فيه .data
    وأحيانًا ترجع None أو dict.
    هذه الدالة ترجع القيمة بأمان أو None.
    """
    if resp is None:
        return None
    data = getattr(resp, "data", None)
    # إذا رجع dict مباشرة من postgrest:
    if data is None and isinstance(resp, dict):
        data = resp
    return data

def load_cloud_data(user_id: str):
    """
    تحميل بيانات البلانر من جدول planner_data:
    أعمدة: user_id (PK/unique), data (jsonb), updated_at (timestamp)
    """
    try:
        resp = SUPA.table("planner_data").select("data").eq("user_id", user_id).maybe_single().execute()
        d = _safe_get_data_field(resp)
        if isinstance(d, dict) and "data" in d:
            return d["data"]
        return None
    except Exception:
        return None

def save_cloud_data(user_id: str, data_obj: dict):
    """حفظ/تحديث بيانات المستخدم"""
    try:
        SUPA.table("planner_data").upsert(
            {"user_id": user_id, "data": data_obj, "updated_at": datetime.utcnow().isoformat()}
        ).execute()
    except Exception as e:
        st.warning(f"تعذّر الحفظ السحابي: {e}")

# ========================= أدوات مساعدة =========================
def ensure_month_shapes(data: dict):
    """تأمين أن جميع الشهور والمهام لها مصفوفات الأيام بالشكل الصحيح"""
    for mkey, mmeta in MONTHS.items():
        if mkey not in data["months"]:
            data["months"][mkey] = {"tasks": {}, "note": ""}
        for tid in list(data["tasks"].keys()):
            if tid not in data["months"][mkey]["tasks"]:
                data["months"][mkey]["tasks"][tid] = [False] * mmeta["days"]
        # لو تغيّر عدد أيام الشهر (سنة كبيسة)، اضبط الأطوال:
        for tid, arr in data["months"][mkey]["tasks"].items():
            need = mmeta["days"]
            if len(arr) < need:
                data["months"][mkey]["tasks"][tid] = arr + [False] * (need - len(arr))
            elif len(arr) > need:
                data["months"][mkey]["tasks"][tid] = arr[:need]

# ========================= تسجيل الدخول/إنشاء حساب =========================
with st.expander("تسجيل الدخول / إنشاء حساب", expanded=(st.session_state.user is None)):
    tabs = st.tabs(["تسجيل دخول", "إنشاء حساب جديد"])
    # --- تبويب تسجيل دخول
    with tabs[0]:
        email = st.text_input("الإيميل", key="login_email")
        pwd = st.text_input("كلمة المرور", type="password", key="login_pwd")
        if st.button("دخول", key="btn_login"):
            try:
                result = supa_sign_in(email, pwd)
                # v2: نستخرج المستخدم من result.user
                user_obj = getattr(result, "user", None)
                if user_obj is None:
                    # fallback: حاول الحصول على المستخدم من get_user
                    gu = supa_get_user()
                    user_obj = getattr(gu, "user", None)

                if user_obj:
                    st.session_state.user = user_obj
                    st.success("تم تسجيل الدخول ✅")
                else:
                    st.error("تسجيل الدخول نجح ظاهريًا ولكن لم نتمكّن من الحصول على بيانات المستخدم.")
            except Exception as e:
                st.error(f"فشل تسجيل الدخول: {e}")

    # --- تبويب إنشاء حساب
    with tabs[1]:
        email2 = st.text_input("الإيميل الجديد", key="signup_email")
        pwd2 = st.text_input("كلمة المرور الجديدة", type="password", key="signup_pwd")
        if st.button("إنشاء حساب", key="btn_signup"):
            try:
                resp = supa_sign_up(email2, pwd2)
                # بعض المشاريع تفرض تأكيد الإيميل
                need_confirm = True
                # إن وُجد user رجّحي أنه تم إنشاء الحساب
                if getattr(resp, "user", None):
                    if need_confirm:
                        st.success("تم إنشاء الحساب. قد تحتاجين لتأكيد الإيميل قبل أول تسجيل دخول.")
                    else:
                        st.success("تم إنشاء الحساب. يمكنكِ تسجيل الدخول الآن.")
                else:
                    st.info("تم طلب إنشاء الحساب. إن كان لديكِ تفعيل تأكيد الإيميل، تحقّقي من بريدك.")
            except Exception as e:
                st.error(f"تعذّر إنشاء الحساب: {e}")

# لو ما في مستخدم مسجّل دخول — ننهي هنا
if st.session_state.user is None:
    st.stop()

# ========================= تحميل بيانات السحابة أول مرة بعد الدخول =========================
if not st.session_state.cloud_loaded:
    uid = st.session_state.user.id
    cloud_data = load_cloud_data(uid)
    if cloud_data:
        st.session_state.data = cloud_data
    else:
        # أول مرة: خزّني نسخة فارغة
        save_cloud_data(uid, st.session_state.data)
    st.session_state.cloud_loaded = True

# نضمن الشكل
data = st.session_state.data
ensure_month_shapes(data)

# ========================= واجهة إدارة المهام =========================
st.write("### ✨ إدارة مهامي")
new_task = st.text_input("اسم المهمة", placeholder="مثال: رياضة صباحية، قراءة…", key="new_task_name")
col_a, col_b = st.columns(2)
with col_a:
    if st.button("➕ إضافة مهمة", key="btn_add_task"):
        name = new_task.strip()
        if name:
            tid = str(data["next_id"])
            data["next_id"] += 1
            data["tasks"][tid] = name
            # أنشئ مصفوفات الأيام لكل الشهور للمهمة الجديدة
            for mkey, mmeta in MONTHS.items():
                data["months"][mkey]["tasks"][tid] = [False] * mmeta["days"]
            st.session_state.selected_task_id = tid
            save_cloud_data(st.session_state.user.id, data)
            st.success("تمت إضافة المهمة ✨")
        else:
            st.warning("اكتبي اسم المهمة أولًا.")

with col_b:
    if st.session_state.selected_task_id and st.button("🗑️ حذف المهمة الحالية", key="btn_del_task"):
        tid = st.session_state.selected_task_id
        data["tasks"].pop(tid, None)
        for m in data["months"].values():
            m["tasks"].pop(tid, None)
        st.session_state.selected_task_id = None
        save_cloud_data(st.session_state.user.id, data)
        st.info("تم حذف المهمة.")

# ========================= اختيار الشهر والمهمة =========================
month_keys = list(MONTHS.keys())
month_labels = [MONTHS[m]["label"] for m in month_keys]
cur_idx = month_keys.index(st.session_state.selected_month)
sel_label = st.selectbox("اختاري الشهر:", month_labels, index=cur_idx)
st.session_state.selected_month = month_keys[month_labels.index(sel_label)]

tasks_dict = data["tasks"]
if not tasks_dict:
    st.info("أضيفي مهمة من الأعلى لبدء التتبّع.")
    st.stop()

# قائمة المهام (مرتبة أبجديًا)
sorted_ids = sorted(tasks_dict.keys(), key=lambda k: tasks_dict[k])
labels = [tasks_dict[i] for i in sorted_ids]
default_idx = sorted_ids.index(st.session_state.selected_task_id) if st.session_state.selected_task_id in sorted_ids else 0
chosen = st.selectbox("اختاري مهمة:", labels, index=default_idx)
tid = sorted_ids[labels.index(chosen)]
st.session_state.selected_task_id = tid
st.markdown(f"<span class='task-badge'>المهمة المختارة: {tasks_dict[tid]}</span>", unsafe_allow_html=True)

st.write("---")
st.markdown("### بلانر هذه المهمة")

# ========================= بلانر المهمة للشهر المختار =========================
mkey = st.session_state.selected_month
mmeta = MONTHS[mkey]
mstate = data["months"][mkey]
if tid not in mstate["tasks"]:
    mstate["tasks"][tid] = [False] * mmeta["days"]

days_list = mstate["tasks"][tid]
done_count = sum(1 for d in days_list if d)
progress = int((done_count / mmeta["days"]) * 100)

st.subheader(tasks_dict[tid])
st.progress(progress / 100.0, text=f"تم إنجاز {progress}% ({done_count}/{mmeta['days']})")

cols = st.columns(7)
dirty = False
for day in range(1, mmeta["days"] + 1):
    c = cols[(day - 1) % 7]
    done = days_list[day - 1]
    if c.button(f"{day} {'💗' if done else ''}", key=f"{mkey}_{tid}_{day}"):
        days_list[day - 1] = not done
        dirty = True

st.write("---")
st.write("### 🩷 ملاحظات الشهر")
note_before = mstate.get("note", "")
note_after = st.text_area("ملاحظات عامة لهذا الشهر:", value=note_before, height=100)
if note_after != note_before:
    mstate["note"] = note_after
    dirty = True

# أزرار سريعة
a, b = st.columns(2)
with a:
    if st.button("تحديد كل الأيام لهذه المهمة 💖", key="btn_all_on"):
        for i in range(len(days_list)):
            days_list[i] = True
        dirty = True
with b:
    if st.button("مسح كل الأيام لهذه المهمة 🩶", key="btn_all_off"):
        for i in range(len(days_list)):
            days_list[i] = False
        dirty = True

# حفظ تلقائي عند أي تعديل
if dirty:
    save_cloud_data(st.session_state.user.id, data)
    st.toast("تم الحفظ ✨", icon="💾")

# نسخ احتياطي/استيراد
c1, c2 = st.columns(2)
with c1:
    st.download_button(
        "تنزيل نسخة احتياطية 💾",
        data=json.dumps(data, ensure_ascii=False, indent=2),
        file_name="routine_backup.json",
        mime="application/json",
        key="btn_backup",
    )
with c2:
    up = st.file_uploader("استيراد نسخة", type=["json"], key="uploader_json")
    if up:
        try:
            st.session_state.data = json.load(up)
            ensure_month_shapes(st.session_state.data)
            save_cloud_data(st.session_state.user.id, st.session_state.data)
            st.success("تم الاستيراد والحفظ سحابيًا 🌸")
        except Exception:
            st.error("ملف غير صالح.")
