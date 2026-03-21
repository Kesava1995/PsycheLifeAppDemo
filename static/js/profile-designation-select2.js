(function () {
    function init() {
        if (typeof window.jQuery === 'undefined' || !window.jQuery.fn.select2) return;
        var $el = window.jQuery('#designation');
        if (!$el.length || $el.hasClass('select2-hidden-accessible')) return;
        var ph = $el.data('placeholder') || 'Select or type designation...';
        $el.select2({
            width: '100%',
            placeholder: ph,
            allowClear: true,
            tags: true,
            createTag: function (params) {
                var term = window.jQuery.trim(params.term);
                if (term === '') return null;
                return { id: term, text: term };
            }
        });
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    window.setTimeout(init, 50);
})();
