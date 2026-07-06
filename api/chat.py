from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import urllib.error

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

ملاحظة مهمة جدا: عمود property_type يحتوي على قيم انجليزية فقط، من ضمنها:
Villa, Duplex, Chalet, Apartment, Townhouse, Twinhouse, Cabin, Penthouse, Office, Loft, Studio, Medical, Family House, Retail, Building.
لازم تترجم كلام المستخدم العربي للقيمة الانجليزية المطابقة قبل ما تكتب SQL. مثال: "شقة" -> Apartment, "فيلا" -> Villa, "دوبلكس" -> Duplex, "شاليه" -> Chalet, "تاون هاوس" -> Townhouse, "بنتهاوس" -> Penthouse, "استوديو" -> Studio, "مكتب" -> Office, "محل" -> Retail.

ملاحظة مهمة جدا: عمود location قد يحتوي على اسماء مناطق بالانجليزي او مترجمة صوتيا (transliterated)، وليس بالعربي دايما. لو المستخدم كتب اسم منطقة بالعربي، حاول تولد اكتر من صيغة محتملة بالانجليزي باستخدام OR، مثال:
"التجمع" -> location ILIKE '%New Cairo%' OR location ILIKE '%Tagamo%' OR location ILIKE '%5th Settlement%'
"الشيخ زايد" -> location ILIKE '%Sheikh Zayed%' OR location ILIKE '%Zayed%'
"العاصمة الادارية" -> location ILIKE '%New Capital%' OR location ILIKE '%Administrative Capital%'
"المعادي" -> location ILIKE '%Maadi%'
"الساحل الشمالي" -> location ILIKE '%North Coast%' OR location ILIKE '%Sahel%'

القواعد:
- ارجع كود SQL فقط بدون اي نص او markdown.
- استخدم الجداول التجميعية قدر الامكان.
- استخدم ILIKE للبحث النصي، وحط اي شروط OR بين قوسين صح نحويا.
- استخدم SQL Aliases واضحة للاعمدة.
- تجنب كلمة order كاسم عمود، استخدم اسماء بديلة.
- لو السؤال مش متعلق بالعقارات او البيانات (زي تحية، شكر، أو كلام عام)، ارجع بالظبط الجملة دي وبس بدون اي تعديل:
NOT_A_DATA_QUERY
"""

GREETING_SENTINEL = "NOT_A_DATA_QUERY"
GREETING_RESPONSE_AR = "أهلاً بيك! اسأل عن أسعار العقارات، المناطق، أو الأنواع المتاحة وهجاوبك ببيانات حقيقية من السوق."


def call_gemini(user_query):
    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY is not set in environment variables")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": user_query}]}],
        "generationConfig": {
            "thinkingConfig": {
                "thinkingBudget": 0
            },
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
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {DATABRICKS_TOKEN}",
            "Content-Type": "application/json"
        }, method="POST"
    )
    with urllib.request.urlopen(req, timeout=35) as resp:
        result = json.loads(resp.read())

    if result.get("status", {}).get("state") != "SUCCEEDED":
        raise Exception(f"Query did not succeed: {result.get('status')}")

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

            # Handle greetings / non-data queries without touching Databricks
            if GREETING_SENTINEL in sql_query.upper():
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