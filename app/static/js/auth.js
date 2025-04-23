// Password strength indicator with enhanced UI feedback
function checkPasswordStrength(password) {
    let strength = 0;
    const indicators = {
        length: password.length >= 8,
        uppercase: /[A-Z]/.test(password),
        lowercase: /[a-z]/.test(password),
        numbers: /[0-9]/.test(password),
        special: /[^A-Za-z0-9]/.test(password),
        hasAtSymbol: password.includes('@')
    };

    // Required criteria for our application
    const requiredCriteria = {
        length: password.length >= 8,
        numbers: /[0-9]/.test(password),
        hasAtSymbol: password.includes('@')
    };

    // Check if all required criteria are met
    const allRequirementsMet = Object.values(requiredCriteria).every(Boolean);

    // Calculate strength score (0-6)
    strength = Object.values(indicators).filter(Boolean).length;

    // Update strength bar
    const strengthBar = document.getElementById('password-strength');
    if (!strengthBar) return;

    // Calculate percentage with smooth animation
    const percentage = (strength / 6) * 100;
    strengthBar.style.width = `${percentage}%`;
    strengthBar.className = 'password-strength-bar';

    // Update strength text
    const strengthText = document.querySelector('.password-strength-text');
    if (strengthText) {
        strengthText.className = 'password-strength-text';

        if (strength <= 2) {
            strengthText.textContent = 'Weak';
            strengthText.classList.add('strength-weak');
            strengthBar.classList.add('bg-danger');
        } else if (strength <= 4) {
            strengthText.textContent = 'Medium';
            strengthText.classList.add('strength-medium');
            strengthBar.classList.add('bg-warning');
        } else {
            strengthText.textContent = 'Strong';
            strengthText.classList.add('strength-strong');
            strengthBar.classList.add('bg-success');
        }
    } else {
        // If no strength text element, just update the bar
        if (strength <= 2) {
            strengthBar.classList.add('bg-danger');
        } else if (strength <= 4) {
            strengthBar.classList.add('bg-warning');
        } else {
            strengthBar.classList.add('bg-success');
        }
    }

    // Update the password field styling
    const passwordInput = document.querySelector('input[name="password"]');
    if (passwordInput) {
        passwordInput.classList.remove('is-valid', 'is-invalid');
        if (password.length > 0) {
            passwordInput.classList.add(allRequirementsMet ? 'is-valid' : 'is-invalid');
        }
    }

    // Update the password requirements list
    updatePasswordRequirements(requiredCriteria, allRequirementsMet);

    // Update the submit button state
    updateSubmitButtonState(allRequirementsMet);

    return allRequirementsMet;
}

// Update password requirements list with enhanced visual feedback
function updatePasswordRequirements(criteria, allRequirementsMet) {
    const requirementsList = document.getElementById('password-requirements');
    if (!requirementsList) return;

    // Update each requirement item
    const lengthItem = requirementsList.querySelector('.req-length');
    const numberItem = requirementsList.querySelector('.req-number');
    const atSymbolItem = requirementsList.querySelector('.req-at-symbol');

    // Helper function to update requirement items with animation
    const updateRequirement = (item, isMet) => {
        if (!item) return;

        // Add a small delay for staggered animation effect
        setTimeout(() => {
            // Toggle classes
            item.classList.toggle('text-success', isMet);
            item.classList.toggle('text-danger', !isMet);

            // Update the icon
            const icon = item.querySelector('i');
            if (icon) {
                // Use checkmark icons with animation
                if (isMet) {
                    icon.className = 'bi bi-check-circle-fill';
                    // Add a subtle animation when requirement is met
                    icon.animate([
                        { transform: 'scale(0.8)', opacity: 0.5 },
                        { transform: 'scale(1.2)', opacity: 1 },
                        { transform: 'scale(1)', opacity: 1 }
                    ], {
                        duration: 300,
                        easing: 'ease-out'
                    });
                } else {
                    icon.className = 'bi bi-circle';
                }
            }
        }, isMet ? Math.random() * 200 : 0); // Random delay only for met requirements
    };

    // Update each requirement with the helper function
    updateRequirement(lengthItem, criteria.length);
    updateRequirement(numberItem, criteria.numbers);
    updateRequirement(atSymbolItem, criteria.hasAtSymbol);

    // Update or create the overall validation status indicator
    updateValidationStatus(allRequirementsMet);
}

