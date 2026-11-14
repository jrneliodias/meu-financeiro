document.addEventListener('DOMContentLoaded', function() {
    // Toggle Buttons
    const toggleButtons = document.querySelectorAll('.toggle-btn');
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const id = this.getAttribute('data-id');

            fetch(`/recurring-expense/${id}/toggle/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json',
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update icon
                    const icon = this.querySelector('i');
                    const newState = data.generate_debit;
                    icon.className = `fas fa-toggle-${newState ? 'on' : 'off'} ${newState ? 'text-green-500' : 'text-gray-500'}`;
                    this.setAttribute('data-active', newState ? 'True' : 'False');

                    // Display message (you can implement toast notifications)
                    console.log(data.message);
                    alert(data.message);
                } else {
                    alert(data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error toggling recurring expense');
            });
        });
    });

    // Delete Buttons
    const deleteButtons = document.querySelectorAll('.delete-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function() {
            const id = this.getAttribute('data-id');
            const description = this.getAttribute('data-description');

            if (confirm(`Are you sure you want to delete "${description}"?`)) {
                fetch(`/recurring-expense/${id}/delete/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Content-Type': 'application/json',
                    },
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(data.message);
                        // Reload page after short delay
                        setTimeout(() => window.location.reload(), 500);
                    } else {
                        alert(data.error);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error deleting recurring expense');
                });
            }
        });
    });

    // Funções utilitárias
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
