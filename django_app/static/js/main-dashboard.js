// 대시보드 메인 페이지 JS 초기화 스크립트
// - 사용자 정보 표시 (이름, 이메일)
// - "AI 채팅 시작하기" 버튼 클릭 처리
// - 로그아웃 버튼 표시/숨김 및 인터랙션(hover) 처리

document.addEventListener("DOMContentLoaded", () => {
  // 대시보드 루트 컨테이너를 찾는다 (data-dashboard 속성 이용)
  const root = document.querySelector("[data-dashboard]");
  if (!root) {
    // 대시보드 아니면 리턴
    return;
  }

  // 데이터 속성에서 정보를 읽어온다
  const userName = root.dataset.userName || "";
  const userEmail = root.dataset.userEmail || "";
  const chatUrl = root.dataset.chatUrl || "/";
  const logoutUrl = root.dataset.logoutUrl || "";
  const showLogout = root.dataset.showLogout === "true";

  // 사용자 이름 및 이메일 DOM 요소에 값 표시
  const userNameEl = document.getElementById("userName");
  const userEmailEl = document.getElementById("userEmail");
  if (userNameEl) {
    userNameEl.textContent = userName;
  }
  if (userEmailEl) {
    userEmailEl.textContent = userEmail;
  }

  // "AI 채팅 시작하기" 버튼 클릭 시 채팅 페이지로 이동
  const startChatBtn = document.getElementById("startChatBtn");
  if (startChatBtn) {
    startChatBtn.addEventListener("click", () => {
      window.location.href = chatUrl;
    });
  }

  // 로그아웃 버튼 표시 및 동작 처리
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    // showLogout이 false면 버튼 숨김
    if (!showLogout) {
      logoutBtn.style.display = "none";
    } else {
      // 로그아웃 버튼 클릭 시 로그아웃 URL로 이동
      logoutBtn.addEventListener("click", () => {
        if (logoutUrl) {
          window.location.href = logoutUrl;
        }
      });
      // 마우스 오버 시 버튼 배경색 변경
      logoutBtn.addEventListener("mouseenter", () => {
        logoutBtn.style.background = "#f3f4f6";
      });
      // 마우스 아웃 시 버튼 배경색 원래대로
      logoutBtn.addEventListener("mouseleave", () => {
        logoutBtn.style.background = "transparent";
      });
    }
  }
});
