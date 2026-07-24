import pandas as pd
from datetime import datetime, timedelta
import os
import yaml

with open("config.yml", "r") as file:
    config = yaml.safe_load(file)

EMAIL_AGENT_SPEEDUP = config["backend"]["email_agent"]["virtual_speedup_factor"]

class SimulatedEmailService:
    def __init__(self, csv_path="data/dataset.csv", download_if_missing=True):
        self.csv_path = csv_path
        # Record exactly when the Streamlit/API app booted up
        # We simulate that "App Start Time" is 1 minute BEFORE the earliest email in the data
        self.app_start_real_time = datetime.now()
        self.download_if_missing = download_if_missing
        self.df = self._load_and_prep_data()
        self.virtual_speedup_factor = EMAIL_AGENT_SPEEDUP
        
        if not self.df.empty:
            self.dataset_start_time = self.df['timestamp'].min()
            # Start virtual time 1 minute before the first email in the dataset
            self.virtual_start_time = self.dataset_start_time - timedelta(minutes=1)
        else:
            self.dataset_start_time = datetime.now()
            self.virtual_start_time = datetime.now()

    def _load_and_prep_data(self):
        """Loads Kaggle CSV, parses dates, and filters out internal support emails."""
        # 1. Acquire the data frame based on existence
        if not os.path.exists(self.csv_path):
            if self.download_if_missing:
                # Ensure the directory directory structure exists cleanly
                os.makedirs("data", exist_ok=True)
                import kagglehub
                path = kagglehub.dataset_download("rtweera/customer-care-emails", output_dir='./data', force_download=True)
                self.csv_path = os.path.join(path, "dataset.csv")
                
                df = pd.read_csv(self.csv_path)
            else:
                # Fallback mockup if file doesn't exist yet for testing
                mock_data = {
                    'timestamp': [datetime.now() + timedelta(minutes=2), datetime.now() + timedelta(minutes=5)],
                    'sender': ['customer1@gmail.com', 'support@aetheros.com'], 
                    'subject': ['Urgent: Server down', 'Internal ticket updates'],
                    'message_body': ['My application is throwing a 500 error.', 'Disregard this internal note.']
                }
                df = pd.DataFrame(mock_data)
        else:
            df = pd.read_csv(self.csv_path)
        
        # 2. Standardize timestamp formatting for all loaded CSV files
        if 'timestamp' in df.columns:
            if df['timestamp'].dtype == object:  # If it's stored as strings
                df['timestamp'] = df['timestamp'].astype(str).str.split('.').str[0]  # Remove milliseconds
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
        
        # Rule: Exclude internal support email address
        df = df[df['sender'] != 'support@aetheros.com']
        
        # Sort chronologically to process in order
        return df.sort_values(by='timestamp').reset_index(drop=True)

    def get_current_virtual_time(self) -> datetime:
        """Calculates virtual time based on elapsed real time * speed multiplier"""
        real_now = datetime.now()
        
        # 1. How much actual time has passed since we booted the app?
        real_time_elapsed = real_now - self.app_start_real_time
        
        # 2. Fast-forward that elapsed time
        virtual_time_elapsed = real_time_elapsed * self.virtual_speedup_factor
        
        # 3. Add the sped-up elapsed time to our starting point in the dataset
        return self.virtual_start_time + virtual_time_elapsed

    def fetch_new_incoming_emails(self, processed_ids: list) -> list:
        """
        Returns all emails whose dataset timestamp is less than or equal to the 
        current virtual time, skipping any IDs that have already been processed.
        """
        if self.df.empty:
            return []
            
        virtual_now = self.get_current_virtual_time()
        
        # Filter for emails that have "arrived" by now
        arrived_emails = self.df[self.df['timestamp'] <= virtual_now]
        
        # Filter out already handled rows
        new_emails = []
        for idx, row in arrived_emails.iterrows():
            email_id = f"kaggle_{idx}"
            if email_id not in processed_ids:
                new_emails.append({
                    "email_id": email_id,
                    "sender_email": row['sender'],
                    "subject": row['subject'],
                    "email_content": row['message_body'],
                    "dataset_timestamp": row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                })
        return new_emails

    def send_simulated_reply(self, recipient: str, subject: str, body: str):
        """Simulates sending an email by logging it cleanly to the console/file."""
        print(f"\n[OUTBOUND EMAIL SENT]")
        print(f"To: {recipient}")
        print(f"Subject: Re: {subject}")
        print(f"Body:\n{body}\n{'-'*40}")