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
  const avatarUrl = root.dataset.avatarUrl || "";
  const profileUploadUrl = root.dataset.profileUploadUrl || "";

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

  // 사용자 프로필 모달 제어 로직
  const avatarBtn = document.getElementById("userAvatarBtn");
  const avatarImg = document.getElementById("userAvatarImage");
  const avatarIcon = avatarBtn ? avatarBtn.querySelector(".user-avatar__icon") : null;
  const profileModal = document.getElementById("profileModal");
  const profileModalClose = document.getElementById("profileModalClose");
  const profileModalCancel = document.getElementById("profileModalCancel");
  const profileUploadForm = document.getElementById("profileUploadForm");
  const profileImageInput = document.getElementById("profileImageInput");
  const profilePreviewContainer = document.getElementById("profilePreviewContainer");
  const profilePreviewImage = document.getElementById("profilePreviewImage");
  const profilePreviewPlaceholder = document.getElementById("profilePreviewPlaceholder");
  const profileUploadMessage = document.getElementById("profileUploadMessage");

  const getCsrfToken = () => {
    const name = "csrftoken";
    const cookies = document.cookie ? document.cookie.split("; ") : [];
    for (const cookie of cookies) {
      const [key, value] = cookie.split("=");
      if (key === name) {
        return decodeURIComponent(value);
      }
    }
    return "";
  };

  if (avatarBtn && profileModal) {
    let previewDataUrl = "";
    let selectedFile = null;
    let currentAvatarUrl = avatarUrl;

    const setAvatarImage = (url) => {
      if (!avatarBtn) return;
      if (url) {
        avatarBtn.classList.add("user-avatar--has-image");
        if (avatarImg) {
          avatarImg.src = url;
          avatarImg.hidden = false;
        }
        if (avatarIcon) {
          avatarIcon.hidden = true;
        }
        if (profilePreviewImage) {
          profilePreviewImage.src = url;
          profilePreviewImage.hidden = false;
        }
        if (profilePreviewPlaceholder) {
          profilePreviewPlaceholder.hidden = true;
        }
        if (profilePreviewContainer) {
          profilePreviewContainer.classList.add("profile-modal__preview--has-image");
        }
        currentAvatarUrl = url;
      } else {
        avatarBtn.classList.remove("user-avatar--has-image");
        if (avatarImg) {
          avatarImg.src = "";
          avatarImg.hidden = true;
        }
        if (avatarIcon) {
          avatarIcon.hidden = false;
        }
        if (profilePreviewImage) {
          profilePreviewImage.src = "";
          profilePreviewImage.hidden = true;
        }
        if (profilePreviewPlaceholder) {
          profilePreviewPlaceholder.hidden = false;
        }
        if (profilePreviewContainer) {
          profilePreviewContainer.classList.remove("profile-modal__preview--has-image");
        }
        currentAvatarUrl = "";
      }
    };

    if (currentAvatarUrl) {
      setAvatarImage(currentAvatarUrl);
    }

    const setMessage = (text = "", type = "info") => {
      if (!profileUploadMessage) {
        return;
      }
      profileUploadMessage.textContent = text;
      profileUploadMessage.classList.remove("is-error", "is-success");
      if (type === "error") {
        profileUploadMessage.classList.add("is-error");
      } else if (type === "success") {
        profileUploadMessage.classList.add("is-success");
      }
    };

    const resetPreview = () => {
      previewDataUrl = "";
      selectedFile = null;
      if (profileImageInput) {
        profileImageInput.value = "";
      }
      if (profilePreviewImage) {
        profilePreviewImage.src = "";
        profilePreviewImage.hidden = true;
      }
      if (profilePreviewPlaceholder) {
        profilePreviewPlaceholder.hidden = false;
      }
      if (profilePreviewContainer) {
        profilePreviewContainer.classList.remove("profile-modal__preview--has-image");
      }
      setMessage();
    };

    const openModal = () => {
      profileModal.classList.add("is-visible");
      profileModal.setAttribute("aria-hidden", "false");
      setMessage();
    };

    const closeModal = () => {
      profileModal.classList.remove("is-visible");
      profileModal.setAttribute("aria-hidden", "true");
      resetPreview();
    };

    avatarBtn.addEventListener("click", openModal);

    if (profileModalClose) {
      profileModalClose.addEventListener("click", closeModal);
    }

    if (profileModalCancel) {
      profileModalCancel.addEventListener("click", closeModal);
    }

    profileModal.addEventListener("click", (event) => {
      if (event.target === profileModal) {
        closeModal();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && profileModal.classList.contains("is-visible")) {
        closeModal();
      }
    });

    if (profileImageInput) {
      profileImageInput.addEventListener("change", () => {
        const [file] = profileImageInput.files || [];
        if (!file) {
          resetPreview();
          return;
        }

        selectedFile = file;
        const reader = new FileReader();
        reader.onload = (evt) => {
          previewDataUrl = String(evt.target?.result || "");
          if (profilePreviewImage) {
            profilePreviewImage.src = previewDataUrl;
            profilePreviewImage.hidden = false;
          }
          if (profilePreviewPlaceholder) {
            profilePreviewPlaceholder.hidden = true;
          }
          if (profilePreviewContainer) {
            profilePreviewContainer.classList.add("profile-modal__preview--has-image");
          }
          setMessage("미리보기를 확인하고 저장을 눌러주세요.");
        };
        reader.readAsDataURL(file);
      });
    }

    if (profileUploadForm) {
      profileUploadForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!selectedFile || !previewDataUrl) {
          setMessage("업로드할 이미지를 먼저 선택해주세요.", "error");
          return;
        }
        if (!profileUploadUrl) {
          setMessage("업로드 경로를 찾을 수 없습니다.", "error");
          return;
        }

        const formData = new FormData();
        formData.append("profile_image", selectedFile);
        setMessage("이미지를 업로드하는 중입니다...");

        try {
          const response = await fetch(profileUploadUrl, {
            method: "POST",
            body: formData,
            credentials: "same-origin",
            headers: {
              "X-CSRFToken": getCsrfToken(),
            },
          });

          const data = await response.json().catch(() => ({}));
          if (!response.ok) {
            throw new Error(data.error || "이미지 업로드에 실패했습니다.");
          }

          const newImageUrl = data.image_url || previewDataUrl;
          setAvatarImage(newImageUrl);
          setMessage(data.message || "프로필 이미지가 업데이트되었습니다.", "success");

          setTimeout(() => {
            closeModal();
          }, 800);
        } catch (error) {
          setMessage(error.message || "이미지 업로드 중 오류가 발생했습니다.", "error");
        }
      });
    }
  }
});
