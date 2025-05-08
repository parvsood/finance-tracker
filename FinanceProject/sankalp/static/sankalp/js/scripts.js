// Scripts for Sankalp application

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            // Ensure bootstrap is available
            if (typeof bootstrap !== 'undefined') {
                var bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } else {
                console.error('Bootstrap is not defined. Ensure it is properly loaded.');
            }
        });
    }, 5000);

    // Set min date for date inputs to today
    var startDateInputs = document.querySelectorAll('input[type="date"][name="start_date"]');
    var today = new Date().toISOString().split('T')[0];
    
    startDateInputs.forEach(function(input) {
        if (!input.value) {
            input.value = today;
        }
    });

    // Ensure target date is after start date
    var startDateInput = document.getElementById('id_start_date');
    var targetDateInput = document.getElementById('id_target_date');
    
    if (startDateInput && targetDateInput) {
        startDateInput.addEventListener('change', function() {
            if (targetDateInput.value && targetDateInput.value < startDateInput.value) {
                targetDateInput.value = startDateInput.value;
            }
            targetDateInput.min = startDateInput.value;
        });
        
        // Set initial min value for target date
        if (startDateInput.value) {
            targetDateInput.min = startDateInput.value;
        }
    }
});
