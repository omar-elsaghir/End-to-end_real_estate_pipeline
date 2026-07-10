from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import urllib.error
import time

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN")
DB_HOST = "dbc-58a1a3ba-94fc.cloud.databricks.com"
WAREHOUSE_ID = "4d72dcee6968660b"

SYSTEM_PROMPT = """
انت محلل بيانات خبير. مهمتك تحويل اسئلة المستخدم الى Databricks SQL فقط.

مخطط قاعدة البيانات:
1. gold_df: title (STRING), location (STRING), price (DOUBLE), area (DOUBLE), property_type (STRING), price_per_sqm (DOUBLE).
2. gold_location_summary: location (STRING), total_properties (BIGINT), avg_price (DOUBLE), avg_area (DOUBLE), avg_price_per_sqm (DOUBLE), max_price (DOUBLE), min_price (DOUBLE).
3. gold_type_summary: property_type (STRING), total_properties (BIGINT), avg_price_per_type (DOUBLE), avg_area_per_type (DOUBLE).
4. gold_area_segment: area_segment (STRING), total_properties (BIGINT), avg_price (DOUBLE).
5. gold_top_expensive: title (STRING), location (STRING), price (DOUBLE), area (DOUBLE).

ملاحظة مهمة جدا: عمود property_type يحتوي على قيم انجليزية فقط:
Villa, Duplex, Chalet, Apartment, Townhouse, Twinhouse, Cabin, Penthouse, Office, Loft, Studio, Medical, Family House, Retail, Building.
لازم تترجم كلام المستخدم العربي للقيمة الانجليزية المطابقة قبل ما تكتب SQL، مثال:
"شقة" -> Apartment, "فيلا" -> Villa, "دوبلكس" -> Duplex, "شاليه" -> Chalet, "تاون هاوس" -> Townhouse,
"توين هاوس" -> Twinhouse, "بنتهاوس" -> Penthouse, "استوديو" -> Studio, "مكتب" -> Office, "محل" -> Retail,
"كابينة" -> Cabin, "مبنى" -> Building.

ملاحظة مهمة جدا: عمود location يحتوي فقط على القيم الانجليزية دي بالظبط (استخدم ILIKE على القيمة المطابقة، ومتعملش تخمين لقيم تانية):
6th of October City, Ain Sokhna, Al Agamy, Al Alamein, Al Dabaa, Alexandria, Central Cairo, El Choueifat,
El Gouna, El Lotus, El Sheikh Zayed, El Shorouk, Ghazala Bay, Golden Square, Heliopolis, Hurghada, Maadi,
Madinaty, Makadi, Mokattam, Mostakbal City, Nasr City, New Alamein, New Cairo, New Cairo - 5th Settlement,
New Capital City, New Capital Gardens, New Heliopolis, New Sphinx, New Zayed, North Coast-Sahel,
North Coast-sahel, North Investors, Northern Expansion, October Gardens, Old Cairo, Port Said,
Qesm Borg El Arab, Ras El Hekma, Ras Sudr, Sahl Hasheesh, Sidi Abdel Rahman, Sidi Heneish, Somabay,
South Investors, South New Cairo.

ترجمة اسماء المناطق من العربي للانجليزي (استخدم ILIKE '%...%' على القيمة المطابقة، ولو فيه اكتر من قيمة محتملة استخدم OR بين قوسين):
"التجمع" أو "التجمع الخامس" أو "الخامس" -> location ILIKE '%New Cairo%' OR location ILIKE '%5th Settlement%'
"التجمع الجنوبي" -> location ILIKE '%South New Cairo%'
"الشيخ زايد" -> location ILIKE '%Sheikh Zayed%'
"زايد الجديدة" أو "نيو زايد" -> location ILIKE '%New Zayed%'
"العاصمة الادارية" أو "العاصمة" -> location ILIKE '%New Capital City%' OR location ILIKE '%New Capital Gardens%'
"المعادي" -> location ILIKE '%Maadi%'
"الساحل الشمالي" أو "الساحل" -> location ILIKE '%North Coast%'
"مدينتي" -> location ILIKE '%Madinaty%'
"مستقبل سيتي" -> location ILIKE '%Mostakbal City%'
"الشروق" -> location ILIKE '%El Shorouk%'
"مدينة نصر" -> location ILIKE '%Nasr City%'
"مصر الجديدة" أو "هليوبوليس" -> location ILIKE '%Heliopolis%'
"هليوبوليس الجديدة" -> location ILIKE '%New Heliopolis%'
"المقطم" -> location ILIKE '%Mokattam%'
"القاهرة القديمة" -> location ILIKE '%Old Cairo%'
"وسط البلد" أو "القاهرة الخديوية" -> location ILIKE '%Central Cairo%'
"السادس من أكتوبر" أو "أكتوبر" -> location ILIKE '%6th of October City%'
"حدائق أكتوبر" -> location ILIKE '%October Gardens%'
"العلمين" -> location ILIKE '%Al Alamein%' OR location ILIKE '%New Alamein%'
"الدبعة" -> location ILIKE '%Al Dabaa%'
"العجمي" -> location ILIKE '%Al Agamy%'
"الاسكندرية" -> location ILIKE '%Alexandria%'
"العين السخنة" أو "السخنة" -> location ILIKE '%Ain Sokhna%'
"الغردقة" -> location ILIKE '%Hurghada%'
"الجونة" -> location ILIKE '%El Gouna%'
"مكادي" -> location ILIKE '%Makadi%'
"سهل حشيش" -> location ILIKE '%Sahl Hasheesh%'
"سوما باي" -> location ILIKE '%Somabay%'
"غزالة باي" -> location ILIKE '%Ghazala Bay%'
"رأس الحكمة" -> location ILIKE '%Ras El Hekma%'
"رأس سدر" -> location ILIKE '%Ras Sudr%'
"سيدي عبد الرحمن" -> location ILIKE '%Sidi Abdel Rahman%'
"سيدي هنيش" -> location ILIKE '%Sidi Heneish%'
"بورسعيد" -> location ILIKE '%Port Said%'
"برج العرب" -> location ILIKE '%Qesm Borg El Arab%'
"الشويفات" -> location ILIKE '%El Choueifat%'
"اللوتس" -> location ILIKE '%El Lotus%'
"سفينكس الجديدة" -> location ILIKE '%New Sphinx%'
"المربع الذهبي" -> location ILIKE '%Golden Square%'
"التوسعة الشمالية" -> location ILIKE '%Northern Expansion%'
"المستثمرين الشمالية" -> location ILIKE '%North Investors%'
"المستثمرين الجنوبية" -> location ILIKE '%South Investors%'

القواعد:
- ارجع كود SQL فقط بدون اي نص او markdown.
- استخدم الجداول التجميعية قدر الامكان.
- استخدم ILIKE للبحث النصي، وحط اي شروط OR بين قوسين صح نحويا.
- استخدم SQL Aliases واضحة للاعمدة.
- تجنب كلمة order كاسم عمود، استخدم اسماء بديلة.

- تنبيه هام جدا: لو المستخدم طلب عقار بشكل عام (مثلا "عايز شقة" أو "I want an apartment" أو "محتاج فيلا")، ده يعتبر سؤال بيانات! لازم ترجع كود SQL يجيب عينة من العقارات دي وتستخدم LIMIT 10.
- فقط لو السؤال مجرد تحية أو شكر ولا يحتوي على أي طلب عقاري (مثلا "السلام عليكم" أو "شكرا")، ارجع بالظبط الجملة دي وبس بدون اي تعديل:
NOT_A_DATA_QUERY
"""

