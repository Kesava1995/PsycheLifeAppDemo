# Design System Specification: Clinical Clarity & Editorial Depth

## 1. Overview & Creative North Star
**The Creative North Star: "The Clinical Curator"**

In the sensitive context of psychiatric clinical case sheets, the UI must transcend the "utility-first" look of legacy medical software. This design system is built on the principle of **The Clinical Curator**—a philosophy that treats medical data with the same intentionality as a high-end editorial publication. 

We move beyond standard grids by utilizing **intentional asymmetry, sophisticated tonal layering, and expansive breathing room.** By rejecting the traditional "boxed-in" interface in favor of organic depth and glassmorphism, we create an environment that feels calm, authoritative, and profoundly focused. The goal is to reduce cognitive load for clinicians through a "soft-focus" periphery and a "sharp-focus" core.

---

## 2. Color & Surface Architecture

### The "No-Line" Rule
Traditional 1px solid borders create visual noise and "grid-locking." In this system, **1px solid lines for sectioning are strictly prohibited.** Structural boundaries are defined exclusively through:
*   **Tonal Shifts:** Moving between `Surface` and `Surface-Container-Low`.
*   **Vertical Rhythm:** Using the spacing scale to define grouping.
*   **Elevation Nesting:** Placing a `Surface-Container-Lowest` element inside a `Surface-Container` to create natural contrast.

### Surface Hierarchy
We utilize a five-tier nesting system to establish a physical sense of depth, mimicking stacked sheets of high-grade clinical paper.
*   **Base Layer (`Surface` #f6fafa):** The canvas for the entire application.
*   **Structural Sections (`Surface-Container-Low` #f0f4f4):** Used for large sidebar areas or background groupings.
*   **Content Cards (`Surface-Container-Lowest` #ffffff):** The primary focal point for case data.
*   **Interactive Overlays (`Surface-Container-High` #dfe3e3):** Used for hover states or subtle UI elevation.

### The "Glass & Gradient" Signature
To inject a premium feel into a clinical setting:
*   **Glassmorphism:** All floating elements (modals, dropdowns, snackbars) must use a semi-transparent `Surface` color with a `backdrop-filter: blur(20px)`.
*   **Teal Gradient:** Primary CTAs must not be flat. Apply a subtle linear gradient from `Primary` (#006672) to `Primary-Container` (#16808f) at a 135-degree angle. This adds "soul" and depth to the most critical actions.

---

## 3. Typography: The Editorial Voice

We employ a dual-font strategy to balance character with legibility.

*   **Manrope (Headlines & Section Titles):** A modern geometric sans-serif that provides a "Display" feel. Use it for `Display-LG` through `Headline-SM`. It conveys authority and modern clinical precision.
*   **Inter (Body, Labels, & Data):** Chosen for its exceptional readability in dense data environments. Use it for all `Title`, `Body`, and `Label` tokens.

**The Hierarchy Strategy:**
*   **Display/Headline (Manrope):** Large, low-contrast (tracking -2%) for a bold, editorial entrance to case files.
*   **Body (Inter):** Generous line-height (1.6) to ensure clinician notes are readable during long shifts.
*   **Labels (Inter Bold):** Use `Label-SM` in `On-Surface-Variant` (#3f4948) for field headers to keep them secondary to the patient data.

---

## 4. Elevation & Depth

### The Layering Principle
Depth is achieved through "Tonal Stacking" rather than shadows. 
*   *Example:* A patient’s history card (`Surface-Container-Lowest`) should sit on a section background of `Surface-Container-Low`. The 2-point hex shift is enough for the eye to perceive a layer without the "dirtiness" of a drop shadow.

### Ambient Shadows
Where floating is required (Modals/Floating Action Buttons):
*   **Value:** `0px 12px 32px rgba(24, 28, 29, 0.06)`. 
*   **Rule:** Shadows must be diffused and use the `On-Surface` color as the tint, never pure black.

### The "Ghost Border" Fallback
Borders are only permitted for input fields and are defined as **Ghost Borders**:
*   **Token:** `Outline-Variant` (#bdc8cb) at **20% opacity**.
*   This creates a "suggestion" of a container that disappears into the background, keeping the focus on the clinical text.

---

## 5. Components

### Input Fields
*   **Corner Radius:** 6px.
*   **Style:** Ghost Border (20% opacity). On focus, transition to `Primary` (#006672) with a 2px stroke.
*   **Layout:** Labels should be top-aligned using `Label-MD` for immediate scanning.

### Cards & Case Modules
*   **Corner Radius:** 12px.
*   **Rule:** No dividers. Use `2.5rem` (Space 10) of vertical white space to separate medical history from current symptoms.
*   **Background:** Always `Surface-Container-Lowest` (#ffffff).

### Buttons
*   **Primary:** Teal Gradient (`Primary` to `Primary-Container`), 6px radius, white text.
*   **Secondary:** `Secondary-Container` (#dae5e4) background with `On-Secondary-Container` (#5c6666) text. No border.
*   **Tertiary:** Ghost button (no background), `Primary` text, bold weight.

### Modals & Dialogs
*   **Corner Radius:** 16px.
*   **Effect:** Glassmorphism (`backdrop-filter: blur(16px)`).
*   **Shadow:** Large ambient shadow (8% opacity).

### Chips (Clinical Tags)
*   **Style:** `Surface-Container-High` (#dfe3e3) background with 999px radius.
*   **Usage:** For symptoms, diagnoses, or status indicators.

---

## 6. Do’s and Don’ts

### Do
*   **Do** use tonal shifts (e.g., #f6fafa to #f0f4f4) to separate the sidebar from the main case sheet.
*   **Do** utilize `Primary-Fixed` (#9eefff) for highlighting critical "New" or "Urgent" patient alerts.
*   **Do** provide at least `2rem` (Space 8) of padding inside all data cards.
*   **Do** use `Tertiary` (#b7131a) exclusively for high-alert psychiatric warnings or self-harm risks.

### Don’t
*   **Don’t** use a 1px solid line to separate the header from the body. Use a subtle `Surface-Container` shift instead.
*   **Don’t** use pure black (#000000) for text. Always use `On-Surface` (#181c1d) to maintain a soft, clinical eye-feel.
*   **Don’t** exceed a 6px radius on input fields; psychiatric applications require a sense of "structured order" that overly rounded corners can undermine.
*   **Don’t** use heavy drop shadows on cards; let the tonal shifts do the heavy lifting.