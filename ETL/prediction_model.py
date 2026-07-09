# Databricks notebook source
import numpy as np
import pandas as pd
import logging
logging.getLogger("mlflow.utils.requirements_utils").setLevel(logging.ERROR)

gold_df = spark.table("gold_df").toPandas()
gold_df["log_price"] = np.log1p(gold_df["price"])

model_df = gold_df.dropna(subset=["price","area","bedrooms","bathrooms","location","property_type"])
model_df = model_df.copy()

model_df["location"] = model_df["location"].str.strip().replace({
    "North Coast-sahel": "North Coast-Sahel",
    "New Cairo - 5th Settlement": "New Cairo",
})

TOP_TYPES = ["Apartment","Chalet","Villa","Townhouse","Duplex",
             "Twinhouse","Penthouse","Studio","Loft","Cabin",
             "Office","Medical","Family House","Retail"]
model_df["property_type_clean"] = model_df["property_type"].where(
    model_df["property_type"].isin(TOP_TYPES), other="Other")
model_df = model_df[model_df["property_type_clean"] != "Other"]

p1  = model_df["price"].quantile(0.01)
p99 = model_df["price"].quantile(0.99)
model_df = model_df[(model_df["price"] >= p1) & (model_df["price"] <= p99)]
model_df["price_per_sqm_raw"] = model_df["price"] / model_df["area"]
model_df = model_df[model_df["price_per_sqm_raw"] >= 5000]

# ── Per location+type IQR filter (removes segment-level outliers) ──
before = len(model_df)
model_df["loc_type_key"] = model_df["location"] + "_" + model_df["property_type_clean"]
def iqr_filter(group):
    q1 = group["log_price"].quantile(0.10)
    q3 = group["log_price"].quantile(0.90)
    iqr = q3 - q1
    return group[(group["log_price"] >= q1 - 1.5*iqr) & 
                 (group["log_price"] <= q3 + 1.5*iqr)]
model_df = model_df.groupby("loc_type_key", group_keys=False).apply(iqr_filter)
print(f"IQR filter removed {before - len(model_df)} per-segment outliers")

# ── Only keep is_ready from title (only valid signal) ─────────
model_df["is_ready"] = model_df["title"].str.lower().apply(
    lambda t: 1 if any(x in str(t) for x in 
              ["ready to move","ready-to-move","rtm","move in","move-in"]) else 0
)

# ── Expanded compound list ────────────────────────────────────
COMPOUNDS = [
    # Premium / Well-known
    "palm hills","palm valley","palm parks","palm walk",
    "sodic","ora","katameya heights","katameya dunes","katameya residence",
    "mivida","hyde park","sarai","scene","village gate","village gardens",
    "hacienda","hacienda bay","hacienda white","hacienda waters",
    "hacienda hills","marassi","caesar","cali","badya","capri",
    "zed","zed east","zed towers","mountain view","mountain view icity",
    "mountain view hyde park","mountain view 5th",
    "bloomfields","telal","la vista","la vista bay","la vista city",
    "la vista topaz","la vista gardens",
    "il monte galala","azzurra","soma bay","the med","jefaira",
    "lakeyard","brix","kerasia","monark","owest","o west",
    "westown","gaia","taj city","the estates","valory","kinda",
    "ivoire","midtown","leaves","petal","fouka bay","seashore",
    "solare","skywaves","mazarine","amwaj","naia","naia bay",
    "samaher","elora","layan","lago","cleopatra","golfville",
    "anakaji","kaveh","vero","neopolis","rivan","b home",
    "june","sidi heneish","marina","porto","porto said","porto sokhna",
    "porto new cairo","ain bay","silver sands","north edge","vale",
    "blue blue","white sand","pearl","diamond bay","coral",
    "veranda","azha","sia","sia alamein","grand alamein",
    "dnc","dabaa","alamein towers","salt","soul","vida","vida alamein",
    "one ninety","scene7","scene 7","uptown cairo","mirage",
    "royal maxim","garden city","heliopolis","sheraton","nasr city",
    "zamalek","dokki","mohandeseen","madina","hayah","ora ora",
    "green river","new giza","giza pyramids","sky condos",
    "lakeville","lake park","lake residence","the waterway",
    "compound 90","new city","star city","city view","garden view",
    "the gate","north gate","south gate","east gate","west gate",
    "aria","senia","mona park","rock eden","quartet","revin",
    "el patio","patio vera","patio zahia","patio town",
    "green square","oia","cairo gate","capital gardens","capital prime",
    "r7","r8","r9","downtown","trio","lc waikiki","golf porto",
    "golf university","pyramids hills","allegria","beverly hills",
    "wadi degla","lotus","south lotus","north lotus","south investors",
    "north investors","investors","golden square","golden land",
    "makadi","makadi heights","makadi orascom",
    "sahl hasheesh","el gouna","gouna","hurghada grand",
    "el ahyaa","mena garden city","meadows park","valore",
    "one katameya","sunridge","zizinia","mena","menafn",
    "one90","lv","leben","evora","nova","elysium","serenity",
    "lmonte","lavista","vinci north coast","v nile","4seasons"
]

