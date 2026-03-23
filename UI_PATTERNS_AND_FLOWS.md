# PsycheLife - UI Patterns & Conditional Flow Reference

**Purpose:** Visual reference for UI implementation and conditional display logic

---

## 1. Badge Selection Pattern

Used throughout MSE and multiple-state fields

### Visual Example:
```
Label: [ Option 1 ]  [ Option 2 ]  [ Option 3 ]  [ Option 4 ]
                       ^^^^^^^^^^^
                    (Selected: Click to toggle)
```

### Implementation Details:
- All options on **single line**
- Each option is a clickable badge/button
- Selected badge: Highlighted + Bold
- Only ONE can be selected at a time (radio behavior)
- No dropdown arrow
- Keyboard accessible (Tab to nav, Space/Enter to select)

### Fields Using This:
- Consciousness
- Appearance (Normal/Over dressed/Unkempt)
- Cooperativeness (Cooperative/Not Cooperative)
- Rapport (Established/Not Established/Est w/ Difficulty)
- Eye Contact Achieved (Achieved/Not Achieved)
- Eye Contact Sustained (Sustained/Not Sustained)
- Psychomotor Activity (Normal/Decreased/Increased)
- Reaction Time (Normal/Decreased/Increased)
- Relevance (Relevant/Irrelevant)
- Coherence (Coherent/Incoherent)
- Intensity (Audible/Excessively Loud/Soft)
- Pitch (Monotonous/Normal fluctuation)
- Ease of Speech (Spontaneous/Hesitant/Mute/Normal)
- Reactivity (Present/Absent)
- Range (Normal/Restricted/Labile)
- Congruence (Congruent/Incongruent)
- Appropriateness (Appropriate/Inappropriate)

---

## 2. Conditional Display Pattern

Show/Hide fields based on parent field selection

### Pattern 1: Expand on "Yes"
```
Question: [ Yes ]  [ No ]  [ Unknown ]
             ↓
IF "Yes" selected:
  ├─ Sub-field 1: [ Input ]
  ├─ Sub-field 2: [ Dropdown ]
  └─ Sub-field 3: [ Text ]

IF "No" or "Unknown":
  └─ (Sub-fields hidden)
```

**Used in:**
- Involuntary Movements (if Psychomotor abnormal)
- Negative History questions (if "Yes" selected)
- Eye Contact subdivisions (after main selection)

### Pattern 2: Stop and Hide
```
Selection: [ Option A ]  [ Option B ]  [ Option C ]

IF "Option B" selected:
  └─ STOP HERE
     ❌ Hide: All subsequent sections
     ✅ Keep: Only "Affect" section visible

IF "Option A" or "Option C":
  └─ CONTINUE to next section
```

**Used in:**
- Cooperativeness → Not Cooperative = STOP (except Affect)
- Rapport → Not Established = STOP (except Affect)

### Pattern 3: Conditional Field Pool
```
Question: [ Yes ]  [ No ]  [ Unknown ] ◄── Default

IF Yes:
  Severity:  [ Mild ]  [ Moderate ]  [ Severe ]
  Duration:  [ ___ ] [ Days ▼ / Weeks ▼ / Months ▼ / Years ▼ ] ago
  Sequelae:  [ Text input field ]

IF No or Unknown:
  └─ All sub-fields hidden
```

**Used in:**
- Negative History items
- Family History detail fields (when editing)

### Pattern 4: Status-Dependent Behavior
```
Current Status: [ Option 1 ]  [ Option 2 ]  [ Option 3 ]

IF "Currently Abstinent":
  └─ Hide: Pattern of Use field
  └─ Show: "Since: [ ___ ] days ago"

IF "Current Use" or other:
  ├─ Show: Pattern of Use field
  └─ Show: "Since: [ ___ ] days ago"
```

**Used in:**
- Substance Use (in follow-up)
- Medication Adherence (Partial/No Adherence)

### Pattern 5: Age-Based Display
```
IF Patient Age >= 60:
  ├─ H/o Progressive Memory Impairment
  └─ H/o Decline in Daily Functioning

IF Patient Age < 60:
  └─ (These fields hidden)
```

**Used in:**
- Negative History

