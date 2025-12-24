// Utility functions for the product analyzer web application

// Auto-scroll conversation to bottom
function scrollConversationToBottom() {
    const conversationBody = document.querySelector('.conversation-body');
    if (conversationBody) {
        conversationBody.scrollTop = conversationBody.scrollHeight;
    }
}

// Format timestamp
function formatTimestamp(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

// Initialize event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Auto-scroll conversation
    scrollConversationToBottom();
    
    // Submit button loading state
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 处理中...';
            }
        });
    });
}); 