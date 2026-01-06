// Main JavaScript file for Modern School

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Add fade-in animation to elements
    const fadeElements = document.querySelectorAll('.fade-in-section');
    fadeElements.forEach((element, index) => {
        element.style.animationDelay = `${index * 0.1}s`;
    });

    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Skip validation for login form - let Alpine.js handle it
            if (form.id === 'loginForm') {
                // Remove required attribute from hidden fields to prevent browser validation errors
                const allFields = form.querySelectorAll('[required]');
                allFields.forEach(field => {
                    // Only validate visible fields
                    if (field.offsetParent === null) {
                        field.removeAttribute('required');
                    }
                });
                return true;
            }
            
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;

            requiredFields.forEach(field => {
                // Only validate visible fields
                if (field.offsetParent !== null && !field.value.trim()) {
                    isValid = false;
                    field.classList.add('border-red-500');
                } else {
                    field.classList.remove('border-red-500');
                }
            });

            if (!isValid) {
                e.preventDefault();
                alert('Please fill in all required fields.');
            }
        });
    });

    // Remove error styling on input
    const inputs = document.querySelectorAll('input, textarea, select');
    inputs.forEach(input => {
        input.addEventListener('input', function() {
            this.classList.remove('border-red-500');
        });
    });

    // Listen for custom event to open login modal
    window.addEventListener('open-login-modal', function() {
        // Trigger Alpine.js modal opening
        if (window.Alpine && window.Alpine.store) {
            // Dispatch event to Alpine.js component
            const event = new CustomEvent('open-login-modal');
            document.dispatchEvent(event);
        }
        // Fallback: directly set Alpine.js data if available
        const alpineData = document.querySelector('[x-data*="loginModalOpen"]');
        if (alpineData && window.Alpine) {
            const alpineComponent = window.Alpine.$data(alpineData);
            if (alpineComponent && typeof alpineComponent.loginModalOpen !== 'undefined') {
                alpineComponent.loginModalOpen = true;
            }
        }
    });

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href !== '#' && href.length > 1) {
                const target = document.querySelector(href);
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });

    // Auto-dismiss flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.bg-red-100, .bg-green-100, .bg-blue-100');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.transition = 'opacity 0.5s';
            message.style.opacity = '0';
            setTimeout(() => {
                message.remove();
            }, 500);
        }, 5000);
    });

    // Mobile menu toggle (if needed)
    const mobileMenuButton = document.querySelector('[data-mobile-menu-toggle]');
    const mobileMenu = document.querySelector('[data-mobile-menu]');
    
    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', function() {
            mobileMenu.classList.toggle('hidden');
        });
    }

    // Sidebar link animations on open
    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                const sidebar = document.querySelector('aside');
                if (sidebar && sidebar.classList.contains('translate-x-0')) {
                    // Sidebar is open, animate links
                    sidebarLinks.forEach((link, index) => {
                        link.style.animationDelay = `${index * 0.05}s`;
                        link.style.opacity = '1';
                    });
                } else {
                    // Sidebar is closed, reset
                    sidebarLinks.forEach(link => {
                        link.style.opacity = '0';
                    });
                }
            }
        });
    });

    // Observe sidebar for class changes
    const sidebar = document.querySelector('aside');
    if (sidebar) {
        observer.observe(sidebar, {
            attributes: true,
            attributeFilter: ['class']
        });
    }

    // Image lazy loading
    if ('loading' in HTMLImageElement.prototype) {
        const images = document.querySelectorAll('img[data-src]');
        images.forEach(img => {
            img.src = img.dataset.src;
        });
    } else {
        // Fallback for browsers that don't support lazy loading
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/lazysizes/5.3.2/lazysizes.min.js';
        document.body.appendChild(script);
    }
});

// Utility function for form validation
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Utility function for phone validation
function validatePhone(phone) {
    const re = /^[\d\s\-\+\(\)]+$/;
    return re.test(phone) && phone.replace(/\D/g, '').length >= 10;
}

