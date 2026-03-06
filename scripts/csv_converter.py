import pandas as pd
import os

# Define paths
input_dir = 'bets/testing/csv_to_xlsx/csv'
output_dir = 'bets/testing/csv_to_xlsx/xlsx'

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

def convert_csv_to_xlsx():
    # Loop through files in input folder
    for filename in os.listdir(input_dir):
        if filename.endswith('.csv'):
            # Read CSV
            csv_path = os.path.join(input_dir, filename)
            df = pd.read_csv(csv_path)
            
            # Create output filename (change .csv to .xlsx)
            xlsx_filename = filename.replace('.csv', '.xlsx')
            xlsx_path = os.path.join(output_dir, xlsx_filename)
            
            # Save as XLSX
            df.to_excel(xlsx_path, index=False)
            print(f"Converted: {filename} -> {xlsx_filename}")

if __name__ == "__main__":
    convert_csv_to_xlsx()
