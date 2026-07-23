# DESIGN SYSTEM: Blinkit Discovery Engine

**Design Direction:** "Insights Control Room"  
*Not a marketing site. Not a generic dashboard. A precision instrument for reading customer feedback at scale. Blinkit's identity is the accent, never the base.*

## Color Tokens

- **bg**: `#FAFAF7` (warm off-white, paper-like)
- **surface**: `#FFFFFF` with a 1px `#E7E5DE` border, radius 10px, no drop shadows
- **ink**: `#191D1A` (primary text)
- **ink-muted**: `#6B7069`
- **accent**: `#F8CB46` (Blinkit yellow)  
  *Usage constraint:* Used ONLY for the active state, primary CTA, and citation highlights.
- **accent-ink**: `#191D1A` (text on yellow, never white on yellow)
- **positive**: `#2E7D4F` (pipeline pass)
- **negative**: `#C4442A` (pipeline discard)

### Source Badge Colors
Badges are tinted at 10% opacity backgrounds with full-color text.
- **play_store**: `#2E7D4F`
- **app_store**: `#4A6FA5`
- **reddit**: `#C4562A`
- **youtube**: `#B03A3A`

## Typography

- **UI and Body:** `IBM Plex Sans`
- **Data & Citations:** `IBM Plex Mono`  
  *Usage constraint:* All data, numbers, citation IDs, source names, timestamps, and status messages MUST use IBM Plex Mono. This is the visual signature of the app.

### Type Scale
- **13px mono**: Data labels, citation IDs, metadata
- **15px body**: General UI and paragraphs
- **18px section titles**: Headers for cards and sections
- **24px page title**: Top-level page headers  
*No massive hero text anywhere.*

## Layout & Architecture

- **Left Sidebar (220px)**: 
  - App Name: "Discovery Engine"
  - Nav Items: Chat, Pipeline, Admin
  - Live Status Dot: At the bottom, showing ingestion state (gray idle, pulsing yellow running, green completed, red failed). Fed by `/api/admin/ingest/status`.
- **Main Content**: 
  - Max-width 860px for the Chat interface to ensure readability.
  - Full width for the Pipeline Dashboard.

## Signature Elements

### Citations ("Evidence Receipts")
Citations render as slim cards styled like a till receipt:
- **Type**: Mono
- **Border**: Dashed top border
- **Content**: Source badge, snippet text
- **Footer**: Citation ID in 11px mono at the bottom.
*This is the one memorable element; keep everything else quiet.*