GREETING_SENTINEL = "NOT_A_DATA_QUERY"
GREETING_RESPONSE_AR = "أهلاً بيك! اسأل عن أسعار العقارات، المناطق، أو الأنواع المتاحة وهجاوبك ببيانات حقيقية من السوق."


def call_gemini(user_query):
    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY is not set in environment variables")

    # THIS WILL CRASH THE BUILD INSTANTLY
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-lite-latest:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": user_query}]}],
        "generationConfig": {
            "maxOutputTokens": 1024
        }
    }
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode(errors="replace")
        raise Exception(f"Gemini API error ({e.code}): {err_body}")

    if "error" in data:
        raise Exception(f"Gemini API error: {data['error']}")

    candidates = data.get("candidates")
    if not candidates:
        raise Exception(f"Gemini returned no candidates. Full response: {json.dumps(data)}")

    candidate = candidates[0]
    finish_reason = candidate.get("finishReason")
    content = candidate.get("content")

    if not content or "parts" not in content:
        raise Exception(
            f"Gemini did not return content (finishReason={finish_reason}). "
            f"Full candidate: {json.dumps(candidate)}"
        )

    text = content["parts"][0].get("text", "")
    if not text:
        raise Exception(f"Gemini returned empty text (finishReason={finish_reason})")

    return text.replace("```sql", "").replace("```", "").strip()


def run_databricks_sql(query):
    url = f"https://{DB_HOST}/api/2.0/sql/statements"
    payload = {
        "statement": query,
        "warehouse_id": WAREHOUSE_ID,
        "wait_timeout": "30s"
    }
    headers = {
        "Authorization": f"Bearer {DATABRICKS_TOKEN}",
        "Content-Type": "application/json"
    }

    # 1. Send the initial query
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        result = json.loads(resp.read())

    # 2. Poll if the warehouse is waking up or the query is still running
    while result.get("status", {}).get("state") in ["PENDING", "RUNNING"]:
        statement_id = result.get("statement_id")
        poll_url = f"https://{DB_HOST}/api/2.0/sql/statements/{statement_id}"

        time.sleep(2)

        poll_req = urllib.request.Request(
            poll_url, headers=headers, method="GET"
        )
        with urllib.request.urlopen(poll_req, timeout=40) as resp:
            result = json.loads(resp.read())

    # 3. Check final status and handle errors gracefully
    state = result.get("status", {}).get("state")
    if state != "SUCCEEDED":
        error_msg = result.get("status", {}).get("error", {}).get("message", "")
        if state == "FAILED":
            raise Exception(f"SQL Error: {error_msg}")
        else:
            raise Exception(
                f"يتم الآن تشغيل خوادم قواعد البيانات، برجاء المحاولة مرة أخرى خلال دقيقة. (Status: {state})")

    # 4. Extract data
    columns = [c["name"] for c in result["manifest"]["schema"]["columns"]]
    rows = result.get("result", {}).get("data_array", [])

    return columns, rows


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers["Content-Length"])
            body = json.loads(self.rfile.read(length))
            user_query = body.get("query", "").strip()

            if not user_query:
                self._send(400, {"error": "Empty query"})
                return

            sql_query = call_gemini(user_query)

            if sql_query.strip().upper() == GREETING_SENTINEL:
                self._send(200, {
                    "sql": None,
                    "columns": ["response"],
                    "rows": [[GREETING_RESPONSE_AR]]
                })
                return

            columns, rows = run_databricks_sql(sql_query)

            self._send(200, {
                "sql": sql_query,
                "columns": columns,
                "rows": rows
            })
        except Exception as e:
            self._send(400, {"error": str(e)})

    def _send(self, status, payload):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()