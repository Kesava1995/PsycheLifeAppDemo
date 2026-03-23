# PsycheLife - Quick Reference Summary

**File:** REORGANIZED_REQUIREMENTS.md for full details

---

## At-a-Glance Feature Matrix

| Feature | First Visit | Follow-up | Key Change |
|---------|-------------|-----------|-----------|
| **Historical Data Display** | N/A | ✅ Show in badges | New: Light font in brackets |
| **Type of Follow-up** | ❌ No | ✅ Yes | Available immediately after registration |
| **Substance - Name/Age of Onset** | ✅ Edit | 🔒 Lock | Immutable after first visit |
| **Substance - Current Status** | ✅ Edit | ✅ Edit | Fully editable |
| **Substance - Pattern of Use** | ✅ Full options | ⚠️ Limited | Conditional on status; no "Past Use" |
| **Substance - Duration Format** | Days/Months/Years | "Since X days" | New format: blank field + "since" prefix |
| **New Substance in Follow-up** | N/A | ✅ Like First Visit | Full editable if adding NEW entry |
| **Family History** | ✅ Edit | 🔍 Edit Icon | Read-only, pencil icon for edits |
| **Family History - Degree of Relative** | ✅ Dropdown | 🔍 Edit Icon | First/Second/Third degree options |
| **Consanguinity** | ✅ Yes/No/Unknown | 🔍 Edit Icon | Under Family History section |
| **Dev Milestone Delay** | ✅ Edit | 🔍 Edit Icon | Read-only, pencil icon like Family History |
| **Medication Adherence** | ✅ Select | ✅ Select | Renamed from "Manage Adherence ranges" |
| **Adherence - Single Selection** | ➖ N/A | ✅ Yes | Only one option at a time |
| **Adherence - Non-Good Status** | ➖ N/A | "Since" format | Number + Unit dropdown + "Since" prefix |
| **Clinical States** | ✅ Input | ✅ Input | Single entry only (radio, not checkboxes) |
| **MSE - Consciousness** | Badges | Badges | All options on one line |
| **MSE - Cooperativeness** | Badges | Badges | Not Cooperative → STOP MSE (except Affect) |
| **MSE - Rapport** | Badges | Badges | Not Established → STOP MSE (except Affect) |
| **MSE - Eye Contact** | Achieved + Sustained | Achieved + Sustained | Two independent badge sets |
| **MSE - Psychomotor** | Badges | Badges | If abnormal → show Involuntary Movements |
| **MSE - Involuntary Movements** | Search dropdown | Search dropdown | Tremors, Dystonia, Akathisia, etc. |
| **MSE - Speech** | 6 dimensions | 6 dimensions | Reaction, Relevance, Coherence, Intensity, Pitch, Ease |
| **MSE - Thought** | Dropdown | Dropdown | ✨ NEW: Search + smart dropdown |
| **MSE - Perception** | Dropdown | Dropdown | ✨ NEW: Search + smart dropdown |
| **MSE - Affect** | Dropdown | Dropdown | ✨ NEW: Search + Reactivity/Range/Congruence/Appropriateness badges |
| **MSE - Mood** | Dropdown | Dropdown | ✨ NEW: Search + smart dropdown |
| **MSE - Insight** | As-is | As-is | No changes |
| **Negative History Tab** | ✅ Full form | 🔍 Edit Icon | NEW TAB: 11 base + age/alcohol specific questions |
| **Functional Impairment Tab** | ✅ 5 sliders | ✅ 5 sliders | NEW TAB: 1-10 rating for 5 domains |

---

## Key Behavioral Rules

### Substance Use
```
First Visit:
  - All fields editable
  - Pattern of Use: includes "Past Use"
  - Duration: Days/Months/Years dropdowns

Follow-up - Existing Substance:
  - Name & Age of Onset: 🔒 LOCKED (read-only)
  - Current Status: ✏️ Editable
  - Pattern of Use: ✏️ Limited (conditional on status)
    - If "Currently Abstinent": Hide Pattern, Show "Since X days"
    - If "Current Use": Show Pattern + "Since X days"
  - Duration: "Since X days ago" format
  - NO "Past Use" option in follow-up

Follow-up - NEW Substance:
  - Same as First Visit (all fields editable)
```

### Duration Entry Formats

**First Visit (Past Use):**
```
Total Duration: [___] [Months ▼] or [Years ▼]
Abstinent Since: [___] [Months ▼] or [Years ▼]
```

**Follow-up Visits:**
```
Since: [___] [Days ▼] or [Weeks ▼] or [Months ▼]
```

### MSE Conditional Flow

```
START
  ↓
Consciousness: [Select badge]
  ↓
Appearance: [Select badge]
  ↓
Cooperativeness: [Coop/Not Coop]
  ├─ NOT COOP → STOP (except Affect)
  └─ COOP
      ↓
      Rapport: [Est/Not Est/Est w/ Diff]
      ├─ NOT EST → STOP (except Affect)
      └─ EST or EST w/ DIFF
          ↓
          Eye Contact, Psychomotor, Speech, Thought, Perception
          ↓
Affect: [Always present, with Reactivity/Range/Congruence badges]
  ↓
Mood: [Select badge]
  ↓
Insight: [As-is]
END
```

