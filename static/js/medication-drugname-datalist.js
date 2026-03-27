// Attach Select2 single-select+tags to medication drug-name inputs.
// Keeps custom entry support and existing taper behavior unchanged.
(function () {
    function getUniqueMedicationList() {
        var meds = Array.isArray(window.PSYCHIATRIC_MEDICATIONS) ? window.PSYCHIATRIC_MEDICATIONS : [];
        var seen = Object.create(null);
        return meds.map(function (name) { return String(name || '').trim(); })
            .filter(function (v) {
                if (!v) return false;
                var k = v.toLowerCase();
                if (seen[k]) return false;
                seen[k] = true;
                return true;
            });
    }

    function escapeHtml(text) {
        return String(text || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function initSelect2ForElement(el) {
        if (!el || el.dataset.medDrugDropdownApplied === '1') return;
        if (el.tagName && el.tagName.toLowerCase() === 'select') return;
        if (el.readOnly || el.disabled) return;
        if (!(window.jQuery && window.jQuery.fn && window.jQuery.fn.select2)) return;

        var meds = getUniqueMedicationList();
        var currentValue = String(el.value || '').trim();
        var select = document.createElement('select');
        select.name = el.name || 'drug_name[]';
        select.className = el.className + ' drug-name-select2-native';
        select.style.width = '100%';
        select.setAttribute('data-placeholder', el.getAttribute('placeholder') || 'Drug Name');

        var optionsHtml = ['<option value=""></option>'];
        meds.forEach(function (name) {
            optionsHtml.push('<option value="' + escapeHtml(name) + '">' + escapeHtml(name) + '</option>');
        });
        if (currentValue && !meds.some(function (m) { return m.toLowerCase() === currentValue.toLowerCase(); })) {
            optionsHtml.push('<option value="' + escapeHtml(currentValue) + '">' + escapeHtml(currentValue) + '</option>');
        }
        select.innerHTML = optionsHtml.join('');

        el.parentNode.replaceChild(select, el);
        var wrap = select.closest('.drug-name-wrap');
        if (wrap) wrap.classList.add('has-select2');

        var $ = window.jQuery;
        var $sel = $(select);
        $sel.select2({
            width: '100%',
            tags: true,
            multiple: false,
            allowClear: true,
            placeholder: select.getAttribute('data-placeholder') || 'Drug Name',
            closeOnSelect: true,
            dropdownAutoWidth: false
        });

        if (currentValue) {
            $sel.val(currentValue).trigger('change');
        }

        $sel.on('change', function () {
            var block = select.closest('.med-entry-block');
            if (typeof window.syncMedFollowIdentity === 'function' && block) {
                try { window.syncMedFollowIdentity(block); } catch (e) {}
            }
        });

        select.dataset.medDrugDropdownApplied = '1';
    }

    function initAll() {
        var inputs = document.querySelectorAll('input.drug-name-input[name="drug_name[]"]');
        inputs.forEach(initSelect2ForElement);
    }

    function observeNewRows() {
        if (typeof MutationObserver === 'undefined') return;
        var observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (m) {
                m.addedNodes.forEach(function (node) {
                    if (!node || node.nodeType !== 1) return;
                    if (node.matches && node.matches('input.drug-name-input[name="drug_name[]"]')) {
                        initSelect2ForElement(node);
                        return;
                    }
                    if (node.querySelectorAll) {
                        node.querySelectorAll('input.drug-name-input[name="drug_name[]"]').forEach(initSelect2ForElement);
                    }
                });
            });
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }

    window.initMedicationDrugNameDropdown = function () {
        initAll();
        observeNewRows();
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', window.initMedicationDrugNameDropdown);
    } else {
        window.initMedicationDrugNameDropdown();
    }
})();
