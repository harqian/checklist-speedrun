# Checklist Speedrun

A simple, keyboard-driven web application for running through personal checklists quickly. It tracks the time taken to complete a checklist and logs it to a Google Sheet.

## Features

-   **Keyboard-Driven:** Navigate and complete your checklists without taking your hands off the keyboard.
-   **Time Tracking:** A built-in timer tracks how long it takes to complete a checklist.
-   **Google Sheets Integration:** Automatically logs your completion times to a Google Sheet for tracking and analysis.
-   **Customizable Checklists:** Create your own checklists in a simple JSON format.
-   **Customizable Keyboard Shortcuts:** Modify `keyboard_shortcuts.json` to fit your workflow.
-   **Light & Dark Modes:** Switch between light and dark themes.

## Setup

1.  **Clone the repository:**

    ```bash
    git clone <repository-url>
    cd checklist_speed
    ```

2.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up Google Sheets API:**

    -   Follow the instructions [here](https://developers.google.com/sheets/api/quickstart/python#authorize_credentials_for_a_service_account) to create a service account and enable the Google Sheets API.
    -   Download the service account key file and save it in the project directory. The application looks for a file named `atticus_service_account.json` by default, but you can name it whatever you want.

4.  **Create a Google Sheet:**

    -   Create a new Google Sheet.
    -   The first row should be a header row. The application expects a "Date" column and then columns for each checklist. For example: `Date`, `Day`, `Day (rushed)`, `Night`.
    -   Share the sheet with the service account's email address (found in the service account JSON file).

5.  **Configure environment variables:**
    -   Create a `.env` file in the project root.
    -   Add the following variables:
        ```
        SPREADSHEET_ID=<your-google-sheet-id>
        SHEET_NAME=<your-sheet-name>
        SERVICE_ACCOUNT_FILE=<path-to-your-service-account-json-file>
        ```

## Usage

1.  **Run the application:**

    ```bash
    python todo_app.py
    ```

2.  **Open in your browser:**
    Navigate to `http://127.0.0.1:5001`

3.  **Use the application:**
    -   Use the dropdown to select a checklist.
    -   Use keyboard shortcuts to navigate and complete items. Press `?` to see the list of shortcuts.

## Checklist Format

Checklists are stored as JSON files in the `checklists/` directory. The format is a nested dictionary. The keys are the checklist items. A value of `null` indicates a leaf item. A dictionary as a value indicates a nested checklist.

### Example: `checklists/morning.json`

```json
{
    "morning": {
        "start timer!": null,
        "get ready": {
            "get": {
                "earbuds": null,
                "glasses": null,
                "keys": null
            },
            "do": {
                "deodorant": null,
                "moisturization": null
            }
        },
        "end timer, log time": null
    }
}
```

## TODO

### bugs

when clicking, goes into a mode where spacebar no longer works (also the skipping from clicking is a bit wrong, skips items with bar children)

### features / tweaks

make state save for reloads (shift x to reset)
make space & down arrow go to the next available item, not just the next one
keyboard shortcut hints? (maybe tell ppl shift x when they reload)
make the the checklists more customizable; instead of things with pipes arent items, can do if you write : null, its not an item, and you should write : true for things you want

-   somehow be able to get parents also as items?
    more fun animations!
-   animations + sounds for all of the keyboard shortcuts
-   something better for when i finish
-   speed effect
    editing checklists?
