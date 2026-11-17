# Source-code audit and migration decisions

## Source 1: CreateRevisionConfig

The supplied .NET 8 Windows Forms project contains two user workflows:

### A. Create Revision Config
- Loads Process Landscape children from the configured root page.
- Supports three-level page selection (root/level 2/level 3).
- Calls the Confluence child-page REST endpoint.
- Removes the UUID-like prefix from display titles when present.
- Uses Selenium/Chrome to open the QMS version-history endpoint.
- Reads JSON from the page's `<pre>` element.
- Finds the published revision (`latest == "true"`).
- Adds up to five older revisions (`latest == "false"`).
- Generates XML using the main-page and page-revision templates.
- Writes `output.xml`.

### B. Create Compass Config
- Loads the same Process Landscape hierarchy.
- Selects a level-2 page.
- Fetches its child pages.
- Applies the configured workflow XML template to each child.
- Generates a `Confluence_Page_Tree` document.
- Writes `Confluence_Page_Config.xml`.

### Migration implications
- Keep the two workflows as separate routes/pages under the CreateRevisionConfig module.
- Preserve root page ID and XML templates as configuration, not hardcoded UI logic.
- Preserve title normalization and XML escaping correctly.
- Use an XML library to construct/validate XML rather than unsafe string concatenation.
- Confirm pagination behavior: the original child-page code reads `results` but does not visibly follow pagination links.
- Preserve the existing revision-history source initially; investigate whether an authenticated HTTP request can replace Selenium without changing returned data.

## Source 2: ProcManUtilities

This is a process comparison and Excel reporting application.

### Main active UI workflow
- Loads a three-level Process Landscape hierarchy.
- Loads a configured revision XML file (`Compass_Config_Template_V01.xml`).
- For the selected level-3 page, displays the published revision and historical revisions as checkboxes.
- Enables comparison only when exactly two revisions are selected.
- Identifies the higher revision as published and lower revision as outdated.
- Fetches each page through Confluence REST API using `expand=body.view`.
- Extracts the process-flow table with class `qms-structure-table aui confluenceTable`.
- Parses rows into activity data:
  - Number, title, successor
  - Input and output labels and links
  - RASIC role/name/link records
  - Dependency type/name/link records
- Compares published and previous versions.
- Creates an Excel workbook with `Info` and `CompReport` sheets.
- Highlights additions/modifications in green and deletions in red.
- Adds hyperlinks/comments, totals and activity-wise summaries.

### Comparison dimensions to preserve
- Activities added/deleted/modified.
- Successor changes.
- Inputs added/deleted.
- Outputs added/deleted.
- RASIC roles added/deleted.
- Dependency/guidance elements added/deleted.
- Activity-wise and overall summary counts.
- Excel sheet names, column order, formatting, hyperlinks, comments and freeze panes.

### Other code paths found
- The source contains an IronXL-based comparison implementation in addition to the ClosedXML-based
  `CompareVersions` path used by the active Compare button.
- It also contains inline HTML diff and helper/experimental comparison methods.
- Audit which of these are still required before removing them. Do not silently drop them during porting.

## Integration finding

The ProcManUtilities resource config points to `Compass_Config_Template_V01.xml`.
CreateRevisionConfig writes `output.xml` and `Confluence_Page_Config.xml` to the system temp directory.
The source does not establish that these outputs are the same format or are automatically consumed
by ProcManUtilities. Confirm the intended hand-off with the business owner.

## Known technical risks / items to validate
1. Authentication: hardcoded credentials exist in both C# sources. Rotate and externalize them.
2. Selenium: current revision-history retrieval depends on Chrome/ChromeDriver and page rendering.
3. XML: current code uses string replacement and fragment insertion; validate escaping and malformed values.
4. Excel: reproduce workbook styling, hyperlinks, comments, formulas/counts and row placement.
5. Matching: the existing comparison logic matches activities primarily by title and has fallback matching
   behavior; preserve first, then improve only with approval.
6. Ordering: preserve source ordering for pages, revisions, activities and nested elements.
7. Error handling: replace console/message-box errors with structured API errors without losing actionable detail.
8. Pagination/timeouts: explicitly test large Confluence page trees and slow responses.
9. File flow: make config input/output paths explicit and downloadable through the UI.
10. Golden tests: compare migrated XML and XLSX outputs against known-good outputs from the original apps.

## Functional parity acceptance criteria

A migration is not complete merely because the screens load. Each workflow must be tested with the
same source data and compared against the original:
- XML structure, values, ordering and escaping.
- Selected published/outdated revision IDs.
- Parsed process-flow records and links.
- Added/deleted/modified classifications.
- Excel sheet names, data, colors, hyperlinks, comments and summaries.


## Application 1 backend migration - first implementation pass

The scaffold now includes initial Python implementations for:
- Confluence child-page retrieval.
- UUID-prefixed page-title normalization.
- Selenium-based QMS revision-history retrieval with `<pre>` JSON parsing.
- Published revision + up to five historical revisions selection.
- XML generation for `output.xml` and `Confluence_Page_Config.xml`.
- API endpoints returning downloadable XML attachments.

This is an initial port, not yet parity-certified. Important follow-ups:
- Validate QMS browser authentication/SSO in the target corporate environment.
- Verify exact XML output against original generated files, including whether parent grouping and template whitespace are consumed downstream.
- Check whether `Dataresult.Count > 1` is an intentional business rule in Compass XML generation.
- The original Compass workflow generates nodes for all child pages of every level-2 item currently loaded; the API takes those level-2 IDs explicitly.
- Add API integration tests with mocked Confluence and Selenium responses.
