(function () {
  function initPremorbidPersonalitySelect2() {
    if (typeof window.jQuery === 'undefined' || !window.jQuery.fn.select2) return;
    var $ = window.jQuery;
    var el = $('#premorbid_personality');
    if (!el.length || el.hasClass('select2-hidden-accessible')) return;
    var $modal = $('#modalPers');
    el.select2({
      placeholder: 'Select personality traits...',
      allowClear: true,
      width: '100%',
      closeOnSelect: false,
      dropdownParent: $modal.length ? $modal : $(document.body)
    });
  }

  window.jQuery(function () {
    initPremorbidPersonalitySelect2();
  });

  document.addEventListener('click', function (ev) {
    var tr = ev.target && ev.target.closest && ev.target.closest('.click-trigger');
    if (!tr || !tr.getAttribute('onclick') || tr.getAttribute('onclick').indexOf('modalPers') === -1) return;
    window.setTimeout(initPremorbidPersonalitySelect2, 50);
  });
})();
