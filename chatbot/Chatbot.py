# Databricks notebook source
# MAGIC %pip install google-generativeai

# COMMAND ----------

import google.generativeai as genai

# 1. إعداد الـ API Key
GEMINI_API_KEY = ""
genai.configure(api_key=GEMINI_API_KEY)

# 2. هندسة الأوامر 
SYSTEM_PROMPT = """
أنت مساعد ذكي ومحلل بيانات خبير. مهمتك هي تحويل أسئلة المستخدم إلى Databricks SQL.
مخطط قاعدة البيانات (Gold Layer):

1. `gold_df`: title (STRING), location (STRING), price (DOUBLE), area (DOUBLE), property_type (STRING), price_per_sqm (DOUBLE).
2. `gold_location_summary`: location (STRING), total_properties (BIGINT), avg_price (DOUBLE), avg_area (DOUBLE), avg_price_per_sqm (DOUBLE), max_price (DOUBLE), min_price (DOUBLE).
3. `gold_type_summary`: property_type (STRING), total_properties (BIGINT), avg_price_per_type (DOUBLE), avg_area_per_type (DOUBLE).
4. `gold_area_segment`: area_segment (STRING), total_properties (BIGINT), avg_price (DOUBLE).
5. `gold_top_expensive`: title (STRING), location (STRING), price (DOUBLE), area (DOUBLE).

القواعد الصارمة:
1. أرجع كود SQL فقط بدون أي نصوص أو Markdown.
2. استخدم الجداول التجميعية (Summaries) للإحصائيات العامة لتسريع الاستعلام.
3. استعلم باسم الجدول مباشرة (مثال: SELECT * FROM gold_df).
4. استخدم ILIKE للبحث النصي غير الحساس لحالة الأحرف.
5. هام جداً: عند عرض أعمدة السعر أو المساحة، استخدم SQL Aliases دائماً لتوضيح الوحدة. (مثال: area AS `Area (sqm)` و price AS `Price (EGP)`).
"""
# 3. دالة المحادثة وتنفيذ الـ Query
def chat_with_data(user_query):
    print(f"السؤال: {user_query}\n")
    print("جاري التفكير وكتابة الـ Query...\n")
    
    try:
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            system_instruction=SYSTEM_PROMPT
        )
        response = model.generate_content(user_query)
        
        # تنظيف الكود الراجع من أي تنسيقات
        clean_sql = response.text.replace("```sql", "").replace("```", "").strip()
        
        print(f"الاستعلام اللي تم تنفيذه:\n{clean_sql}\n")
        print("-" * 50)
        
        # تنفيذ الـ SQL باستخدام محرك Spark وعرضه
        result_df = spark.sql(clean_sql)
        display(result_df)
        
    except Exception as e:
        print(f"حصلت مشكلة: {e}")

# COMMAND ----------

chat_with_data("إيه هو متوسط أسعار الشقق في New Cairo؟")

# COMMAND ----------

chat_with_data("هاتلي كل الشقق الموجودة في كل المدن اللي سعرها بيتراوح بين 2000000 و 5000000، واعرضلي اسم المدينة، اسم العقار، السعر، والمساحة.")

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT property_type, COUNT(*) FROM gold_df WHERE location ILIKE '%Madinaty%' GROUP BY property_type;
# MAGIC

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT property_type, COUNT(*) FROM gold_df WHERE location ILIKE '%Nasr City%' GROUP BY property_type;
# MAGIC

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT property_type, COUNT(*) FROM gold_df WHERE location ILIKE '%Mokattam%' GROUP BY property_type;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT MIN(price) FROM gold_df WHERE location ILIKE '%El Shorouk%' AND property_type ILIKE 'Apartment';

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT title, location, price, area, property_type
# MAGIC FROM gold_df
# MAGIC WHERE property_type ILIKE 'Apartment' AND location ILIKE '%Nasr City%'
# MAGIC LIMIT 20;