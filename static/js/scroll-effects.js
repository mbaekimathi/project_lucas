// Modern Scroll Effects and Animations

// Scroll Reveal Animation
function initScrollReveal() {
    const revealElements = document.querySelectorAll('.scroll-reveal');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('revealed');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });
    
    revealElements.forEach(element => {
        observer.observe(element);
    });
}

// Parallax Scroll Effect
function initParallax() {
    const parallaxElements = document.querySelectorAll('.parallax-bg');
    
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        
        parallaxElements.forEach(element => {
            const speed = 0.5;
            const yPos = -(scrolled * speed);
            element.style.transform = `translate3d(0, ${yPos}px, 0)`;
        });
    });
}

// Smooth Scroll for Anchor Links
function initSmoothScroll() {
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
}

// Card Hover Effects Enhancement
function initCardEffects() {
    const cards = document.querySelectorAll('.modern-card');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transition = 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
        });
    });
}

// Animated Counter for Stats
function animateCounter(element, target, duration = 2000) {
    let start = 0;
    const increment = target / (duration / 16);
    
    const timer = setInterval(() => {
        start += increment;
        if (start >= target) {
            element.textContent = target + (element.textContent.includes('+') ? '+' : '') + 
                                 (element.textContent.includes('%') ? '%' : '');
            clearInterval(timer);
        } else {
            element.textContent = Math.floor(start) + (element.textContent.includes('+') ? '+' : '') + 
                                 (element.textContent.includes('%') ? '%' : '');
        }
    }, 16);
}

// Initialize Counter Animations
function initCounters() {
    const counters = document.querySelectorAll('[data-counter]');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !entry.target.classList.contains('counted')) {
                const target = parseInt(entry.target.getAttribute('data-counter'));
                entry.target.classList.add('counted');
                animateCounter(entry.target, target);
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.5
    });
    
    counters.forEach(counter => {
        observer.observe(counter);
    });
}

// Fade In on Scroll
function initFadeIn() {
    const fadeElements = document.querySelectorAll('.fade-in-section');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                setTimeout(() => {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }, index * 100);
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1
    });
    
    fadeElements.forEach(element => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(30px)';
        element.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(element);
    });
}

// Initialize all effects when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initScrollReveal();
    initParallax();
    initSmoothScroll();
    initCardEffects();
    initCounters();
    initFadeIn();
});

// Re-initialize on dynamic content load
if (typeof window !== 'undefined') {
    window.addEventListener('load', () => {
        initScrollReveal();
        initFadeIn();
    });
}