### Read-Only with Edit Pattern (Follow-up)

**Applies to:**
- Family History
- Developmental Milestone Delay
- Negative History (positive findings only)

**UI Pattern:**
```
Field Name: [Read-only value] [pencil icon]
  ↓ [click pencil]
Modal Dialog Opens:
  - "⚠️ Changing these values will affect all previous and future dates"
  - Show editable fields
  - [Cancel] [Save Changes]
  ↓
Update reflects everywhere (all visits)
```

### Smart Dropdown Priority

**Always shows 6 options:**

Top 4: Personalized weighted score (user's frequency + recency)
```
Score = Σ(1/(1+days_since_use)) + Recent_Bonus
```

Last 2: Text match relevance only (based on search input)

**No duplicates:** Same option never appears twice

---

## Field Status Reference

### Locked in Follow-up (Read-only)
- Substance Name
- Substance Age of Onset
- Family History (without edit icon)
- Developmental Milestone (without edit icon)

### Editable in Follow-up
- Substance Current Status
- Substance Pattern of Use (conditional)
- Substance Duration (new format)
- Any "Yes" findings in Negative History (via edit icon)
- Medication Adherence
- Clinical State
- MSE fields (all)
- Functional Impairment sliders

### Conditional Display
- Involuntary Movements (if psychomotor abnormal)
- Pattern of Use (if not "Currently Abstinent")
- Substance details (if adding NEW in follow-up)
- Negative History detail fields (if "Yes" selected)
- Age-specific Negative History (if age >= 60)
- Alcohol-specific Negative History (if Alcohol selected)

---

## New/Renamed Elements

### New Tabs
1. **Negative History** - After "Symptoms"
2. **Functional Impairment** - After "Negative Symptoms"

### Renamed Fields
1. "Manage Adherence ranges" → **"Medication Adherence"**

### New Patterns
1. Smart search dropdowns (Thought, Perception, Affect, Mood, Involuntary Movements)
2. Pencil icon edit pattern
3. "Since X days" duration format
4. Badge selections for MSE
5. Conditional MSE stopping points

---

## Database Considerations

### Track for Smart Dropdown
```
Table: field_usage_tracking
- user_id (doctor_id)
- field_name (e.g., "perception")
- selected_option (e.g., "Auditory Hallucination")
- selection_date
- selection_time
```

### New Fields to Add
- Functional Impairment questions (5 fields for ratings)
- Negative History responses
- Degree of Relative (for Family History)
- Consanguinity field
- Edit history markers (for pencil icon changes)

---

## Priority Implementation Order

**Phase 1 (Core Substance Changes):**
1. Substance Name/Age of Onset locking
2. Substance duration "Since" format
3. Remove "Past Use" from follow-up

**Phase 2 (Data Display & Flow):**
1. Historical data badges
2. Read-only patterns with pencil icons
3. Type of follow-up availability

**Phase 3 (New Tabs):**
1. Negative History tab implementation
2. Functional Impairment tab implementation

**Phase 4 (MSE Restructuring):**
1. Badge selections for conscious/appearance/cooperativeness/rapport/eye contact
2. Conditional display logic (stop points)
3. Speech dimension restructuring

**Phase 5 (Smart Features):**
1. Search dropdowns with smart prioritization
2. Medication Adherence restructuring
3. Clinical States single selection

---

## Testing Checklist (High Priority)

- [ ] MSE Rapport "Not Established" → skips to Affect only
- [ ] MSE Cooperativeness "Not Cooperative" → skips to Affect only
- [ ] Substance locked fields not editable in follow-up
- [ ] New substance in follow-up = fully editable
- [ ] "Currently Abstinent" hides "Pattern of Use"
- [ ] Pencil icon edits update all instances
- [ ] Smart dropdown shows 6 options, no duplicates
- [ ] Involuntary Movements only shows when psychomotor abnormal
- [ ] Negative History "Yes" expands to Severity/Duration/Sequelae
- [ ] Alcohol selection triggers alcohol-related Negative History questions
- [ ] Age >= 60 triggers progressive memory/decline questions
- [ ] Only one Medication Adherence option selectable
- [ ] Only one Clinical State selectable

---

## Key Notes for Implementation

1. **Date Calculations:** All "since X days" must reference Visit.entry_date
2. **Non-editable Display:** Use different styling/disabled input for locked fields
3. **Pencil Icon:** Should open modal/dialog for major changes
4. **Caution Messages:** Include explicit warning about cross-visit updates
5. **Backward Compatibility:** Map old date ranges to new "since" format if needed
6. **User Feedback:** Show count in Negative History "Yes" selections (e.g., "3 findings")

