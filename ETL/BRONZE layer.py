# Databricks notebook source
from functools import reduce

files = [
    "/Workspace/Users/omarashraf15120066@gmail.com/aqarmapfinaaal.csv",
    "/Workspace/Users/omarashraf15120066@gmail.com/nawy_properties_full.csv",
    "/Workspace/Users/omarashraf15120066@gmail.com/property_listings.csv",
    "/Workspace/Users/omarashraf15120066@gmail.com/Dubizzle_Specific_Fields_Scrape.xlsx",
    "/Workspace/Users/omarashraf15120066@gmail.com/bayut_properties.csv",
]
dfs = [
    spark.read
         .option("header", True)
         .option("multiLine", True)
         .option("escape", '"')
         .option("inferSchema", False)
         .csv(f)
    for f in files
]
df = reduce(lambda x, y: x.unionByName(y, allowMissingColumns=True), dfs)
df = df.select(
    "title",
    "price",
    "area",
    "location",
    "bedrooms",
    "bathrooms"
)
df.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("bronze_properties")

display(df)