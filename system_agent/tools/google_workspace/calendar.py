from typing import Any, Dict, List

from googleapiclient.discovery import build
from langchain.tools import Tool


class CalendarManager:
    """Handles Google Calendar operations"""

    def __init__(self, credentials):
        self.credentials = credentials
        self.service = build("calendar", "v3", credentials=credentials)

    def create_event(
        self,
        attendee_emails: List[str],
        summary: str,
        start_time: str,
        end_time: str,
        description: str = "",
        location: str = "",
        create_meet: bool = True,
    ) -> str:
        """Create a calendar event with multiple attendees"""
        try:
            attendees = [{"email": email} for email in attendee_emails]

            event = {
                "summary": summary,
                "description": description,
                "location": location,
                "attendees": attendees,
                "start": {"dateTime": start_time, "timeZone": "Asia/Kolkata"},
                "end": {"dateTime": end_time, "timeZone": "Asia/Kolkata"},
            }

            if create_meet:
                event["conferenceData"] = {
                    "createRequest": {"requestId": f"meet-{hash(summary)}"}
                }

            created_event = (
                self.service.events()
                .insert(
                    calendarId="primary",
                    body=event,
                    conferenceDataVersion=1 if create_meet else 0,
                )
                .execute()
            )

            result = f"Event '{summary}' created successfully"
            result += f"\nEvent Link: {created_event.get('htmlLink')}"

            if create_meet and created_event.get("hangoutLink"):
                result += f"\nMeet Link: {created_event.get('hangoutLink')}"

            return result

        except Exception as e:
            return f"Error creating event: {str(e)}"

    def read_events(
        self, start_date: str, end_date: str = None, max_results: int = 10
    ) -> Dict[str, Any]:
        """Read calendar events within date range"""
        try:
            time_min = start_date
            time_max = end_date

            events_result = (
                self.service.events()
                .list(
                    calendarId="primary",
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])

            formatted_events = []
            for event in events:
                event_data = {
                    "id": event.get("id"),
                    "summary": event.get("summary", "No Title"),
                    "description": event.get("description", ""),
                    "location": event.get("location", ""),
                    "start": event.get("start", {}).get("dateTime", ""),
                    "end": event.get("end", {}).get("dateTime", ""),
                    "attendees": [
                        att.get("email") for att in event.get("attendees", [])
                    ],
                    "meet_link": event.get("hangoutLink", ""),
                    "event_link": event.get("htmlLink", ""),
                }
                formatted_events.append(event_data)

            return {
                "success": True,
                "events": formatted_events,
                "total_found": len(formatted_events),
                "message": f"Found {len(formatted_events)} events",
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error reading events: {str(e)}",
                "events": [],
            }

    def update_event(
        self,
        event_id: str,
        summary: str = None,
        start_time: str = None,
        end_time: str = None,
        description: str = None,
        location: str = None,
        attendee_emails: List[str] = None,
    ) -> str:
        """Update existing calendar event"""
        try:
            # Get existing event
            event = (
                self.service.events()
                .get(calendarId="primary", eventId=event_id)
                .execute()
            )

            # Update fields that are provided
            if summary is not None:
                event["summary"] = summary
            if description is not None:
                event["description"] = description
            if location is not None:
                event["location"] = location
            if start_time is not None:
                event["start"] = {"dateTime": start_time, "timeZone": "Asia/Kolkata"}
            if end_time is not None:
                event["end"] = {"dateTime": end_time, "timeZone": "Asia/Kolkata"}
            if attendee_emails is not None:
                event["attendees"] = [{"email": email} for email in attendee_emails]

            # Update the event
            updated_event = (
                self.service.events()
                .update(calendarId="primary", eventId=event_id, body=event)
                .execute()
            )

            return f"Event '{updated_event.get('summary')}' updated successfully"

        except Exception as e:
            return f"Error updating event: {str(e)}"

    def delete_event(self, event_id: str) -> str:
        """Delete calendar event"""
        try:
            self.service.events().delete(
                calendarId="primary", eventId=event_id
            ).execute()

            return "Event deleted successfully"

        except Exception as e:
            return f"Error deleting event: {str(e)}"

    def create_calendar(
        self, calendar_name: str, description: str = ""
    ) -> Dict[str, Any]:
        """Create a new calendar"""
        try:
            calendar = {
                "summary": calendar_name,
                "description": description,
                "timeZone": "Asia/Kolkata",
            }

            created_calendar = self.service.calendars().insert(body=calendar).execute()

            return {
                "success": True,
                "calendar_id": created_calendar.get("id"),
                "calendar_name": created_calendar.get("summary"),
                "message": f"Calendar '{calendar_name}' created successfully",
            }

        except Exception as e:
            return {"success": False, "error": f"Error creating calendar: {str(e)}"}

    def list_calendars(self) -> Dict[str, Any]:
        """List all accessible calendars"""
        try:
            calendars_result = self.service.calendarList().list().execute()
            calendars = calendars_result.get("items", [])

            formatted_calendars = []
            for calendar in calendars:
                cal_data = {
                    "id": calendar.get("id"),
                    "summary": calendar.get("summary"),
                    "description": calendar.get("description", ""),
                    "primary": calendar.get("primary", False),
                    "access_role": calendar.get("accessRole", ""),
                    "background_color": calendar.get("backgroundColor", ""),
                }
                formatted_calendars.append(cal_data)

            return {
                "success": True,
                "calendars": formatted_calendars,
                "total_found": len(formatted_calendars),
                "message": f"Found {len(formatted_calendars)} calendars",
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error listing calendars: {str(e)}",
                "calendars": [],
            }

    def share_calendar(
        self, calendar_id: str, emails: List[str], role: str = "reader"
    ) -> str:
        """Share calendar with multiple users"""
        try:
            results = []

            for email in emails:
                rule = {
                    "scope": {
                        "type": "user",
                        "value": email,
                    },
                    "role": role,
                }

                self.service.acl().insert(calendarId=calendar_id, body=rule).execute()

                results.append(f"Shared with {email} as {role}")

            return f"Calendar shared successfully. {'; '.join(results)}"

        except Exception as e:
            return f"Error sharing calendar: {str(e)}"

    def get_free_busy(
        self, emails: List[str], start_time: str, end_time: str
    ) -> Dict[str, Any]:
        """Check free/busy status for multiple users"""
        try:
            items = [{"id": email} for email in emails]

            body = {
                "timeMin": start_time,
                "timeMax": end_time,
                "timeZone": "Asia/Kolkata",
                "items": items,
            }

            freebusy = self.service.freebusy().query(body=body).execute()

            formatted_result = {}
            for email in emails:
                busy_times = freebusy["calendars"].get(email, {}).get("busy", [])
                formatted_result[email] = {
                    "busy_periods": busy_times,
                    "is_free": len(busy_times) == 0,
                }

            return {
                "success": True,
                "free_busy_data": formatted_result,
                "time_range": f"{start_time} to {end_time}",
            }

        except Exception as e:
            return {"success": False, "error": f"Error checking free/busy: {str(e)}"}

    # Wrapper methods for CalendarManager
    def _create_event_wrapper(self, input_str: str) -> str:
        """Wrapper for create_event. Format: 'attendee_emails_json|||summary|||start_time|||end_time|||description|||location|||create_meet'"""  # noqa
        try:
            import json

            parts = input_str.split("|||")
            attendee_emails = json.loads(parts[0].strip()) if parts[0].strip() else []
            summary = parts[1].strip()
            start_time = parts[2].strip()
            end_time = parts[3].strip()
            description = parts[4].strip() if len(parts) > 4 else ""
            location = parts[5].strip() if len(parts) > 5 else ""
            create_meet = parts[6].strip().lower() == "true" if len(parts) > 6 else True

            result = self.create_event(
                attendee_emails=attendee_emails,
                summary=summary,
                start_time=start_time,
                end_time=end_time,
                description=description,
                location=location,
                create_meet=create_meet,
            )
            return result
        except Exception as e:
            return f"Error creating event: {str(e)}"

    def _read_events_wrapper(self, input_str: str) -> str:
        """Wrapper for read_events. Format: 'start_date|||end_date|||max_results'"""
        try:
            parts = input_str.split("|||")
            start_date = parts[0].strip()
            end_date = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
            max_results = (
                int(parts[2].strip()) if len(parts) > 2 and parts[2].strip() else 10
            )

            result = self.read_events(
                start_date=start_date, end_date=end_date, max_results=max_results
            )
            return str(result)
        except Exception as e:
            return f"Error reading events: {str(e)}"

    def _update_event_wrapper(self, input_str: str) -> str:
        """Wrapper for update_event. Format: 'event_id|||summary|||start_time|||end_time|||description|||location|||attendee_emails_json'"""  # noqa
        try:
            import json

            parts = input_str.split("|||")
            event_id = parts[0].strip()
            summary = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
            start_time = (
                parts[2].strip() if len(parts) > 2 and parts[2].strip() else None
            )
            end_time = parts[3].strip() if len(parts) > 3 and parts[3].strip() else None
            description = (
                parts[4].strip() if len(parts) > 4 and parts[4].strip() else None
            )
            location = parts[5].strip() if len(parts) > 5 and parts[5].strip() else None
            attendee_emails = (
                json.loads(parts[6].strip())
                if len(parts) > 6 and parts[6].strip()
                else None
            )

            result = self.update_event(
                event_id=event_id,
                summary=summary,
                start_time=start_time,
                end_time=end_time,
                description=description,
                location=location,
                attendee_emails=attendee_emails,
            )
            return result
        except Exception as e:
            return f"Error updating event: {str(e)}"

    def _delete_event_wrapper(self, input_str: str) -> str:
        """Wrapper for delete_event. Format: 'event_id'"""
        try:
            event_id = input_str.strip()
            result = self.delete_event(event_id=event_id)
            return result
        except Exception as e:
            return f"Error deleting event: {str(e)}"

    def _create_calendar_wrapper(self, input_str: str) -> str:
        """Wrapper for create_calendar. Format: 'calendar_name|||description'"""
        try:
            parts = input_str.split("|||")
            calendar_name = parts[0].strip()
            description = parts[1].strip() if len(parts) > 1 else ""

            result = self.create_calendar(
                calendar_name=calendar_name, description=description
            )
            return str(result)
        except Exception as e:
            return f"Error creating calendar: {str(e)}"

    def _list_calendars_wrapper(self, input_str: str) -> str:
        """Wrapper for list_calendars. Format: '' (no parameters)"""
        try:
            result = self.list_calendars()
            return str(result)
        except Exception as e:
            return f"Error listing calendars: {str(e)}"

    def _share_calendar_wrapper(self, input_str: str) -> str:
        """Wrapper for share_calendar. Format: 'calendar_id|||emails_json|||role'"""
        try:
            import json

            parts = input_str.split("|||")
            calendar_id = parts[0].strip()
            emails = json.loads(parts[1].strip()) if len(parts) > 1 else []
            role = parts[2].strip() if len(parts) > 2 and parts[2].strip() else "reader"

            result = self.share_calendar(
                calendar_id=calendar_id, emails=emails, role=role
            )
            return result
        except Exception as e:
            return f"Error sharing calendar: {str(e)}"

    def _get_free_busy_wrapper(self, input_str: str) -> str:
        """Wrapper for get_free_busy. Format: 'emails_json|||start_time|||end_time'"""
        try:
            import json

            parts = input_str.split("|||")
            emails = json.loads(parts[0].strip()) if parts[0].strip() else []
            start_time = parts[1].strip()
            end_time = parts[2].strip()

            result = self.get_free_busy(
                emails=emails, start_time=start_time, end_time=end_time
            )
            return str(result)
        except Exception as e:
            return f"Error checking free/busy status: {str(e)}"

    def get_tools_wrappers(self):
        """Get tools with wrapper methods that parse string inputs"""
        tools = [
            Tool(
                name="create_calendar_event",
                description="Create calendar event. Format: 'attendee_emails_json|||summary|||start_time|||end_time|||description|||location|||create_meet'",  # noqa
                func=self._create_event_wrapper,
            ),
            Tool(
                name="read_calendar_events",
                description="Read calendar events. Format: 'start_date|||end_date|||max_results'",
                func=self._read_events_wrapper,
            ),
            Tool(
                name="update_calendar_event",
                description="Update calendar event. Format: 'event_id|||summary|||start_time|||end_time|||description|||location|||attendee_emails_json'",  # noqa
                func=self._update_event_wrapper,
            ),
            Tool(
                name="delete_calendar_event",
                description="Delete calendar event. Format: 'event_id'",
                func=self._delete_event_wrapper,
            ),
            Tool(
                name="create_new_calendar",
                description="Create new calendar. Format: 'calendar_name|||description'",
                func=self._create_calendar_wrapper,
            ),
            Tool(
                name="list_all_calendars",
                description="List all calendars. Format: '' (no parameters needed)",
                func=self._list_calendars_wrapper,
            ),
            Tool(
                name="share_calendar_with_users",
                description="Share calendar with users. Format: 'calendar_id|||emails_json|||role'",
                func=self._share_calendar_wrapper,
            ),
            Tool(
                name="check_free_busy_status",
                description="Check free/busy status. Format: 'emails_json|||start_time|||end_time'",
                func=self._get_free_busy_wrapper,
            ),
        ]
        return tools

    def get_tools(self):
        tools = [
            Tool(
                name="create_calendar_event",
                description='Create calendar event. JSON: {"attendee_emails": ["str"], "summary": "str", "start_time": "str", "end_time": "str", "description": "str", "location": "str", "create_meet": true/false}',
                func=lambda params: self.create_event(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
            Tool(
                name="read_calendar_events",
                description='Read calendar events. JSON: {"start_date": "str", "end_date": "str", "max_results": int}',
                func=lambda params: self.read_events(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
            Tool(
                name="update_calendar_event",
                description='Update calendar event. JSON: {"event_id": "str", "updates": {"summary": "str", "start_time": "str", "end_time": "str", "description": "str", "location": "str"}}',
                func=lambda params: self.update_event(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
            Tool(
                name="delete_calendar_event",
                description='Delete calendar event. JSON: {"event_id": "str"}',
                func=lambda params: self.delete_event(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
            Tool(
                name="create_new_calendar",
                description='Create a new calendar. JSON: {"title": "str", "description": "str"}',
                func=lambda params: self.create_calendar(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
            Tool(
                name="list_all_calendars",
                description='List all accessible calendars. JSON: {"min_access_role": "str"}',
                func=lambda params: self.list_calendars(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
            Tool(
                name="share_calendar_with_users",
                description='Share calendar with users. JSON: {"calendar_id": "str", "emails": ["str"], "role": "str", "notifications": true/false}',
                func=lambda params: self.share_calendar(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
            Tool(
                name="check_free_busy_status",
                description='Check free/busy status. JSON: {"emails": ["str"], "start_time": "str", "end_time": "str", "calendar_id": "str"}',
                func=lambda params: self.get_free_busy(**(params if isinstance(params, dict) else __import__("json").loads(params))),
            ),
        ]
        return tools
