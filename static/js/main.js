/**
 * SalesPulse Main Client-Side Utilities
 * Handles CSRF-enabled fetch requests and currency formatting.
 */

function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') : '';
}

/**
 * Wrapper around standard fetch to automatically include CSRF token header
 */
async function apiFetch(url, options = {}) {
  const defaultHeaders = {
    'X-CSRFToken': getCsrfToken(),
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  };

  options.headers = {
    ...defaultHeaders,
    ...options.headers
  };

  const response = await fetch(url, options);
  return response;
}

/**
 * Format numbers into Indian Rupee format
 */
function formatINR(val) {
  const n = Number(val) || 0;
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2
  }).format(n);
}

// Auto-dismiss standard alerts after 5 seconds
document.addEventListener('DOMContentLoaded', () => {
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(alert => {
    setTimeout(() => {
      try {
        const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
        if (bsAlert) bsAlert.close();
      } catch (e) {}
    }, 5000);
  });
});
