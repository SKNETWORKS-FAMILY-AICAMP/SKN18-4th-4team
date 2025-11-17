document.addEventListener("DOMContentLoaded", () => {
  const passwordInput = document.getElementById("id_password");
  const togglePassword = document.getElementById("togglePassword");
  const eyeIcon = document.getElementById("eyeIcon");
  const loginForm = document.getElementById("loginForm");
  const loginBtn = document.getElementById("loginBtn");

  if (togglePassword && passwordInput && eyeIcon) {
    togglePassword.addEventListener("click", () => {
      const shouldShow = passwordInput.getAttribute("type") === "password";
      passwordInput.setAttribute("type", shouldShow ? "text" : "password");

      eyeIcon.classList.toggle("fa-eye", !shouldShow);
      eyeIcon.classList.toggle("fa-eye-slash", shouldShow);
    });
  }

  if (loginForm && loginBtn) {
    loginForm.addEventListener("submit", () => {
      loginBtn.disabled = true;
      loginBtn.dataset.originalText = loginBtn.textContent;
      loginBtn.textContent = "로그인 중...";
    });
  }
});
