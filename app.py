import streamlit as st
import easyocr
import cv2
import numpy as np
import zipfile
import os
import re
from PIL import Image

# إعدادات الصفحة العامة (يجب أن تكون أول أمر في Streamlit)
st.set_page_config(
    page_title="مستخرج الأسماء الذكي",
    page_icon="🏷️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تطبيق تنسيق CSS مخصص لتحسين المظهر وجعل الواجهة عصرية
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button {
        width: 100%;
        background-color: #4361ee;
        color: white;
        border-radius: 8px;
        padding: 10px;
        font-weight: bold;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #3f37c9; color: white; }
    .success-box {
        padding: 15px;
        background-color: #d4edda;
        color: #155724;
        border-radius: 8px;
        border-left: 5px solid #28a745;
        margin-bottom: 10px;
    }
    .preview-card {
        border: 1px solid #e0e0e0;
        padding: 10px;
        border-radius: 8px;
        background-color: white;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# دالة لتخزين نموذج الـ OCR في الذاكرة المؤقتة لمنع إعادة تحميله مع كل تفاعل
@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['en'], model_storage_directory='/tmp', gpu=False)

reader = load_ocr_reader()

# --- الشريط الجانبي (Sidebar) للإعدادات ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1086/1086741.png", width=100)
    st.title("⚙️ لوحة التحكم")
    st.write("اضبط إعدادات التسمية التلقائية بما يناسب ملفاتك:")
    
    # خيار مخصص لنمط البحث (Regex) لزيادة الاحترافية
    pattern_type = st.selectbox(
        "نمط التسمية المستهدف:",
        ["يبدأ بـ CA (مثال: ca5_3)", "أي نص إنجليزي يحتوي أرقام", "كل النصوص المكتشفة"]
    )
    
    st.markdown("---")
    st.info("💡 **نصيحة:** تأكد من أن الصور واضحة والإضاءة جيدة للحصول على أفضل دقة في قراءة النصوص.")

# --- الواجهة الرئيسية ---
st.title("🏷️ تطبيق إعادة تسمية الصور التلقائي بالذكاء الاصطناعي")
st.caption("ارفع صور موقعك أو مشروعك، وسيقوم النظام بقراءة الأكواد وتسميتها وضغطها لك في ثوانٍ.")

uploaded_files = st.file_uploader(
    "اسحب وأفلت الصور هنا (يدعم JPG, PNG)", 
    accept_multiple_files=True, 
    type=['jpg', 'jpeg', 'png']
)

if uploaded_files:
    st.subheader(f"📸 الملفات المرفوعة ({len(uploaded_files)})")
    
    # مصفوفة لتخزين البيانات المعالجة مؤقتاً
    processed_images = []
    
    # شريط تقدم رئيسي
    main_progress = st.progress(0)
    status_text = st.empty()
    
    for idx, file in enumerate(uploaded_files):
        status_text.text(f"⏳ جاري معالجة وفحص: {file.name}...")
        
        # قراءة الصورة
        file_bytes = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        # تحويل الألوان للعرض في Streamlit بشكل صحيح (RGB)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # قراءة النص عبر OCR
        results = reader.readtext(img)
        
        detected_name = None
        
        # تطبيق الفلترة بناءً على اختيار المستخدم من الشريط الجانبي
        for (bbox, text, prob) in results:
            clean_text = text.strip()
            
            if pattern_type == "يبدأ بـ CA (مثال: ca5_3)":
                if re.search(r'(?i)ca[\d_\-]+', clean_text):
                    detected_name = clean_text
                    break
            elif pattern_type == "أي نص إنجليزي يحتوي أرقام":
                if re.search(r'[A-Za-z]+.*\d+|\d+.*[A-Za-z]+', clean_text):
                    detected_name = clean_text
                    break
            else:
                if len(clean_text) > 2: # أي نص مكون من أكثر من حرفين
                    detected_name = clean_text
                    break
        
        # إذا لم يجد الاسم، نعتمد الاسم الأصلي كاحتياط
        if not detected_name:
            detected_name = os.path.splitext(file.name)[0]
            status_style = "⚠️ لم يتم العثور على كود - تم الحفاظ على الاسم الأصلي"
        else:
            status_style = f"✅ تم اكتشاف الكود: **{detected_name}**"
            
        # تنظيف اسم الملف من الرموز غير المسموحة في نظام التشغيل
        detected_name = re.sub(r'[\\/*?:"<>| ]', "_", detected_name)
        ext = os.path.splitext(file.name)[1].lower()
        
        # تخزين النتائج في قائمة لعرضها بشكل تفاعلي
        processed_images.append({
            "original_name": file.name,
            "suggested_name": detected_name,
            "extension": ext,
            "image_data": img_rgb,
            "bytes": file_bytes,
            "status": status_style
        })
        
        main_progress.progress((idx + 1) / len(uploaded_files))
    
    status_text.success("🎉 اكتملت عملية الفحص الفوري للصور!")
    
    # --- عرض النتائج في نظام بطاقات تفاعلي (Interactive Cards) ---
    st.markdown("### 👁️ مراجعة وتعديل الأسماء المقترحة")
    st.write("يمكنك تعديل أي اسم يدوياً من الحقول أدناه قبل الضغط على زر الحفظ النهائي.")
    
    final_files_to_zip = {}
    
    # عرض الصور على شكل شبكة (Grid) كل سطر يحتوي صورتين لترتيب احترافي
    cols = st.columns(2)
    for i, item in enumerate(processed_images):
        col = cols[i % 2]
        with col:
            st.markdown(f'<div class="preview-card">', unsafe_allow_html=True)
            
            # تقسيم داخلي للبطاقة: الصورة على اليمين والحقول على اليسار
            sub_col1, sub_col2 = st.columns([1, 2])
            with sub_col1:
                st.image(item["image_data"], use_container_width=True)
            with sub_col2:
                st.markdown(f"**الملف الأصلي:** `{item['original_name']}`")
                st.markdown(item["status"])
                
                # حقل تفاعلي يتيح للمستخدم تعديل الاسم المقترح فوراً
                user_edited_name = st.text_input(
                    f"الاسم النهائي للصورة #{i+1}", 
                    value=item["suggested_name"],
                    key=f"input_{i}"
                )
                
                # معالجة مشكلة تكرار الأسماء (تلقائياً إضافة رقم إذا تكرر الاسم)
                final_name = f"{user_edited_name}{item['extension']}"
                if final_name in final_files_to_zip:
                    final_name = f"{user_edited_name}_{i}{item['extension']}"
                    
                final_files_to_zip[final_name] = item["bytes"]
                
            st.markdown('</div>', unsafe_allow_html=True)
            st.write("") # مسافة تفصل الأسطر

    # --- الخطوة النهائية: الحفظ وتحميل ملف ZIP ---
    st.markdown("---")
    st.subheader("📦 خطوة الإنهاء والتحميل")
    
    if st.button("🚀 إنشاء ملف ZIP بالأسماء الجديدة"):
        zip_path = "renamed_images_package.zip"
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for filename, file_bytes in final_files_to_zip.items():
                zipf.writestr(filename, file_bytes)
                
        st.balloons() # تأثير احتفالي عند النجاح
        
        with open(zip_path, "rb") as f:
            st.download_button(
                label="📥 اضغط هنا لتحميل ملف الـ ZIP الجاهز",
                data=f,
                file_name="renamed_site_images.zip",
                mime="application/zip",
                use_container_width=True
            )
