// ==========================================
// PSYCHIATRIC SCALES LOGIC
// ==========================================
const scalesLibrary = [
    {
        "scaleId": "CIWA-Ar",
        "scaleName": "Clinical Institute Withdrawal Assessment for Alcohol (CIWA-Ar)",
        "questions": [
            {"id": "q1", "text": "Nausea/Vomiting", "options": [{"value": 0, "label": "None"}, {"value": 1, "label": "Mild nausea with no vomiting"}, {"value": 2, "label": "2"}, {"value": 3, "label": "3"}, {"value": 4, "label": "Intermittent nausea"}, {"value": 5, "label": "5"}, {"value": 6, "label": "6"}, {"value": 7, "label": "Constant nausea, frequent dry heaves/vomiting"}]},
            {"id": "q2", "text": "Tremors - have patient extend arms & spread fingers", "options": [{"value": 0, "label": "No tremor"}, {"value": 1, "label": "Not visible, but can be felt"}, {"value": 2, "label": "2"}, {"value": 3, "label": "3"}, {"value": 4, "label": "Moderate, arms extended"}, {"value": 5, "label": "5"}, {"value": 6, "label": "6"}, {"value": 7, "label": "Severe, even arms not extended"}]},
            {"id": "q3", "text": "Anxiety", "options": [{"value": 0, "label": "No anxiety"}, {"value": 1, "label": "Mildly anxious"}, {"value": 2, "label": "2"}, {"value": 3, "label": "3"}, {"value": 4, "label": "Moderately anxious"}, {"value": 5, "label": "5"}, {"value": 6, "label": "6"}, {"value": 7, "label": "Equivalent to acute panic states"}]},
            {"id": "q4", "text": "Agitation", "options": [{"value": 0, "label": "Normal activity"}, {"value": 1, "label": "Somewhat normal"}, {"value": 2, "label": "2"}, {"value": 3, "label": "3"}, {"value": 4, "label": "Moderately fidgety/restless"}, {"value": 5, "label": "5"}, {"value": 6, "label": "6"}, {"value": 7, "label": "Paces back & forth, thrashes about"}]},
            {"id": "q5", "text": "Paroxysmal Sweats", "options": [{"value": 0, "label": "No sweats"}, {"value": 1, "label": "Barely perceptible, palms moist"}, {"value": 2, "label": "2"}, {"value": 3, "label": "3"}, {"value": 4, "label": "Beads of sweat on forehead"}, {"value": 5, "label": "5"}, {"value": 6, "label": "6"}, {"value": 7, "label": "Drenching sweats"}]},
            {"id": "q6", "text": "Orientation and clouding of sensorium", "options": [{"value": 0, "label": "Oriented"}, {"value": 1, "label": "Cannot do serial additions or uncertain date"}, {"value": 2, "label": "Disoriented to date by no more than 2 calendar days"}, {"value": 3, "label": "Disoriented to date by > 2 days"}, {"value": 4, "label": "Disoriented to place and/or person"}]},
            {"id": "q7", "text": "Tactile disturbances", "options": [{"value": 0, "label": "None"}, {"value": 1, "label": "Very mild itching, pins/needles"}, {"value": 2, "label": "Mild"}, {"value": 3, "label": "Moderate"}, {"value": 4, "label": "Moderate hallucinations"}, {"value": 5, "label": "Severe hallucinations"}, {"value": 6, "label": "Extremely severe hallucinations"}, {"value": 7, "label": "Continuous hallucinations"}]},
            {"id": "q8", "text": "Auditory Disturbances", "options": [{"value": 0, "label": "Not present"}, {"value": 1, "label": "Very mild harshness/startle"}, {"value": 2, "label": "Mild"}, {"value": 3, "label": "Moderate"}, {"value": 4, "label": "Moderate hallucinations"}, {"value": 5, "label": "Severe hallucinations"}, {"value": 6, "label": "Extremely severe hallucinations"}, {"value": 7, "label": "Continuous hallucinations"}]},
            {"id": "q9", "text": "Visual disturbances", "options": [{"value": 0, "label": "Not present"}, {"value": 1, "label": "Very mild sensitivity"}, {"value": 2, "label": "Mild"}, {"value": 3, "label": "Moderate"}, {"value": 4, "label": "Moderate hallucinations"}, {"value": 5, "label": "Severe hallucinations"}, {"value": 6, "label": "Extremely severe hallucinations"}, {"value": 7, "label": "Continuous hallucinations"}]},
            {"id": "q10", "text": "Headache", "options": [{"value": 0, "label": "Not present"}, {"value": 1, "label": "Very mild"}, {"value": 2, "label": "Mild"}, {"value": 3, "label": "Moderate"}, {"value": 4, "label": "Moderately severe"}, {"value": 5, "label": "Severe"}, {"value": 6, "label": "Very severe"}, {"value": 7, "label": "Extremely severe"}]}
        ],
        "interpretation": [
            {"min": 0, "max": 9, "label": "Absent or minimal withdrawal"},
            {"min": 10, "max": 19, "label": "Mild to moderate withdrawal"},
            {"min": 20, "max": 67, "label": "Severe withdrawal"}
        ]
    },
    {
        "scaleId": "Y-BOCS",
        "scaleName": "Yale Brown OCD Scale",
        "questions": [
            {"id": "q1", "text": "Time spent on obsessive thoughts?", "options": [{"value": 0, "label": "None"}, {"value": 1, "label": "0-1 hrs/day"}, {"value": 2, "label": "1-3 hrs/day"}, {"value": 3, "label": "3-8 hrs/day"}, {"value": 4, "label": "More than 8 hrs/day"}]},
            {"id": "q2", "text": "Interference from obsessive thoughts?", "options": [{"value": 0, "label": "None"}, {"value": 1, "label": "Mild"}, {"value": 2, "label": "Definite but manageable"}, {"value": 3, "label": "Substantial interference"}, {"value": 4, "label": "Severe"}]},
            {"id": "q3", "text": "Distress from obsessive thoughts?", "options": [{"value": 0, "label": "None"}, {"value": 1, "label": "Little"}, {"value": 2, "label": "Moderate but manageable"}, {"value": 3, "label": "Severe"}, {"value": 4, "label": "Nearly constant, Disabling"}]},
            {"id": "q4", "text": "Resistance to obsessions?", "options": [{"value": 0, "label": "Always try"}, {"value": 1, "label": "Try much of the time"}, {"value": 2, "label": "Try some of the time"}, {"value": 3, "label": "Rarely try. Often yield"}, {"value": 4, "label": "Never try. Completely yield"}]},
            {"id": "q5", "text": "Control over obsessive thoughts?", "options": [{"value": 0, "label": "Complete control"}, {"value": 1, "label": "Much control"}, {"value": 2, "label": "Some control"}, {"value": 3, "label": "Little control"}, {"value": 4, "label": "No control"}]},
            {"id": "q6", "text": "Time spent on compulsions?", "options": [{"value": 0, "label": "None"}, {"value": 1, "label": "0-1 hrs/day"}, {"value": 2, "label": "1-3 hrs/day"}, {"value": 3, "label": "3-8 hrs/day"}, {"value": 4, "label": "More than 8 hrs/day"}]},
            {"id": "q7", "text": "Interference from compulsions?", "options": [{"value": 0, "label": "None"}, {"value": 1, "label": "Mild"}, {"value": 2, "label": "Definite but manageable"}, {"value": 3, "label": "Substantial interference"}, {"value": 4, "label": "Severe"}]},
            {"id": "q8", "text": "Anxiety if compulsions prevented?", "options": [{"value": 0, "label": "None"}, {"value": 1, "label": "Little"}, {"value": 2, "label": "Moderate but manageable"}, {"value": 3, "label": "Severe"}, {"value": 4, "label": "Nearly constant, Disabling"}]},
            {"id": "q9", "text": "Resistance to compulsions?", "options": [{"value": 0, "label": "Always try"}, {"value": 1, "label": "Try much of the time"}, {"value": 2, "label": "Try some of the time"}, {"value": 3, "label": "Rarely try. Often yield"}, {"value": 4, "label": "Never try. Completely yield"}]},
            {"id": "q10", "text": "Control over compulsions?", "options": [{"value": 0, "label": "Complete control"}, {"value": 1, "label": "Much control"}, {"value": 2, "label": "Some control"}, {"value": 3, "label": "Little control"}, {"value": 4, "label": "No control"}]}
        ],
        "interpretation": [
            {"min": 0, "max": 7, "label": "Subclinical"},
            {"min": 8, "max": 15, "label": "Mild OCD"},
            {"min": 16, "max": 23, "label": "Moderate OCD"},
            {"min": 24, "max": 31, "label": "Severe OCD"},
            {"min": 32, "max": 40, "label": "Extreme OCD"}
        ]
    },
    {
        "scaleId": "whodas2",
        "scaleName": "WHODAS 2.0 (36-item)",
        "questions": [
            {"id":"D1.1","text":"Concentrating on doing something for ten minutes?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D1.2","text":"Remembering to do important things?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D1.3","text":"Analyzing and finding solutions to problems in day-to-day life?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D1.4","text":"Learning a new task, for example, learning how to get to a new place?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D1.5","text":"Generally understanding what people say?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D1.6","text":"Starting and maintaining a conversation?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D2.1","text":"Standing for long periods, such as 30 minutes?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D2.2","text":"Standing up from sitting down?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D2.3","text":"Moving around inside your home?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D2.4","text":"Getting out of your home?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D2.5","text":"Walking a long distance, such as a kilometer (or equivalent)?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D3.1","text":"Washing your whole body?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D3.2","text":"Getting dressed?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D3.3","text":"Eating?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D3.4","text":"Staying by yourself for a few days?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D4.1","text":"Dealing with people you do not know?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D4.2","text":"Maintaining a friendship?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D4.3","text":"Getting along with people who are close to you?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D4.4","text":"Making new friends?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D4.5","text":"Sexual activities?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D5.1","text":"Taking care of your household responsibilities?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D5.2","text":"Doing most important household tasks well?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D5.3","text":"Getting all of the household work done that you needed to do?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D5.4","text":"Getting your household work done as quickly as needed?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D5.5","text":"Your day-to-day work/school?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D5.6","text":"Doing your most important work/school tasks well?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D5.7","text":"Getting all of the work done that you need to do?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D5.8","text":"Getting your work done as quickly as needed?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D6.1","text":"How much of a problem did you have in joining in community activities in the same way as anyone else can?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D6.2","text":"How much of a problem did you have because of barriers or hindrances around you?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D6.3","text":"How much of a problem did you have living with dignity because of the attitudes and actions of others?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D6.4","text":"How much time did you spend on your health condition or its consequences?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D6.5","text":"How much have you been emotionally affected by your health condition?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D6.6","text":"How much has your health been a drain on the financial resources of you or your family?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D6.7","text":"How much of a problem did your family have because of your health problems?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]},
            {"id":"D6.8","text":"How much of a problem did you have in doing things by yourself for relaxation or pleasure?","options":[{"value":1,"label":"None"},{"value":2,"label":"Mild"},{"value":3,"label":"Moderate"},{"value":4,"label":"Severe"},{"value":5,"label":"Extreme / Cannot do"}]}
        ],
        "interpretation": [
            {"min": 0, "max": 53, "label": "None"},
            {"min": 54, "max": 89, "label": "Mild"},
            {"min": 90, "max": 125, "label": "Moderate"},
            {"min": 126, "max": 161, "label": "Severe"},
            {"min": 162, "max": 180, "label": "Extreme"}
        ]
    }
];

let appliedScales = {};
let currentActiveScale = null;
let currentScaleReadOnly = false;

window.addEventListener('load', () => {
    const hiddenData = document.getElementById('scales_data');
    if (hiddenData && hiddenData.value && hiddenData.value !== '[]') {
        try {
            const parsed = JSON.parse(hiddenData.value);
            parsed.forEach(s => appliedScales[s.scale_id] = s);
            updateScalesBadge();
            renderCompletedScalesCards();
        } catch (e) {}
    } else {
        renderCompletedScalesCards();
    }
});

function openScalesModal() {
    document.getElementById('scalesModal').style.display = 'block';
    showScalesList();
    renderScalesList(scalesLibrary);
}

function openNewAssessmentModal() {
    const backBtn = document.getElementById('scale-modal-back-btn');
    if (backBtn) backBtn.style.display = 'inline-flex';
    const saveBtn = document.getElementById('scale-save-btn');
    if (saveBtn) saveBtn.style.display = 'block';
    openScalesModal();
}

function showScalesList() {
    document.getElementById('scale-assessment-view').style.display = 'none';
    document.getElementById('scales-list-view').style.display = 'flex';
}

function renderScalesList(scalesToRender) {
    const listDiv = document.getElementById('available-scales-list');
    listDiv.innerHTML = '';
    scalesToRender.forEach(scale => {
        const isApplied = appliedScales[scale.scaleId] ? '✅ (Applied)' : '';
        const html = '<div style="padding: 12px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center;"><div><strong style="color: #444;">' + scale.scaleName + '</strong> <span style="color: green; font-size: 12px;">' + isApplied + '</span></div><button type="button" class="btn" style="margin:0; padding: 6px 12px; font-size: 12px; background: #a5dcfe; color: #333;" onclick="openScaleAssessment(\'' + scale.scaleId + '\')">Assess</button></div>';
        listDiv.insertAdjacentHTML('beforeend', html);
    });
}

function filterScales(recommendedVal = '') {
    const searchVal = document.getElementById('scale-search').value.toLowerCase();
    const dropdownVal = recommendedVal || document.getElementById('scale-recommended').value;
    const filtered = scalesLibrary.filter(s => {
        const matchesSearch = s.scaleName.toLowerCase().includes(searchVal);
        const matchesDropdown = dropdownVal === '' || s.scaleId === dropdownVal;
        return matchesSearch && matchesDropdown;
    });
    renderScalesList(filtered);
}

function openScaleAssessment(scaleId, readOnly = false) {
    currentActiveScale = scalesLibrary.find(s => s.scaleId === scaleId);
    currentScaleReadOnly = !!readOnly;
    document.getElementById('scales-list-view').style.display = 'none';
    document.getElementById('scale-assessment-view').style.display = 'flex';
    document.getElementById('active-scale-title').innerText = currentActiveScale.scaleName;
    const backBtn = document.getElementById('scale-modal-back-btn');
    if (backBtn) backBtn.style.display = readOnly ? 'none' : 'inline-flex';
    const saveBtn = document.getElementById('scale-save-btn');
    if (saveBtn) saveBtn.style.display = readOnly ? 'none' : 'block';
    const form = document.getElementById('active-scale-form');
    form.innerHTML = '';
    const prevAnswers = appliedScales[scaleId] ? appliedScales[scaleId].raw_responses : {};
    currentActiveScale.questions.forEach((q, idx) => {
        let optionsHtml = '';
        q.options.forEach(opt => {
            const isChecked = prevAnswers[q.id] == opt.value ? 'checked' : '';
            const dis = readOnly ? 'disabled' : '';
            const chg = readOnly ? '' : 'onchange="calculateLiveScore()"';
            optionsHtml += '<label style="display: block; margin-bottom: 5px; cursor: pointer;"><input type="radio" name="' + q.id + '" value="' + opt.value + '" ' + isChecked + ' ' + dis + ' ' + chg + '> <span style="margin-left: 8px;">' + opt.value + ' - ' + opt.label + '</span></label>';
        });
        form.insertAdjacentHTML('beforeend', '<div style="background: #fdfdfd; padding: 15px; margin-bottom: 10px; border-radius: 6px; border: 1px solid #e0e0e0;"><strong style="display: block; margin-bottom: 10px;">' + (idx + 1) + '. ' + q.text + '</strong>' + optionsHtml + '</div>');
    });
    calculateLiveScore();
}

function openScaleDetails(scaleId, patientData) {
    const backBtn = document.getElementById('scale-modal-back-btn');
    if (backBtn) backBtn.style.display = 'none';
    document.getElementById('scalesModal').style.display = 'block';
    openScaleAssessment(scaleId, true);
}

function calculateLiveScore() {
    if (!currentActiveScale) return;
    const container = document.getElementById('active-scale-form');
    let totalScore = 0;

    // Find all checked radio buttons inside our div
    const checkedInputs = container.querySelectorAll('input[type="radio"]:checked');
    checkedInputs.forEach(input => {
        totalScore += parseInt(input.value);
    });

    document.getElementById('scale-live-score').innerText = totalScore;
    let severity = "Score out of bounds";
    for (let band of currentActiveScale.interpretation) {
        if (totalScore >= band.min && totalScore <= band.max) {
            severity = band.label;
            break;
        }
    }
    document.getElementById('scale-live-severity').innerText = severity;
}

function saveActiveScale() {
    const container = document.getElementById('active-scale-form');
    let rawResponses = {};

    // Save only the checked values
    const checkedInputs = container.querySelectorAll('input[type="radio"]:checked');
    checkedInputs.forEach(input => {
        rawResponses[input.name] = parseInt(input.value);
    });

    const totalScore = parseInt(document.getElementById('scale-live-score').innerText);
    const severityLabel = document.getElementById('scale-live-severity').innerText;
    appliedScales[currentActiveScale.scaleId] = {
        scale_id: currentActiveScale.scaleId,
        scale_name: currentActiveScale.scaleName,
        total_score: totalScore,
        severity_label: severityLabel,
        raw_responses: rawResponses,
        administered_on: new Date().toISOString()
    };
    document.getElementById('scales_data').value = JSON.stringify(Object.values(appliedScales));
    updateScalesBadge();
    renderCompletedScalesCards();
    showScalesList();
    renderScalesList(scalesLibrary);
}

function updateScalesBadge() {
    const badge = document.getElementById('scales-count-badge');
    if (!badge) return;
    const count = Object.keys(appliedScales).length;
    if (count > 0) {
        badge.innerText = count + ' Applied';
        badge.style.display = 'inline-block';
    } else {
        badge.style.display = 'none';
    }
}

function severityClass(label) {
    const v = String(label || '').toLowerCase();
    if (v.includes('extreme')) return 'severity-extreme';
    if (v.includes('severe')) return 'severity-severe';
    if (v.includes('moderate')) return 'severity-moderate';
    return 'severity-mild';
}

function formatAdminDate(isoStr) {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return '';
    return d.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' });
}

function getScaleMax(scaleId) {
    const scale = scalesLibrary.find(s => s.scaleId === scaleId);
    if (!scale || !scale.questions) return 0;
    return scale.questions.length * 5;
}

function renderCompletedScalesCards() {
    const container = document.getElementById('completed-scales-list');
    if (!container) return;
    const items = Object.values(appliedScales);
    if (!items.length) {
        container.innerHTML = '<div class="scale-card"><div class="scale-left"><div class="scale-icon"><span class="material-symbols-outlined">assignment</span></div><div class="scale-info"><h4>No assessments yet</h4><p>Click + New Assessment to add a clinical scale.</p></div></div></div>';
        return;
    }
    container.innerHTML = '';
    items.forEach(function(s) {
        const max = getScaleMax(s.scale_id);
        const dateTxt = formatAdminDate(s.administered_on);
        const sevClass = severityClass(s.severity_label);
        const html = '<div class="scale-card">' +
            '<div class="scale-left">' +
                '<div class="scale-icon"><span class="material-symbols-outlined">assignment</span></div>' +
                '<div class="scale-info">' +
                    '<h4>' + (s.scale_name || s.scale_id) + '</h4>' +
                    '<p>' + (dateTxt ? ('Administered on ' + dateTxt) : 'Assessment recorded') + '</p>' +
                '</div>' +
            '</div>' +
            '<div class="scale-right">' +
                '<span class="severity-badge ' + sevClass + '">Severity: ' + (s.severity_label || '-') + '</span>' +
                '<span class="scale-score">' + (s.total_score || 0) + ' / ' + (max || '-') + '</span>' +
                '<button type="button" class="btn-outline" onclick="openScaleDetails(\'' + s.scale_id + '\', null)">Details</button>' +
            '</div>' +
        '</div>';
        container.insertAdjacentHTML('beforeend', html);
    });
}