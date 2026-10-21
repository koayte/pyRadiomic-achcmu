from BrainMetastased_radiomics_extraction import my_main_funct
results = my_main_funct("./mri_folder")
# results is a list of DataFrames, one per patient
for df in results:
    df.to_csv(f"outputs/features_{df['patient_id'].iloc[0]}.csv", index=False)