// CubeMaster Pro - Interactive Animations

// Animated cube for homepage
function createAnimatedCube() {
    const cubeContainer = document.getElementById('animated-cube');
    if (!cubeContainer) return;
    
    // Create 3D cube with CSS transforms
    const cube = document.createElement('div');
    cube.className = 'cube-3d cube-rotate-animation';
    cube.style.cssText = `
        width: 60px;
        height: 60px;
        position: relative;
        transform-style: preserve-3d;
        margin: 0 auto;
    `;
    
    // Create cube faces
    const faces = ['front', 'back', 'right', 'left', 'top', 'bottom'];
    const colors = ['#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff8000', '#ffffff'];
    
    faces.forEach((face, index) => {
        const faceDiv = document.createElement('div');
        faceDiv.className = `cube-face cube-face-${face}`;
        faceDiv.style.cssText = `
            position: absolute;
            width: 60px;
            height: 60px;
            background: ${colors[index]};
            border: 2px solid #333;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: repeat(3, 1fr);
            gap: 1px;
        `;
        
        // Add face-specific transforms
        switch(face) {
            case 'front':
                faceDiv.style.transform = 'rotateY(0deg) translateZ(30px)';
                break;
            case 'back':
                faceDiv.style.transform = 'rotateY(180deg) translateZ(30px)';
                break;
            case 'right':
                faceDiv.style.transform = 'rotateY(90deg) translateZ(30px)';
                break;
            case 'left':
                faceDiv.style.transform = 'rotateY(-90deg) translateZ(30px)';
                break;
            case 'top':
                faceDiv.style.transform = 'rotateX(90deg) translateZ(30px)';
                break;
            case 'bottom':
                faceDiv.style.transform = 'rotateX(-90deg) translateZ(30px)';
                break;
        }
        
        // Add stickers to face
        for (let i = 0; i < 9; i++) {
            const sticker = document.createElement('div');
            sticker.style.cssText = `
                background: ${colors[index]};
                border: 1px solid #000;
                filter: brightness(${0.8 + Math.random() * 0.4});
            `;
            faceDiv.appendChild(sticker);
        }
        
        cube.appendChild(faceDiv);
    });
    
    cubeContainer.appendChild(cube);
}

// Confetti animation for successful solve
function triggerConfetti() {
    const colors = ['#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff8000', '#ffffff'];
    
    for (let i = 0; i < 50; i++) {
        setTimeout(() => {
            const confetti = document.createElement('div');
            confetti.style.cssText = `
                position: fixed;
                width: 10px;
                height: 10px;
                background: ${colors[Math.floor(Math.random() * colors.length)]};
                top: -10px;
                left: ${Math.random() * 100}%;
                z-index: 9999;
                border-radius: 50%;
                animation: confettiFall ${2 + Math.random() * 3}s linear forwards;
            `;
            
            document.body.appendChild(confetti);
            
            setTimeout(() => confetti.remove(), 5000);
        }, i * 100);
    }
}

// Add confetti animation CSS
const style = document.createElement('style');
style.textContent = `
    @keyframes confettiFall {
        to {
            transform: translateY(100vh) rotate(360deg);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Typing animation for text
function typeWriter(element, text, speed = 100) {
    let i = 0;
    element.innerHTML = '';
    
    function type() {
        if (i < text.length) {
            element.innerHTML += text.charAt(i);
            i++;
            setTimeout(type, speed);
        }
    }
    
    type();
}

// Parallax scrolling effect
function initParallax() {
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        const parallaxElements = document.querySelectorAll('.floating-sticker');
        
        parallaxElements.forEach((element, index) => {
            const speed = 0.5 + (index * 0.1);
            element.style.transform = `translateY(${scrolled * speed}px)`;
        });
    });
}

// Initialize animations when page loads
document.addEventListener('DOMContentLoaded', () => {
    createAnimatedCube();
    initParallax();
    
    // Add hover effects to buttons
    document.querySelectorAll('button, .btn-3d').forEach(button => {
        button.classList.add('btn-3d');
    });
});

// Export functions for use in templates
window.CubeMasterAnimations = {
    triggerConfetti,
    typeWriter,
    createAnimatedCube
};