### Pattern 6: Substance-Based Display
```
Primary Substance: [ Alcohol ]  [ Cannabis ]  [ Tobacco ]

IF "Alcohol" selected:
  ├─ H/o Hematemesis/Melena
  ├─ H/o Jaundice
  ├─ H/o Confusion/Ataxia/Memory Loss
  └─ H/o Ascites/Pancreatitis

IF other substances:
  └─ (Alcohol-specific fields hidden)
```

**Used in:**
- Negative History (in follow-up visits)

---

## 3. Read-Only with Edit Pattern

Used for fields that shouldn't be directly editable but still updatable

### Visual Flow:
```
┌─────────────────────────────────────────┐
│ Field Label: [Read-only value]  [✎ edit] │
└─────────────────────────────────────────┘
                                        ↓ 
                              (User clicks pencil)
                                        ↓
┌─────────────────────────────────────────────────────┐
│ EDIT DIALOG OPENS                                   │
│                                                     │
│ ⚠️ WARNING MESSAGE:                                 │
│ "Changing these values will affect all previous    │
│  and future dates."                                │
│                                                     │
│ Field 1: [Editable input]                          │
│ Field 2: [Editable dropdown]                       │
│ Field 3: [Editable text]                           │
│                                                     │
│ [Cancel]  [Save Changes]                           │
└─────────────────────────────────────────────────────┘
                                        ↓
                          (Changes applied everywhere)
                                        ↓
┌─────────────────────────────────────────┐
│ Field Label: [Updated value]  [✎ edit]  │
└─────────────────────────────────────────┘
```

### Implementation Notes:
- **Read-only input:** Use `<input disabled>` or read-only styling
- **Pencil icon:** SVG icon, clickable/hoverable
- **Modal backdrop:** Prevent interaction with form behind
- **Caution message:** Prominent, yellow/orange background
- **Both buttons:** Cancel (discard changes), Save (update all instances)

### Fields Using This:
- Family History (in follow-up)
- Developmental Milestone Delay (in follow-up)
- Negative History positive findings (in follow-up)

---

## 4. Duration Input Patterns

### Pattern A: First Visit / New Substance

**"Past Use" scenario:**
```
Total Duration of Use:
  [ Number Input ]  [ Dropdown: Months / Years ]
  Example: [ 24 ]  [ Months ▼ ]

Abstinent Since:
  [ Number Input ]  [ Dropdown: Months / Years / Days ]
  Example: [ 6 ]  [ Months ▼ ]
```

**Current Use scenario:**
```
Frequency:
  [ Free text or dropdown ]

Duration Using:
  [ Number Input ]  [ Dropdown: Days / Months / Years ]
```

### Pattern B: Follow-up Visit

**"Since" format (all substances):**
```
Since: [ Number Input ]  [ Dropdown: Days / Weeks / Months ]
       Example: [ 15 ]  [ Days ▼ ]

Display as: "Since 15 days ago"
             or
             "In the last 15 days"
```

### Pattern C: Medication Adherence (Follow-up)

**When Non-Good Adherence selected:**
```
Since: [ Number Input ]  [ Dropdown: Days / Weeks / Months ]
       Example: [ 3 ]  [ Weeks ▼ ]

Meaning: Non-adherence started 3 weeks ago
```

---

## 5. Search Dropdown Pattern

Used for complex lists that benefit from personalization

### Visual:
```
Search: [Type to filter...]
        ↓ (after typing)

┌────────────────────────────┐
│ 1. Auditory Hallucination  │ ← Personalized
│ 2. Visual Hallucination    │ ← (Weighted Score)
│ 3. Tactile Hallucination   │ ←
│ 4. Olfactory Hallucination │ ←
│ 5. Gustatory hallucination │ ← Text Match Only
│ 6. Somatic hallucination   │ ←
└────────────────────────────┘
```

### Behavior:
- User types: Real-time filter of options
- Always shows 6 options (if available)
- Scroll down for more if > 6 total options
- Click to select
- Selected items appear as **tags/chips** below
- Can remove tags by clicking X on tag

