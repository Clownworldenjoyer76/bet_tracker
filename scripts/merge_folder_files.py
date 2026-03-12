import os
import pandas as pd

# -------- SETTINGS --------
input_folder = r"C:\path\to\folderX"      # Folder containing all files
output_file = r"C:\path\to\combined.csv"  # Output file path
file_extension = ".csv"                   # File type to combine
# --------------------------

all_data = []

# Loop through all files in folder
for file in os.listdir(input_folder):
    
    if file.endswith(file_extension):
        
        file_path = os.path.join(input_folder, file)
        
        print(f"Reading: {file}")
        
        df = pd.read_csv(file_path)
        all_data.append(df)

# Combine all files
combined_df = pd.concat(all_data, ignore_index=True)

# Save result
combined_df.to_csv(output_file, index=False)

print("Finished. Combined file saved to:", output_file)