def extract_compound(title):
    t = str(title).lower()
    for compound in COMPOUNDS:
        if compound in t:
            return compound
    return "unknown"

model_df["compound"] = model_df["title"].apply(extract_compound)

identified = (model_df["compound"] != "unknown").sum()
total = len(model_df)
print(f"✅ Compound coverage: {identified} / {total} = {identified/total*100:.1f}%")
print(f"Unique compounds identified: {model_df[model_df['compound'] != 'unknown']['compound'].nunique()}")
print("\nTop 25 compounds:")
print(model_df["compound"].value_counts()[model_df["compound"].value_counts().index != "unknown"].head(25))

# ── Check avg price by compound (validation)
comp_price = model_df.groupby("compound")["price"].median().sort_values(ascending=False)
print("\nTop 10 compounds by median price:")
print(comp_price[comp_price.index != "unknown"].head(10).apply(lambda x: f"{x:,.0f} EGP"))

# COMMAND ----------

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

train_df, test_df = train_test_split(model_df, test_size=0.2, random_state=42)
train_df = train_df.copy()
test_df  = test_df.copy()

global_mean = train_df["log_price"].mean()

# ── Smoothed location encoding ────────────────────────────────
K = 10
loc_counts   = train_df.groupby("location")["log_price"].count()
loc_means    = train_df.groupby("location")["log_price"].mean()
smoothed_map = (loc_counts * loc_means + K * global_mean) / (loc_counts + K)
train_df["location_encoded"] = train_df["location"].map(smoothed_map)
test_df["location_encoded"]  = test_df["location"].map(smoothed_map).fillna(global_mean)

# ── Location + Type combo encoding ───────────────────────────
train_df["loc_type"] = train_df["location"] + "_" + train_df["property_type_clean"]
test_df["loc_type"]  = test_df["location"]  + "_" + test_df["property_type_clean"]
lt_counts = train_df.groupby("loc_type")["log_price"].count()
lt_means  = train_df.groupby("loc_type")["log_price"].mean()
lt_map    = (lt_counts * lt_means + K * global_mean) / (lt_counts + K)
train_df["loc_type_encoded"] = train_df["loc_type"].map(lt_map)
test_df["loc_type_encoded"]  = test_df["loc_type"].map(lt_map).fillna(global_mean)

# ── NEW: Compound target encoding ────────────────────────────
comp_counts = train_df.groupby("compound")["log_price"].count()
comp_means  = train_df.groupby("compound")["log_price"].mean()
K_comp = 5  # lower K for compounds (more specific signal)
compound_map = (comp_counts * comp_means + K_comp * global_mean) / (comp_counts + K_comp)
train_df["compound_encoded"] = train_df["compound"].map(compound_map)
test_df["compound_encoded"]  = test_df["compound"].map(compound_map).fillna(
    compound_map.get("unknown", global_mean))

print("Top 10 compounds by encoded price (log scale):")
print(compound_map[compound_map.index != "unknown"].sort_values(ascending=False).head(10))
print(f"\nunknown compound encoded value: {compound_map.get('unknown', global_mean):.4f}")