// Update the validation status indicator with enhanced animation
function updateValidationStatus(isValid) {
    // Find the password input container
    const passwordInput = document.querySelector('input[name="password"]');
    if (!passwordInput) return;

    const container = passwordInput.closest('.form-group');
    if (!container) return;

    // Check if status element already exists
    let statusElement = container.querySelector('.password-validation-status');

    // If all requirements are met and status element doesn't exist, create it
    if (isValid) {
        if (!statusElement) {
            statusElement = document.createElement('div');
            statusElement.className = 'password-validation-status valid';
            statusElement.innerHTML = '<i class="bi bi-shield-check"></i> All requirements met!';

            // Insert after the small text
            const smallText = container.querySelector('small');
            if (smallText) {
                smallText.parentNode.insertBefore(statusElement, smallText.nextSibling);
            } else {
                container.appendChild(statusElement);
            }

            // Add confetti animation when all requirements are met
            if (typeof confetti === 'function') {
                confetti({
                    particleCount: 100,
                    spread: 70,
                    origin: { y: 0.6 },
                    colors: ['#28a745', '#20c997', '#87e8b5'],
                    disableForReducedMotion: true
                });
            }
        } else {
            statusElement.className = 'password-validation-status valid';
        }

        // Add a subtle highlight effect to the password field
        passwordInput.animate([
            { boxShadow: '0 0 0 3px rgba(40, 167, 69, 0.25)' },
            { boxShadow: '0 0 0 3px rgba(40, 167, 69, 0)' }
        ], {
            duration: 1000,
            easing: 'ease-out'
        });

    } else if (statusElement) {
        // If requirements not met and element exists, remove it with fade out
        statusElement.style.opacity = '0';
        statusElement.style.transform = 'translateY(10px)';
        setTimeout(() => {
            statusElement.remove();
        }, 300);
    }
}

// Update the submit button state with enhanced visual feedback
function updateSubmitButtonState(isValid) {
    const form = document.querySelector('form.auth-form');
    if (!form) return;

    const submitBtn = form.querySelector('button[type="submit"]');
    if (!submitBtn) return;

    // Add visual indicator to the button with smooth transition
    if (isValid) {
        submitBtn.classList.add('btn-success');
        submitBtn.classList.remove('btn-primary');

        // Add a subtle pulse animation to draw attention
        submitBtn.animate([
            { transform: 'scale(1)' },
            { transform: 'scale(1.05)' },
            { transform: 'scale(1)' }
        ], {
            duration: 600,
            easing: 'ease-in-out'
        });

        // Add checkmark icon if not already present
        const btnText = submitBtn.querySelector('.btn-text');
        if (btnText && !btnText.querySelector('.bi-check-circle')) {
            const icon = btnText.querySelector('i');
            if (icon) {
                icon.className = 'bi bi-check-circle-fill me-2';
            }
        }
    } else {
        submitBtn.classList.add('btn-primary');
        submitBtn.classList.remove('btn-success');

        // Restore original icon
        const btnText = submitBtn.querySelector('.btn-text');
        if (btnText) {
            const icon = btnText.querySelector('i');
            if (icon) {
                icon.className = 'bi bi-person-plus me-2';
            }
        }
    }
}

