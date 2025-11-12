document.addEventListener("DOMContentLoaded", () => {
  const root = document.querySelector("[data-chat]");
  if (!root) return;

  const mainUrl = root.dataset.mainUrl || "/main/";
  const logoutUrl = root.dataset.logoutUrl || "";

  const storedUser = (() => {
    try {
      return JSON.parse(localStorage.getItem("user") || "{}");
    } catch (e) {
      return {};
    }
  })();

  const user = {
    name: root.dataset.userName || storedUser.name || "게스트 연구자",
    email: root.dataset.userEmail || storedUser.email || "research@example.com",
  };

  const userNameEl = document.getElementById("sidebarUserName");
  const userEmailEl = document.getElementById("sidebarUserEmail");
  if (userNameEl) userNameEl.textContent = user.name;
  if (userEmailEl) userEmailEl.textContent = user.email;

  let conversations = [];
  try {
    conversations = JSON.parse(localStorage.getItem("conversations")) || [];
  } catch {
    conversations = [];
  }

  if (conversations.length === 0) {
    conversations = [
      {
        id: Date.now().toString(),
        title: "새로운 대화",
        messages: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
    ];
    saveConversations();
  }

  let currentConversationId = conversations[0]?.id;
  let isLoading = false;

  function saveConversations() {
    localStorage.setItem("conversations", JSON.stringify(conversations));
  }

  function getCurrentConversation() {
    return conversations.find((c) => c.id === currentConversationId);
  }

  function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return "오늘";
    if (days === 1) return "어제";
    if (days < 7) return `${days}일 전`;
    return date.toLocaleDateString("ko-KR", { month: "short", day: "numeric" });
  }

  function renderChatHistory() {
    const historyContainer = document.getElementById("chatHistory");
    if (!historyContainer) return;
    historyContainer.innerHTML = "";

    conversations.forEach((conv) => {
      const div = document.createElement("div");
      div.className = `conversation-item ${conv.id === currentConversationId ? "active" : ""}`;
      div.innerHTML = `
        <div class="conversation-item-content">
          <i class="conversation-icon fa-solid fa-comment-dots"></i>
          <div class="conversation-text">
            <div class="conversation-title">${conv.title}</div>
            <div class="conversation-date">${formatDate(conv.updatedAt)}</div>
          </div>
        </div>
        <button class="conversation-delete" data-id="${conv.id}">
          <i class="fa-solid fa-trash"></i>
        </button>
      `;

      div.querySelector(".conversation-item-content").addEventListener("click", () => {
        currentConversationId = conv.id;
        renderChatHistory();
        renderMessages();
        updateTemplateVisibility();
      });

      div.querySelector(".conversation-delete").addEventListener("click", (e) => {
        e.stopPropagation();
        deleteConversation(conv.id);
      });

      historyContainer.appendChild(div);
    });
  }

  function deleteConversation(id) {
    if (conversations.length === 1) {
      alert("마지막 대화는 삭제할 수 없습니다.");
      return;
    }
    conversations = conversations.filter((c) => c.id !== id);
    if (currentConversationId === id) {
      currentConversationId = conversations[0]?.id;
    }
    saveConversations();
    renderChatHistory();
    renderMessages();
    updateTemplateVisibility();
  }

  function renderMessages() {
    const messagesContainer = document.getElementById("chatMessages");
    const conversation = getCurrentConversation();
    if (!messagesContainer || !conversation) return;

    if (conversation.messages.length === 0 && !isLoading) {
      messagesContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-content">
            <i class="empty-state-icon fa-solid fa-comments"></i>
            <h2 style="margin-bottom: 0.5rem; color: #6b7280; font-size: 1.125rem;">새로운 대화를 시작하세요</h2>
            <p style="font-size: 0.875rem;">의학 연구 관련 질문을 입력하거나 아래 템플릿을 선택해보세요.</p>
          </div>
        </div>
      `;
      return;
    }

    messagesContainer.innerHTML = '<div class="chat-messages-content" id="messagesContent"></div>';
    const messagesContent = document.getElementById("messagesContent");

    conversation.messages.forEach((msg) => {
      const wrapper = document.createElement("div");
      wrapper.className = `message-wrapper ${msg.role}`;

      if (msg.role === "assistant") {
        wrapper.innerHTML = `
          <div class="message-avatar assistant">
            <i class="fa-solid fa-robot"></i>
          </div>
          <div class="message-content-wrapper">
            <div class="message-bubble assistant">${formatMessageContent(msg.content)}</div>
            ${msg.references ? renderReferences(msg.references) : ""}
            ${renderFeedbackButtons(msg)}
          </div>
        `;
      } else {
        wrapper.innerHTML = `
          <div class="message-content-wrapper">
            <div class="message-bubble user">${msg.content}</div>
          </div>
          <div class="message-avatar user">
            <i class="fa-solid fa-user"></i>
          </div>
        `;
      }

      messagesContent.appendChild(wrapper);

      if (msg.role === "assistant") {
        wrapper.querySelectorAll(".feedback-btn").forEach((btn) => {
          btn.addEventListener("click", () => {
            handleFeedback(msg.id, btn.dataset.feedback);
          });
        });
      }
    });

    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function formatMessageContent(content) {
    return content.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>").replace(/\n/g, "<br>");
  }

  function renderReferences(references) {
    if (!references || !references.length) return "";
    let html = '<div class="references-box"><div class="references-title">📚 참고문헌</div>';
    references.forEach((ref) => {
      html += `
        <div class="reference-item">
          <div class="reference-item-header">
            <span class="reference-number">[${ref.id}]</span>
            <div class="reference-content">
              <div class="reference-title">${ref.title}</div>
              <div class="reference-authors">${ref.authors} • ${ref.journal} (${ref.year})</div>
              <div class="reference-links">
                ${
                  ref.doi
                    ? `<a href="https://doi.org/${ref.doi}" target="_blank" class="reference-link">DOI <i class="icon-xs fa-solid fa-arrow-up-right-from-square"></i></a>`
                    : ""
                }
                ${
                  ref.pmid
                    ? `<a href="https://pubmed.ncbi.nlm.nih.gov/${ref.pmid}" target="_blank" class="reference-link">PubMed <i class="icon-xs fa-solid fa-arrow-up-right-from-square"></i></a>`
                    : ""
                }
              </div>
            </div>
          </div>
        </div>
      `;
    });
    html += "</div>";
    return html;
  }

  function renderFeedbackButtons(msg) {
    return `
      <div class="feedback-buttons">
        <button class="feedback-btn ${msg.feedback === "positive" ? "active-positive" : ""}" data-feedback="positive" data-id="${msg.id}" title="도움이 되었습니다">
          <i class="fa-solid fa-thumbs-up"></i>
        </button>
        <button class="feedback-btn ${msg.feedback === "negative" ? "active-negative" : ""}" data-feedback="negative" data-id="${msg.id}" title="개선이 필요합니다">
          <i class="fa-solid fa-thumbs-down"></i>
        </button>
      </div>
    `;
  }

  function handleFeedback(messageId, feedback) {
    const conversation = getCurrentConversation();
    if (!conversation) return;
    conversation.messages = conversation.messages.map((msg) => {
      if (msg.id === messageId) {
        return {
          ...msg,
          feedback: msg.feedback === feedback ? null : feedback,
        };
      }
      return msg;
    });
    saveConversations();
    renderMessages();
  }

  function sendMessage(content) {
    if (!content.trim() || isLoading) return;
    const conversation = getCurrentConversation();
    if (!conversation) return;

    const userMessage = {
      id: Date.now(),
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    };

    conversation.messages.push(userMessage);

    if (conversation.messages.length === 1) {
      conversation.title = content.slice(0, 30);
    }

    conversation.updatedAt = new Date().toISOString();
    saveConversations();
    renderChatHistory();
    renderMessages();
    updateTemplateVisibility();

    isLoading = true;
    showLoadingMessage();

    setTimeout(() => {
      const aiMessage = {
        id: Date.now() + 1,
        role: "assistant",
        content:
          "안녕하세요! 저는 의료 연구 AI 어시스턴트입니다.\n\n질문하신 내용에 대해 답변드리겠습니다. 실제 환경에서는 여기에 LLM API를 연동하여 실시간 응답과 관련 논문 참고문헌을 제공할 수 있습니다.\n\n**주요 내용:**\n- 의학 용어와 약어에 마우스를 올리면 설명을 볼 수 있습니다\n- 참고문헌은 응답 하단에 표시됩니다\n- 응답이 도움이 되셨다면 피드백을 남겨주세요",
        timestamp: new Date().toISOString(),
        references: [
          {
            id: 1,
            title: "Example Medical Research Article",
            authors: "Smith J, et al.",
            journal: "Journal of Medical AI",
            year: 2024,
            doi: "10.1234/example.2024",
            pmid: "12345678",
          },
        ],
      };

      conversation.messages.push(aiMessage);
      conversation.updatedAt = new Date().toISOString();
      saveConversations();

      isLoading = false;
      removeLoadingMessage();
      renderMessages();
    }, 1000);
  }

  function showLoadingMessage() {
    const messagesContainer = document.getElementById("chatMessages");
    if (!messagesContainer) return;
    let messagesContent = document.getElementById("messagesContent");
    if (!messagesContent) {
      messagesContainer.innerHTML = '<div class="chat-messages-content" id="messagesContent"></div>';
      messagesContent = document.getElementById("messagesContent");
    }

  const loadingDiv = document.createElement("div");
  loadingDiv.id = "loadingMessage";
  loadingDiv.className = "loading-message";
  loadingDiv.innerHTML = `
    <div class="message-avatar assistant">
        <i class="fa-solid fa-robot"></i>
      </div>
      <div class="message-bubble assistant">
        <div class="loading-dots">
          <div class="loading-dot"></div>
          <div class="loading-dot"></div>
          <div class="loading-dot"></div>
        </div>
      </div>
    `;

    messagesContent.appendChild(loadingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function removeLoadingMessage() {
    const loading = document.getElementById("loadingMessage");
    if (loading) loading.remove();
  }

  function updateTemplateVisibility() {
    const conversation = getCurrentConversation();
    const container = document.getElementById("quickTemplatesContainer");
    if (!container) return;
    if (conversation && conversation.messages.length === 0) {
      container.style.display = "block";
    } else {
      container.style.display = "none";
    }
  }

  const newChatBtn = document.getElementById("newChatBtn");
  if (newChatBtn) {
    newChatBtn.addEventListener("click", () => {
      const newConv = {
        id: Date.now().toString(),
        title: "새로운 대화",
        messages: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      conversations.unshift(newConv);
      currentConversationId = newConv.id;
      saveConversations();
      renderChatHistory();
      renderMessages();
      updateTemplateVisibility();
    });
  }

  const toggleSidebarBtn = document.getElementById("toggleSidebarBtn");
  if (toggleSidebarBtn) {
    toggleSidebarBtn.addEventListener("click", () => {
      const sidebar = document.getElementById("chatSidebar");
      const toggleIcon = document.getElementById("toggleIcon");
      if (!sidebar || !toggleIcon) return;
      sidebar.classList.toggle("closed");
      const isClosed = sidebar.classList.contains("closed");
      toggleIcon.classList.toggle("fa-bars", isClosed);
      toggleIcon.classList.toggle("fa-xmark", !isClosed);
    });
  }
  (() => {
    const sidebar = document.getElementById("chatSidebar");
    const toggleIcon = document.getElementById("toggleIcon");
    if (sidebar && toggleIcon) {
      const isClosed = sidebar.classList.contains("closed");
      toggleIcon.classList.toggle("fa-bars", isClosed);
      toggleIcon.classList.toggle("fa-xmark", !isClosed);
    }
  })();

  const backToMainBtn = document.getElementById("backToMainBtn");
  if (backToMainBtn) {
    backToMainBtn.addEventListener("click", () => {
      window.location.href = mainUrl;
    });
  }

  const logoutBtn = document.getElementById("sidebarLogoutBtn");
  if (logoutBtn) {
    if (logoutUrl) {
      logoutBtn.addEventListener("click", () => {
        window.location.href = logoutUrl;
      });
    } else {
      logoutBtn.style.display = "none";
    }
  }

  const chatInput = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");
  const chatForm = document.getElementById("chatForm");

  if (sendBtn && sendBtn.disabled) {
    sendBtn.style.background = "#d1d5db";
    sendBtn.style.cursor = "not-allowed";
  }

  if (chatInput && sendBtn) {
    chatInput.addEventListener("input", function () {
      sendBtn.disabled = !this.value.trim();
      sendBtn.style.background = this.value.trim() ? "#3b82f6" : "#d1d5db";
      sendBtn.style.cursor = this.value.trim() ? "pointer" : "not-allowed";
    });
  }

  if (chatForm) {
    chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      if (!chatInput || !sendBtn) return;
      const content = chatInput.value;
      if (content.trim() && !isLoading) {
        sendMessage(content);
        chatInput.value = "";
        sendBtn.disabled = true;
        sendBtn.style.background = "#d1d5db";
      }
    });
  }

  document.querySelectorAll(".template-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (!chatInput || !sendBtn) return;
      chatInput.value = btn.dataset.template || "";
      sendBtn.disabled = !chatInput.value.trim();
      sendBtn.style.background = sendBtn.disabled ? "#d1d5db" : "#3b82f6";
      sendBtn.style.cursor = sendBtn.disabled ? "not-allowed" : "pointer";
      chatInput.focus();
    });
  });

  renderChatHistory();
  renderMessages();
  updateTemplateVisibility();
});
