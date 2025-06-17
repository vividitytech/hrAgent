document.addEventListener('DOMContentLoaded', function() {
  const passwordInput = document.getElementById('yourPassword');
  const showPasswordCheckbox = document.getElementById('show_password');

  if (showPasswordCheckbox && passwordInput) { // Check if elements exist
      showPasswordCheckbox.addEventListener('change', function() {
          if (showPasswordCheckbox.checked) {
              passwordInput.type = 'text';
          } else {
              passwordInput.type = 'password';
          }
      });
  } else {
      console.error("Password input or show password checkbox not found!");
  }
});