# ── Location frequency ────────────────────────────────────────
loc_freq = train_df["location"].value_counts()
train_df["location_count"] = train_df["location"].map(loc_freq)
test_df["location_count"]  = test_df["location"].map(loc_freq).fillna(1)

# ── Label encode property_type ────────────────────────────────
le = LabelEncoder()
le.fit(train_df["property_type_clean"])
train_df["property_type_enc"] = le.transform(train_df["property_type_clean"])
test_df["property_type_enc"]  = test_df["property_type_clean"].map(
    lambda x: le.transform([x])[0] if x in le.classes_ else -1)

# ── Derived features (fixed — no more area_x_location) ────────
for df in [train_df, test_df]:
    df["log_area"]            = np.log1p(df["area"])
    df["log_area_x_location"] = df["log_area"] * df["location_encoded"]  # fixed interaction
    df["bed_bath_ratio"]      = df["bedrooms"] / (df["bathrooms"] + 1)
    df["sqm_per_room"]        = df["area"] / (df["bedrooms"] + df["bathrooms"] + 1)

# ── Clean 13-feature set (dropped 3 dead + fixed redundancy) ──
feature_cols = [
    "area", "log_area",               # size
    "bedrooms", "bathrooms",          # rooms
    "bed_bath_ratio", "sqm_per_room", # room ratios
    "location_encoded",               # where
    "loc_type_encoded",               # where + type
    "compound_encoded",               # ✅ NEW: which compound
    "location_count",                 # market depth
    "property_type_enc",              # property type
    "log_area_x_location",            # fixed interaction
    "is_ready",                       # ✅ KEEP: only valid title signal
]

X_train = train_df[feature_cols]
y_train = train_df["log_price"]
X_test  = test_df[feature_cols]
y_test  = test_df["log_price"]

print(f"\nX_train: {X_train.shape}  |  X_test: {X_test.shape}")
print(f"\nFeature correlations with log_price:")
corr = train_df[feature_cols + ["log_price"]].corr()["log_price"].drop("log_price").sort_values(ascending=False)
print(corr.round(4))

# COMMAND ----------

import mlflow
import mlflow.xgboost
from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

def evaluate(y_true_log, y_pred_log):
    y_pred_log_clipped = np.clip(y_pred_log, a_min=None, a_max=25)
    y_true = np.expm1(y_true_log)
    y_pred = np.expm1(y_pred_log_clipped)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae  = mean_absolute_error(y_true, y_pred)
    r2   = r2_score(y_true, y_pred)
    return rmse, mae, r2

with mlflow.start_run(run_name="xgboost_16features_baseline"):
    xgb_baseline = XGBRegressor(
        n_estimators=500, learning_rate=0.05, max_depth=6,
        subsample=0.8, colsample_bytree=0.8, random_state=42
    )
    xgb_baseline.fit(X_train, y_train)
    preds = xgb_baseline.predict(X_test)
    rmse, mae, r2 = evaluate(y_test, preds)
    mlflow.log_params(xgb_baseline.get_params())
    mlflow.log_metric("rmse", rmse)
    mlflow.log_metric("mae", mae)
    mlflow.log_metric("r2", r2)
    mlflow.xgboost.log_model(xgb_baseline, "model", input_example=X_train.head(3))
    print(f"XGBoost baseline (16 features) -> RMSE: {rmse:,.0f}  MAE: {mae:,.0f}  R2: {r2:.3f}")

importances = pd.DataFrame({
    "feature": feature_cols,
    "importance": xgb_baseline.feature_importances_
}).sort_values("importance", ascending=False)
display(importances)

# COMMAND ----------

from hyperopt import fmin, tpe, hp, Trials, STATUS_OK

def objective(params):
    with mlflow.start_run(nested=True):
        model = XGBRegressor(
            n_estimators=int(params['n_estimators']),
            max_depth=int(params['max_depth']),
            learning_rate=params['learning_rate'],
            subsample=params['subsample'],
            colsample_bytree=params['colsample_bytree'],
            min_child_weight=int(params['min_child_weight']),
            gamma=params['gamma'],
            reg_alpha=params['reg_alpha'],
            reg_lambda=params['reg_lambda'],
            random_state=42
        )
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        rmse, mae, r2 = evaluate(y_test, preds)
        mlflow.log_metric("rmse", rmse)
        return {"loss": rmse, "status": STATUS_OK}

