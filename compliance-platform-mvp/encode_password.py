#!/usr/bin/env python3
from urllib.parse import quote_plus

# Your actual RDS password
password = input("Enter your RDS password: ")
rds_endpoint = input("Enter your RDS endpoint: ")

# URL-encode the password
encoded_password = quote_plus(password)

# Build the DATABASE_URL
database_url = f"postgresql://complianceadmin:{encoded_password}@{rds_endpoint}:5432/postgres"

print("\n" + "="*80)
print("URL-Encoded Password:")
print(encoded_password)
print("\n" + "="*80)
print("Complete DATABASE_URL:")
print(database_url)
print("="*80)
