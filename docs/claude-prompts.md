I have a website that details the classes and slots we need in this
model. It has descriptions. The website is at
https://sleepdata.org/datasets. The page lists 50 data sets. Each data
sets has documentation and a data dictionary listing variables. Each
variable has information about label, domain, type, and enumerative
values. Use it to make classes and slots. I prefer linkml slots
annotations to attributes, so make slots not attributes. Do not add
class_uri or slot_uri annotations. Pay attention to variables that are
calculated from other variables and include that in the schema using
linkml expressions.

Go to sleepdata.org/datasets and make a list of the studies available
there that have variables listed. Examples include DISECAD, LOFTHF, and
PIMECFS.

For the studies in studies_with_variables.txt, go to
sleepdata.org/datasets and make a list of variables in two tab-delimited
files. One file should contain continuous variables. Examples of
continuous variables include BMI, hip_total_steps, bloods_hdlchol, and
age. The other file should contain categorical variables. Examples of
categorical variables include race, sex, and cesd_3mo_2. In the file for
the continuous variables, the column headers should be study_name
variable_name variable_label folder description visit domain type
total_subjects units n mean stddev median min max unknown. None of these
should be multivalued. In the file for the categorical variables, the
column headers should be study_name variable_name variable_label folder
description visit domain type. In the continuous variable file, the
domain column will be multivalued. Make multivalued domain
pipe-delimited. Example of a categorical variable with a multivalued
domain is ethnicity with a domain 1:hispanic or latino|2:not hispanic or
latino. Some continuous and categorical variables will have multiple
measurements over time. This value should go in the visit column.
Examples of visits include baseline, 9-month followup, and 18-month
followup. In both files, each row should be a unique combination of
variable_name and visit within a study. Save these two files.

I've manually curated your lists of continuous and categorical
variables. These files are in continuous_variables_updated_curated.txt
and categorical_variables_updated_curated.txt. I have removed the domain
column from the continuous variables and replaced in with calculation.
Go through each of these files and update each row by looking up the
variable-specific page at sleepdata.org/datasets. Don't forget what you
learned earlier about the URLs needing the study names to be in lower
case. For the continuous variables, look up each variable and update the
description and calculation column. If these fields are not present,
then leave blank. Remember that variables are repeated in there is more
than one visit, so you can copy and paste information rather than
looking it up more than once. Toward the end of the file are variables
that don't have any visit, unit, or summary statistics. Fill in that
information where it is missing. For the categorical variables, look up
each variable and update the domain and description columns. Return two
updated, tab-delimited files.

The file continuous_variables_cde contains results from your work plus
some manual curation. The last time you extracted these variables you
still missed some descriptions and visits. Try again and use nsrr_bmi
and nsrr_age as examples. Not all studies will have both. Do not use
nsrr_age in FDCSR as an example. For MESA, use ahi_a0h3 as an example.
Do not overwrite any data, but update any missing information. Add rows
if needed. Output results in a tsv file.

You still missed some visits. Retrieve summary statistics for the
variables in these specific studies and visit pairs. ANSWERS -
Cross-Sectional Survey; APPLES - Baseline (BL); APPLES - Clinical
Evaluation (CE); APPLES - Diagnostic Visit (DX); APPLES - CPAP Titration
Visit (CPAP); APPLES - Two Month Post-CPAP Neurocognitive Visit (2M);
APPLES - Four Month Post-CPAP Neurocognitive Visit (4M); APPLES Six
Month Post-CPAP Neurocognitive Visit (6M); HCHS - Sueno Ancillary;
LOFTHF - Follow-up On Treatment; NCHSDB - Second overnight sleep study;
NCHSDB - Third overnight sleep study; NCHSDB - Fourth overnight sleep
study; NCHSDB - Fifth overnight sleep study; SANDD - 12 mo[1yr] follow
up; SANDD - 18mo[1.5yr]; SANDD - 24mo[2yr]; SANDD - 30mo[2.5y]; SHHS -
CVD Outcomes; SHINE - Intake; WSC - Mailed Survey. Also, grab the
summary statistics for the variables listed in the MESA, MSP, and STAGES
studies.

For every variable in the ANSWERS, APPLES, HCHS, LOFTHF, NCHSDB, SANDD,
SHHS, SHINE, and WSC studies go to the variable-specific page and add
rows to include the missing visits for that study. Populate the new rows
with the study_name, variable_name, variable_label, folder, description,
visit, calculation, type, total_subjects, units, n, mean, stddev,
median, min, max, unknown. The list of missing visits is given in the
following list of study - visit pairs. ANSWERS - Cross-Sectional Survey;
APPLES - Baseline (BL); APPLES - Clinical Evaluation (CE); APPLES -
Diagnostic Visit (DX); APPLES - CPAP Titration Visit (CPAP); APPLES -
Two Month Post-CPAP Neurocognitive Visit (2M); APPLES - Four Month
Post-CPAP Neurocognitive Visit (4M); APPLES Six Month Post-CPAP
Neurocognitive Visit (6M); HCHS - Sueno Ancillary; LOFTHF - Follow-up On
Treatment; NCHSDB - Second overnight sleep study; NCHSDB - Third
overnight sleep study; NCHSDB - Fourth overnight sleep study; NCHSDB -
Fifth overnight sleep study; SANDD - 12 mo[1yr] follow up; SANDD -
18mo[1.5yr]; SANDD - 24mo[2yr]; SANDD - 30mo[2.5y]; SHHS - CVD Outcomes;
SHINE - Intake; WSC - Mailed Survey.

Look at the categorical_variables_cde file. For all of the variables in
the ABC, ANSWERS study, add descriptions. 

