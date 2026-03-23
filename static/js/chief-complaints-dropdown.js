/**
 * Chief complaints Select2 — JSON: /static/data/chief_complaints.json
 *
 * Legacy: #chief_complaints syncs with first input[name="symptom_name[]"] in #symptoms-container.
 * First visit (master-detail): each row uses .cc-symptom-chief-select in #cc-symptom-details;
 * call window.initCcSymptomChiefSelect(selectElement, initialValue) after adding a row.
 */
(function () {
    var JSON_URL = (typeof window.CHIEF_COMPLAINTS_JSON_URL === 'string' && window.CHIEF_COMPLAINTS_JSON_URL)
        ? window.CHIEF_COMPLAINTS_JSON_URL
        : '/static/data/chief_complaints.json';

    var loadPromise = null;

    function loadChiefComplaintsData($) {
        if (window.chiefComplaintsData) {
            return $.Deferred().resolve(window.chiefComplaintsData).promise();
        }
        if (loadPromise) {
            return loadPromise;
        }
        loadPromise = $.getJSON(JSON_URL)
            .done(function (chiefComplaintsData) {
                window.chiefComplaintsData = chiefComplaintsData;
            })
            .fail(function () {
                loadPromise = null;
                console.warn('Chief complaints list failed to load:', JSON_URL);
            });
        return loadPromise;
    }

    function getFirstSymptomInput() {
        var c = document.getElementById('symptoms-container');
        if (!c) {
            return null;
        }
        var row = c.querySelector('.entry-wrapper');
        return row ? row.querySelector('input[name="symptom_name[]"]') : null;
    }

    function setSelectValue($el, v) {
        v = (v || '').trim();
        if (!v) {
            $el.val(null).trigger('change');
            return;
        }
        var found = false;
        $el.find('option').each(function () {
            if (this.value === v) {
                found = true;
            }
        });
        if (!found) {
            $el.append(new Option(v, v, true, true));
        }
        $el.val(v).trigger('change');
    }

    function syncSelectFromFirstInput($el) {
        if (!$el.data('chiefComplaintsInited')) {
            return;
        }
        var inp = getFirstSymptomInput();
        if (!inp) {
            return;
        }
        var v = (inp.value || '').trim();
        setSelectValue($el, v);
    }

    function syncFirstInputFromSelect($el) {
        var inp = getFirstSymptomInput();
        if (!inp) {
            return;
        }
        var v = $el.val();
        inp.value = v ? String(v) : '';
    }

    function initChiefComplaintsSelect($) {
        var $el = $('#chief_complaints');
        if (!$el.length || !$.fn.select2 || $el.data('chiefComplaintsInited')) {
            return;
        }
        loadChiefComplaintsData($)
            .done(function () {
                $el.select2({
                    data: window.chiefComplaintsData,
                    placeholder: 'Select Chief Complaint',
                    allowClear: true,
                    width: '100%',
                    tags: true,
                    createTag: function (params) {
                        var term = $.trim(params.term);
                        if (term === '') {
                            return null;
                        }
                        return { id: term, text: term };
                    }
                });
                $el.data('chiefComplaintsInited', true);

                $el.on('change', function () {
                    syncFirstInputFromSelect($el);
                });

                var $form = $el.closest('form');
                if ($form.length) {
                    $form.on('submit', function () {
                        syncFirstInputFromSelect($el);
                    });
                }

                var sc = document.getElementById('symptoms-container');
                if (sc) {
                    if (window.MutationObserver) {
                        var mo = new MutationObserver(function () {
                            syncSelectFromFirstInput($el);
                        });
                        mo.observe(sc, { childList: true, subtree: true });
                    }
                    sc.addEventListener('input', function (e) {
                        if (!e.target || !e.target.matches || !e.target.matches('input[name="symptom_name[]"]')) {
                            return;
                        }
                        var first = getFirstSymptomInput();
                        if (first && e.target === first) {
                            syncSelectFromFirstInput($el);
                        }
                    });
                }

                syncSelectFromFirstInput($el);
                window.setTimeout(function () { syncSelectFromFirstInput($el); }, 200);
                window.setTimeout(function () { syncSelectFromFirstInput($el); }, 600);
            });
    }

    /**
     * Init Select2 on one row select (first_visit master-detail). Updates left list via updateSymptomListItem.
     */
    window.initCcSymptomChiefSelect = function (selectEl, initialValue) {
        if (!selectEl || typeof window.jQuery === 'undefined' || !window.jQuery.fn.select2) {
            return;
        }
        var $ = window.jQuery;
        var $el = $(selectEl);
        if (!$el.length || $el.data('ccChiefInited')) {
            return;
        }
        loadChiefComplaintsData($)
            .done(function () {
                if (!$el.length || $el.data('ccChiefInited')) {
                    return;
                }
                $el.select2({
                    data: window.chiefComplaintsData,
                    placeholder: 'Select Chief Complaint',
                    allowClear: true,
                    width: '100%',
                    tags: true,
                    createTag: function (params) {
                        var term = $.trim(params.term);
                        if (term === '') {
                            return null;
                        }
                        return { id: term, text: term };
                    }
                });
                $el.data('ccChiefInited', true);

                var idx = parseInt($el.attr('data-cc-idx'), 10);
                if (isNaN(idx)) {
                    idx = -1;
                }

                function syncListLabel() {
                    if (typeof window.updateSymptomListItem !== 'function' || idx < 0) {
                        return;
                    }
                    var v = $el.val();
                    var data = $el.select2('data');
                    var text = (data && data[0] && data[0].text) ? String(data[0].text) : (v ? String(v) : '');
                    window.updateSymptomListItem(idx, text, null, null);
                }

                $el.on('change', function () {
                    syncListLabel();
                    if (typeof window.syncDurationRequired === 'function') {
                        window.syncDurationRequired();
                    }
                });

                var v0 = (initialValue != null && initialValue !== undefined) ? String(initialValue).trim() : '';
                if (v0) {
                    setSelectValue($el, v0);
                }
                syncListLabel();
            });
    };

    function boot() {
        if (typeof window.jQuery === 'undefined') {
            return;
        }
        loadChiefComplaintsData(window.jQuery);
        initChiefComplaintsSelect(window.jQuery);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
    window.setTimeout(boot, 80);
})();