### Implementation:
```javascript
// Pseudo-code logic
function updateDropdown(searchTerm, userHistory) {
  let candidates = optionList.filter(opt => 
    opt.toLowerCase().includes(searchTerm.toLowerCase())
  );
  
  let top4 = scoreAndSort(candidates, userHistory).slice(0, 4);
  let textMatches = candidates
    .filter(opt => !top4.includes(opt))
    .slice(0, 2);
  
  return [...top4, ...textMatches];
}
```

### Fields Using This:
- Thought disorders
- Perception types
- Affect types
- Mood types
- Involuntary Movements (subset)

---

## 6. Single Selection with Single Radio

Used when only ONE option can be selected (not multiple)

### Visual:
```
Option Set: ○ Option 1    ● Option 2    ○ Option 3
            └─────────────────────────────────────
                     (Selected: filled circle)
```

### Behavior:
- Choose one option
- Selecting a new option deselects the previous
- Cannot have multiple selections simultaneously
- Cannot deselect without selecting another

### Fields Using This:
- Clinical States (one state per visit)
- Medication Adherence (one level per visit)
- Consciousness (one state)
- Appearance (one state)
- Cooperativeness (binary)
- Rapport (one state)

---

## 7. Slider Rating Pattern

Used for numerical 1-10 scales

### Visual:
```
Question: How affected is the function?

[—●—————————————————————————————]
1  2  3  4  5  6  7  8  9  10

Value Display: [ 5 ]
               (updates as slider moves)

Legend:
1  = No impairment
10 = Severe impairment
```

### Implementation:
- Draggable slider thumb
- Shows numeric value on hover
- Display current value below
- Can also click number directly to set
- Range: 1-10 (integer only)

### Fields Using This:
- Functional Impairment (5 separate questions)
  1. Work/Academic functioning
  2. Social interactions
  3. Home relationships & responsibilities
  4. Self-care ability
  5. Leisure activities engagement

---

## 8. Locked/Immutable Field Pattern

Used for fields that cannot be edited in follow-up

### Visual:
```
Field Name: [Value] 🔒
            └─────────── Disabled/Grayed out styling
```

### Styling:
- Background color: Light gray
- Text color: Medium gray
- Cursor: Not-allowed
- Border: Optional, subtle
- Icon: Lock icon (🔒) optional

### User Intent:
- Display for reference
- Prevent accidental modification
- Still visible for context

### Fields Using This:
- Substance Name (follow-up)
- Substance Age of Onset (follow-up)

---

## 9. MSE Complete Flow Diagram

