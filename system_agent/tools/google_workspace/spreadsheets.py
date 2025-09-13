import json
from typing import Any, Dict, List

from googleapiclient.discovery import build
from langchain.tools import Tool


class SpreadSheetsManager:
    """Handles Google Sheets operations"""

    def __init__(self, credentials):
        self.credentials = credentials
        self.service = build("sheets", "v4", credentials=credentials)
        self.drive_service = build("drive", "v3", credentials=credentials)

    def create_spreadsheet(
        self, title: str, sheet_names: List[str] = None
    ) -> Dict[str, Any]:
        """Create a new Google Spreadsheet"""
        try:
            spreadsheet = {"properties": {"title": title}}

            if sheet_names:
                sheets = []
                for i, sheet_name in enumerate(sheet_names):
                    sheets.append({"properties": {"sheetId": i, "title": sheet_name}})
                spreadsheet["sheets"] = sheets

            result = self.service.spreadsheets().create(body=spreadsheet).execute()
            spreadsheet_id = result.get("spreadsheetId")

            return {
                "success": True,
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit",
                "message": f"Spreadsheet '{title}' created successfully",
            }

        except Exception as e:
            return {"success": False, "error": f"Error creating spreadsheet: {str(e)}"}

    def read_data(
        self,
        spreadsheet_id: str = None,
        spreadsheet_name: str = None,
        range_name: str = "Sheet1",
    ) -> Dict[str, Any]:
        """Read data from spreadsheet by ID or name"""
        try:
            if spreadsheet_name and not spreadsheet_id:
                spreadsheet_id = self._find_spreadsheet_id(spreadsheet_name)
                if not spreadsheet_id:
                    return {
                        "success": False,
                        "error": f"Spreadsheet '{spreadsheet_name}' not found",
                    }

            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=range_name)
                .execute()
            )

            values = result.get("values", [])

            return {
                "success": True,
                "spreadsheet_id": spreadsheet_id,
                "range": range_name,
                "data": values,
                "rows": len(values),
                "message": f"Read {len(values)} rows from {range_name}",
            }

        except Exception as e:
            return {"success": False, "error": f"Error reading data: {str(e)}"}

    def write_data(
        self,
        spreadsheet_id: str,
        data: List[List[Any]],
        range_name: str = "Sheet1",
        append: bool = False,
    ) -> str:
        """Write data to spreadsheet (replace or append)"""
        try:
            body = {"values": data}

            if append:
                result = (
                    self.service.spreadsheets()
                    .values()
                    .append(
                        spreadsheetId=spreadsheet_id,
                        range=range_name,
                        valueInputOption="RAW",
                        body=body,
                    )
                    .execute()
                )

                updated_range = result.get("updates", {}).get("updatedRange", "")
                return f"Data appended successfully to {updated_range}"
            else:
                result = (
                    self.service.spreadsheets()
                    .values()
                    .update(
                        spreadsheetId=spreadsheet_id,
                        range=range_name,
                        valueInputOption="RAW",
                        body=body,
                    )
                    .execute()
                )

                updated_cells = result.get("updatedCells", 0)
                return f"Data updated successfully. {updated_cells} cells updated"

        except Exception as e:
            return f"Error writing data: {str(e)}"

    def add_formula(self, spreadsheet_id: str, cell_range: str, formula: str) -> str:
        """Add formula to specific cell or range"""
        try:
            body = {"values": [[formula]]}

            (
                self.service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=spreadsheet_id,
                    range=cell_range,
                    valueInputOption="USER_ENTERED",  # This processes formulas
                    body=body,
                )
                .execute()
            )

            return f"Formula added to {cell_range} successfully"

        except Exception as e:
            return f"Error adding formula: {str(e)}"

    def format_cells(
        self,
        spreadsheet_id: str,
        sheet_id: int,
        start_row: int,
        end_row: int,
        start_col: int,
        end_col: int,
        background_color: Dict = None,
        text_format: Dict = None,
    ) -> str:
        """Format cells with colors and text styling"""
        try:
            requests = []

            cell_format = {}

            if background_color:
                cell_format["backgroundColor"] = background_color

            if text_format:
                cell_format["textFormat"] = text_format

            if cell_format:
                requests.append(
                    {
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": start_row,
                                "endRowIndex": end_row,
                                "startColumnIndex": start_col,
                                "endColumnIndex": end_col,
                            },
                            "cell": {"userEnteredFormat": cell_format},
                            "fields": "userEnteredFormat("
                            + ",".join(cell_format.keys())
                            + ")",
                        }
                    }
                )

            if requests:
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id, body={"requests": requests}
                ).execute()

                return "Cell formatting applied successfully"
            else:
                return "No formatting changes specified"

        except Exception as e:
            return f"Error formatting cells: {str(e)}"

    def _find_spreadsheet_id(self, spreadsheet_name: str) -> str:
        """Find spreadsheet ID by name"""
        try:
            results = (
                self.drive_service.files()
                .list(
                    q=f"name='{spreadsheet_name}' and mimeType='application/vnd.google-apps.spreadsheet'",  # noqa
                    fields="files(id, name)",
                )
                .execute()
            )

            files = results.get("files", [])
            return files[0]["id"] if files else None

        except Exception:
            return None

    def _create_spreadsheet_wrapper(self, input_str: str) -> str:
        """
        Wrapper for create_spreadsheet function.

        Input format: 'title|||options_json'
        - title: Spreadsheet title (required)
        - options_json: JSON string with optional parameters (optional)

        Options JSON can contain:
        - sheet_names: List of sheet names (default: ["Sheet1"])

        Examples:
        - "My Spreadsheet"
        - "Sales Data|||{\"sheet_names\": [\"Q1\", \"Q2\", \"Summary\"]}"
        """
        try:
            if "|||" in input_str:
                parts = input_str.split("|||", 1)
                title = parts[0]
                options_json = parts[1] if len(parts) > 1 else "{}"
            else:
                title = input_str
                options_json = "{}"

            options = {"sheet_names": None}

            if options_json.strip():
                try:
                    user_options = json.loads(options_json)
                    options.update(user_options)
                except json.JSONDecodeError:
                    return f"Error: Invalid JSON in options: {options_json}"

            result = self.create_spreadsheet(
                title=title, sheet_names=options["sheet_names"]
            )
            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def _read_data_wrapper(self, input_str: str) -> str:
        """
        Wrapper for read_data function.

        Input format: 'spreadsheet_id_or_name|||options_json'
        - spreadsheet_id_or_name: Spreadsheet ID or name (required)
        - options_json: JSON string with optional parameters (optional)

        Options JSON can contain:
        - range_name: Sheet range to read (default: "Sheet1")

        Examples:
        - "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        - "Sales Data|||{\"range_name\": \"Q1!A1:D10\"}"
        """
        try:
            if "|||" in input_str:
                parts = input_str.split("|||", 1)
                identifier = parts[0]
                options_json = parts[1] if len(parts) > 1 else "{}"
            else:
                identifier = input_str
                options_json = "{}"

            options = {"range_name": "Sheet1"}

            if options_json.strip():
                try:
                    user_options = json.loads(options_json)
                    options.update(user_options)
                except json.JSONDecodeError:
                    return f"Error: Invalid JSON in options: {options_json}"

            # Check if it looks like a spreadsheet ID
            if (
                len(identifier) > 30
                and identifier.replace("_", "").replace("-", "").isalnum()
            ):
                result = self.read_data(
                    spreadsheet_id=identifier, range_name=options["range_name"]
                )
            else:
                result = self.read_data(
                    spreadsheet_name=identifier, range_name=options["range_name"]
                )

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def _write_data_wrapper(self, input_str: str) -> str:
        """
        Wrapper for write_data function.

        Input format: 'spreadsheet_id|||data_json|||options_json'
        - spreadsheet_id: Spreadsheet ID (required)
        - data_json: JSON array of data rows (required)
        - options_json: JSON string with optional parameters (optional)

        Options JSON can contain:
        - range_name: Sheet range to write to (default: "Sheet1")
        - append: Boolean to append data (default: false)

        Examples:
        - "sheet123|||[[\"Name\", \"Age\"], [\"John\", 25]]"
        - "sheet123|||[[\"Data1\", \"Data2\"]]|||{\"range_name\": \"Sheet2!A1\", \"append\": true}"
        """
        try:
            parts = input_str.split("|||")
            if len(parts) < 2:
                return "Error: Input format should be 'spreadsheet_id|||data_json|||options_json'"

            spreadsheet_id = parts[0]

            try:
                data = json.loads(parts[1])
            except json.JSONDecodeError:
                return f"Error: Invalid JSON in data: {parts[1]}"

            options = {"range_name": "Sheet1", "append": False}

            if len(parts) > 2 and parts[2].strip():
                try:
                    user_options = json.loads(parts[2])
                    options.update(user_options)
                except json.JSONDecodeError:
                    return f"Error: Invalid JSON in options: {parts[2]}"

            return self.write_data(
                spreadsheet_id=spreadsheet_id,
                data=data,
                range_name=options["range_name"],
                append=options["append"],
            )

        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def _add_formula_wrapper(self, input_str: str) -> str:
        """
        Wrapper for add_formula function.

        Input format: 'spreadsheet_id|||cell_range|||formula'
        - spreadsheet_id: Spreadsheet ID (required)
        - cell_range: Cell range (e.g., "A1" or "Sheet1!B2") (required)
        - formula: Formula to add (required)

        Example:
        - "sheet123|||A1|||=SUM(B1:B10)"
        """
        try:
            parts = input_str.split("|||")
            if len(parts) != 3:
                return "Error: Input format should be 'spreadsheet_id|||cell_range|||formula'"

            spreadsheet_id, cell_range, formula = parts

            return self.add_formula(
                spreadsheet_id=spreadsheet_id, cell_range=cell_range, formula=formula
            )

        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def _format_cells_wrapper(self, input_str: str) -> str:
        """
        Wrapper for format_cells function.

        Input format: 'spreadsheet_id|||sheet_id|||start_row|||end_row|||start_col|||end_col|||options_json'
        - spreadsheet_id: Spreadsheet ID (required)
        - sheet_id: Sheet ID (usually 0 for first sheet) (required)
        - start_row: Start row index (required)
        - end_row: End row index (required)
        - start_col: Start column index (required)
        - end_col: End column index (required)
        - options_json: JSON string with formatting options (optional)

        Options JSON can contain:
        - background_color: RGB color object (e.g., {"red": 1.0, "green": 0.0, "blue": 0.0})
        - text_format: Text formatting object (e.g., {"bold": true, "fontSize": 12})

        Example:
        - "sheet123|||0|||0|||5|||0|||3|||{\"background_color\": {\"red\": 0.9, \"green\": 0.9, \"blue\": 0.9}}"
        """  # noqa
        try:
            parts = input_str.split("|||")
            if len(parts) < 6:
                return "Error: Input format should be 'spreadsheet_id|||sheet_id|||start_row|||end_row|||start_col|||end_col|||options_json'"  # noqa

            spreadsheet_id = parts[0]
            sheet_id = int(parts[1])
            start_row = int(parts[2])
            end_row = int(parts[3])
            start_col = int(parts[4])
            end_col = int(parts[5])

            options = {}

            if len(parts) > 6 and parts[6].strip():
                try:
                    options = json.loads(parts[6])
                except json.JSONDecodeError:
                    return f"Error: Invalid JSON in options: {parts[6]}"

            return self.format_cells(
                spreadsheet_id=spreadsheet_id,
                sheet_id=sheet_id,
                start_row=start_row,
                end_row=end_row,
                start_col=start_col,
                end_col=end_col,
                background_color=options.get("background_color"),
                text_format=options.get("text_format"),
            )

        except Exception as e:
            return f"Error parsing input: {str(e)}"

    def get_tools(self):
        tools = [
            Tool(
                name="create_spreadsheet",
                description='Create a new Google Spreadsheet. JSON: {"title": "str", "sheet_names": ["str"]}',
                func=lambda params: self.create_spreadsheet(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
            Tool(
                name="read_spreadsheet_data",
                description='Read data from spreadsheet. JSON: {"spreadsheet_id": "str", "spreadsheet_name": "str", "range_name": "str"}',
                func=lambda params: self.read_data(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
            Tool(
                name="write_spreadsheet_data",
                description='Write data to spreadsheet. JSON: {"spreadsheet_id": "str", "data": [[any]], "range_name": "str", "append": true/false}',
                func=lambda params: self.write_data(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
            Tool(
                name="add_spreadsheet_formula",
                description='Add formula to spreadsheet. JSON: {"spreadsheet_id": "str", "range_name": "str", "formula": "str"}',
                func=lambda params: self.add_formula(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
            Tool(
                name="format_spreadsheet_cells",
                description='Format spreadsheet cells. JSON: {"spreadsheet_id": "str", "range_name": "str", "format": {"backgroundColor": {"red": float, "green": float, "blue": float}, "textFormat": {"bold": bool, "italic": bool, "fontSize": int}}}',
                func=lambda params: self.format_cells(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
        ]
        return tools

    def get_tools_wrappers(self):
        tools = [
            Tool(
                name="create_spreadsheet",
                description="Create a new Google Spreadsheet. Format: 'title|||options_json'",
                func=self._create_spreadsheet_wrapper,
            ),
            Tool(
                name="read_spreadsheet_data",
                description="Read spreadsheet data. Format: 'spreadsheet_id_or_name|||options_json'",  # noqa
                func=self._read_data_wrapper,
            ),
            Tool(
                name="write_spreadsheet_data",
                description="Write data to spreadsheet. Format: 'spreadsheet_id|||data_json|||options_json'",  # noqa
                func=self._write_data_wrapper,
            ),
            Tool(
                name="add_spreadsheet_formula",
                description="Add formula to cell. Format: 'spreadsheet_id|||cell_range|||formula'",
                func=self._add_formula_wrapper,
            ),
            Tool(
                name="format_spreadsheet_cells",
                description="Format spreadsheet cells. Format: 'spreadsheet_id|||sheet_id|||start_row|||end_row|||start_col|||end_col|||options_json'",  # noqa
                func=self._format_cells_wrapper,
            ),
        ]
        return tools
