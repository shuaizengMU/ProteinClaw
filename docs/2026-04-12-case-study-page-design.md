# Case Study Page — Design Spec

**Date:** 2026-04-12  
**Branch:** dev-desktop-app  
**Status:** Approved

---

## Overview

Add a Case Study page to ProteinClaw that users can navigate to from the sidebar. The page replaces the chat window, shows curated bioinformatics use-case cards organized by category, and lets users launch any example directly into a new conversation with the prompt pre-filled.

---

## Architecture

### View switching

`App.tsx` gains a `currentView: 'chat' | 'case-study'` state. The Sidebar receives an `onNavigate` callback. When the user clicks "Case study" in the sidebar nav, `currentView` is set to `'case-study'` and `<CaseStudyPage>` is rendered in place of `<ChatWindow>`. Clicking "New chat" or selecting any conversation resets `currentView` to `'chat'`.

### Data source

Case study data is stored in a local JSON file at `~/.config/proteinclaw/case-studies.json` — the same directory the backend already uses for `config.toml`. This file ships with a default set of cases and can be edited by the user to add or modify cases.

The Python backend (FastAPI, `proteinclaw/server/`) exposes a new endpoint:

```
GET /api/case-studies
```

Response:

```json
{
  "cases": [
    {
      "id": "predict-binding-sites",
      "title": "Predict Binding Sites",
      "category": "sequence",
      "icon": "dna",
      "description": "Given a protein sequence in FASTA format, identify active site residues and binding pocket candidates.",
      "examplePrompt": "Analyze the following protein sequence and identify potential binding site residues...",
      "exampleResult": "Active Site Residues Identified:\n• Kinase domain: D855, N842..."
    }
  ]
}
```

The backend reads the file on each request (no caching), so the user can edit the file without restarting the app.

### Categories

Categories are hardcoded in the frontend. Each case in the JSON includes a `category` field that maps to one of the predefined category IDs.

| ID | Label | Color |
|---|---|---|
| `sequence` | Sequence Analysis | Blue (`#60a5fa`) |
| `structure` | Structure | Purple (`#a78bfa`) |
| `drug` | Drug Discovery | Green (`#34d399`) |
| `function` | Function | Orange (`#fb923c`) |

---

## Page Layout

The Case Study page is a two-column layout that fills the area previously occupied by `<ChatWindow>`.

### Left: Category navigation (`CaseStudyCategoryNav`)

- Fixed width (~170 px), vertically scrollable
- "All" item at top showing total count
- One item per category, each with a colored dot and case count
- Clicking a category filters the right panel to show only cards from that category
- "All" shows every case grouped by category with section labels
- Active category is highlighted

### Right: Card grid (`CaseStudyGrid`)

- Scrollable main area with 24 px padding
- Page header: "Case Studies" title + subtitle
- Cases grouped by category with a section label above each group
- Each group renders a 2-column card grid

---

## Components

### `CaseStudyPage`

Top-level component. Fetches data from `/api/case-studies` on mount. Manages selected category state. Renders `CaseStudyCategoryNav` + `CaseStudyGrid`.

Props: `onTryIt: (prompt: string) => void`

### `CaseStudyCategoryNav`

Renders the left category list. Highlights the active category. On click, notifies parent to filter/scroll.

Props: `categories`, `activeCategoryId`, `counts`, `onSelect`

### `CaseStudyGrid`

Renders case cards grouped by category. When a category is selected (not "All"), only that group is shown.

Props: `cases`, `activeCategoryId`, `onCardClick`

### `CaseStudyCard`

Single card. Flat by default, hover reveals a `#242424` background. Layout: icon box (left) + title/description (center) + chevron button (right, appears on hover).

Props: `caseStudy`, `onClick`

### `CaseStudyModal`

Detail modal. Opens centered with a dimmed backdrop (`rgba(0,0,0,0.55)` + `backdrop-filter: blur(2px)`). Contains:

- **Header**: colored icon box + title + category tag + close (×) button
- **Body**: description paragraph, "Example Prompt" code block, "Example Result" block
- **Footer**: "Close" secondary button + "Try it →" primary button

Props: `caseStudy`, `onClose`, `onTryIt`

---

## Icon mapping

Each case has an `icon` field (string). The frontend maps icon names to Lucide components:

| Value | Lucide component |
|---|---|
| `dna` | `Dna` |
| `search` | `Search` |
| `bar-chart` | `BarChart2` |
| `git-branch` | `GitBranch` |
| `layers` | `Layers` |
| `box` | `Box` |
| `flask` | `FlaskConical` |
| `activity` | `Activity` |

Unknown icon values fall back to `BookOpen`.

---

## "Try it" flow

1. User clicks "Try it" in the modal
2. Modal closes
3. `onTryIt(examplePrompt)` fires — propagates up through `CaseStudyPage` → `App`
4. `App` sets `currentView = 'chat'`
5. `App` calls `handleNewChat()` to create a new pending conversation
6. `App` stores the prompt string in a `pendingPrompt` ref
7. `ChatWindow` receives `pendingPrompt` and pre-fills the input on mount (sets the textarea value, does not send)

---

## Backend changes

**File:** `src-tauri/src/main.rs` or the Python backend (wherever HTTP routes are defined)

New route: `GET /api/case-studies`

1. Resolve the path to `case-studies.json` in the app data directory
2. If the file does not exist, write the bundled default JSON to that path, then return it
3. Read and parse the JSON
4. Return the parsed content as the response body

**Default `case-studies.json`** is bundled inside the Python package at `proteinclaw/resources/case-studies.json`. On first run (when `~/.config/proteinclaw/case-studies.json` does not exist), the backend copies the bundled default to that path so the user can edit it.

---

## File structure

```
frontend/src/
  components/
    CaseStudyPage.tsx         ← top-level page component
    CaseStudyCategoryNav.tsx
    CaseStudyGrid.tsx
    CaseStudyCard.tsx
    CaseStudyModal.tsx
  hooks/
    useCaseStudies.ts         ← fetch + loading/error state
  types.ts                    ← add CaseStudy, CaseStudyCategory types

proteinclaw/
  server/
    case_studies.py           ← GET /api/case-studies router
    main.py                   ← include new router here
  resources/
    case-studies.json         ← default bundled data (copied to ~/.config/proteinclaw/ on first run)
```

---

## Default case studies (initial set)

| Title | Category | Icon |
|---|---|---|
| Predict Binding Sites | sequence | dna |
| Motif Search | sequence | search |
| Conservation Analysis | sequence | bar-chart |
| Phylogenetic Tree | sequence | git-branch |
| Structure Comparison | structure | layers |
| Pocket Detection | structure | box |
| Contact Map | structure | box |
| Virtual Screening | drug | flask |
| ADMET Prediction | drug | activity |

---

## Out of scope

- Search/filter within case studies
- User-created case studies via UI (edit JSON file directly)
- Pagination
- Case study ratings or favorites
