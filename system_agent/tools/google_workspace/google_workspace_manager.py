import os
import pickle

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from system_agent.tools.google_workspace.calendar import CalendarManager
from system_agent.tools.google_workspace.documents import DocumentsManager
from system_agent.tools.google_workspace.drive import DriveManager
from system_agent.tools.google_workspace.gmail import GmailManager
from system_agent.tools.google_workspace.spreadsheets import SpreadSheetsManager


class GoogleWorkspaceManager:
    def __init__(
        self,
        enabled: bool,
        credentials_path: str,
        token_path: str,
        scopes: list,
    ):
        self.enabled = enabled
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.scopes = scopes

        self.gmail_manager = None
        self.calendar_manager = None
        self.drive_manager = None
        self.spread_sheets_manager = None
        self.documents_manager = None

        if self.enabled:
            self.__init_services()

    def __init_services(self):
        try:
            creds = self.__get_credentials()
            scopes = creds.scopes or []

            if (
                "https://www.googleapis.com/auth/gmail.readonly" in scopes
                or "https://www.googleapis.com/auth/gmail.send" in scopes
            ):
                self.gmail_manager = GmailManager(creds)

            if "https://www.googleapis.com/auth/calendar" in scopes:
                self.calendar_manager = CalendarManager(creds)

            if "https://www.googleapis.com/auth/drive" in scopes:
                self.drive_manager = DriveManager(creds)

            if "https://www.googleapis.com/auth/spreadsheets" in scopes:
                self.spread_sheets_manager = SpreadSheetsManager(creds)

            if "https://www.googleapis.com/auth/documents" in scopes:
                self.documents_manager = DocumentsManager(creds)

        except Exception as e:
            print(f"[GoogleWorkspaceManager] Failed to initialize: {e}")

    def __get_credentials(self):
        creds = None
        if os.path.exists("token.pickle"):
            with open("token.pickle", "rb") as token:
                creds = pickle.load(token)

        # If no valid creds, start the OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", self.scopes
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for later
            with open("token.pickle", "wb") as token:
                pickle.dump(creds, token)

        return creds

    def get_tools(self):
        """Return tools from all active managers"""
        if not self.enabled:
            return []

        tools = []

        if self.gmail_manager:
            tools.extend(self.gmail_manager.get_tools())

        if self.calendar_manager:
            tools.extend(self.calendar_manager.get_tools())

        if self.drive_manager:
            tools.extend(self.drive_manager.get_tools())

        if self.documents_manager:
            tools.extend(self.documents_manager.get_tools())

        if self.spread_sheets_manager:
            tools.extend(self.spread_sheets_manager.get_tools())

        return tools
