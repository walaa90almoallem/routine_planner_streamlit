# app.py
# ——————————————————————————————————————————
# بلانر مهام شهري (عربي) مع تخزين على Supabase + تشخيص اتصال واضح
# ——————————————————————————————————————————

import json
from datetime import datetime
import streamlit as st

# نستخدم httpx للفحص السريع للرابط قبل إنشاء عميل Supabase
import httpx

# مكتبة supabase الرسمية (>=2.6.0,<3.0)
from supabase import create_client, Client

# ========= إعداد الصفحة + ستايل بسيط =========
st.set_page_config(page_title="بلانري الجميل 💖", page_icon="💖", layout="centered")
st.markdown("""
<style>
body { background: linear-gradient(180deg,#fff8fb 0%,#ffeef5 100%); color:#444; font-family:"Tajawal",sans-serif; }
h1,h2,h3 { text-align:center; color:#d63384; font-weight:700; }
.stButton>button { background:#ffb6c1; color:#fff; border:0; border-radius:12px; padding:.6rem 1rem; font-weight:700; }
.stButton>button:hover { filter:brightness(1.06); }
[data-testid="stProgress"]>div>div { background:#ffb6c1; }
textarea,input,select { background:#fff; border-radius:10px; border:1px solid #ffd6e0; }
.task-badge{display:inline-block;padding:.25rem .6rem;background:#ffe3ea;border-radius:999px;color:#c2185b;font-weight:700;}
hr{border:none;border-top:1px solid #ffd6e0;margin:1rem 0;}
</style>
""", unsafe_allow_html=True)

# ========= شهور =========
MONTHS = {
    "jan":{"label":"يناير","days":31}, "feb":{"label":"فبراير","days":29}, "mar":{"label":"مارس","days":31},
    "apr":{"label":"أبريل","days":30}, "may":{"label":"مايو","days":31}, "jun":{"label":"يونيو","days":30},
    "jul":{"label":"يوليو","days":31}, "aug":{"label":"أغسطس","days":31}, "sep":{"label":"سبتمبر","days":30},
    "oct":{"label":"أكتوبر","days":31}, "nov":{"label":"نوفمبر","days":30}, "dec":{"label":"ديسمبر","days":31},
}

# ========= دالة إنشاء عميل Supabase مع تشخيص قوي =========
def get_client() -> Client:
    """
    - تقرأ supabase_url و supabase_anon_key من Secrets
    - تعرض القيم المقروءة (repr + الطول) على الشاشة
    - تفحص DNS/HTTP قبل إنشاء عميل Supabase
    """
    # 1) قراءة Secrets بأمان مع strip لإزالة أي مسافات خفية
    try:
        url = st.secrets.get("supabase_url", "").strip()
        key = st.secrets.get("supabase_anon_key", "").strip()
    except Exception as e:
        st.error(f"⚠️ لم أستطع قراءة Secrets: {e}")
        st.stop()

    # 2) تشخيص: أعرض القيم الفعلية التي يقرأها التطبيق
    st.caption(f"🔎 diag: supabase_url={repr(url)} | len={len(url)}")
    st.caption(f"🔎 diag: anon_key_len={len(key)}")

    # 3) تحقّق سريع من الشكل
    if not url or not key:
        st.error("⚠️ Secrets ناقصة. تأكدي من إدخال السطرين بالضبط في Settings → Secrets.")
        st.stop()
    if not url.startswith("https://") or ".supabase.co" not in url:
        st.error("⚠️ صيغة الرابط غير صحيحة (لازم ينتهي بـ .supabase.co). تأكدي من النسخ الحرفي من Supabase.")
        st.stop()

    # 4) فحص DNS/HTTP — إذا فشل بيظهر السبب (بيوضح مشاكل من نوع Name or service not known)
    try:
        r = httpx.get(url, timeout=5.0)
        st.caption(f"🔎 probe: GET {url} → status={r.status_code}")
    except Exception as e:
        st.error(f"⚠️ فشل فحص الرابط (DNS/Network): {e}\nتحقّقي من أن الرابط مكتوب تمامًا مثل لوحة Supabase.")
        st.stop()

    # 5) إنشاء عميل Supabase
    try:
        supa = create_client(url, key)
        return supa
    except Exception as e:
        st.error(f"⚠️ تعذّر إنشاء عميل Supabase: {e}")
        st.stop()