// Toggle password visibility with enhanced UI
document.addEventListener('DOMContentLoaded', function() {
    // Handle both old and new toggle buttons
    const toggleButtons = document.querySelectorAll('.toggle-password, .toggle-password-btn');

    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Find the associated password input
            const passwordInput = this.previousElementSibling ||
                                 this.parentElement.querySelector('input[type="password"]') ||
                                 this.parentElement.querySelector('input[type="text"]');

            if (!passwordInput) return;

            // Toggle between password and text type with animation
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                this.innerHTML = '<i class="bi bi-eye-slash"></i>';
                // Add a class to indicate the password is visible
                passwordInput.classList.add('password-visible');

                // Add a subtle highlight animation
                passwordInput.animate([
                    { backgroundColor: 'rgba(255, 255, 200, 0.2)' },
                    { backgroundColor: 'transparent' }
                ], {
                    duration: 1000,
                    easing: 'ease-out'
                });
            } else {
                passwordInput.type = 'password';
                this.innerHTML = '<i class="bi bi-eye"></i>';
                // Remove the class when password is hidden again
                passwordInput.classList.remove('password-visible');
            }
        });
    });

    // Add visual feedback when form is submitted
    const authForms = document.querySelectorAll('.auth-form');

    authForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Check if this is a registration form
            const passwordInput = this.querySelector('input[name="password"]');
            const isRegistrationForm = passwordInput && this.querySelector('input[name="password2"]');

            if (isRegistrationForm) {
                // Validate password requirements
                const password = passwordInput.value;
                const meetsRequirements = checkPasswordStrength(password);

                if (!meetsRequirements) {
                    e.preventDefault();

                    // Show error message with more specific details and better styling
                    const errorMsg = document.createElement('div');
                    errorMsg.className = 'alert alert-danger mt-3';
                    errorMsg.style.borderLeft = '4px solid #dc3545';
                    errorMsg.style.borderRadius = '4px';
                    errorMsg.style.animation = 'fadeIn 0.3s ease-in-out';
                    errorMsg.innerHTML = `
                        <div class="d-flex align-items-center">
                            <i class="bi bi-exclamation-triangle-fill me-3 fs-4"></i>
                            <div>
                                <strong>Password doesn't meet requirements</strong>
                                <p class="mb-0 small">Please check the requirements below and try again.</p>
                            </div>
                        </div>
                    `;

                    // Remove any existing error messages
                    const existingError = form.querySelector('.alert.alert-danger');
                    if (existingError) {
                        existingError.remove();
                    }

                    // Find the best place to insert the error message
                    const passwordField = passwordInput.closest('.password-field-container') ||
                                         passwordInput.closest('.form-group');
                    if (passwordField) {
                        passwordField.appendChild(errorMsg);
                    } else {
                        form.appendChild(errorMsg);
                    }

                    // Highlight the password field with shake animation
                    passwordInput.classList.add('is-invalid');
                    passwordInput.animate([
                        { transform: 'translateX(0)' },
                        { transform: 'translateX(-5px)' },
                        { transform: 'translateX(5px)' },
                        { transform: 'translateX(-5px)' },
                        { transform: 'translateX(0)' }
                    ], {
                        duration: 300,
                        easing: 'ease-in-out'
                    });

                    // Scroll to password requirements with highlight effect
                    const requirementsList = document.getElementById('password-requirements');
                    if (requirementsList) {
                        requirementsList.scrollIntoView({ behavior: 'smooth', block: 'center' });

                        // Highlight unfulfilled requirements
                        requirementsList.querySelectorAll('.text-danger').forEach(item => {
                            item.animate([
                                { backgroundColor: 'rgba(220, 53, 69, 0.1)' },
                                { backgroundColor: 'transparent' }
                            ], {
                                duration: 1500,
                                easing: 'ease-out'
                            });
                        });
                    }
                    return;
                } else {
                    // Remove any validation styling
                    passwordInput.classList.remove('is-invalid');
                    passwordInput.classList.add('is-valid');
                }
            }

            // Add loading state to submit button
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Processing...';
                submitBtn.disabled = true;
            }

            // Add a subtle animation to the form
            this.classList.add('submitting');
        });
    });

    // Enhance form field focus effects
    const formControls = document.querySelectorAll('.auth-form .form-control');

    formControls.forEach(input => {
        // Add animation when field gets focus
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('input-focused');
        });

        // Remove animation when field loses focus
        input.addEventListener('blur', function() {
            if (!this.value) {
                this.parentElement.classList.remove('input-focused');
            }
        });

        // Initialize with class if field has value
        if (input.value) {
            input.parentElement.classList.add('input-focused');
        }
    });
});

// Image preview functionality
function previewImage(input) {
    const preview = document.getElementById('imagePreview');
    const icon = preview.querySelector('i');

    if (input.files && input.files[0]) {
        const reader = new FileReader();

        reader.onload = function(e) {
            if (icon) icon.style.display = 'none';

            let img = preview.querySelector('img');
            if (!img) {
                img = document.createElement('img');
                preview.appendChild(img);
            }
            img.src = e.target.result;
        };

        reader.readAsDataURL(input.files[0]);
    } else if (icon) {
        icon.style.display = 'block';
        const img = preview.querySelector('img');
        if (img) img.remove();
    }
}

