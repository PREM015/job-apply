#!/usr/bin/env python3
import openpyxl

wb = openpyxl.load_workbook("D:\code\plans\PLACEMENT\job\job-agent\Master_Job_Tracker_final.xlsx")
ws = wb["Companies"]
# Ensure headers
if not ws.cell(row=1, column=1).value:
    headers = ["Master ID", "Company Name", "Priority Tier (Best Available)", "Application Status", "Official Careers Page", "Current Openings URL", "Company Website"]
    for c, h in enumerate(headers, 1):
        ws.cell(row=1, column=c, value=h)
# Add sample companies
samples = [
    ("MID001", "Google LLC", "Tier 1", "Closed", "https://careers.google.com", "https://careers.google.com/jobs", "https://google.com"),
    ("MID002", "Microsoft Corporation", "Tier 2", "Closed", "https://careers.microsoft.com", "https://careers.microsoft.com/jobs", "https://microsoft.com"),
]
for row_idx, row_data in enumerate(samples, 2):
    for c, val in enumerate(row_data, 1):
        ws.cell(row=row_idx, column=c, value=val)
wb.save("D:\code\plans\PLACEMENT\job\job-agent\Master_Job_Tracker_final.xlsx")
print("Companies sheet updated.")