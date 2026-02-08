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
        searchInput: null,
        dropdown: null,
        hiddenSelect: null,
    },

    debounceTimer: null,
    DEBOUNCE_DELAY: 300,

    init: function () {
        this.cacheElements();
        if (!this.elements.searchInput || !this.elements.hiddenSelect) return;

        this.bindEvents();
        this.setInitialValue();
    },

    cacheElements: function () {
        this.elements.searchInput = document.getElementById('category-search-input');
        this.elements.dropdown = document.getElementById('category-dropdown');
        this.elements.hiddenSelect = document.getElementById('id_category');
    },

    bindEvents: function () {
        var self = this;

        this.elements.searchInput.addEventListener('input', function () {
            clearTimeout(self.debounceTimer);
            self.debounceTimer = setTimeout(function () {
                self.onSearch();
            }, self.DEBOUNCE_DELAY);
        });

        this.elements.searchInput.addEventListener('focus', function () {
            self.onSearch();
        });

        document.addEventListener('click', function (e) {
            var wrapper = document.getElementById('category-autocomplete-wrapper');
            if (wrapper && !wrapper.contains(e.target)) {
                self.closeDropdown();
            }
        });

        this.elements.searchInput.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                self.closeDropdown();
            }
        });
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

        fetch(this.ENDPOINTS.SEARCH + '?q=' + encodeURIComponent(searchTerm))
            .then(function (response) { return response.json(); })
            .then(function (data) {
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
            li.className = 'px-3 py-2 cursor-pointer hover:bg-zinc-700 text-gray-200';
            li.textContent = cat.name;
            li.addEventListener('click', function () {
                self.selectCategory(cat.id, cat.name);
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
            createLi.className = 'px-3 py-2 cursor-pointer hover:bg-zinc-700 text-blue-400 flex items-center gap-2';
            createLi.innerHTML = '<i class="fas fa-plus text-xs"></i> Create "' +
                this.escapeHtml(searchTerm) + '"';
            createLi.addEventListener('click', function () {
                self.createCategory(searchTerm);
            });
            dropdown.appendChild(createLi);
        }

        dropdown.classList.remove('hidden');
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

        fetch(this.ENDPOINTS.CREATE, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCookie('csrftoken'),
            },
            body: JSON.stringify({ name: name }),
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
