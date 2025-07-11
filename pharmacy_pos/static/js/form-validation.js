// Reusable real-time form validation module
window.applyFormValidation = function(config) {
    const form = document.querySelector('form');
    if (!form) return;

    // Helper to show error
    function showError(input, message) {
        let error = input.parentNode.querySelector('.form-error');
        if (!error) {
            error = document.createElement('div');
            error.className = 'form-error text-red-600 text-xs mt-1';
            input.parentNode.appendChild(error);
        }
        error.textContent = message;
        input.classList.add('border-red-500');
    }

    // Helper to clear error
    function clearError(input) {
        let error = input.parentNode.querySelector('.form-error');
        if (error) error.textContent = '';
        input.classList.remove('border-red-500');
    }

    // Validation rules
    function validateInput(input, type) {
        const value = input.value.trim();
        if (type === 'required' && !value) {
            showError(input, 'This field is required');
            return false;
        }
        if (type === 'email' && value) {
            const emailRegex = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
            if (!emailRegex.test(value)) {
                showError(input, 'Enter a valid email address');
                return false;
            }
        }
        if (type === 'phone' && value) {
            const phoneRegex = /^\+?[1-9]\d{7,14}$/;
            if (!phoneRegex.test(value.replace(/\s/g, ''))) {
                showError(input, 'Enter a valid phone number');
                return false;
            }
        }
        if (type === 'number' && value) {
            if (isNaN(value) || value === '') {
                showError(input, 'Enter a valid number');
                return false;
            }
        }
        clearError(input);
        return true;
    }

    // Attach listeners
    function attachValidation(selector, type) {
        (config[type] || []).forEach(function(sel) {
            const input = document.querySelector(sel);
            if (!input) return;
            input.addEventListener('input', function() {
                validateInput(input, type);
            });
            input.addEventListener('blur', function() {
                validateInput(input, type);
            });
        });
    }

    // Attach all validations
    ['required', 'email', 'phone', 'number'].forEach(function(type) {
        attachValidation(type, type);
    });

    // On submit, validate all
    form.addEventListener('submit', function(e) {
        let valid = true;
        ['required', 'email', 'phone', 'number'].forEach(function(type) {
            (config[type] || []).forEach(function(sel) {
                const input = document.querySelector(sel);
                if (input && !validateInput(input, type)) {
                    valid = false;
                }
            });
        });
        if (!valid) {
            e.preventDefault();
        }
    });
}; 