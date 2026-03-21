(function () {
    const mseData = {
        Thought: [
            'Flight of ideas', 'Prolixity', 'Poverty of thought', 'Pressured Speech',
            'Circumstantiality', 'Tangentiality', 'Inhibition or Slowing of Thinking',
            'Perseveration', 'Thought echo', 'Desultory thinking', 'Transitory thinking',
            'Drivelling thinking', 'Substitution', 'Omission', 'Fusion', 'Thought block',
            'Loosening of associations', 'Derailment of thought', 'Incoherence / word salad',
            'Neologisms', 'Clang associations', 'Punning', 'Increased self esteem',
            'Illogical thinking', 'Verbigeration', 'Echolalia', 'Thought insertion',
            'Thought withdrawal', 'Thought broadcasting', 'Influenced thinking',
            'Obsessive thinking', 'Made impulses (passivity of impulses)',
            'Made acts (passivity of actions)', 'Delusional perception', 'Delusional Mood',
            'Somatic passivity', 'Over‑valued ideas', 'Preoccupations', 'Ruminations',
            'Suicidal ideation', 'Homicidal ideation',
            'Over‑valued cultural or religious beliefs (non‑psychotic)',
            'Guilty ideas of reference (non‑psychotic)', 'Obsessions', 'Delusions of reference',
            'Delusions of Persecution', 'Delusions of infidelity',
            'Delusions of love / erotomanic delusions', 'Delusions of Grandiosity',
            'Nihilistic delusions', 'Hypochondriacal / somatic delusions', 'Shared Delusions',
            'Delusional parasitosis', 'Delusions of bodily change or dysmorphia',
            'Delusions of control', 'Delusions of passivity',
            'Delusions of doubles (Capgras‑like misidentification)',
            'Delusional misidentification of place or time', 'Delusions of guilt and sin',
            'Delusions of possession by spirits or deities (culturally shaped)',
            'Bizarre Delusions', 'Delusional Dysmorphophobia', 'Magical thinking',
            'Paranoid ideation', 'Excessive guilt ideas', 'Ideas of worthlessness',
            'Ideas of hopelessness', 'Ideas of helplessness', 'Obsessions of contamination',
            'Obsessive pathological doubts', 'Obsessions of symmetry', 'Obsessions of exactness',
            'Obsessive moral or religious scruples', 'Obsessive aggressive impulses',
            'Obsessive sexual thoughts', 'Obsessive blasphemous thoughts',
            'Intrusive images without overt compulsions', 'Intrusive impulses without overt compulsions',
            'Compulsive checking behaviors (behavior)', 'Compulsive washing and cleaning (behavior)',
            'Compulsive counting or ordering (behavior)', 'Obsessive ruminations about relationships',
            'Obsessive ruminations about past mistakes', 'Obsessive ruminations',
            'Passive suicidal ideation (wish to die)', 'Active suicidal ideation with plan',
            'Recurrent suicidal ideas despite treatment', 'Homicidal thoughts towards specific individuals',
            'Homicidal ideas in context of persecutory delusions', 'Knight’s move thinking',
            'Overinclusion', 'Loss of goal', 'Poverty of content of speech', 'Delusion of jealousy',
            'Delusion of poverty', 'Delusion of ruin', 'Delusion of thought control',
        ],
        Perception: [
            'Auditory Hallucination', 'Elementary auditory hallucinations (non‑verbal sounds)',
            '1st Person Auditory Hallucination (Thought echo)', '2nd Person Auditory Hallucination',
            '3rd Person Auditory Hallucination (commentary)',
            '3rd Person Auditory Hallucination (running commentary/conversing voices)',
            'Visual Hallucinations', 'Delusional perception',
            'Macropsia / micropsia‑type hallucinatory distortions',
            'Formication (sensation of insects crawling on skin)',
            'Thermal hallucinations (hot or cold sensations without stimulus)',
            'Olfactory Hallucinations', 'Gustatory Hallucinations', 'Tactile Hallucinations',
            'Pain & Deep Sensation Hallucinations', 'Superficial Touch Hallucinations',
            'Kinesthetic Touch Hallucinations', 'Visceral Touch Hallucinations',
            'Alcoholic Halucinosis', 'Organic Hallucinations', 'Functional Hallucinations',
            'Reflex Hallucinations', 'Extracampine Hallucinations', 'Autoscopy',
            'Hypnagogic auditory hallucinations (on falling asleep)',
            'Hypnopompic auditory hallucinations (on waking)',
            'Experimental & Pandramic hallucinations', 'Pendular Hallucinations',
            'Broddignagian & Liliputian Hallucinations', 'Musical Hallucinations',
            'Induced Hallucinations', 'Visceral hallucinations (abnormal experiences of internal organs)',
            'Experiences of electric currents passing through body', 'Negative hallucinations',
            'Pseudo Hallucinations', 'Passage Hallucinations', 'Hallucinations of presence',
            'Illusions of misrecognition in low light', 'Affect‑laden illusions',
            'Completion illusions', 'Pareidolic illusions', 'Inattention illusions',
            'Derealization', 'Depersonalization', 'Altered sense of time passage',
            'Metamorphopsias', 'Passivity Experiences',
        ],
        Affect: [
            'Appropriate', 'Inappropriate', 'Blunted', 'Restricted', 'Flat', 'Labile',
        ],
    };

    function optionValueExists(selectEl, value) {
        const opts = selectEl.querySelectorAll('option');
        for (let i = 0; i < opts.length; i++) {
            if (opts[i].value === value) return true;
        }
        return false;
    }

    function initMSEDropdowns() {
        if (typeof window.jQuery === 'undefined' || !window.jQuery.fn || !window.jQuery.fn.select2) {
            return;
        }
        const $ = window.jQuery;
        $('.mse-finding-select:not(.select2-hidden-accessible)').each(function () {
            const selectElement = $(this);
            const category = selectElement.attr('data-category');
            const native = selectElement[0];

            if (mseData[category]) {
                if (selectElement.find('option[value=""]').length === 0) {
                    selectElement.prepend('<option value=""></option>');
                }

                mseData[category].forEach(function (finding) {
                    if (!optionValueExists(native, finding)) {
                        selectElement.append(new Option(finding, finding, false, false));
                    }
                });
            }

            selectElement.select2({
                tags: true,
                placeholder: 'Select or type ' + category + ' finding...',
                allowClear: true,
                width: '100%',
            });

            selectElement.next('.select2-container').css('flex', '1.5');
        });
    }

    window.initMSEDropdowns = initMSEDropdowns;

    window.jQuery(function () {
        initMSEDropdowns();
    });
})();
