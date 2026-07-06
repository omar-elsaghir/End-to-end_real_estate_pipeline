from http.server import BaseHTTPRequestHandler
import json
import os
import numpy as np
import onnxruntime as ort

BASE = os.path.dirname(__file__)

sess = ort.InferenceSession(os.path.join(BASE, "artifacts", "model.onnx"))
input_name = sess.get_inputs()[0].name

with open(os.path.join(BASE, "artifacts", "artifacts.json")) as f:
    A = json.load(f)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers["Content-Length"])
            body = json.loads(self.rfile.read(length))

            area = float(body["area"])
            bedrooms = float(body["bedrooms"])
            bathrooms = float(body["bathrooms"])
            location = body["location"]
            ptype = body["property_type"]
            compound = body.get("compound", "unknown")
            is_ready = float(body.get("is_ready", 0))

            global_mean = A["global_mean"]
            location_encoded = A["smoothed_map"].get(location, global_mean)
            loc_type_key = f"{location}_{ptype}"
            loc_type_encoded = A["lt_map"].get(loc_type_key, global_mean)
            loc_count = A["loc_freq"].get(location, 1)
            compound_enc = A["compound_map"].get(
                compound, A["compound_map"].get("unknown", global_mean)
            )
            le_classes = A["le_classes"]
            property_type_enc = float(le_classes.index(ptype)) if ptype in le_classes else -1.0
            log_area = float(np.log1p(area))

            row = [
                area, log_area, bedrooms, bathrooms,
                bedrooms / (bathrooms + 1),
                area / (bedrooms + bathrooms + 1),
                location_encoded, loc_type_encoded, compound_enc,
                loc_count, property_type_enc,
                log_area * location_encoded, is_ready,
            ]

            row_arr = np.array([row], dtype=np.float32)
            log_pred = sess.run(None, {input_name: row_arr})[0][0][0]
            price = float(np.expm1(log_pred))

            self._send(200, {"price_egp": round(price)})
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