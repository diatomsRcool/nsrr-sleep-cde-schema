#!/usr/bin/env python3
"""
Comprehensive variable extraction from all WebFetch outputs into TSV files.
This script compiles all the data extracted from sleepdata.org studies.
"""

import csv

# Initialize data storage
continuous_vars = []
categorical_vars = []

# ABC Study - Continuous Variables
abc_cont = [
    ["ABC", "bmi", "Body mass index (BMI)", "Anthropometry", "Calculated measurement of body weight relative to height", "Anthropometry", "numeric", "", "", "", "", "", "", "", "", ""],
    ["ABC", "age", "Age of the participant", "Demographics", "Subject age at baseline assessment", "Demographics", "numeric", "", "years", "", "", "", "", "", "", ""],
    ["ABC", "nsrr_bmi", "Body mass index (BMI)", "Harmonized/Anthropometry", "Harmonized by NSRR team to align with TOPMed standards", "Anthropometry", "numeric", "", "kg/m2", "", "", "", "", "", "", ""],
    ["ABC", "nsrr_age", "Subject age", "Harmonized/Demographics", "Harmonized by NSRR team to align with TOPMed standards", "Demographics", "numeric", "", "years", "", "", "", "", "", "", ""],
    ["ABC", "height", "Height", "Anthropometry", "Subject height measurement", "Anthropometry", "numeric", "", "cm", "", "", "", "", "", "", ""],
    ["ABC", "weight", "Weight", "Anthropometry", "Subject weight measurement", "Anthropometry", "numeric", "", "kg", "", "", "", "", "", "", ""],
    ["ABC", "active_ghrelin", "Active Ghrelin", "Clinical Data/Laboratory", "Hormone measurement from blood test", "Laboratory", "numeric", "", "", "", "", "", "", "", "", ""],
    ["ABC", "adiponectin_hmw", "Adiponectin - HMW", "Clinical Data/Laboratory", "High molecular weight adiponectin level", "Laboratory", "numeric", "", "", "", "", "", "", "", "", ""],
    ["ABC", "bloods_creactivepro", "C-Reactive Protein", "Clinical Data/Laboratory", "Cardiac inflammatory marker measurement", "Laboratory", "numeric", "", "", "", "", "", "", "", "", ""],
    ["ABC", "bloods_hdlchol", "HDL Cholesterol", "Clinical Data/Laboratory", "High-density lipoprotein cholesterol level", "Laboratory", "numeric", "", "mg/dL", "", "", "", "", "", "", ""],
    ["ABC", "bloods_ldlcholcalc", "LDL Cholesterol", "Clinical Data/Laboratory", "Calculated low-density lipoprotein level", "Laboratory", "numeric", "", "mg/dL", "", "", "", "", "", "", ""],
    ["ABC", "bloods_serumgluc", "Glucose, Serum", "Clinical Data/Laboratory", "Blood glucose concentration", "Laboratory", "numeric", "", "mg/dL", "", "", "", "", "", "", ""],
    ["ABC", "bloods_totalchol", "Cholesterol, Total", "Clinical Data/Laboratory", "Total serum cholesterol level", "Laboratory", "numeric", "", "mg/dL", "", "", "", "", "", "", ""],
    ["ABC", "bloods_triglyc", "Triglycerides", "Clinical Data/Laboratory", "Blood triglyceride concentration", "Laboratory", "numeric", "", "mg/dL", "", "", "", "", "", "", ""],
    ["ABC", "insulin", "Insulin", "Clinical Data/Laboratory", "Blood insulin level", "Laboratory", "numeric", "", "", "", "", "", "", "", "", ""],
    ["ABC", "ess_total", "Epworth Sleepiness Scale Total", "Sleep Questionnaires", "Total score 0-24 based on 8-item questionnaire", "Sleep", "numeric", "", "", "", "", "", "", "", "", ""],
    ["ABC", "ahi_ap0uhp3x3u_f1t1", "Apnea-Hypopnea Index", "Sleep Monitoring/Polysomnography", "All apneas + hypopneas with >= 3% oxygen desaturation per hour", "Sleep", "numeric", "", "events/hour", "", "", "", "", "", "", ""],
    ["ABC", "ahi_ap0uhp3x4u_f1t1", "Apnea-Hypopnea Index", "Sleep Monitoring/Polysomnography", "Apneas/hypopneas with >= 4% desaturation per hour", "Sleep", "numeric", "", "events/hour", "", "", "", "", "", "", ""],
    ["ABC", "ttldursp_f1t1", "Total sleep duration", "Sleep Monitoring/Polysomnography", "Sleep interval from onset to offset", "Sleep", "numeric", "", "minutes", "", "", "", "", "", "", ""],
    ["ABC", "avglvlsa_f1t1", "Average oxygen saturation", "Sleep Monitoring/Polysomnography", "Mean oxygen saturation during sleep", "Sleep", "numeric", "", "%", "", "", "", "", "", "", ""],
    ["ABC", "minlvlsa_f1t1", "Minimum oxygen saturation", "Sleep Monitoring/Polysomnography", "Lowest oxygen saturation during sleep", "Sleep", "numeric", "", "%", "", "", "", "", "", "", ""],
]

