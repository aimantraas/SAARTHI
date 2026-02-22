"""
Google Sheets integration for the LeadGen system.
"""
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

from .models import LeadRecord, EmailVerificationResult
from .config import LeadGenConfig, sheet_columns


class GoogleSheetsClient:
    """
    Client for Google Sheets operations.
    Uses google-auth-oauthlib and google-api-python-client.
    """
    
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    def __init__(self, config: LeadGenConfig):
        self.config = config
        self.sheet_id = config.google_sheet_id
        self.credentials_path = config.google_credentials_path
        self._service = None
        self._credentials = None
    
    def _get_credentials(self):
        """Get Google OAuth2 credentials."""
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        
        creds = None
        token_path = Path(self.credentials_path).parent / 'token.json'
        
        # Load existing token if available
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), self.SCOPES)
        
        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        
        return creds
    
    @property
    def service(self):
        """Get Google Sheets service instance (lazy initialization)."""
        if self._service is None:
            from googleapiclient.discovery import build
            creds = self._get_credentials()
            self._service = build('sheets', 'v4', credentials=creds)
        return self._service
    
    def get_sheet_data(
        self,
        sheet_name: str,
        range_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all data from a sheet.
        Returns list of dictionaries with column headers as keys.
        """
        if range_name:
            range_spec = f"{sheet_name}!{range_name}"
        else:
            range_spec = sheet_name
        
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.sheet_id,
            range=range_spec
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            return []
        
        # First row is headers
        headers = values[0]
        
        # Convert to list of dicts
        data = []
        for row in values[1:]:
            row_dict = {}
            for i, header in enumerate(headers):
                row_dict[header] = row[i] if i < len(row) else ''
            data.append(row_dict)
        
        return data
    
    def get_rows_by_filter(
        self,
        sheet_name: str,
        filters: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Get rows that match filter criteria.
        """
        all_data = self.get_sheet_data(sheet_name)
        
        filtered = []
        for row in all_data:
            match = True
            for key, value in filters.items():
                if row.get(key) != value:
                    match = False
                    break
            if match:
                filtered.append(row)
        
        return filtered
    
    def append_row(
        self,
        sheet_name: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Append a new row to the sheet.
        """
        # Get existing headers
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.sheet_id,
            range=f"{sheet_name}!1:1"
        ).execute()
        
        headers = result.get('values', [[]])[0]
        
        # Build row values in order of headers
        row_values = []
        for header in headers:
            value = data.get(header, '')
            if isinstance(value, list):
                value = json.dumps(value)
            row_values.append(str(value) if value is not None else '')
        
        body = {
            'values': [row_values]
        }
        
        result = self.service.spreadsheets().values().append(
            spreadsheetId=self.sheet_id,
            range=sheet_name,
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        return result
    
    def append_or_update_row(
        self,
        sheet_name: str,
        data: Dict[str, Any],
        matching_column: str = "LinkedinUrl"
    ) -> Dict[str, Any]:
        """
        Append a new row or update existing if matching column value exists.
        Equivalent to N8N Google Sheets appendOrUpdate node.
        """
        # Get all data to check for existing row
        all_data = self.get_sheet_data(sheet_name)
        
        match_value = data.get(matching_column)
        
        if not match_value:
            # No match value, just append
            return self.append_row(sheet_name, data)
        
        # Find existing row index
        headers = list(all_data[0].keys()) if all_data else []
        
        if not headers:
            # No data yet, append
            return self.append_row(sheet_name, data)
        
        # Find matching column index
        if matching_column not in headers:
            return self.append_row(sheet_name, data)
        
        # Search for existing row
        row_index = None
        for i, row in enumerate(all_data):
            if row.get(matching_column) == match_value:
                row_index = i + 2  # +2 because sheets are 1-indexed and we skip header
                break
        
        if row_index is None:
            # No existing row, append
            return self.append_row(sheet_name, data)
        
        # Update existing row
        return self.update_row(sheet_name, row_index, data, headers)
    
    def update_row(
        self,
        sheet_name: str,
        row_index: int,
        data: Dict[str, Any],
        headers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Update an existing row.
        """
        if headers is None:
            # Get headers
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=f"{sheet_name}!1:1"
            ).execute()
            headers = result.get('values', [[]])[0]
        
        # Build row values
        row_values = []
        for header in headers:
            value = data.get(header, '')
            if isinstance(value, list):
                value = json.dumps(value)
            row_values.append(str(value) if value is not None else '')
        
        body = {
            'values': [row_values]
        }
        
        result = self.service.spreadsheets().values().update(
            spreadsheetId=self.sheet_id,
            range=f"{sheet_name}!{row_index}:{row_index}",
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        
        return result
    
    def batch_update(
        self,
        sheet_name: str,
        updates: List[Dict[str, Any]],
        matching_column: str = "LinkedinUrl"
    ) -> List[Dict[str, Any]]:
        """
        Batch append or update multiple rows.
        """
        results = []
        for data in updates:
            result = self.append_or_update_row(sheet_name, data, matching_column)
            results.append(result)
        return results
    
    def save_lead_record(self, sheet_name: str, record: LeadRecord) -> Dict[str, Any]:
        """Save a LeadRecord to the sheet."""
        return self.append_or_update_row(
            sheet_name,
            record.to_dict(),
            matching_column="LinkedinUrl"
        )
    
    def save_verification_result(
        self,
        sheet_name: str,
        result: EmailVerificationResult
    ) -> Dict[str, Any]:
        """Save email verification result to sheet."""
        data = {
            "LinkedinUrl": result.linkedin_url,
            "Email": result.email,
            " email verification": result.status,
            "status": result.status,
            "verified_at": result.verified_at
        }
        return self.append_or_update_row(
            sheet_name,
            data,
            matching_column="LinkedinUrl"
        )
    
    def get_unverified_emails(
        self,
        sheet_name: str,
        status_filter: str = "PROCESS"
    ) -> List[Dict[str, Any]]:
        """
        Get rows with emails that need verification.
        Equivalent to N8N LoadSheets with filter.
        """
        return self.get_rows_by_filter(sheet_name, {
            " email verification": status_filter
        })
    
    def get_verified_emails(
        self,
        sheet_name: str
    ) -> List[str]:
        """Get list of already verified emails."""
        all_data = self.get_sheet_data(sheet_name)
        
        verified = []
        for row in all_data:
            status = row.get(" email verification", "")
            if status and status != "PROCESS":
                email = row.get("Email", "")
                if email:
                    verified.append(email.lower().strip())
        
        return verified


class MockGoogleSheetsClient:
    """
    Mock client for testing without Google Sheets connection.
    Stores data in memory.
    """
    
    def __init__(self, config: LeadGenConfig = None):
        self.config = config
        self._data: Dict[str, List[Dict[str, Any]]] = {}
        self.records = []
    
    def get_sheet_data(self, sheet_name: str) -> List[Dict[str, Any]]:
        return self._data.get(sheet_name, [])
    
    def append_row(self, sheet_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if sheet_name not in self._data:
            self._data[sheet_name] = []
        self._data[sheet_name].append(data)
        return {"status": "appended", "data": data}
    
    def append_or_update_row(
        self,
        sheet_name: str,
        data: Dict[str, Any],
        matching_column: str = "LinkedinUrl"
    ) -> Dict[str, Any]:
        if sheet_name not in self._data:
            self._data[sheet_name] = []
        
        match_value = data.get(matching_column)
        
        for i, row in enumerate(self._data[sheet_name]):
            if row.get(matching_column) == match_value:
                self._data[sheet_name][i].update(data)
                return {"status": "updated", "data": data}
        
        self._data[sheet_name].append(data)
        return {"status": "appended", "data": data}
    
    def get_rows_by_filter(
        self,
        sheet_name: str,
        filters: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        all_data = self._data.get(sheet_name, [])
        
        filtered = []
        for row in all_data:
            match = True
            for key, value in filters.items():
                if row.get(key) != value:
                    match = False
                    break
            if match:
                filtered.append(row)
        
        return filtered

    def get_unverified_emails(
        self,
        sheet_name: str,
        status_filter: str = "PROCESS"
    ) -> List[Dict[str, Any]]:
        """Mirror GoogleSheetsClient API for email verification workflow."""
        return self.get_rows_by_filter(sheet_name, {
            " email verification": status_filter
        })

    def get_verified_emails(self, sheet_name: str) -> List[str]:
        """Return normalized emails with non-PROCESS verification status."""
        all_data = self._data.get(sheet_name, [])
        verified = []
        for row in all_data:
            status = row.get(" email verification", "")
            if status and status != "PROCESS":
                email = row.get("Email", "")
                if email:
                    verified.append(str(email).lower().strip())
        return verified
    
    def save_lead_record(self, *args, **kwargs) -> Dict[str, Any]:
        """Save a LeadRecord to the sheet or a dict to self.records."""
        # Check if first true argument is a dictionary 
        # based on the method signature in the prompt
        if len(args) == 1 and isinstance(args[0], dict):
            self.records.append(args[0])
            return {"status": "success", "message": "Lead record saved successfully."}
        elif 'lead_data' in kwargs:
            self.records.append(kwargs['lead_data'])
            return {"status": "success", "message": "Lead record saved successfully."}
            
        sheet_name = args[0] if len(args) > 0 else kwargs.get('sheet_name', 'Sheet1')
        record = args[1] if len(args) > 1 else kwargs.get('record')
        
        return self.append_or_update_row(
            sheet_name,
            record.to_dict(),
            matching_column="LinkedinUrl"
        )
    
    def save_verification_result(
        self,
        sheet_name: str,
        result: EmailVerificationResult
    ) -> Dict[str, Any]:
        """Save email verification result to sheet."""
        data = {
            "LinkedinUrl": result.linkedin_url,
            "Email": result.email,
            " email verification": result.status,
            "status": result.status,
            "verified_at": result.verified_at
        }
        return self.append_or_update_row(
            sheet_name,
            data,
            matching_column="LinkedinUrl"
        )
