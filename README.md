<div align="center">

# 🇪🇬 End-to-End Real Estate Price Intelligence Pipeline

## Web Scraping • Medallion Lakehouse • Predictive Pricing • Conversational AI

*Digital Egypt Builders Initiative (DEPI) — Final Project (July 2026)*

![Databricks](https://img.shields.io/badge/Databricks-Lakehouse-F37021?logo=databricks)
![Apache Airflow](https://img.shields.io/badge/Airflow-Orchestration-017CEE?logo=apacheairflow)
![PySpark](https://img.shields.io/badge/PySpark-Data_Engineering-E25A1C?logo=apachespark)
![XGBoost](https://img.shields.io/badge/ML-XGBoost-blue?logo=xgboost)
![Gemini](https://img.shields.io/badge/AI-Gemini_LLM-8E75B2)

</div>

---

## 📋 Table of Contents

- [Abstract & Overview](#-abstract--overview)
- [Market Problem](#-market-problem)
- [Pipeline Architecture](#-pipeline-architecture)
  - [1. Data Collection](#1-data-collection-web-scraping)
  - [2. Databricks Lakehouse (Medallion)](#2-databricks-lakehouse-medallion-architecture)
- [Downstream Products](#-downstream-products)
  - [Price Prediction Model](#1-price-prediction-model)
  - [Conversational Chatbot (RAG)](#2-conversational-chatbot-rag)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Results & Discussion](#-results--discussion)

---

## ✨ Abstract & Overview

The residential and commercial real estate markets generate large volumes of listing data across many independent platforms, but that data is fragmented, inconsistently structured, and rarely analysis-ready. 

This project designs and implements an **end-to-end real estate data pipeline** that ingests listings from **five web-scraped property platforms**, processes them through a **Databricks Lakehouse** using the Medallion Architecture (Bronze, Silver, Gold), and delivers two downstream products:
1. A **Machine Learning Model** that predicts property prices from listing attributes.
2. A **Conversational Chatbot (RAG)** that lets end users query the market data and obtain price estimates in natural language.

---

## 🎯 Market Problem

Real estate listings are scattered across dozens of independent platforms, each with its own layout, terminology, and update frequency. Buyers, sellers, and analysts who want a reliable, up-to-date view of the market face:
- **Fragmented Data:** Visiting multiple sites manually to compare listings.
- **Inconsistent Quality:** Prices in different currencies, mixed area units, duplicate listings, and missing critical fields (like finishing level).
- **No Reliable Pricing:** Without a systematic pipeline, raw data cannot be reliably used for pricing analysis, trend detection, or machine learning.

---

## 🚀 Pipeline Architecture

The entire system is built around a scalable, automated data pipeline, orchestrated by **Apache Airflow**.

### 1. Data Collection (Web Scraping)
Listing data is collected daily from five live real estate platforms in Egypt, covering residential, rental, commercial, and off-plan segments:
- **Aqar Map** (General residential & commercial resale)
- **Bayut** (Apartments, villas & duplex listings with finishing detail)
- **Nawy** (New-development & off-plan project listings)
- **Property Finder** (Rental & resale with strong neighborhood coverage)
- **Dubizzle** (Commercial & investment property listings)

*Tools: Scrapy handles static pages at scale; Selenium renders JavaScript-heavy listings.*

### 2. Databricks Lakehouse (Medallion Architecture)

The pipeline utilizes **Databricks, Delta Lake, and PySpark** to enforce ACID transactions, time travel, and schema enforcement over cloud object storage.

| Layer | Purpose | Details |
|-------|---------|---------|
| **🥉 Bronze** | **Raw Ingestion** | Unmodified scraper output stored as-is in append-only Delta tables. Acts as a complete audit history for full reprocessing. |
| **🥈 Silver** | **Cleaning & Standardization** | Prices parsed to numeric EGP values, area converted to square meters, locations geocoded to lat/long, and fuzzy deduplication across all platforms. |
| **🥇 Gold** | **Aggregation & Features** | Business-ready feature tables. Computes price per square meter, location summaries, area segmentation tiers, and ML feature tables. |

---

## 🧠 Downstream Products

### 1. Price Prediction Model
Using the curated Gold-layer features, we trained gradient-boosted ensembles to predict property prices.
- **Models Compared:** Linear Regression (Baseline), Random Forest, XGBoost, LightGBM.
- **Results:** **LightGBM** and **XGBoost** significantly outperformed linear models across MAE, RMSE, and R².
- **MLOps:** Experiment versioning, hyperparameter tuning, and metric logging handled via **MLflow**. The best model is promoted to a **Databricks Model Serving** REST endpoint.

### 2. Conversational Chatbot (RAG)
A natural language assistant that answers market questions strictly grounded in our data.
- **Flow:** User asks an Arabic natural-language question → Gemini LLM translates the intent into an optimized Databricks SQL query (Text-to-SQL) → Query executes against the live Gold layer → Chatbot responds with a grounded answer citing specific data.
- **No Hallucinations:** Every answer is strictly grounded in live Gold-layer data, not the LLM's prior training knowledge.

---

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Web Scraping** | Python, Scrapy, Selenium, BeautifulSoup | Scalable extraction from static and dynamic sites |
| **Orchestration** | Apache Airflow | Schedules parallel scrapers and isolates failures |
| **Lakehouse** | Databricks, Delta Lake, PySpark | Scalable ETL and Medallion architecture |
| **ML Training** | XGBoost, LightGBM, scikit-learn, MLflow | Model training and experiment tracking |
| **Model Serving** | Databricks Model Serving | Real-time REST endpoints for predictions |
| **Chatbot / RAG** | Gemini LLM, Databricks SQL Connector | Natural-language queries over structured data |

---

## 📁 Project Structure

```text
NHA-017/
│
├── dags/                               # Airflow DAGs for pipeline orchestration
│   └── main_pipeline_dag.py            # Complete ETL workflow orchestration
│
├── shared/                             # Shared volume - All processing scripts
│   │
│   ├── scraping_scripts/               # 🔵 Stage 1: Web Scraping (Bronze Layer)
│   │   ├── scrape_propertyfinder.py    # PropertyFinder scraper
│   │   ├── scrape_bayut.py             # Bayut scraper
│   │   ├── scrape_dubizzle.py          # Dubizzle scraper
│   │   └── scrape_fazwaz.py            # Fazwaz scraper
│   │
│   ├── Cleaning_Layer_Pyspark/         # 🟢 Stage 2: Data Cleaning (Silver Layer)
│   │   ├── clean_propertyfinder.py     # Clean PropertyFinder data
│   │   ├── clean_bayut.py              # Clean Bayut data
│   │   ├── clean_dubizzle.py           # Clean Dubizzle data
│   │   └── clean_fazwaz.py             # Clean Fazwaz data
│   │
│   ├── Transformation_Layer_Pyspark/   # 🟡 Stage 3: Feature Engineering (Silver Layer)
│   │   ├── transform_propertyfinder.py # Transform PropertyFinder data
│   │   ├── transform_bayut.py          # Transform Bayut data
│   │   ├── transform_dubizzle.py       # Transform Dubizzle data
│   │   └── transform_fazwaz.py         # Transform Fazwaz data
│   │
│   ├── ingest_to_bronze.py             # Ingest scraped data to HDFS Bronze layer
│   ├── load_to_dwh.py                  # Load processed data to PostgreSQL
│   ├── create_dwh_table.py             # Create One Big Table (OBT) in DWH
│   ├── create_datamarts.py             # Create specialized data marts
│   ├── populate_datamarts.py           # Populate data marts from OBT
│   │
│   ├── data_csv_files/                 # Intermediate CSV files
│   ├── __pycache__/                    # Python cache files
│   └── datalake-hdfs-commands.ipynb    # HDFS setup and management
│
├── postgres_data/                      # Persistent PostgreSQL data volume
│
├── logs/                               # Airflow logs and execution history
│
├── datasets_analysis_reports/          # EDA notebooks and analysis reports
│
├── ML_model/                           # Machine Learning components (Optional)
│   ├── knn_recommender.py              # KNN recommendation model
│   └── train_model.py                  # Model training script
│
├── RAG/                                # AI Assistant components (Optional)
│   ├── app.py                          # Flask application for AI Assistant
│   ├── ingest_embeddings.py            # Build FAISS index
│   └── faiss_index.idx                 # FAISS vector index
│
├── docker-compose.yaml                 # Multi-service orchestration
├── airflow.Dockerfile                  # Custom Airflow image
├── jupyter.Dockerfile                  # Custom PySpark/Jupyter image
├── PBI_Analysis_Dashboard.pbix         # Power BI Report file
└── README.md                           # This file
```

---

## 📈 Results & Discussion

- **Data Quality:** Layered Lakehouse engineering materially reduces data-quality issues before they reach modelling — a structured pipeline vastly outperforms raw-data approaches.
- **Predictive Accuracy:** Gradient boosting models successfully capture non-linear interactions between location, size, and finishing levels to estimate fair prices.
- **Trusted AI:** The Text-to-SQL approach ensures that the chatbot provides consistent, citable answers without domain hallucinations.

---
<div align="center">

**⭐ Digital Egypt Builders Initiative (DEPI) — July 2026 ⭐**

</div>
