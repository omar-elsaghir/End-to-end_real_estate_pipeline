from http.server import BaseHTTPRequestHandler
import json
import os

BASE = os.path.dirname(__file__)
with open(os.path.join(BASE, "artifacts", "artifacts.json")) as f:
    A = json.load(f)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        payload = {
            "locations": A["location_choices"],
            "property_types": A["type_choices"],
            "compounds": A["compound_choices"],
        }
        self.wfile.write(json.dumps(payload).encode())