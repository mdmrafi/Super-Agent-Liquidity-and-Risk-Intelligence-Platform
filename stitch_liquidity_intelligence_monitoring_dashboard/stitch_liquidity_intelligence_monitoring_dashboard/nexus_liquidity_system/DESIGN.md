---
name: Nexus Liquidity System
colors:
  surface: '#fbf8fa'
  surface-dim: '#dcd9db'
  surface-bright: '#fbf8fa'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f3f4'
  surface-container: '#f0edef'
  surface-container-high: '#eae7e9'
  surface-container-highest: '#e4e2e3'
  on-surface: '#1b1b1d'
  on-surface-variant: '#45474c'
  inverse-surface: '#303032'
  inverse-on-surface: '#f3f0f2'
  outline: '#75777d'
  outline-variant: '#c5c6cd'
  surface-tint: '#545f73'
  primary: '#091426'
  on-primary: '#ffffff'
  primary-container: '#1e293b'
  on-primary-container: '#8590a6'
  inverse-primary: '#bcc7de'
  secondary: '#5c5f61'
  on-secondary: '#ffffff'
  secondary-container: '#e0e3e5'
  on-secondary-container: '#626567'
  tertiary: '#041528'
  on-tertiary: '#ffffff'
  tertiary-container: '#1a2a3e'
  on-tertiary-container: '#8191a9'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d8e3fb'
  primary-fixed-dim: '#bcc7de'
  on-primary-fixed: '#111c2d'
  on-primary-fixed-variant: '#3c475a'
  secondary-fixed: '#e0e3e5'
  secondary-fixed-dim: '#c4c7c9'
  on-secondary-fixed: '#191c1e'
  on-secondary-fixed-variant: '#444749'
  tertiary-fixed: '#d3e4fe'
  tertiary-fixed-dim: '#b7c8e1'
  on-tertiary-fixed: '#0b1c30'
  on-tertiary-fixed-variant: '#38485d'
  background: '#fbf8fa'
  on-background: '#1b1b1d'
  surface-variant: '#e4e2e3'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  data-mono:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: -0.01em
  label-caps:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  container-max: 1440px
  gutter: 20px
---

## Brand & Style
This design system is engineered for high-stakes financial operations, specifically for agents and teams monitoring multi-provider liquidity in real-time. The brand personality is **authoritative, analytical, and vigilant**. It prioritizes data density without sacrificing clarity, ensuring that critical information is surfaced instantly.

The visual style is **Corporate Modern**, utilizing a structured layout with subtle depth. It leverages a "Pro-Grade" aesthetic—combining the clean utility of SaaS with the robust reliability of enterprise fintech. The interface uses a neutral foundation to allow high-contrast provider colors and status indicators to serve as primary navigational cues.

## Colors
The palette is rooted in a deep slate primary for structural elements (navigation, headers) to evoke stability. The secondary background color is a crisp, off-white slate to reduce eye strain during long shifts.

**Functional Application:**
- **Provider Colors:** Used specifically for branding transaction rows, provider-specific cards, and filter toggles. These must maintain their brand integrity.
- **Semantic Status:** Success, Warning, and Danger colors are reserved strictly for liquidity thresholds and system health.
- **Neutral Scale:** A wide range of grays from `#f8fafc` to `#0f172a` is used to create hierarchy in data tables and metadata.

## Typography
This design system utilizes a dual-font strategy. **Plus Jakarta Sans** provides a modern, professional character for headings and dashboard titles. **Inter** is utilized for all body copy, data tables, and UI controls due to its exceptional legibility at small sizes and high x-height.

**Guidelines:**
- Use `data-mono` (Inter Medium) for all numerical figures in tables to ensure alignment and readability.
- Multi-language support (English, Bengali, Banglish) requires consistent line-heights; `body-md` is the standard for localized text strings to prevent layout shifts.
- Use `label-caps` for table headers and section overviews to differentiate from interactive content.

## Layout & Spacing
The system follows a **Fluid Grid** model with a 12-column structure for the main dashboard content. 

- **Desktop:** 240px fixed left navigation, fluid content area with 32px padding.
- **Tablet:** 80px collapsed rail navigation, 24px padding.
- **Mobile:** Single column stack with 16px horizontal margins.
- **Spacing Rhythm:** Based on a 4px baseline. Components use `md` (16px) for internal padding to maintain a dense but breathable information architecture.

## Elevation & Depth
To maintain a professional fintech feel, the system uses **Tonal Layers** supplemented by subtle ambient shadows. 

- **Level 0 (Background):** `#f8fafc` - The canvas.
- **Level 1 (Cards/Sections):** White surface with a 1px border in `#e2e8f0`. No shadow.
- **Level 2 (Hover/Active):** White surface with a `0 4px 6px -1px rgb(0 0 0 / 0.1)` shadow. Used for interactive cards.
- **Level 3 (Modals/Overlays):** White surface with a `0 20px 25px -5px rgb(0 0 0 / 0.1)` shadow.

This approach ensures that even with high data density, the user can distinguish between background containers and actionable elements.

## Shapes
The system uses a **Rounded** philosophy. Standard UI components (buttons, inputs) utilize a `0.5rem` (8px) radius. Larger layout containers and dashboard cards utilize `rounded-xl` (24px) to soften the density of the numerical data and create a more modern, approachable interface.

## Components

### Data Cards & Sparklines
Cards are the primary unit of information. Each liquidity card must feature:
- Provider logo and name.
- Large numerical balance (`data-mono`).
- A subtle trend sparkline (Emerald for up, Rose for down).
- A footer containing the "Last Updated" timestamp.

### Status Badges
Badges use high-contrast text on a low-opacity background of the same color (e.g., Emerald text on 10% Emerald background). Use icons within badges (Check, Alert, Info) to assist color-blind users.

### AI Chatbot & Explainable AI
The sidebar chatbot uses a distinct `primary_color` (Slate 800) header. 
- **AI Explanations:** Inside alerts, use a "Confidence Level" meter (0-100%).
- **Evidence Blocks:** Use a slightly darker background (`#f1f5f9`) for automated reasoning sections to separate human-entered data from machine-generated insights.

### Inputs & Multi-language Toggles
- **Inputs:** Use 1px borders with a focus state of `primary_color`. 
- **Language Toggle:** A segmented control (English | বাংলা | Banglish) located in the top utility bar. Active state uses a Slate background with White text.

### Tables
Dense rows (32px - 40px height). Alternate row striping is discouraged; use subtle 1px dividers. Header text should be `label-caps`.