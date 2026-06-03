import os
import zipfile
from pathlib import Path

class KaggleClient:
    """
    A client to interact with the Kaggle API.
    Handles authenticating and downloading external datasets (like EA FC ratings).
    """
    
    def __init__(self):
        # Anchor to the raw data directory
        self.raw_data_dir = Path(__file__).resolve().parents[2] / "data" / "raw"
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        
        # We import kaggle here so it only authenticates when the class is instantiated
        import kaggle
        self.api = kaggle.api
        self.api.authenticate()

    def download_dataset(self, dataset_path, filename):
        """
        Downloads a specific file from a Kaggle dataset and unzips it if necessary.
        dataset_path: e.g., 'flynn28/eafc26-player-database'
        """
        print(f"Downloading {filename} from Kaggle...")
        
        self.api.dataset_download_file(
            dataset=dataset_path,
            file_name=filename,
            path=self.raw_data_dir
        )
        
        # Kaggle downloads files as .zip, so we need to extract it
        zip_path = self.raw_data_dir / f"{filename}.zip"
        if zip_path.exists():
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.raw_data_dir)
            
            # Clean up the zip file to save space
            os.remove(zip_path)
            print(f"Successfully extracted {filename} to {self.raw_data_dir}")
        else:
            print(f"Downloaded {filename} successfully.")

if __name__ == "__main__":
    client = KaggleClient()
    # Pulling the exact dataset you linked
    client.download_dataset("flynn28/eafc26-player-database", "EAFC26-Men.csv")