# ABC Study - Categorical Variables
abc_cat = [
    ["ABC", "nsrrid", "NSRR subject identifier", "Administrative", "Unique identifier linking subject data and files within NSRR", "Administrative", "string"],
    ["ABC", "rand_siteid", "Site identifier", "Administrative", "Recruitment site used as stratification factor for randomization", "Administrative", "enumeration"],
    ["ABC", "rand_treatmentarm", "Randomized treatment arm", "Administrative", "Assignment to CPAP or laparoscopic gastric banding treatment group", "Administrative", "enumeration"],
    ["ABC", "visitnumber", "Visit number", "Administrative", "Sequential visit designation for study assessment", "Administrative", "enumeration"],
    ["ABC", "ethnicity", "Ethnicity (Hispanic or Latino)", "Demographics", "Person of Cuban, Mexican, Puerto Rican, or other Spanish culture/origin", "Demographics", "categorical"],
    ["ABC", "gender", "Gender", "Demographics", "Participant gender classification", "Demographics", "categorical"],
    ["ABC", "race", "Race", "Demographics", "Participant racial classification", "Demographics", "categorical"],
    ["ABC", "nsrr_age_gt89", "Age greater than 89 years", "Harmonized/Demographics", "Binary indicator for age obfuscation", "Demographics", "choices"],
    ["ABC", "nsrr_ethnicity", "Subject ethnicity", "Harmonized/Demographics", "Harmonized ethnicity; missing values recoded as 'not reported'", "Demographics", "categorical"],
    ["ABC", "nsrr_race", "Subject race", "Harmonized/Demographics", "Harmonized racial classification per TOPMed standards", "Demographics", "categorical"],
    ["ABC", "nsrr_sex", "Subject sex", "Harmonized/Demographics", "Harmonized sex classification per TOPMed standards", "Demographics", "categorical"],
    ["ABC", "surgery_occurred", "Surgery occurred", "Administrative", "Binary indicator: subject underwent laparoscopic gastric banding surgery", "Administrative", "choices"],
]

# ANSWERS Study Variables
answers_cont = [
    ["ANSWERS", "nsrr_age", "Subject age", "Harmonized/Demographics", "Subject age harmonized to align with TOPMed standards", "Demographics", "numeric", "", "years", "", "", "", "", "", "", ""],
    ["ANSWERS", "cesd_total", "CESD Sum of 20 items", "General Health/CESD", "Sum of 20 items from depression scale", "Mental Health", "numeric", "", "", "", "", "", "", "", "", ""],
    ["ANSWERS", "gad_total", "GAD-7 Total Score", "General Health/GAD-7", "Summary score for generalized anxiety", "Mental Health", "numeric", "", "", "", "", "", "", "", "", ""],
    ["ANSWERS", "inq_perceivedburden", "INQ Perceived Burden Summary", "General Health/INQ", "Calculated from inq_1 to inq_6", "Mental Health", "numeric", "", "", "", "", "", "", "", "", ""],
    ["ANSWERS", "inq_thwartedbelong", "INQ Thwarted Belonging Summary", "General Health/INQ", "Calculated from inq_7 to inq_15", "Mental Health", "numeric", "", "", "", "", "", "", "", "", ""],
]

answers_cat = [
    ["ANSWERS", "id", "Record ID", "Administrative", "Record ID for participant identification", "Administrative", "categorical"],
    ["ANSWERS", "visit", "Cross-Sectional Survey", "Administrative", "Survey visit designation", "Administrative", "categorical"],
    ["ANSWERS", "nsrr_sex", "Subject sex", "Harmonized/Demographics", "Subject biological sex classification", "Demographics", "categorical"],
    ["ANSWERS", "ethnicity", "Subject ethnicity", "Demographics", "What is your ethnicity?", "Demographics", "categorical"],
    ["ANSWERS", "race", "Subject race", "Demographics", "What is your race (select all that apply)?", "Demographics", "categorical"],
    ["ANSWERS", "sex", "Subject sex", "Demographics", "What is your sex?", "Demographics", "categorical"],
]

# Compile all data
continuous_vars.extend(abc_cont)
continuous_vars.extend(answers_cont)
categorical_vars.extend(abc_cat)
categorical_vars.extend(answers_cat)

# Write TSV files with proper headers
continuous_header = ['study_name', 'variable_name', 'variable_label', 'folder', 'description', 'domain', 'type', 'total_subjects', 'units', 'n', 'mean', 'stddev', 'median', 'min', 'max', 'unknown']
categorical_header = ['study_name', 'variable_name', 'variable_label', 'folder', 'description', 'domain', 'type']

with open('/Users/athessen/sleep-cde-schema/continuous_variables.tsv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f, delimiter='\t')
    writer.writerow(continuous_header)
    writer.writerows(continuous_vars)

with open('/Users/athessen/sleep-cde-schema/categorical_variables.tsv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f, delimiter='\t')
    writer.writerow(categorical_header)
    writer.writerows(categorical_vars)

print(f"TSV files created successfully!")
print(f"Continuous variables: {len(continuous_vars)}")
print(f"Categorical variables: {len(categorical_vars)}")
print(f"\\nContinuous variables file: /Users/athessen/sleep-cde-schema/continuous_variables.tsv")
print(f"Categorical variables file: /Users/athessen/sleep-cde-schema/categorical_variables.tsv")
