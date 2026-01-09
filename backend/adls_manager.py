
import os
import logging
from azure.storage.filedatalake import DataLakeServiceClient
from config import Config
import glob

logger = logging.getLogger(__name__)

class ADLSManager:
    """
    Manages interactions with Azure Data Lake Storage Gen2.
    Handles connection, file listing, and downloading.
    """

    def __init__(self):
        self.account_name = Config.AZURE_STORAGE_ACCOUNT_NAME
        self.account_key = Config.AZURE_STORAGE_ACCOUNT_KEY
        self.container_name = Config.AZURE_STORAGE_CONTAINER_NAME
        self.directory = Config.AZURE_STORAGE_DIRECTORY
        
        self.service_client = None
        self.file_system_client = None
        
        if self._validate_config():
            self._connect()

    def _validate_config(self):
        """Check if necessary config is present"""
        if not all([self.account_name, self.account_key, self.container_name]):
            logger.warning("ADLS credentials missing. ADLS Manager disabled.")
            return False
        return True

    def _connect(self):
        """Establish connection to ADLS"""
        try:
            service_url = f"https://{self.account_name}.dfs.core.windows.net"
            self.service_client = DataLakeServiceClient(
                account_url=service_url, 
                credential=self.account_key
            )
            self.file_system_client = self.service_client.get_file_system_client(file_system=self.container_name)
            logger.info(f"Successfully connected to ADLS container '{self.container_name}'")
        except Exception as e:
            logger.error(f"Failed to connect to ADLS: {str(e)}")
            self.service_client = None

    def list_csv_files(self):
        """List all CSV files in the configured directory, sorted by modification time (descending)"""
        if not self.file_system_client:
            return []

        try:
            paths = self.file_system_client.get_paths(path=self.directory)
            csv_files = []
            
            for path in paths:
                if not path.is_directory and path.name.lower().endswith('.csv'):
                    csv_files.append({
                        'name': path.name,
                        'last_modified': path.last_modified,
                        'size': path.content_length
                    })
            
            # Sort by last modified date, newest first
            csv_files.sort(key=lambda x: x['last_modified'], reverse=True)
            return csv_files
        except Exception as e:
            logger.error(f"Error listing files from ADLS: {str(e)}")
            return []

    def download_file(self, adls_file_name, local_dir="downloads"):
        """
        Download a file from ADLS to local directory.
        Returns the local path of the downloaded file.
        """
        if not self.file_system_client:
            raise RuntimeError("ADLS Client not initialized")

        try:
            file_client = self.file_system_client.get_file_client(adls_file_name)
            
            # Ensure local directory exists
            if not os.path.exists(local_dir):
                os.makedirs(local_dir)
                
            # Use only the filename, not the full path if directory was included
            local_filename = os.path.basename(adls_file_name)
            local_path = os.path.join(local_dir, local_filename)
            
            logger.info(f"Downloading {adls_file_name} to {local_path}...")
            
            download = file_client.download_file()
            with open(local_path, "wb") as f:
                download.readinto(f)
                
            logger.info("Download complete.")
            return local_path
        except Exception as e:
            logger.error(f"Error downloading file {adls_file_name}: {str(e)}")
            raise

    def sync_latest_file(self, local_dir="downloads") -> tuple[str, bool]:
        """
        Ensures the latest file from ADLS is present locally.
        
        Returns:
            tuple: (local_file_path, is_new_download)
            
        Logic:
        1. List files in ADLS
        2. Identify latest CSV
        3. Check if this file already exists locally
        4. If not, delete other CSVs in downloads/ and download the new one
        """
        if not self.service_client:
            logger.warning("ADLS not configured, skipping sync.")
            # Fallback to finding local file
            local_csvs = glob.glob(os.path.join(local_dir, "*.csv"))
            if local_csvs:
                return local_csvs[0], False
            return None, False

        csv_files = self.list_csv_files()
        if not csv_files:
            logger.warning("No CSV files found in ADLS.")
            return None, False

        latest_file = csv_files[0]
        latest_filename = os.path.basename(latest_file['name'])
        expected_local_path = os.path.join(local_dir, latest_filename)
        
        if os.path.exists(expected_local_path):
            logger.info(f"Latest file {latest_filename} already exists locally.")
            return expected_local_path, False
        
        # New file detected
        logger.info(f"New file specific detected: {latest_file['name']}")
        
        # Clean up old CSV files
        logger.info("Cleaning up old CSV files...")
        existing_csvs = glob.glob(os.path.join(local_dir, "*.csv"))
        for f in existing_csvs:
            try:
                os.remove(f)
                logger.info(f"Removed old file: {f}")
            except Exception as e:
                logger.warning(f"Could not remove {f}: {e}")

        # Download new file
        downloaded_path = self.download_file(latest_file['name'], local_dir)
        return downloaded_path, True
