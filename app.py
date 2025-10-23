import json
from datetime import datetime
import streamlit as st
from supabase import create_client, Client

# ========= إعداد الصفحة =========
st.set_page_config(page_title="بلانري الجميل 💖", page_icon="💖", layout="centered")

# ========= ألوان ناعمة =========
st.markdown("""
<style>
body { background: linear-gradient(180deg,#fff8fb 0%,#ffeef5 100%); color:#444; font-family:"Tajawal",sans-serif; }
h1,h2,h3 { text-align:center; color:#d63384; font-weight:700; }
.stButton>button { background:#ffb6c1; color:#fff; border:0; border-radius:12px; padding:.6rem 1rem; font-weight:700; }
.stButton>button:hover { filter:brightness(1.06); }
[data-testid="stProgress"]>div>div { background:#ffb6c1; }
textarea,input,select { background:#fff; border-radius:10px; border:1px solid #ffd6e0; }
.task-badge{display:inline-block;padding:.25rem .6rem;background:#ffe3ea;border-radius:999px;color:#c2185b;font-weight:700;}
</style>
""", unsafe_allow_html=True)

# ========= شهور =========
MONTHS = {
    "jan":{"label":"يناير","days":31},"feb":{"label":"فبراير","days":29},"mar":{"label":"مارس","days":31},
    "apr":{"label":"أبريل","days":30},"may":{"label":"مايو","days":31},"jun":{"label":"يونيو","days":30},
    "jul":{"label":"يوليو","days":31},"aug":{"label":"أغسطس","days":31},"sep":{"label":"سبتمبر","days":30},
    "oct":{"label":"أكتوبر","days":31},"nov":{"label":"نوفمبر","days":30},"dec":{"label":"ديسمبر","days":31},
}

# ========= Supabase: دالة تشخيص =========
def get_client() -> Client:
    # جمع أسماء المفاتيح الموجودة بدون إظهار قيمها
    available_keys = list(st.secrets.keys()) if hasattr(st, "secrets") else []
    url = st.secrets.get("supabase_url") if hasattr(st, "secrets") else None
    key = st.secrets.get("supabase_anon_key") if hasattr(st, "secrets") else None

    if not url or not key:
        st.error(
            "⚠️ Secrets ناقصة.\n\n"
            f"يجب أن يكون لديك مفتاحان بالضبط في Secrets:\n"
            f"- supabase_url\n- supabase_anon_key\n\n"
            f"المفاتيح الموجودة حاليًا: {available_keys}"
        )
        st.stop()

    try:
        return create_client(url, key)
    except Exception as e:
        st.error("تعذّر إنشاء عميل Supabase. تحقّقي من صحة القيم في Secrets.")
        st.stop()

SUPA: Client | None = None

def supa_sign_up(email, password):
    return SUPA.auth.sign_up({"email": email, "password": password})

def supa_sign_in(email, password):
    return SUPA.auth.sign_in_with_password({"email": email, "password": password})

def supa_get_user():
    return SUPA.auth.get_user()

def load_cloud_data(user_id):
    res = SUPA.table("planner_data").select("data").eq("user_id", user_id).maybe_single().execute()
    if res.data:
        return res.data["data"]
    return None

def save_cloud_data(user_id, data):
    SUPA.table("planner_data").upsert(
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
        for tid in list(data["tasks"].keys()):
            if tid not in data["months"][m]["tasks"]:
                data["months"][m]["tasks"][tid] = [False] * mobj["days"]

# ========= تهيئة جلسة =========
if "data" not in st.session_state: st.session_state.data = blank_state()
if "selected_month" not in st.session_state:
    st.session_state.selected_month = list(MONTHS.keys())[datetime.now().month - 1]
if "selected_task_id" not in st.session_state: st.session_state.selected_task_id = None
if "user" not in st.session_state: st.session_state.user = None
if "cloud_loaded" not in st.session_state: st.session_state.cloud_loaded = False

# ========= ترويسة =========
st.markdown("<h1>بلانري الجميل 💖</h1>", unsafe_allow_html=True)

# ========= تهيئة Supabase =========
SUPA = get_client()

# ========= مصادقة =========
with st.expander("تسجيل الدخول / إنشاء حساب", expanded=(st.session_state.user is None)):
    tab1, tab2 = st.tabs(["تسجيل دخول", "إنشاء حساب جديد"])
    with tab1:
        email = st.text_input("الإيميل", key="login_email")
        pwd = st.text_input("كلمة المرور", type="password", key="login_pwd")
        if st.button("دخول"):
            try:
                supa_sign_in(email, pwd)
                st.session_state.user = supa_get_user().user
                st.success("تم تسجيل الدخول ✅")
            except Exception:
                st.error("فشل تسجيل الدخول. تحقّقي من الإيميل/الرمز.")
    with tab2:
        email2 = st.text_input("الإيميل الجديد", key="signup_email")
        pwd2 = st.text_input("كلمة المرور الجديدة", type="password", key="signup_pwd")
        if st.button("إنشاء حساب"):
            try:
                supa_sign_up(email2, pwd2)
                st.success("تم إنشاء الحساب. سجّلي الدخول الآن.")
            except Exception:
                st.error("تعذّر إنشاء الحساب.")

if st.session_state.user is None:
    st.stop()

# تحميل بيانات المستخدم مرة واحدة
if not st.session_state.cloud_loaded:
    uid = st.session_state.user.id
    cloud = load_cloud_data(uid)
    if cloud:
        st.session_state.data = cloud
    else:
        save_cloud_data(uid, st.session_state.data)
    st.session_state.cloud_loaded = True

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
            save_cloud_data(st.session_state.user.id, data)
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
        save_cloud_data(st.session_state.user.id, data)
        st.info("تم حذف المهمة.")

# ========= اختيار الشهر والمهمة =========
month_keys = list(MONTHS.keys())
month_labels = [MONTHS[m]["label"] for m in month_keys]
cur_idx = month_keys.index(st.session_state.selected_month)
sel_label = st.selectbox("اختاري الشهر الذي أنتِ فيه:", month_labels, index=cur_idx)
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

# أزرار سريعة
a,b = st.columns(2)
with a:
    if st.button("تحديد كل الأيام لهذه المهمة 💖"):
        for i in range(len(days_list)): days_list[i] = True
        dirty = True
with b:
    if st.button("مسح كل الأيام لهذه المهمة 🩶"):
        for i in range(len(days_list)): days_list[i] = False
        dirty = True

# حفظ تلقائي عند أي تعديل
if dirty:
    save_cloud_data(st.session_state.user.id, data)
    st.toast("تم الحفظ ✨", icon="💾")

# نسخ احتياطي يدوي (اختياري)
c1,c2 = st.columns(2)
with c1:
    st.download_button("تنزيل نسخة احتياطية 💾",
        data=json.dumps(data, ensure_ascii=False, indent=2),
        file_name="routine_backup.json",
        mime="application/json")
with c2:
    up = st.file_uploader("استيراد نسخة", type=["json"])
    if up:
        try:
            st.session_state.data = json.load(up)
            ensure_month_shapes(st.session_state.data)
            save_cloud_data(st.session_state.user.id, st.session_state.data)
            st.success("تم الاستيراد والحفظ سحابيًا 🌸")
        except Exception:
            st.error("ملف غير صالح.")