# ========= دوال Supabase مساعدة =========
def supa_sign_up(supa: Client, email, password):
    return supa.auth.sign_up({"email": email, "password": password})

def supa_sign_in(supa: Client, email, password):
    return supa.auth.sign_in_with_password({"email": email, "password": password})

def supa_get_user(supa: Client):
    return supa.auth.get_user()

def load_cloud_data(supa: Client, user_id: str):
    res = supa.table("planner_data").select("data").eq("user_id", user_id).maybe_single().execute()
    if res.data:
        # res.data قد تكون dict أو {'data': {...}}
        return res.data.get("data") if isinstance(res.data, dict) else res.data
    return None

def save_cloud_data(supa: Client, user_id: str, data):
    supa.table("planner_data").upsert(
        {"user_id": user_id, "data": data, "updated_at": datetime.utcnow().isoformat()}
    ).execute()

# ========= حالة افتراضية محلية =========
def blank_state():
    return {
        "meta": {"createdAt": datetime.utcnow().isoformat()},
        "tasks": {},        # {"1":"رياضة", ...}
        "next_id": 1,
        "months": {m: {"tasks": {}, "note": ""} for m in MONTHS},
    }

def ensure_month_shapes(data):
    for m, mobj in MONTHS.items():
        if m not in data["months"]:
            data["months"][m] = {"tasks": {}, "note": ""}
        for tid, _ in data["tasks"].items():
            if tid not in data["months"][m]["tasks"]:
                data["months"][m]["tasks"][tid] = [False] * mobj["days"]

# ========= تهيئة جلسة =========
if "data" not in st.session_state: st.session_state.data = blank_state()
if "selected_month" not in st.session_state:
    month_key = list(MONTHS.keys())[datetime.now().month - 1]
    st.session_state.selected_month = month_key
if "selected_task_id" not in st.session_state: st.session_state.selected_task_id = None
if "user" not in st.session_state: st.session_state.user = None
if "cloud_loaded" not in st.session_state: st.session_state.cloud_loaded = False
if "supa" not in st.session_state: st.session_state.supa = None

# ========= ترويسة =========
st.markdown("<h1>بلانري الجميل 💖</h1>", unsafe_allow_html=True)

# ========= تهيئة Supabase (مع التشخيص) =========
SUPA = get_client()
st.session_state.supa = SUPA  # نحتفظ به للاستخدام

# ========= مصادقة (تسجيل/تسجيل دخول) =========
with st.expander("تسجيل الدخول / إنشاء حساب", expanded=(st.session_state.user is None)):
    tab1, tab2 = st.tabs(["تسجيل دخول", "إنشاء حساب جديد"])
    with tab1:
        email = st.text_input("الإيميل", key="login_email")
        pwd = st.text_input("كلمة المرور", type="password", key="login_pwd")
        if st.button("دخول"):
            try:
                supa_sign_in(SUPA, email, pwd)
                user = supa_get_user(SUPA).user
                st.session_state.user = user
                st.success("تم تسجيل الدخول ✅")
            except Exception as e:
                st.error(f"فشل تسجيل الدخول: {e}")
    with tab2:
        email2 = st.text_input("الإيميل الجديد", key="signup_email")
        pwd2 = st.text_input("كلمة المرور الجديدة", type="password", key="signup_pwd")
        if st.button("إنشاء حساب"):
            try:
                supa_sign_up(SUPA, email2, pwd2)
                st.success("تم إنشاء الحساب. سجّلي الدخول الآن.")
            except Exception as e:
                st.error(f"تعذّر إنشاء الحساب: {e}")

if st.session_state.user is None:
    st.info("سجّلي الدخول أو أنشئي حسابًا للمتابعة.")
    st.stop()

# ========= تحميل/حفظ بيانات المستخدم =========
if not st.session_state.cloud_loaded:
    user_id = st.session_state.user.id
    try:
        cloud = load_cloud_data(SUPA, user_id)
        if cloud:
            st.session_state.data = cloud
        else:
            # أول مرة: أنشئي صف للمستخدم
            save_cloud_data(SUPA, user_id, st.session_state.data)
        st.session_state.cloud_loaded = True
    except Exception as e:
        st.error(f"فشل تحميل بيانات السحابة: {e}")
        st.stop()

