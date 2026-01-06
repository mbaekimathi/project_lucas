// Interactive Animations and Effects

// Count Up Animation for Stats
function animateCountUp() {
    const counters = document.querySelectorAll('.animate-count-up');
    
    counters.forEach(counter => {
        const target = parseInt(counter.getAttribute('data-target'));
        const duration = 2000; // 2 seconds
        const increment = target / (duration / 16); // 60fps
        let current = 0;
        
        const updateCounter = () => {
            current += increment;
            if (current < target) {
                counter.textContent = Math.floor(current) + (counter.getAttribute('data-target').includes('%') ? '%' : '+');
                requestAnimationFrame(updateCounter);
            } else {
                counter.textContent = target + (counter.getAttribute('data-target').includes('%') ? '%' : '+');
            }
        };
        
        // Start animation when element is in viewport
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    updateCounter();
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });
        
        observer.observe(counter);
    });
}

// Parallax Effect for Sections with Background Images
function initParallax() {
    const parallaxElements = document.querySelectorAll('.parallax-bg');
    const floatingContent = document.querySelectorAll('.floating-content');
    
    let ticking = false;
    
    function updateParallax() {
        const scrolled = window.pageYOffset;
        
        parallaxElements.forEach(element => {
            const rect = element.getBoundingClientRect();
            const speed = parseFloat(element.dataset.speed) || 0.5;
            
            // Only animate if element is in viewport
            if (rect.bottom >= 0 && rect.top <= window.innerHeight) {
                const yPos = -(scrolled * speed);
                element.style.transform = `translateY(${yPos}px)`;
            }
        });
        
        // Floating content effect
        floatingContent.forEach((content, index) => {
            const rect = content.getBoundingClientRect();
            if (rect.bottom >= 0 && rect.top <= window.innerHeight) {
                const offset = (scrolled * 0.1) + (index * 20);
                content.style.transform = `translateY(${Math.sin(offset * 0.01) * 10}px)`;
            }
        });
        
        ticking = false;
    }
    
    window.addEventListener('scroll', () => {
        if (!ticking) {
            window.requestAnimationFrame(updateParallax);
            ticking = true;
        }
    });
    
    // Initial call
    updateParallax();
}

// Interactive Hover Effects
function initInteractiveElements() {
    // Add ripple effect to buttons
    const buttons = document.querySelectorAll('a, button');
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple');
            
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
}

// Smooth Scroll Animation
function smoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Notification Popup Handler
function initNotifications() {
    // Ensure notifications are visible when they appear
    const notifications = document.querySelectorAll('[x-data*="show"]');
    notifications.forEach(notification => {
        // Show notification immediately
        notification.style.display = 'flex';
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (notification && notification.querySelector('[x-data]')) {
                const alpineData = Alpine.$data(notification.querySelector('[x-data]'));
                if (alpineData && alpineData.show !== undefined) {
                    alpineData.show = false;
                }
            }
        }, 5000);
    });
}

// Initialize all animations when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    animateCountUp();
    initParallax();
    initInteractiveElements();
    smoothScroll();
    
    // Initialize notifications after a short delay to ensure Alpine.js is ready
    setTimeout(() => {
        initNotifications();
    }, 100);
});

// Add CSS for ripple effect
const style = document.createElement('style');
style.textContent = `
    .ripple {
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.6);
        transform: scale(0);
        animation: ripple-animation 0.6s ease-out;
        pointer-events: none;
    }
    
    @keyframes ripple-animation {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
    
    a, button {
        position: relative;
        overflow: hidden;
    }
`;
document.head.appendChild(style);

