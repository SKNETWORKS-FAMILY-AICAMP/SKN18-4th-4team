document.addEventListener("DOMContentLoaded", () => {
  const root = document.querySelector("[data-chat]");
  if (!root) return;

  const mainUrl = root.dataset.mainUrl || "/main/";
  const logoutUrl = root.dataset.logoutUrl || "";
  const conversationsUrl = root.dataset.conversationsUrl || "/chat/api/conversations/";
  const conversationBaseUrl = conversationsUrl.endsWith("/") ? conversationsUrl : `${conversationsUrl}/`;

  const state = {
    conversations: [],
    messagesCache: {},
    currentConversationId: null,
    isSending: false,
    isMessagesLoading: false,
    activeStreamIntervals: [],
  };

  const user = {
    name: root.dataset.userName || "게스트 연구자",
    email: root.dataset.userEmail || "research@example.com",
  };

  initUserProfile(user);
  hydrateInitialConversations();
  renderChatHistory();
  renderMessages();
  refreshConversations();
  attachStaticHandlers();

  // ---------------------------------------------------------------------------
  function initUserProfile(profile) {
    const userNameEl = document.getElementById("sidebarUserName");
    const userEmailEl = document.getElementById("sidebarUserEmail");
    if (userNameEl) userNameEl.textContent = profile.name;
    if (userEmailEl) userEmailEl.textContent = profile.email;
  }

  function hydrateInitialConversations() {
    const initialConvsElem = document.getElementById("initialConversations");
    if (initialConvsElem && initialConvsElem.textContent) {
      try {
        state.conversations = JSON.parse(initialConvsElem.textContent) || [];
        state.currentConversationId = state.conversations[0]?.id || null;
      } catch {
        state.conversations = [];
      }
    }
  }

  async function refreshConversations({ preserveCurrent = true } = {}) {
    try {
      const res = await fetch(conversationsUrl, { headers: { Accept: "application/json" } });
      if (!res.ok) throw new Error("Failed to load conversations");
      const data = await res.json();
      state.conversations = data.conversations || [];
      if (!state.conversations.length) {
        state.currentConversationId = null;
      } else if (
        !preserveCurrent ||
        !state.currentConversationId ||
        !state.conversations.some((conv) => conv.id === state.currentConversationId)
      ) {
        state.currentConversationId = state.conversations[0].id;
      }
      renderChatHistory();
      if (state.currentConversationId) {
        await loadMessages(state.currentConversationId);
      } else {
        renderMessages();
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function loadMessages(conversationId, { force = false } = {}) {
    if (!conversationId) return;
    if (!force && state.messagesCache[conversationId]) {
      renderMessages();
      return;
    }

    state.isMessagesLoading = true;
    renderMessages();

    try {
      const res = await fetch(`${conversationBaseUrl}${conversationId}/`, {
        headers: { Accept: "application/json" },
      });
      if (!res.ok) throw new Error("Failed to load messages");
      const data = await res.json();
      clearStreamIntervals();
      state.messagesCache[conversationId] = data.messages || [];
    } catch (err) {
      console.error(err);
      state.messagesCache[conversationId] = [];
    } finally {
      state.isMessagesLoading = false;
      renderMessages();
      updateTemplateVisibility();
    }
  }

  function getCurrentConversation() {
    return state.conversations.find((conv) => conv.id === state.currentConversationId) || null;
  }

  function getCurrentMessages() {
    return state.messagesCache[state.currentConversationId] || [];
  }

  function renderChatHistory() {
    const historyContainer = document.getElementById("chatHistory");
    if (!historyContainer) return;
    historyContainer.innerHTML = "";

    if (!state.conversations.length) {
      historyContainer.innerHTML = `
        <div class="conversation-empty">
          아직 대화가 없습니다.<br/>
          <strong>새로운 대화를 시작해 보세요.</strong>
        </div>
      `;
      return;
    }

    state.conversations.forEach((conv) => {
      const div = document.createElement("div");
      div.className = `conversation-item ${conv.id === state.currentConversationId ? "active" : ""}`;
      div.innerHTML = `
        <div class="conversation-item-content">
          <i class="conversation-icon fa-solid fa-comment-dots"></i>
          <div class="conversation-text">
            <div class="conversation-title">${conv.title || "새로운 대화"}</div>
            <div class="conversation-date">${formatDate(conv.updated_at)}</div>
          </div>
        </div>
        <button class="conversation-delete" data-id="${conv.id}">
          <i class="fa-solid fa-trash"></i>
        </button>
      `;

      div.querySelector(".conversation-item-content").addEventListener("click", async () => {
        if (state.currentConversationId === conv.id) return;
        state.currentConversationId = conv.id;
        renderChatHistory();
        await loadMessages(conv.id);
      });

      div.querySelector(".conversation-delete").addEventListener("click", async (e) => {
        e.stopPropagation();
        await deleteConversation(conv.id);
      });

      historyContainer.appendChild(div);
    });
  }

  async function deleteConversation(id) {
    if (!id) return;
    if (!confirm("이 대화를 삭제하시겠습니까?")) return;
    try {
      const res = await fetch(`${conversationBaseUrl}${id}/`, {
        method: "DELETE",
        headers: {
          "X-CSRFToken": getCsrfToken(),
          Accept: "application/json",
        },
      });
      if (!res.ok) throw new Error("delete_failed");
      delete state.messagesCache[id];
      if (state.currentConversationId === id) {
        state.currentConversationId = null;
      }
      await refreshConversations({ preserveCurrent: false });
    } catch (err) {
      console.error(err);
      alert("대화를 삭제하지 못했습니다.");
    }
  }

  function renderMessages() {
    const messagesContainer = document.getElementById("chatMessages");
    if (!messagesContainer) return;

    const currentConv = getCurrentConversation();

    if (!currentConv) {
      messagesContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-content">
            <i class="empty-state-icon fa-solid fa-comments"></i>
            <p>대화를 선택하거나 새로 시작해 주세요.</p>
          </div>
        </div>
      `;
      updateTemplateVisibility();
      return;
    }

    if (state.isMessagesLoading) {
      messagesContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-content">
            <div class="loading-dots">
              <div class="loading-dot"></div>
              <div class="loading-dot"></div>
              <div class="loading-dot"></div>
            </div>
            <p>메시지를 불러오는 중입니다...</p>
          </div>
        </div>
      `;
      return;
    }

    const messages = getCurrentMessages();
    if (!messages.length) {
      messagesContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-content">
            <i class="empty-state-icon fa-solid fa-comments"></i>
            <h2 style="margin-bottom: 0.5rem; color: #6b7280; font-size: 1.125rem;">새로운 대화를 시작하세요</h2>
            <p style="font-size: 0.875rem;">의학 연구 관련 질문을 입력하거나 아래 템플릿을 선택해보세요.</p>
          </div>
        </div>
      `;
      updateTemplateVisibility();
      return;
    }

    messagesContainer.innerHTML = '<div class="chat-messages-content" id="messagesContent"></div>';
    const messagesContent = document.getElementById("messagesContent");

    messages.forEach((msg) => {
      const wrapper = document.createElement("div");
      wrapper.className = `message-wrapper ${msg.role}`;

      if (msg.role === "assistant") {
        wrapper.innerHTML = `
          <div class="message-avatar assistant">
            <i class="fa-solid fa-robot"></i>
          </div>
          <div class="message-content-wrapper">
            <div class="message-bubble assistant">${formatMessageContent(msg.content)}</div>
            ${msg.citations ? renderReferences(msg.citations) : ""}
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
    updateTemplateVisibility();
  }

  function showLoadingMessage() {
    const messagesContainer = document.getElementById("chatMessages");
    if (!messagesContainer) return;
    let messagesContent = document.getElementById("messagesContent");
    if (!messagesContent) {
      messagesContainer.innerHTML = '<div class="chat-messages-content" id="messagesContent"></div>';
      messagesContent = document.getElementById("messagesContent");
    }
    if (document.getElementById("loadingMessage")) return;

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

  function clearStreamIntervals() {
    state.activeStreamIntervals.forEach((id) => clearInterval(id));
    state.activeStreamIntervals = [];
  }

  function streamAssistantMessage(message) {
    const conversationMsgs = state.messagesCache[state.currentConversationId] || [];
    const target = conversationMsgs.find((msg) => msg.id === message.id);
    if (!target) return;
    const fullText = target.content || "";
    target.content = "";
    renderMessages();
    let index = 0;
    const chunk = Math.max(2, Math.floor(fullText.length / 60));
    const interval = setInterval(() => {
      index += chunk;
      target.content = fullText.slice(0, index);
      renderMessages();
      if (index >= fullText.length) {
        clearInterval(interval);
        state.activeStreamIntervals = state.activeStreamIntervals.filter((id) => id !== interval);
      }
    }, 30);
    state.activeStreamIntervals.push(interval);
  }

  function formatMessageContent(content) {
    return content.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>").replace(/\n/g, "<br>");
  }

  function renderReferences(citations) {
    if (!citations || !citations.length) return "";
    let html = '<div class="references-box"><div class="references-title">📚 참고문헌</div>';
    citations.forEach((ref) => {
      html += `
        <div class="reference-item">
          <div class="reference-item-header">
            <span class="reference-number">[${ref.id ?? ""}]</span>
            <div class="reference-content">
              <div class="reference-title">${ref.title || ""}</div>
              <div class="reference-authors">
                ${(ref.authors || "") + (ref.journal ? ` • ${ref.journal}` : "")} ${ref.year ? `(${ref.year})` : ""}
              </div>
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
    const messages = getCurrentMessages();
    const updated = messages.map((msg) => {
      if (msg.id === messageId) {
        return {
          ...msg,
          feedback: msg.feedback === feedback ? "" : feedback,
        };
      }
      return msg;
    });
    state.messagesCache[state.currentConversationId] = updated;
    renderMessages();
  }

  async function createConversation(title = "") {
    try {
      const res = await fetch(conversationsUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
          Accept: "application/json",
        },
        body: JSON.stringify({ title }),
      });
      if (!res.ok) throw new Error("create_failed");
      const data = await res.json();
      state.conversations.unshift(data.conversation);
      state.currentConversationId = data.conversation.id;
      state.messagesCache[state.currentConversationId] = [];
      renderChatHistory();
      renderMessages();
      updateTemplateVisibility();
      await refreshConversations({ preserveCurrent: true });
    } catch (err) {
      console.error(err);
      alert("새로운 대화를 생성하지 못했습니다.");
    }
  }

  async function sendMessage(content) {
    if (!content.trim() || state.isSending) return;
    if (!state.currentConversationId) {
      await createConversation();
      if (!state.currentConversationId) {
        alert("대화를 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.");
        return;
      }
    }

    state.isSending = true;
    if (!state.messagesCache[state.currentConversationId]) {
      state.messagesCache[state.currentConversationId] = [];
    }
    const tempUserMessage = {
      id: `temp-${Date.now()}`,
      role: "user",
      content,
      created_at: new Date().toISOString(),
      citations: [],
      feedback: "",
    };
    state.messagesCache[state.currentConversationId].push(tempUserMessage);
    renderMessages();
    showLoadingMessage();

    try {
      const res = await fetch(`${conversationBaseUrl}${state.currentConversationId}/messages/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
          Accept: "application/json",
        },
        body: JSON.stringify({ content }),
      });
      if (!res.ok) throw new Error("send_failed");
      const data = await res.json();
      // replace temp user message with actual one if provided
      const conversationMsgs = state.messagesCache[state.currentConversationId] || [];
      const tempIndex = conversationMsgs.findIndex((msg) => msg.id === tempUserMessage.id);
      if (tempIndex !== -1) {
        conversationMsgs.splice(tempIndex, 1);
      }
      const newMessages = data.messages || [];
      conversationMsgs.push(...newMessages);
      state.messagesCache[state.currentConversationId] = conversationMsgs;
      renderMessages();
      newMessages.filter((msg) => msg.role === "assistant").forEach(streamAssistantMessage);
      if (data.error) {
        console.warn("LLM 오류:", data.error);
      }
      await refreshConversations({ preserveCurrent: true });
    } catch (err) {
      console.error(err);
      alert("메시지 전송에 실패했습니다.");
      const conversationMsgs = state.messagesCache[state.currentConversationId] || [];
      const tempIndex = conversationMsgs.findIndex((msg) => msg.id === tempUserMessage.id);
      if (tempIndex !== -1) {
        conversationMsgs.splice(tempIndex, 1);
        state.messagesCache[state.currentConversationId] = conversationMsgs;
        renderMessages();
      }
    } finally {
      state.isSending = false;
      removeLoadingMessage();
    }
  }

  function updateTemplateVisibility() {
    const container = document.getElementById("quickTemplatesContainer");
    if (!container) return;
    const messages = getCurrentMessages();
    if (!messages.length) {
      container.style.display = "block";
    } else {
      container.style.display = "none";
    }
  }

  function attachStaticHandlers() {
    const newChatBtn = document.getElementById("newChatBtn");
    if (newChatBtn) {
      newChatBtn.addEventListener("click", () => createConversation());
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

    if (chatInput && sendBtn) {
      chatInput.addEventListener("input", function () {
        sendBtn.disabled = !this.value.trim();
        sendBtn.style.background = this.value.trim() ? "#3b82f6" : "#d1d5db";
        sendBtn.style.cursor = this.value.trim() ? "pointer" : "not-allowed";
      });
    }

    if (chatForm) {
      chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!chatInput || !sendBtn) return;
        const content = chatInput.value;
        if (!content.trim()) return;
        sendBtn.disabled = true;
        sendBtn.style.background = "#d1d5db";
        await sendMessage(content);
        chatInput.value = "";
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
  }

  function formatDate(dateString) {
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) return "";
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return "오늘";
    if (days === 1) return "어제";
    if (days < 7) return `${days}일 전`;
    return date.toLocaleDateString("ko-KR", { month: "short", day: "numeric" });
  }

  function getCsrfToken() {
    const name = "csrftoken";
    const cookies = document.cookie ? document.cookie.split("; ") : [];
    for (const cookie of cookies) {
      const [key, value] = cookie.split("=");
      if (key === name) {
        return decodeURIComponent(value);
      }
    }
    return "";
  }
});