data = st.session_state.data
ensure_month_shapes(data)

# ========= إدارة المهام =========
st.write("### ✨ إدارة مهامي")
new_task = st.text_input("اسم المهمة", placeholder="مثال: رياضة صباحية، قراءة…")
colA, colB = st.columns([1,1])
with colA:
    if st.button("➕ إضافة مهمة"):
        name = new_task.strip()
        if name:
            tid = str(data["next_id"]); data["next_id"] += 1
            data["tasks"][tid] = name
            for m, mobj in MONTHS.items():
                data["months"][m]["tasks"][tid] = [False] * mobj["days"]
            st.session_state.selected_task_id = tid
            save_cloud_data(SUPA, st.session_state.user.id, data)
            st.success("تمت إضافة المهمة ✨")
        else:
            st.warning("اكتبي اسم المهمة أولًا.")
with colB:
    if st.session_state.selected_task_id and st.button("🗑️ حذف المهمة الحالية"):
        tid = st.session_state.selected_task_id
        data["tasks"].pop(tid, None)
        for m in data["months"].values():
            m["tasks"].pop(tid, None)
        st.session_state.selected_task_id = None
        save_cloud_data(SUPA, st.session_state.user.id, data)
        st.info("تم حذف المهمة.")

# ========= اختيار الشهر والمهمة =========
month_keys = list(MONTHS.keys())
month_labels = [MONTHS[m]["label"] for m in month_keys]
cur_idx = month_keys.index(st.session_state.selected_month)
sel_label = st.selectbox("اختاري الشهر:", month_labels, index=cur_idx)
st.session_state.selected_month = month_keys[month_labels.index(sel_label)]

tasks_dict = data["tasks"]
if not tasks_dict:
    st.info("أضيفي مهمة من الأعلى لبدء التتبّع.")
    st.stop()

sorted_ids = sorted(tasks_dict.keys(), key=lambda k: tasks_dict[k])
labels = [tasks_dict[i] for i in sorted_ids]
default_idx = sorted_ids.index(st.session_state.selected_task_id) if st.session_state.selected_task_id in sorted_ids else 0
chosen = st.selectbox("اختاري مهمة:", labels, index=default_idx)
tid = sorted_ids[labels.index(chosen)]
st.session_state.selected_task_id = tid
st.markdown(f"<span class='task-badge'>المهمة المختارة: {tasks_dict[tid]}</span>", unsafe_allow_html=True)

st.write("---"); st.markdown("### بلانر هذه المهمة")

# ========= بلانر المهمة للشهر =========
mkey = st.session_state.selected_month
mobj = MONTHS[mkey]
mstate = data["months"][mkey]
if tid not in mstate["tasks"]:
    mstate["tasks"][tid] = [False] * mobj["days"]

days_list = mstate["tasks"][tid]
done_count = sum(1 for d in days_list if d)
progress = int((done_count / mobj["days"]) * 100)

st.subheader(tasks_dict[tid])
st.progress(progress/100, text=f"تم إنجاز {progress}% ({done_count}/{mobj['days']})")

cols = st.columns(7)
dirty = False
for day in range(1, mobj["days"] + 1):
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

a,b = st.columns(2)
with a:
    if st.button("تحديد كل الأيام لهذه المهمة 💖"):
        for i in range(len(days_list)): days_list[i] = True
        dirty = True
with b:
    if st.button("مسح كل الأيام لهذه المهمة 🩶"):
        for i in range(len(days_list)): days_list[i] = False
        dirty = True

if dirty:
    save_cloud_data(SUPA, st.session_state.user.id, data)
    st.toast("تم الحفظ ✨", icon="💾")

# نسخ احتياطي يدوي
c1,c2 = st.columns(2)
with c1:
    st.download_button(
        "تنزيل نسخة احتياطية 💾",
        data=json.dumps(data, ensure_ascii=False, indent=2),
        file_name="routine_backup.json",
        mime="application/json",
    )
with c2:
    up = st.file_uploader("استيراد نسخة", type=["json"])
    if up:
        try:
            st.session_state.data = json.load(up)
            ensure_month_shapes(st.session_state.data)
            save_cloud_data(SUPA, st.session_state.user.id, st.session_state.data)
            st.success("تم الاستيراد والحفظ سحابيًا 🌸")
        except Exception:
            st.error("ملف غير صالح.")
