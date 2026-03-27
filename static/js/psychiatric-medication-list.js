// Reusable psychiatric medication suggestions for multiselect fields.
(function () {
    var PSYCHIATRIC_MEDICATIONS = [
        'Risperidone',
        'olanzepine',
        'Haloperidol',
        'Aripipazole',
        'Amisulpride',
        'Clozapine',
        'Chlorpromazine',
        'Cariprazine',
        'Quetiapine',
        'Quetiapine (as Sedative)',
        'Aripipazole (as Adjuvant)',
        'Lithium Carbonate',
        'Sodium Valproate',
        'Carbamazepine',
        'Escitalopram',
        'Fluoxetine',
        'Fluoxamine',
        'Sertraline',
        'Paroxetine',
        'Bupropion',
        'Duloxetine',
        'Venlafaxine',
        'Vortioxetine'
    ];

    if (typeof window !== 'undefined') {
        window.PSYCHIATRIC_MEDICATIONS = PSYCHIATRIC_MEDICATIONS;
    }
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = PSYCHIATRIC_MEDICATIONS;
    }
})();
