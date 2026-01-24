# Checklist Syntax Documentation

This document describes the syntax and special prefixes used in the JSON checklist files for the Checklist Speedrun application.

## 1. Standard Items
The most basic item is a key-value pair where the value is a boolean or an object.

*   `"item name": true/false`: A standard checkable item.
*   `"category name": { ... }`: A nested group of items.

## 2. Special Prefixes

### `[R]` - Rushed Mode Skip
Prefixing a key with `[R]` tells the application to hide this item and all its children when **Rushed Mode** is enabled.
```json
"[R] Morning Reflection": {
  "Gratitude list": false,
  "Long-term goals": false
}
```
*   **Normal Mode**: Visible and navigable.
*   **Rushed Mode**: Completely hidden; treated as "complete" for the purpose of finishing the list.

### `[L]` - Data Logging Component
Prefixing a key with `[L]` transforms the item into an interactive logging form that appends a row to a Google Sheet.
```json
"[L] Log Nutrition": {
  "sheet": "NutritionLog",
  "fields": ["Food Item", "Calories", "Hours Ago"]
}
```
*   **Behavior**: When selected, it focuses an input form instead of toggling a checkbox.
*   **Submit**: Pressing Enter or clicking "Log" appends: `[Timestamp, Field1, Field2, ...]` to the specified sheet.
*   **Configuration**:
    *   `sheet`: (Optional) The name of the tab in your spreadsheet.
    *   `spreadsheet_id`: (Optional) Use this if you want to log to a different file entirely.
    *   `fields`: An array of strings representing the input labels.

## 3. Formatting & Logic

### Headers & Spacers
Items that use pipes `|` or are just long dashes are treated as display-only headers. They are not navigable with arrow keys.
```json
"——————————— (Headphones) ——————————": null,
"| Section Header |": null
```

### Notes (False-only items)
Items with a value of `false` (that aren't part of a nested object) are treated as "Notes". 
*   They are hidden in **Rushed Mode**.
*   In **Normal Mode**, they must be checked off to finish the list.

### Pipes for Navigation Skip
Any key wrapped in pipes (e.g., `"| note |"`) will be rendered but skipped during keyboard navigation (Arrow Up/Down).

## 4. Nested Completion
A parent item is automatically considered "Complete" only when all of its actionable children are completed. If a parent contains only headers or notes that are hidden in Rushed mode, the parent itself becomes actionable.
