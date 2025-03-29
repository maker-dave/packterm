import pandas as pd
from tabulate import tabulate
import tkinter as tk
from tkinter import filedialog, messagebox

def load_and_display_csv():
    # Create a Tkinter root window (it won't be shown)
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    
    try:
        # Open file dialog for CSV selection
        file_path = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not file_path:
            print("No file selected.")
            return
            
        # Read the CSV file using pandas
        df = pd.read_csv(file_path)
        
        # Convert DataFrame to a tabulated format
        table = tabulate(
            df,
            headers='keys',
            tablefmt='pretty',
            showindex=False,
            missingval='N/A'
        )
        
        # Print the table
        print("\nSelected CSV file contents:")
        print(table)
        
        # Optional: Show basic info about the CSV
        print(f"\nNumber of rows: {len(df)}")
        print(f"Number of columns: {len(df.columns)}")
        
    except FileNotFoundError:
        messagebox.showerror("Error", "File not found!")
    except pd.errors.EmptyDataError:
        messagebox.showerror("Error", "The selected file is empty!")
    except pd.errors.ParserError:
        messagebox.showerror("Error", "Error parsing the CSV file!")
    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")
    
    finally:
        root.destroy()

def main():
    print("CSV Table Display Tool")
    print("---------------------")
    
    while True:
        load_and_display_csv()
        
        # Ask if user wants to load another file
        choice = input("\nWould you like to load another CSV file? (y/n): ").lower()
        if choice != 'y':
            print("Goodbye!")
            break

if __name__ == "__main__":
    main()