// Live Clock and Calendar
function updateDateTime() {
    const now = new Date();
    
    // Calendar elements (Desktop)
    const calendarDay = document.getElementById('calendar-day');
    const calendarMonthHeader = document.getElementById('calendar-month-header');
    const calendarWeekday = document.getElementById('calendar-weekday');
    const calendarYear = document.getElementById('calendar-year');
    
    // Mobile elements
    const mobileDate = document.getElementById('mobile-date');
    
    // Date formatting
    const day = String(now.getDate()).padStart(2, '0');
    const months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
    const monthShort = months[now.getMonth()];
    const monthLong = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'][now.getMonth()];
    const weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const weekdaysShort = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const weekday = weekdays[now.getDay()];
    const weekdayShort = weekdaysShort[now.getDay()];
    const year = now.getFullYear();
    
    // Time formatting
    let hours = now.getHours();
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    const period = hours >= 12 ? 'PM' : 'AM';
    
    hours = hours % 12;
    hours = hours ? hours : 12; // 0 should be 12
    const hoursStr = String(hours).padStart(2, '0');
    
    // Update desktop calendar
    if (calendarDay) {
        calendarDay.textContent = now.getDate(); // Just the number, no padding
        if (calendarMonthHeader) calendarMonthHeader.textContent = monthLong;
        if (calendarWeekday) calendarWeekday.textContent = weekdayShort;
        if (calendarYear) calendarYear.textContent = year;
    }
    
    // Update mobile date
    if (mobileDate) {
        mobileDate.textContent = `${monthShort} ${now.getDate()}`;
    }
}

// Initialize and update date/time
document.addEventListener('DOMContentLoaded', function() {
    updateDateTime();
    // Update every minute (calendar doesn't need second updates)
    setInterval(updateDateTime, 60000);
    
    // Login form validation
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            const role = document.querySelector('input[name="role"]').value;
            const password = document.getElementById('password').value;
            
            if (!role) {
                e.preventDefault();
                alert('Please select your role.');
                return false;
            }
            
            if (role === 'parent' || role === 'student') {
                const admissionNumber = document.getElementById('admission_number');
                if (admissionNumber && !admissionNumber.value.trim()) {
                    e.preventDefault();
                    alert('Please enter student admission number.');
                    admissionNumber.focus();
                    return false;
                }
            } else if (role === 'employee') {
                const employeeId = document.getElementById('employee_id');
                if (employeeId && !employeeId.value.trim()) {
                    e.preventDefault();
                    alert('Please enter employee identification number.');
                    employeeId.focus();
                    return false;
                }
            }
            
            if (!password.trim()) {
                e.preventDefault();
                alert('Please enter your password.');
                document.getElementById('password').focus();
                return false;
            }
        });
    }

    // Handle admission links to open modal
    document.querySelectorAll('a[href="/admission"]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            // Dispatch Alpine event to open modal
            window.dispatchEvent(new CustomEvent('open-admission-modal'));
        });
    });
});