```
START: First Visit / Follow-up Visit
│
├─→ CONSCIOUSNESS (Required)
│   └─ Select: [ Clear ]  [ Drowsy ]  [ Fluctuating ]  [ Stupor ]  [ Coma ]
│
├─→ GENERAL APPEARANCE & BEHAVIOUR
│   ├─ Appearance: [ Normal ]  [ Over dressed ]  [ Unkempt ]
│   │
│   ├─→ Cooperativeness: [ Cooperative ]  [ Not Cooperative ]
│   │   │
│   │   ├─ IF "Not Cooperative" ────────────────────┐
│   │   │   └─ STOP MSE evaluation              │
│   │   │      (Except: Continue to Affect) ◄────────┤
│   │   │                                    │
│   │   └─ IF "Cooperative" ──────────────────┐      │
│   │       └─ Continue                    │      │
│   │                                    │      │
├─→ RAPPORT (Only if Cooperative)          │      │
│   └─ Select: [ Established ]  [ Not Est ]  [ Est w/ Diff ]
│       │                                 │      │
│       ├─ IF "Not Established" ──────────┼───────┤
│       │   └─ STOP MSE evaluation      │       │
│       │      (Except: Continue to     │       │
│       │       Affect) ◄───────────────┼───────┤
│       │                              │
│       └─ IF "Established" or         │
│           "Established w/ Diff" ────┘
│           │
│           └─ Continue
│
├─→ EYE CONTACT (Only if Rapport OK)
│   ├─ Achieved: [ Achieved ]  [ Not Achieved ]
│   └─ Sustained: [ Sustained ]  [ Not Sustained ]
│
├─→ PSYCHOMOTOR ACTIVITY
│   └─ Select: [ Normal ]  [ Decreased ]  [ Increased ]
│       │
│       └─ IF "Decreased" or "Increased" ──┐
│           │                             │
│           ├─ INVOLUNTARY MOVEMENTS ◄────┘
│           │   └─ Search dropdown
│           │       [ Tremors, Dystonia, Akathisia, ... ]
│           └─ (Can select multiple)
│
├─→ SPEECH (6 Dimensions)
│   ├─ Reaction Time: [ Normal ]  [ Decreased ]  [ Increased ]
│   ├─ Relevance: [ Relevant ]  [ Irrelevant ]
│   ├─ Coherence: [ Coherent ]  [ Incoherent ]
│   ├─ Intensity: [ Audible ]  [ Excessively Loud ]  [ Soft ]
│   ├─ Pitch: [ Monotonous ]  [ Normal fluctuation ]
│   └─ Ease: [ Spontaneous ]  [ Hesitant ]  [ Mute ]  [ Normal ]
│
├─→ THOUGHT
│   └─ Search dropdown (personalized)
│       └─ Select: Can select multiple thought disorders
│           └─ Display as tags [ Disorder 1 ]  [ Disorder 2 ]
│
├─→ PERCEPTION
│   └─ Search dropdown (personalized)
│       └─ Select: Can select multiple perception types
│           └─ Display as tags [ Type 1 ]  [ Type 2 ]
│
├─→ AFFECT (Always Present)  ◄─── Continues regardless of stopping points
│   ├─ Main Select: Search dropdown
│   │   └─ Display as tags [ Affect 1 ]  [ Affect 2 ]
│   │
│   └─ Affect Attributes (After main selection):
│       ├─ Reactivity: [ Present ]  [ Absent ]
│       ├─ Range: [ Normal ]  [ Restricted ]  [ Labile ]
│       ├─ Congruence: [ Congruent ]  [ Incongruent ]
│       └─ Appropriateness: [ Appropriate ]  [ Inappropriate ]
│
├─→ MOOD
│   └─ Search dropdown (personalized)
│       └─ Select: Can select multiple moods
│           └─ Display as tags [ Mood 1 ]  [ Mood 2 ]
│
├─→ INSIGHT
│   └─ Select: (Existing implementation, no changes)
│
END: Save MSE Data
```

---

## 10. Substance Use Flow - Follow-up Visit

```
START: Add Follow-up Visit
│
├─→ PREVIOUS SUBSTANCES
│   │
│   ├─ Substance #1
│   │   ├─ Name: [Locked: Alcohol] 🔒
│   │   ├─ Age of Onset: [Locked: 18] 🔒
│   │   ├─ Current Status: [ Option A ]  [ Option B ]  [ Option C ]
│   │   │
│   │   └─ IF "Currently Abstinent" ──────┐
│   │       │                            │
│   │       ├─ Pattern of Use: (HIDDEN) │
│   │       └─ Duration: [ ___ ] days ago
│   │                  └─ Show: "Since 30 days ago"
│   │
│   │   IF "Current Use" or other ──┐
│   │       │                      │
│   │       ├─ Pattern of Use: [ Freq ]
│   │       └─ Duration: [ ___ ] days ago
│   │
│   └─ [Remove Substance] [Edit]
│
├─→ ADD NEW SUBSTANCE (if doctor clicks)
│   │
│   ├─ Name: [ Input field - Editable ]
│   ├─ Age of Onset: [ Input field - Editable ]
│   ├─ Current Status: [ Options - Editable ]
│   │
│   └─ IF "Past Use" ──────────────┐
│       │                        │
│       ├─ Total Duration: [ ___ ] [ Months/Years ▼ ]
│       └─ Abstinent Since: [ ___ ] [ Months/Years ▼ ]
│
│   IF "Current Use" ──────────────┐
│       │                        │
│       ├─ Pattern of Use: [ Options ]
│       ├─ Frequency: [ Input ]
│       └─ Duration Using: [ ___ ] [ Days/Months/Years ▼ ]
│
END: Save Substance Data
```

---

## 11. Family History Flow - Follow-up Visit

