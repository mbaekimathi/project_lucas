// Main JavaScript for Modern School Website

// Theme Toggle Functionality
document.addEventListener('DOMContentLoaded', function() {
    // Get theme from session or default to light
    const currentTheme = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
    
    // Theme toggle buttons
    const themeToggles = document.querySelectorAll('#theme-toggle, #theme-toggle-sidebar');
    const themeText = document.getElementById('theme-text');
    
    function updateThemeUI(theme) {
        if (themeText) {
            themeText.textContent = theme === 'dark' ? 'Dark' : 'Light';
        }
    }
    
    themeToggles.forEach(button => {
        button.addEventListener('click', function() {
            const html = document.documentElement;
            const isDark = html.classList.contains('dark');
            
            if (isDark) {
                html.classList.remove('dark');
                updateTheme('light');
                updateThemeUI('light');
            } else {
                html.classList.add('dark');
                updateTheme('dark');
                updateThemeUI('dark');
            }
        });
    });
    
    // Initialize theme text
    const currentTheme = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
    updateThemeUI(currentTheme);
    
    // Update theme on server
    function updateTheme(theme) {
        fetch('/api/toggle-theme', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ theme: theme })
        }).catch(err => console.error('Error updating theme:', err));
    }
    
    // Sidebar Toggle (Mobile)
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    
    if (mobileMenuBtn && sidebar) {
        mobileMenuBtn.addEventListener('click', function() {
            sidebar.classList.toggle('-translate-x-full');
            if (sidebarOverlay) {
                sidebarOverlay.classList.toggle('hidden');
            }
            const icon = mobileMenuBtn.querySelector('i');
            if (sidebar.classList.contains('-translate-x-full')) {
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            } else {
                icon.classList.remove('fa-bars');
                icon.classList.add('fa-times');
            }
        });
    }
    
    // Close sidebar when clicking overlay
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', function() {
            sidebar.classList.add('-translate-x-full');
            sidebarOverlay.classList.add('hidden');
            const icon = mobileMenuBtn.querySelector('i');
            icon.classList.remove('fa-times');
            icon.classList.add('fa-bars');
        });
    }
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(e) {
        if (window.innerWidth < 1024) {
            if (sidebar && !sidebar.contains(e.target) && !mobileMenuBtn.contains(e.target)) {
                if (!sidebar.classList.contains('-translate-x-full')) {
                    sidebar.classList.add('-translate-x-full');
                    if (sidebarOverlay) {
                        sidebarOverlay.classList.add('hidden');
                    }
                    const icon = mobileMenuBtn.querySelector('i');
                    icon.classList.remove('fa-times');
                    icon.classList.add('fa-bars');
                }
            }
        }
    });
    
    // Fade-in on Scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.fade-in-section').forEach(el => {
        observer.observe(el);
    });
    
    // Auto-hide Flash Messages
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            message.style.transform = 'translateX(100%)';
            setTimeout(() => message.remove(), 300);
        }, 5000);
    });
    
    // Smooth Scroll for Anchor Links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href !== '#' && href.length > 1) {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });
    
    // Form Validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
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
    
    // Handle window resize - close mobile sidebar on desktop
    window.addEventListener('resize', function() {
        if (window.innerWidth >= 1024 && sidebar) {
            sidebar.classList.remove('-translate-x-full');
            if (sidebarOverlay) {
                sidebarOverlay.classList.add('hidden');
            }
            const icon = mobileMenuBtn.querySelector('i');
            if (icon) {
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        }
    });
});

// Add random emoji animations to elements
document.addEventListener('DOMContentLoaded', function() {
    // Add random animation delays to emojis
    const emojis = document.querySelectorAll('.emoji-bounce, .emoji-float, .emoji-pulse, .emoji-wiggle');
    emojis.forEach((emoji, index) => {
        emoji.style.animationDelay = `${index * 0.1}s`;
    });
    
    // Add hover effects to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            const emojis = this.querySelectorAll('.emoji-bounce, .emoji-float, .emoji-pulse');
            emojis.forEach(emoji => {
                emoji.style.animationDuration = '0.5s';
            });
        });
        card.addEventListener('mouseleave', function() {
            const emojis = this.querySelectorAll('.emoji-bounce, .emoji-float, .emoji-pulse');
            emojis.forEach(emoji => {
                emoji.style.animationDuration = '';
            });
        });
    });
});

// Utility Functions
function showLoading() {
    const loader = document.createElement('div');
    loader.id = 'page-loader';
    loader.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    loader.innerHTML = '<div class="spinner"></div>';
    document.body.appendChild(loader);
}

function hideLoading() {
    const loader = document.getElementById('page-loader');
    if (loader) {
        loader.remove();
    }
}

// Image Lazy Loading
if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    observer.unobserve(img);
                }
            }
        });
    });
    
    document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
    });
}

