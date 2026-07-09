# Databricks notebook source

silver_df = spark.table("workspace.default.silver_properties")


# COMMAND ----------

display(silver_df)

# COMMAND ----------

import pyspark.sql.functions as f

known_types = [
    "Villa", "Duplex", "Chalet", "Apartment", "Townhouse", "Twinhouse",
    "Cabin", "Penthouse", "Office", "Loft", "Studio", "Medical",
    "Family House", "Retail", "Building"
]

type_expr = f.lit("Unknown")
for t in known_types:
    type_expr = f.when(f.lower(f.col("title")).contains(t.lower()), f.lit(t)).otherwise(type_expr)

gold_df = silver_df \
    .withColumn("property_type", type_expr) \
    .withColumn(
        "price_per_sqm",
        f.round(f.try_divide(f.col("price"), f.col("area")), 2)
    )

display(gold_df)

# COMMAND ----------

gold_location_summary = gold_df.groupBy("location").agg(
    f.count("*").alias("total_properties"),
    f.round(f.avg("price"), 2).alias("avg_price"),
    f.round(f.avg("area"), 2).alias("avg_area"),
    f.round(f.avg("price_per_sqm"), 2).alias("avg_price_per_sqm"),
    f.max("price").alias("max_price"),
    f.min("price").alias("min_price")
).orderBy(f.col("total_properties").desc())

display(gold_location_summary)

# COMMAND ----------

gold_type_summary =  gold_df.groupBy("property_type")\
    .agg(
        f.count("*").alias("total_properties"),
        f.round(f.avg("price"), 2).alias("avg_price_per_type"),
        f.round(f.avg("area"), 2).alias("avg_area_per_type"),
    ).orderBy(f.col("total_properties").desc())

display(gold_type_summary)

# COMMAND ----------

gold_area_segment = silver_df.withColumn(
    "area_segment",
    f.when(f.col("area") < 100, "Small (<100 SQM)")
    .when((f.col("area") >= 100) & (f.col("area") <= 200), "Medium (100-200 SQM)")
    .when((f.col("area") > 200) & (f.col("area") <= 400), "Large (200-400 SQM)")
    .otherwise("Luxury / Mega (>400 SQM)")
)
gold_area_segment = gold_area_segment.groupBy("area_segment").agg(
    f.count("*").alias("total_properties"),
    f.round(f.avg("price"), 2).alias("avg_price")
).orderBy(f.col("avg_price").desc())

display(gold_area_segment)


# COMMAND ----------

gold_top_expensive = silver_df.select("title", "location", "price", "area") \
    .orderBy(f.col("price").desc()) \
    .limit(50)

display(gold_top_expensive)

# COMMAND ----------

gold_df.write.mode("overwrite").saveAsTable("gold_df")
gold_location_summary.write.mode("overwrite").saveAsTable("gold_location_summary")
gold_type_summary.write.mode("overwrite").saveAsTable("gold_type_summary")
gold_area_segment.write.mode("overwrite").saveAsTable("gold_area_segment")
gold_top_expensive.write.mode("overwrite").saveAsTable("gold_top_expensive")