// Add custom validation to email fields
document.addEventListener('DOMContentLoaded', function() {
    const emailFields = document.querySelectorAll('input[type="email"]');
    emailFields.forEach(field => {
        field.addEventListener('blur', function() {
            if (this.value && !validateEmail(this.value)) {
                this.classList.add('border-red-500');
                this.setCustomValidity('Please enter a valid email address.');
            } else {
                this.classList.remove('border-red-500');
                this.setCustomValidity('');
            }
        });
    });

    // Add custom validation to phone fields
    const phoneFields = document.querySelectorAll('input[type="tel"]');
    phoneFields.forEach(field => {
        field.addEventListener('blur', function() {
            if (this.value && !validatePhone(this.value)) {
                this.classList.add('border-red-500');
                this.setCustomValidity('Please enter a valid phone number.');
            } else {
                this.classList.remove('border-red-500');
                this.setCustomValidity('');
            }
        });
    });

    // Employee registration form validation
    const employeeForm = document.getElementById('employeeForm');
    if (employeeForm) {
        // Employee ID validation (6 digits only) with live availability check
        const employeeIdField = employeeForm.querySelector('[name="employee_id"]');
        const employeeIdValidation = document.getElementById('employee_id_validation');
        const employeeIdIcon = document.getElementById('employee_id_icon');
        const employeeIdMessage = document.getElementById('employee_id_message');
        let validationTimeout = null;
        
        if (employeeIdField) {
            employeeIdField.addEventListener('input', function() {
                // Only allow digits
                this.value = this.value.replace(/\D/g, '');
                // Limit to 6 digits
                if (this.value.length > 6) {
                    this.value = this.value.slice(0, 6);
                }
                
                // Hide validation message while typing
                employeeIdValidation.classList.add('hidden');
                employeeIdMessage.classList.add('hidden');
                this.classList.remove('border-green-500', 'border-red-500');
                
                // Clear previous timeout
                if (validationTimeout) {
                    clearTimeout(validationTimeout);
                }
                
                // Check availability after 6 digits are entered
                if (this.value.length === 6) {
                    validationTimeout = setTimeout(() => {
                        checkEmployeeIdAvailability(this.value);
                    }, 500); // Wait 500ms after user stops typing
                }
            });
            
            // Function to check employee ID availability
            function checkEmployeeIdAvailability(employeeId) {
                if (!employeeId || employeeId.length !== 6) {
                    return;
                }
                
                // Show loading state
                employeeIdValidation.classList.remove('hidden');
                employeeIdIcon.className = 'fas fa-spinner fa-spin text-gray-400 text-xl';
                employeeIdField.classList.remove('border-green-500', 'border-red-500');
                employeeIdMessage.classList.add('hidden');
                
                // Make API call to check availability
                fetch('/check-employee-id', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ employee_id: employeeId })
                })
                .then(response => response.json())
                .then(data => {
                    employeeIdValidation.classList.remove('hidden');
                    
                    if (data.available) {
                        // Employee ID is available
                        employeeIdIcon.className = 'fas fa-check-circle text-green-500 text-xl';
                        employeeIdField.classList.remove('border-red-500');
                        employeeIdField.classList.add('border-green-500');
                        employeeIdMessage.textContent = data.message || 'Employee ID is available!';
                        employeeIdMessage.className = 'mt-2 text-sm font-medium text-green-600';
                        employeeIdMessage.classList.remove('hidden');
                    } else {
                        // Employee ID is already taken
                        employeeIdIcon.className = 'fas fa-times-circle text-red-500 text-xl';
                        employeeIdField.classList.remove('border-green-500');
                        employeeIdField.classList.add('border-red-500');
                        employeeIdMessage.textContent = data.message || 'This Employee ID is already registered. Please use a different ID.';
                        employeeIdMessage.className = 'mt-2 text-sm font-medium text-red-600';
                        employeeIdMessage.classList.remove('hidden');
                    }
                })
                .catch(error => {
                    console.error('Error checking employee ID:', error);
                    employeeIdValidation.classList.add('hidden');
                    employeeIdMessage.textContent = 'Error checking employee ID. Please try again.';
                    employeeIdMessage.className = 'mt-2 text-sm font-medium text-yellow-600';
                    employeeIdMessage.classList.remove('hidden');
                });
            }
        }

        // Password confirmation validation
        const passwordField = employeeForm.querySelector('[name="password"]');
        const confirmPasswordField = employeeForm.querySelector('[name="confirm_password"]');
        
        function validatePasswordMatch() {
            if (confirmPasswordField.value && passwordField.value !== confirmPasswordField.value) {
                confirmPasswordField.setCustomValidity('Passwords do not match.');
                confirmPasswordField.classList.add('border-red-500');
            } else {
                confirmPasswordField.setCustomValidity('');
                confirmPasswordField.classList.remove('border-red-500');
            }
        }

        if (passwordField && confirmPasswordField) {
            passwordField.addEventListener('input', validatePasswordMatch);
            confirmPasswordField.addEventListener('input', validatePasswordMatch);
        }

        // Convert text fields to uppercase (except email)
        const uppercaseFields = ['full_name', 'phone', 'id_number'];
        uppercaseFields.forEach(fieldName => {
            const field = employeeForm.querySelector(`[name="${fieldName}"]`);
            if (field) {
                field.addEventListener('input', function() {
                    const cursorPosition = this.selectionStart;
                    this.value = this.value.toUpperCase();
                    this.setSelectionRange(cursorPosition, cursorPosition);
                });
                field.addEventListener('blur', function() {
                    this.value = this.value.toUpperCase();
                });
            }
        });

        // Convert email to lowercase
        const emailField = employeeForm.querySelector('[name="email"]');
        if (emailField) {
            emailField.addEventListener('input', function() {
                const cursorPosition = this.selectionStart;
                this.value = this.value.toLowerCase();
                this.setSelectionRange(cursorPosition, cursorPosition);
            });
            emailField.addEventListener('blur', function() {
                this.value = this.value.toLowerCase();
            });
        }

        // Form submission validation
        employeeForm.addEventListener('submit', function(e) {
            if (passwordField.value !== confirmPasswordField.value) {
                e.preventDefault();
                alert('Passwords do not match. Please try again.');
                confirmPasswordField.focus();
                return false;
            }

            if (employeeIdField && (employeeIdField.value.length !== 6 || !/^\d{6}$/.test(employeeIdField.value))) {
                e.preventDefault();
                alert('Employee ID must be exactly 6 digits.');
                employeeIdField.focus();
                return false;
            }
            
            // Check if employee ID is available before submission
            if (employeeIdField && employeeIdField.classList.contains('border-red-500')) {
                e.preventDefault();
                alert('Please use a different Employee ID. The current one is already registered.');
                employeeIdField.focus();
                return false;
            }
        });
    }

    // Admission form: Convert all text fields to UPPERCASE except email (lowercase)
    const admissionForm = document.getElementById('admissionForm');
    if (admissionForm) {
        // Fields that should be UPPERCASE
        const uppercaseFields = [
            'student_full_name',
            'previous_school',
            'parent_name',
            'parent_phone',
            'address',
            'emergency_contact',
            'medical_conditions',
            'special_needs'
        ];

        // Fields that should be lowercase (email)
        const lowercaseFields = [
            'parent_email'
        ];

        // Apply uppercase conversion on input
        uppercaseFields.forEach(fieldName => {
            const field = admissionForm.querySelector(`[name="${fieldName}"]`);
            if (field) {
                field.addEventListener('input', function() {
                    const cursorPosition = this.selectionStart;
                    this.value = this.value.toUpperCase();
                    // Restore cursor position after conversion
                    this.setSelectionRange(cursorPosition, cursorPosition);
                });
                
                // Also convert on blur to ensure consistency
                field.addEventListener('blur', function() {
                    this.value = this.value.toUpperCase();
                });
            }
        });

        // Apply lowercase conversion for email
        lowercaseFields.forEach(fieldName => {
            const field = admissionForm.querySelector(`[name="${fieldName}"]`);
            if (field) {
                field.addEventListener('input', function() {
                    const cursorPosition = this.selectionStart;
                    this.value = this.value.toLowerCase();
                    // Restore cursor position after conversion
                    this.setSelectionRange(cursorPosition, cursorPosition);
                });
                
                // Also convert on blur to ensure consistency
                field.addEventListener('blur', function() {
                    this.value = this.value.toLowerCase();
                });
            }
        });

        // Convert textarea fields to uppercase
        const textareaFields = admissionForm.querySelectorAll('textarea[name="address"], textarea[name="special_needs"]');
        textareaFields.forEach(textarea => {
            textarea.addEventListener('input', function() {
                const cursorPosition = this.selectionStart;
                this.value = this.value.toUpperCase();
                // Restore cursor position after conversion
                this.setSelectionRange(cursorPosition, cursorPosition);
            });
            
            textarea.addEventListener('blur', function() {
                this.value = this.value.toUpperCase();
            });
        });
    }
});


