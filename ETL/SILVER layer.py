# Databricks notebook source

bronze_df = spark.table("bronze_properties")
silver_df =bronze_df.select(
    "title",
    "price",
    "area",
    "location",
    "bedrooms",
    "bathrooms"
).dropDuplicates()

display(silver_df)






# COMMAND ----------

from pyspark.sql.functions import col, regexp_replace, trim, expr

silver_df = silver_df.withColumn("price", regexp_replace(col("price"), "[^0-9.]", ""))
silver_df = silver_df.withColumn("price", expr("try_cast(trim(price) as double)"))

silver_df = silver_df.withColumn("area", regexp_replace(col("area"), "[^0-9.]", ""))
silver_df = silver_df.withColumn("area", expr("try_cast(trim(area) as double)"))

silver_df = silver_df.withColumn(
    "bedrooms", 
    expr("CASE WHEN lower(bedrooms) = 'studio' OR lower(bedrooms) = 'office' THEN '1' ELSE bedrooms END")
)
silver_df = silver_df.withColumn("bedrooms", expr("try_cast(trim(bedrooms) as int)"))
silver_df = silver_df.withColumn("bathrooms", expr("try_cast(trim(bathrooms) as int)"))

silver_df = silver_df.na.drop(subset=["price", "area", "location", "bedrooms", "bathrooms"])

silver_df = silver_df.filter(col("price") > 0)
silver_df = silver_df.filter(col("area") > 0)
silver_df = silver_df.filter(col("bedrooms") > 0)
silver_df = silver_df.filter(col("bathrooms") > 0)

display(silver_df)

# COMMAND ----------

from pyspark.sql import functions as f
from itertools import chain


location_aliases = {
    "sheikh zayed city": "El Sheikh Zayed",
    "sheikh zayed compounds": "El Sheikh Zayed",
    "sheikh zayed": "El Sheikh Zayed",
    
    "new cairo city": "New Cairo",
    "5th settlement compounds": "New Cairo",
    "the 5th settlement": "New Cairo",
    "5th settlement": "New Cairo",
    "1st settlement": "New Cairo",
    "6th settlement": "New Cairo",
    "new cairo": "New Cairo",
    "el katameya compounds": "New Cairo",
    "el katameya": "New Cairo",
    "katameya": "New Cairo",
    
    "6 october city": "6th of October City",
    "6th of october city": "6th of October City",
    "6 october compounds": "6th of October City",
    "6th of october": "6th of October City",
    "6 october": "6th of October City",
    "northern expansions": "Northern Expansion",
    "hadayek october": "October Gardens",
    
    "mostakbal city - future city": "Mostakbal City",
    "mostakbal city compounds": "Mostakbal City",
    "mostakbal city": "Mostakbal City",
    
    "new capital city": "New Capital City",
    "new capital compounds": "New Capital City",
    "new capital": "New Capital City",
    
    "ras al hekma": "Ras El Hekma",
    "ras el hekma": "Ras El Hekma",
    
    "north coast": "North Coast-Sahel",
    "north coast resorts": "North Coast-Sahel",
    "qesm ad dabaah": "North Coast-Sahel",
    "qesm marsa matrouh": "North Coast-Sahel",
    "matruh": "North Coast-Sahel",
    
    "sidi abdel rahman": "Sidi Abdel Rahman",
    
    "al alamein": "Al Alamein",
    "new alamein city": "Al Alamein",
    "alamein": "Al Alamein",
    
    "hurghada": "Hurghada",
    "red sea": "Hurghada",
    "safaga": "Hurghada",
    
    "el gouna": "El Gouna",
    "gouna": "El Gouna",
    
    "al ain al sokhna": "Ain Sokhna",
    "suez": "Ain Sokhna",
    
    "shorouk city": "El Shorouk",
    "el shorouk compounds": "El Shorouk",
    
    "madinaty": "Madinaty",
    "cairo": "Central Cairo",
    "giza": "Giza",
    "alexandria": "Alexandria",
    "hay sharq": "Alexandria",
    "bolkly": "Alexandria"
}