search_space = {
    'n_estimators':     hp.quniform('n_estimators', 300, 1500, 50),
    'max_depth':        hp.quniform('max_depth', 3, 8, 1),
    'learning_rate':    hp.loguniform('learning_rate', -5, -1),
    'subsample':        hp.uniform('subsample', 0.6, 1.0),
    'colsample_bytree': hp.uniform('colsample_bytree', 0.6, 1.0),
    'min_child_weight': hp.quniform('min_child_weight', 1, 20, 1),
    'gamma':            hp.uniform('gamma', 0, 0.5),
    'reg_alpha':        hp.loguniform('reg_alpha', -5, 2),
    'reg_lambda':       hp.loguniform('reg_lambda', -5, 2),
}

with mlflow.start_run(run_name="xgboost_tuning_16features"):
    best_params = fmin(fn=objective, space=search_space,
                       algo=tpe.suggest, max_evals=60, trials=Trials())

print("Best params:", best_params)

# COMMAND ----------

with mlflow.start_run(run_name="xgboost_final_16features"):
    final_model = XGBRegressor(
        n_estimators=int(best_params['n_estimators']),
        max_depth=int(best_params['max_depth']),
        learning_rate=best_params['learning_rate'],
        subsample=best_params['subsample'],
        colsample_bytree=best_params['colsample_bytree'],
        min_child_weight=int(best_params['min_child_weight']),
        gamma=best_params['gamma'],
        reg_alpha=best_params['reg_alpha'],
        reg_lambda=best_params['reg_lambda'],
        random_state=42
    )
    final_model.fit(X_train, y_train)
    preds_xgb = final_model.predict(X_test)
    rmse, mae, r2 = evaluate(y_test, preds_xgb)
    mlflow.log_params(best_params)
    mlflow.log_metric("rmse", rmse)
    mlflow.log_metric("mae", mae)
    mlflow.log_metric("r2", r2)
    mlflow.xgboost.log_model(final_model, "model", input_example=X_train.head(3))
    xgb_run_id = mlflow.active_run().info.run_id
    print(f"Final XGBoost -> RMSE: {rmse:,.0f}  MAE: {mae:,.0f}  R2: {r2:.3f}")
    print(f"Run ID: {xgb_run_id}")

# COMMAND ----------

from onnxmltools.convert import convert_xgboost
from onnxmltools.convert.common.data_types import FloatTensorType
import xgboost as xgb
import os

# Save and reload as a raw Booster to fully strip feature name metadata
final_model.save_model("/tmp/_temp_model.json")

booster = xgb.Booster()
booster.load_model("/tmp/_temp_model.json")
booster.feature_names = None
booster.feature_types = None

initial_type = [('input', FloatTensorType([None, len(feature_cols)]))]
onnx_model = convert_xgboost(booster, initial_types=initial_type)

export_dir = "/Workspace/Users/omar.ramadan.elsaghir@gmail.com/model_export"
os.makedirs(export_dir, exist_ok=True)

with open(f"{export_dir}/model.onnx", "wb") as f:
    f.write(onnx_model.SerializeToString())

import json
artifacts = {
    "smoothed_map": smoothed_map.to_dict(),
    "lt_map": lt_map.to_dict(),
    "compound_map": compound_map.to_dict(),
    "loc_freq": loc_freq.to_dict(),
    "global_mean": float(global_mean),
    "le_classes": le.classes_.tolist(),
    "location_choices": sorted(smoothed_map.index.tolist()),
    "type_choices": sorted(le.classes_.tolist()),
    "compound_choices": ["unknown"] + sorted([c for c in compound_map.index if c != "unknown"]),
}
with open(f"{export_dir}/artifacts.json", "w") as f:
    json.dump(artifacts, f)

print("Saved model.onnx and artifacts.json to", export_dir)