```
START: Follow-up Visit
│
├─→ FAMILY HISTORY SECTION
│   │
│   ├─ Display: [Read-Only: "Present"]  [✎ edit]
│   │            ├─ Schizophrenia - First Degree
│   │            └─ Depression - Second Degree
│   │
│   └─ Consanguinity: [Read-Only: "Yes"]  [✎ edit]
│
│   (If user clicks pencil) ──→ EDIT DIALOG
│   │                            │
│   │                            ├─ ⚠️ Caution message
│   │                            ├─ Family History: 
│   │                            │   [ Yes ]  [ No ]  [ Unknown ]
│   │                            │   
│   │                            ├─ Items:
│   │                            │   [ Disorder ]  [ Degree ▼ ]
│   │                            │   [  Add Item... ]
│   │                            │
│   │                            ├─ Consanguinity:
│   │                            │   [ Yes ]  [ No ]  [ Unknown ]
│   │                            │
│   │                            ├─ [Cancel] [Save Changes]
│   │                            │
│   │                            └─ (Updates all visits)
│
END
```

---

## 12. Negative History Flow - Follow-up Visit

```
START: Follow-up Visit
│
├─→ NEGATIVE HISTORY SECTION
│   │
│   ├─ Display Positive Findings ONLY
│   │   ├─ H/o Head Injury: Yes (Moderate, 3 years ago) [✎ edit]
│   │   └─ H/o Seizures: Yes (Severe, 1 year ago) [✎ edit]
│   │   (No/Unknown findings hidden)
│   │
│   └─ (If user clicks pencil) → EDIT DIALOG
│       ├─ ⚠️ Caution message
│       ├─ Question: [ Yes ]  [ No ]  [ Unknown ]
│       │
│       └─ IF "Yes" ──────────┐
│           │                }
│           ├─ Severity: [ Mild ]  [ Moderate ]  [ Severe ]
│           ├─ Duration: [ ___ ] [ Unit ▼ ] ago
│           └─ Sequelae: [ Text field ]
│
END
```

---

## 13. Functional Impairment - Visual Layout

```
┌──────────────────────────────────────────┐
│  FUNCTIONAL IMPAIRMENT                   │
├──────────────────────────────────────────┤
│                                          │
│  Q1: How affected is work/academic      │
│      functioning?                        │
│  [—●—————————————————————————]            │
│   1  2  3  4  5  6  7  8  9  10          │
│  Current: [ 5 ] Previous: -              │
│                                          │
├──────────────────────────────────────────┤
│                                          │
│  Q2: How affected are social             │
│      interactions?                       │
│  [———●───────────────────────]           │
│   1  2  3  4  5  6  7  8  9  10          │
│  Current: [ 7 ] Previous: 6              │
│                                          │
├──────────────────────────────────────────┤
│  [Similar for Questions 3, 4, 5]         │
├──────────────────────────────────────────┤
│  Overall Impairment Score: 6.2           │
└──────────────────────────────────────────┘
```

---

## 14. Badge States & Styling

### Badge States:
```
Unselected Badge:
┌──────────────┐
│  Option A    │  ← Light background, normal text
└──────────────┘

Hovered Badge:
┌──────────────┐
│  Option A    │  ← Slightly darker, cursor: pointer
└──────────────┘

Selected Badge:
┌──────────────┐
│  Option A    │  ← Dark background, white text, BOLD
└──────────────┘

Disabled Badge:
┌──────────────┐
│  Option A    │  ← Gray background, gray text, strikethrough
└──────────────┘
```

### CSS Classes Needed:
- `.badge` - Base styling
- `.badge-unselected` - Default state
- `.badge-hover` - On hover
- `.badge-selected` - When selected
- `.badge-disabled` - When disabled

---

## Summary: When to Use Each Pattern

| Pattern | Use Case | Example |
|---------|----------|---------|
| **Badge Selection** | Quick single choice, few options | MSE Consciousness |
| **Conditional Display** | Show/hide based on parent selection | Involuntary movements if Psychomotor abnormal |
| **Read-Only + Edit** | Protected field, update all instances | Family History in follow-up |
| **Duration Input** | Time-based data | "Since 15 days ago" |
| **Search Dropdown** | Long list, personalized ordering | Thought disorders |
| **Single Radio** | Strict one-only selection | Clinical States |
| **Slider Rating** | 1-10 numerical scale | Functional Impairment |
| **Locked Field** | Display only, no editing | Substance name in follow-up |
| **Stop & Revert** | Conditional evaluation skip | MSE after Cooperativeness = Not |