mapping_expr = f.create_map([f.lit(x) for x in chain(*location_aliases.items())])

garbage_regex = r"^\d+\s+(day|days|week|weeks|hour|hours|month|months)\s+ago$|.*ago.*"
df = silver_df.withColumn("is_garbage", f.lower(f.col("location")).rlike(garbage_regex))

df = df.withColumn(
    "location_candidate",
    f.when(f.col("location").contains("\n/\n"),
           f.trim(f.split(f.col("location"), r"\n/\n")[0]))
     .otherwise(f.col("location"))
)

df = df.withColumn("parts", f.split(f.col("location_candidate"), ","))
df = df.withColumn("n_parts", f.size(f.col("parts")))

df = df.withColumn(
    "city_token",
    f.when(f.col("n_parts") >= 2, f.lower(f.trim(f.col("parts")[f.col("n_parts") - 2])))
     .otherwise(f.lower(f.trim(f.col("parts")[0])))
)

df = df.withColumn(
    "clean_location",
    f.when(f.col("is_garbage"), "UNKNOWN") 
     .otherwise(
         f.coalesce(mapping_expr.getItem(f.col("city_token")), f.initcap(f.col("city_token")))
     )
)

silver_df = df.drop(
    "location", "is_garbage", "location_candidate", "parts", "n_parts", "city_token"
).withColumnRenamed("clean_location", "location")






# COMMAND ----------

from pyspark.sql.functions import when, lower, col

silver_df = silver_df.withColumn(
    "bedrooms",
    when(lower(col("bedrooms")) == "studio", "1")
    .otherwise(
        when(lower(col("bedrooms")) == "office", "1")
        .otherwise(col("bedrooms"))
    )
)

silver_df = silver_df.withColumn(
    "bedrooms",
    col("bedrooms").cast("int")
)

# COMMAND ----------

display(silver_df)

# COMMAND ----------

silver_df.printSchema()

# COMMAND ----------

# from pyspark.sql.functions import col, regexp_replace, trim, expr


# silver_df = silver_df.withColumn("area", regexp_replace(col("area"), "[^0-9.]", ""))
# silver_df = silver_df.withColumn("area", trim(col("area")))

# silver_df = silver_df.withColumn("area", expr("try_cast(area as double)"))

# display(silver_df)

# COMMAND ----------

# from pyspark.sql.functions import col, regexp_replace, trim, expr


# silver_df = silver_df.withColumn("price", regexp_replace(col("price"), "[^0-9.]", ""))
# silver_df = silver_df.withColumn("price", trim(col("price")))

# silver_df = silver_df.withColumn("price", expr("try_cast(price as double)"))

# silver_df = silver_df.na.drop(subset=["price", "area", "location"])

# display(silver_df)

# COMMAND ----------

# silver_df = silver_df.na.drop(subset=["price", "area", "location"])
# display(silver_df)

# COMMAND ----------

# silver_df = silver_df.filter(col("price") > 0)
# silver_df = silver_df.filter(col("bedrooms") > 0) 
# silver_df = silver_df.filter(col("bathrooms") > 0)
# display(silver_df)

# COMMAND ----------

silver_df = silver_df.withColumn("title", col("title").cast("string"))
silver_df = silver_df.withColumn("location", col("location").cast("string"))
silver_df = silver_df.withColumn("price", col("price").cast("bigint"))
silver_df = silver_df.withColumn("area", col("area").cast("int"))
silver_df = silver_df.withColumn("bedrooms", col("bedrooms").cast("int"))
silver_df = silver_df.withColumn("bathrooms", col("bathrooms").cast("int"))

# COMMAND ----------

silver_df.printSchema()

# COMMAND ----------

display(silver_df)

# COMMAND ----------

silver_df.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("silver_properties")