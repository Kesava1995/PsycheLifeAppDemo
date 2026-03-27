/**
 * Project color palette (light/dark pairs).
 * Usage:
 *   - Browser global: window.PROJECT_COLORS
 *   - CommonJS (if needed): require('./project-colors.js')
 */
(function () {
    var PROJECT_COLORS = [
        { id: 1, name: 'Teal', light: '#00897B', dark: '#26A69A' },
        { id: 2, name: 'Blue', light: '#1976D2', dark: '#64B5F6' },
        { id: 3, name: 'Light Blue', light: '#03A9F4', dark: '#4FC3F7' },
        { id: 4, name: 'Indigo', light: '#3949AB', dark: '#7986CB' },
        { id: 5, name: 'Deep Purple', light: '#5E35B1', dark: '#9575CD' },
        { id: 6, name: 'Purple', light: '#8E24AA', dark: '#BA68C8' },
        { id: 7, name: 'Magenta', light: '#C2185B', dark: '#F06292' },
        { id: 8, name: 'Pink', light: '#D81B60', dark: '#F48FB1' },
        { id: 9, name: 'Red', light: '#E53935', dark: '#EF5350' },
        { id: 10, name: 'Deep Orange', light: '#E64A19', dark: '#FF8A65' },
        { id: 11, name: 'Orange', light: '#F4511E', dark: '#FF7043' },
        { id: 12, name: 'Amber', light: '#F9A825', dark: '#FFD54F' },
        { id: 13, name: 'Yellow', light: '#FDD835', dark: '#FFF176' },
        { id: 14, name: 'Lime', light: '#C0CA33', dark: '#DCE775' },
        { id: 15, name: 'Green', light: '#43A047', dark: '#66BB6A' },
        { id: 16, name: 'Dark Green', light: '#2E7D32', dark: '#81C784' },
        { id: 17, name: 'Cyan', light: '#00ACC1', dark: '#4DD0E1' },
        { id: 18, name: 'Blue Grey', light: '#546E7A', dark: '#90A4AE' },
        { id: 19, name: 'Brown', light: '#6D4C41', dark: '#A1887F' },
        { id: 20, name: 'Slate Grey', light: '#455A64', dark: '#90A4AE' },
        { id: 21, name: 'Red (E2175F)', light: '#E2175F', dark: '#FC5C74' },
        { id: 22, name: 'Deep Orange (E06A00)', light: '#E06A00', dark: '#FF8F00' },
        { id: 23, name: 'Amber/Gold', light: '#D4A100', dark: '#FFC107' },
        { id: 24, name: 'Blue (1F7AE0)', light: '#1F7AE0', dark: '#5B9DFF' },
        { id: 25, name: 'Crimson', light: '#E0194F', dark: '#FF5C8A' },
        { id: 26, name: 'Green (20A030)', light: '#20A030', dark: '#4CAF50' },
        { id: 27, name: 'Teal (009688)', light: '#009688', dark: '#4DB6AC' },
        { id: 28, name: 'Cyan (00BCD4)', light: '#00BCD4', dark: '#4DD0E1' },
        { id: 29, name: 'Deep Purple (9C27B0)', light: '#9C27B0', dark: '#BA68C8' },
        { id: 30, name: 'Burnt Orange', light: '#FF5722', dark: '#FFAB91' },
        { id: 31, name: 'Brown (795548)', light: '#795548', dark: '#A1887F' },
        { id: 32, name: 'Blue Grey (607D8B)', light: '#607D8B', dark: '#90A4AE' },
        { id: 33, name: 'Light Green', light: '#8BC34A', dark: '#AED581' },
        { id: 34, name: 'Dark Amber', light: '#FF8F00', dark: '#FFB300' },
        { id: 35, name: 'Lime (AFB42B)', light: '#AFB42B', dark: '#DCE775' }
    ];

    function getProjectColor(idOrName, isDark) {
        var keyNum = Number(idOrName);
        var keyName = String(idOrName || '').trim().toLowerCase();
        var item = null;

        for (var i = 0; i < PROJECT_COLORS.length; i++) {
            var c = PROJECT_COLORS[i];
            if (!Number.isNaN(keyNum) && c.id === keyNum) {
                item = c;
                break;
            }
            if (keyName && String(c.name || '').toLowerCase() === keyName) {
                item = c;
                break;
            }
        }
        if (!item) return null;
        return isDark ? item.dark : item.light;
    }

    function getProjectColorLight(idOrName) {
        return getProjectColor(idOrName, false);
    }

    function getProjectColorDark(idOrName) {
        return getProjectColor(idOrName, true);
    }

    if (typeof window !== 'undefined') {
        window.PROJECT_COLORS = PROJECT_COLORS;
        window.getProjectColor = getProjectColor;
        window.getProjectColorLight = getProjectColorLight;
        window.getProjectColorDark = getProjectColorDark;
    }
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = {
            PROJECT_COLORS: PROJECT_COLORS,
            getProjectColor: getProjectColor,
            getProjectColorLight: getProjectColorLight,
            getProjectColorDark: getProjectColorDark
        };
    }
})();
