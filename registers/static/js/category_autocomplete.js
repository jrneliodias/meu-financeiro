/**
 * Category Autocomplete Module
 *
 * Provides search-as-you-type for the category field
 * with inline creation of new categories.
 */
const CategoryAutocomplete = {
    ENDPOINTS: {
        SEARCH: '/register/categories/search/',
        CREATE: '/register/categories/create/',
    },

    elements: {
        wrapper: null,
        searchInput: null,
        dropdown: null,
        hiddenSelect: null,
    },

    categoryType: 'expense',
    highlightedIndex: 0,
    keepKey: null,
    latestRequest: 0,
    debounceTimer: null,
    DEBOUNCE_DELAY: 300,

    init: function () {
        this.cacheElements();
        if (!this.elements.searchInput || !this.elements.hiddenSelect) return;
        this.categoryType = this.elements.wrapper.dataset.categoryType === 'income' ? 'income' : 'expense';

        this.bindEvents();
        this.setInitialValue();
    },

    cacheElements: function () {
        this.elements.wrapper = document.getElementById('category-autocomplete-wrapper');
        this.elements.searchInput = document.getElementById('category-search-input');
        this.elements.dropdown = document.getElementById('category-dropdown');
        this.elements.hiddenSelect = document.getElementById('id_category');
    },

    bindEvents: function () {
        var self = this;
        var input = this.elements.searchInput;
        var wrapper = this.elements.wrapper;

        input.addEventListener('input', function () {
            clearTimeout(self.debounceTimer);
            self.debounceTimer = setTimeout(function () {
                self.onSearch();
            }, self.DEBOUNCE_DELAY);
        });

        input.addEventListener('focus', function (e) {
            // Coming back from an option (Shift+Tab / Escape): keep the list as it is.
            if (e.relatedTarget && wrapper.contains(e.relatedTarget)) return;
            self.onSearch();
        });

        document.addEventListener('click', function (e) {
            if (!wrapper.contains(e.target)) {
                self.closeDropdown();
            }
        });

        // Leaving the widget with Tab / Shift+Tab closes the list.
        wrapper.addEventListener('focusout', function (e) {
            if (e.relatedTarget && !wrapper.contains(e.relatedTarget)) {
                self.closeDropdown();
            }
        });

        input.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                self.closeDropdown();
            } else if (e.key === 'Enter') {
                e.preventDefault();
                // Search again right now so Enter never picks from stale results.
                clearTimeout(self.debounceTimer);
                self.keepHighlight();
                self.onSearch().then(function () { self.activateHighlighted(); });
            } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                e.preventDefault();
                self.moveHighlight(e.key === 'ArrowDown' ? 1 : -1, false);
            }
        });

        this.elements.dropdown.addEventListener('keydown', function (e) {
            var li = e.target.closest('li[role="option"]');
            if (!li) return;
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                self.activateItem(li, true);
            } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                e.preventDefault();
                self.moveHighlight(e.key === 'ArrowDown' ? 1 : -1, true);
            } else if (e.key === 'Escape') {
                e.preventDefault();
                self.closeDropdown();
                input.focus();
            }
        });

        // Focusing an option (Tab) also makes it the highlighted one.
        this.elements.dropdown.addEventListener('focusin', function (e) {
            var li = e.target.closest('li[role="option"]');
            if (li) self.highlight(self.options().indexOf(li));
        });
    },

    options: function () {
        return Array.prototype.slice.call(
            this.elements.dropdown.querySelectorAll('li[role="option"]'));
    },

    optionKey: function (li) {
        return li.dataset.action === 'create' ? 'create' : li.dataset.id;
    },

    // Remember the highlighted option so a re-render can restore it.
    keepHighlight: function () {
        var current = this.options()[this.highlightedIndex];
        this.keepKey = current ? this.optionKey(current) : null;
    },

    highlight: function (index) {
        var items = this.options();
        if (!items.length) return;
        this.highlightedIndex = Math.max(0, Math.min(index, items.length - 1));
        items.forEach(function (li, i) {
            var on = i === this.highlightedIndex;
            li.setAttribute('aria-selected', on ? 'true' : 'false');
            li.classList.toggle('bg-zinc-700', on);
        }, this);
    },

    moveHighlight: function (step, focus) {
        var items = this.options();
        if (!items.length) return;
        this.highlight(this.highlightedIndex + step);
        if (focus) items[this.highlightedIndex].focus();
    },

    activateHighlighted: function () {
        var items = this.options();
        if (items.length && !this.elements.dropdown.classList.contains('hidden')) {
            this.activateItem(items[this.highlightedIndex], false);
        }
    },

    activateItem: function (li, moveFocus) {
        var self = this;
        var done = function () { if (moveFocus) self.focusNextField(); };
        if (li.dataset.action === 'create') {
            this.createCategory(li.dataset.name).then(done);
        } else {
            this.selectCategory(li.dataset.id, li.dataset.name);
            done();
        }
    },

    focusNextField: function () {
        var wrapper = this.elements.wrapper;
        var candidates = document.querySelectorAll(
            'input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), a[href]');
        for (var i = 0; i < candidates.length; i++) {
            var el = candidates[i];
            var after = wrapper.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING;
            if (after && !wrapper.contains(el) && el.offsetParent !== null) {
                el.focus();
                return;
            }
        }
    },

    setInitialValue: function () {
        var select = this.elements.hiddenSelect;
        if (select && select.value) {
            var selectedOption = select.options[select.selectedIndex];
            if (selectedOption && selectedOption.text && selectedOption.value) {
                this.elements.searchInput.value = selectedOption.text;
            }
        }
    },

    onSearch: function () {
        var searchTerm = this.elements.searchInput.value.trim();
        var self = this;
        var request = ++this.latestRequest;

        return fetch(this.ENDPOINTS.SEARCH + '?q=' + encodeURIComponent(searchTerm) +
            '&type=' + this.categoryType)
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (request !== self.latestRequest) return; // a newer search is in flight
                self.renderDropdown(data.categories, searchTerm);
            })
            .catch(function () {
                self.closeDropdown();
            });
    },

    renderDropdown: function (categories, searchTerm) {
        var dropdown = this.elements.dropdown;
        dropdown.innerHTML = '';

        var self = this;

        if (categories.length === 0 && !searchTerm) {
            this.closeDropdown();
            return;
        }

        categories.forEach(function (cat) {
            var li = document.createElement('li');
            li.className = 'px-3 py-2 cursor-pointer hover:bg-zinc-700 text-gray-200 focus:outline-none';
            li.setAttribute('role', 'option');
            li.tabIndex = 0;
            li.dataset.id = cat.id;
            li.dataset.name = cat.name;
            li.textContent = cat.name;
            li.addEventListener('click', function () {
                self.activateItem(li, false);
            });
            dropdown.appendChild(li);
        });

        var hasExactMatch = categories.some(function (cat) {
            return cat.name.toLowerCase() === searchTerm.toLowerCase();
        });

        if (searchTerm && !hasExactMatch) {
            if (categories.length > 0) {
                var separator = document.createElement('li');
                separator.className = 'border-t border-zinc-700';
                dropdown.appendChild(separator);
            }

            var createLi = document.createElement('li');
            createLi.className = 'px-3 py-2 cursor-pointer hover:bg-zinc-700 text-blue-400 flex items-center gap-2 focus:outline-none';
            createLi.setAttribute('role', 'option');
            createLi.tabIndex = 0;
            createLi.dataset.action = 'create';
            createLi.dataset.name = searchTerm;
            createLi.innerHTML = '<i class="fas fa-plus text-xs"></i> Create "' +
                this.escapeHtml(searchTerm) + '"';
            createLi.addEventListener('click', function () {
                self.activateItem(createLi, false);
            });
            dropdown.appendChild(createLi);
        }

        dropdown.classList.remove('hidden');
        var keptIndex = this.keepKey === null ? -1 : this.options().findIndex(function (li) {
            return self.optionKey(li) === self.keepKey;
        });
        this.keepKey = null;
        this.highlight(keptIndex < 0 ? 0 : keptIndex);
    },

    selectCategory: function (id, name) {
        var select = this.elements.hiddenSelect;

        // Check if option exists in select, if not add it
        var optionExists = false;
        for (var i = 0; i < select.options.length; i++) {
            if (String(select.options[i].value) === String(id)) {
                optionExists = true;
                break;
            }
        }
        if (!optionExists) {
            var newOption = document.createElement('option');
            newOption.value = id;
            newOption.textContent = name;
            select.appendChild(newOption);
        }

        select.value = id;
        this.elements.searchInput.value = name;
        this.closeDropdown();
    },

    createCategory: function (name) {
        var self = this;

        return fetch(this.ENDPOINTS.CREATE, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCookie('csrftoken'),
            },
            body: JSON.stringify({ name: name, type: this.categoryType }),
        })
            .then(function (response) { return response.json(); })
            .then(function (data) {
                if (data.success && data.category) {
                    self.selectCategory(data.category.id, data.category.name);
                } else if (data.error) {
                    alert(data.error);
                }
            })
            .catch(function () {
                alert('Error creating category.');
            });
    },

    closeDropdown: function () {
        if (this.elements.dropdown) {
            this.elements.dropdown.classList.add('hidden');
        }
    },

    escapeHtml: function (text) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    },

    getCookie: function (name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    },
};

document.addEventListener('DOMContentLoaded', function () {
    CategoryAutocomplete.init();
});