// Form validation and animation
document.addEventListener('DOMContentLoaded', function() {
    // Only apply to registration form password field
    const passwordInput = document.querySelector('form.auth-form input[name="password"]');
    if (passwordInput) {
        // Add confetti library for celebration animation
        const confettiScript = document.createElement('script');
        confettiScript.src = 'https://cdn.jsdelivr.net/npm/canvas-confetti@1.5.1/dist/confetti.browser.min.js';
        document.head.appendChild(confettiScript);

        // Create modern password strength container
        const strengthContainer = document.createElement('div');
        strengthContainer.className = 'password-strength-container mt-3';
        strengthContainer.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-1">
                <span class="small text-muted">Password Strength</span>
                <span class="password-strength-text small">Too weak</span>
            </div>
            <div class="password-strength-background">
                <div id="password-strength" class="password-strength-bar"></div>
            </div>
            <ul id="password-requirements" class="password-requirements mt-3">
                <li class="req-length text-danger"><i class="bi bi-circle"></i> At least 8 characters</li>
                <li class="req-number text-danger"><i class="bi bi-circle"></i> Contains at least one number</li>
                <li class="req-at-symbol text-danger"><i class="bi bi-circle"></i> Contains @ symbol</li>
            </ul>
            <div class="password-validation-indicator"></div>
        `;

        // Replace the default input group with our custom styled one
        const formGroup = passwordInput.closest('.form-group');
        if (formGroup) {
            // Store the original input attributes
            const inputAttrs = {
                name: passwordInput.name,
                id: passwordInput.id,
                placeholder: passwordInput.placeholder,
                autocomplete: passwordInput.autocomplete,
                required: passwordInput.required
            };

            // Get the label
            const label = formGroup.querySelector('label');
            const labelText = label ? label.textContent : 'Password';

            // Create the new password field container
            const newPasswordField = document.createElement('div');
            newPasswordField.className = 'password-field-container';
            newPasswordField.innerHTML = `
                <label class="password-label" for="${inputAttrs.id || 'password'}">${labelText}</label>
                <div class="position-relative">
                    <input type="password"
                        class="password-input"
                        name="${inputAttrs.name}"
                        id="${inputAttrs.id || 'password'}"
                        placeholder="${inputAttrs.placeholder || 'Create a strong password'}"
                        autocomplete="${inputAttrs.autocomplete || 'new-password'}"
                        ${inputAttrs.required ? 'required' : ''}
                    >
                    <button type="button" class="toggle-password-btn" tabindex="-1">
                        <i class="bi bi-eye"></i>
                    </button>
                </div>
                <small class="form-text text-muted mt-1">Password must be at least 8 characters long, contain @ symbol and at least one number.</small>
            `;

            // Replace the input group with our custom field
            const inputGroup = passwordInput.closest('.input-group');
            if (inputGroup) {
                inputGroup.replaceWith(newPasswordField);
            }

            // Append the strength container
            newPasswordField.appendChild(strengthContainer);

            // Get the new password input and add event listeners
            const newPasswordInput = newPasswordField.querySelector('.password-input');
            if (newPasswordInput) {
                newPasswordInput.addEventListener('input', function() {
                    checkPasswordStrength(this.value);
                });

                // Initial check
                checkPasswordStrength(newPasswordInput.value);
            }

            // Setup toggle password visibility
            const toggleBtn = newPasswordField.querySelector('.toggle-password-btn');
            if (toggleBtn) {
                toggleBtn.addEventListener('click', function() {
                    const input = this.previousElementSibling;
                    const type = input.type === 'password' ? 'text' : 'password';
                    input.type = type;
                    this.innerHTML = type === 'password' ?
                        '<i class="bi bi-eye"></i>' :
                        '<i class="bi bi-eye-slash"></i>';
                });
            }
        } else {
            // Fallback if we can't find the form group
            passwordInput.parentNode.appendChild(strengthContainer);

            passwordInput.addEventListener('input', function() {
                checkPasswordStrength(this.value);
            });

            // Initial check
            checkPasswordStrength(passwordInput.value);
        }
    }

    // Add floating labels effect
    document.querySelectorAll('.auth-form .form-control').forEach(input => {
        input.addEventListener('focus', () => {
            input.parentNode.classList.add('focused');
        });
        input.addEventListener('blur', () => {
            if (!input.value) {
                input.parentNode.classList.remove('focused');
            }
        });
    });
});