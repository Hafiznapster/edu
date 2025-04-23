function previewImage(input) {
    const preview = document.getElementById('imagePreview');
    const file = input.files[0];
    
    if (file) {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            // Remove the icon if it exists
            const icon = preview.querySelector('i');
            if (icon) {
                icon.remove();
            }
            
            // Create or update the preview image
            let img = preview.querySelector('img');
            if (!img) {
                img = document.createElement('img');
                preview.appendChild(img);
            }
            img.src = e.target.result;
            
            // Add animation
            img.classList.add('animate__animated', 'animate__fadeIn');
        };
        
        reader.readAsDataURL(file);
    }
}

// Add animation classes to form elements on load
document.addEventListener('DOMContentLoaded', function() {
    const formElements = document.querySelectorAll('.form-control, .form-check-input');
    formElements.forEach((element, index) => {
        element.classList.add('animate__animated', 'animate__fadeInUp');
        element.style.animationDelay = `${index * 0.1}s`;
    });
});