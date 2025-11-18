document.addEventListener("DOMContentLoaded", () => {
  const root = document.querySelector("[data-chat]");
  if (!root) return;

  const mainUrl = root.dataset.mainUrl || "/main/";
  const logoutUrl = root.dataset.logoutUrl || "";
  const conversationsUrl = root.dataset.conversationsUrl || "/chat/api/conversations/";
  const conversationBaseUrl = conversationsUrl.endsWith("/") ? conversationsUrl : `${conversationsUrl}/`;
  const messageFeedbackBaseUrl = "/chat/api/messages/";
  const conceptGraphBaseUrl = "/chat/api/messages/";
  const relatedQuestionsBaseUrl = "/chat/api/messages/";

  const state = {
    conversations: [],
    messagesCache: {},
    currentConversationId: null,
    isSending: false,
    isMessagesLoading: false,
    activeStreamIntervals: [],
    pendingFeedbackMessageId: null,
  };

  const user = {
    name: root.dataset.userName || "게스트 연구자",
    email: root.dataset.userEmail || "research@example.com",
  };

  const feedbackModal = document.getElementById("feedbackModal");
  const feedbackForm = document.getElementById("feedbackForm");
  const feedbackTextarea = document.getElementById("feedbackReasonText");
  const feedbackTextareaWrapper = document.getElementById("feedbackTextareaWrapper");
  const feedbackCancelBtn = document.getElementById("feedbackCancelBtn");
  const feedbackSubmitBtn = document.getElementById("feedbackSubmitBtn");
  const feedbackRemoveBtn = document.getElementById("feedbackRemoveBtn");
  const relatedModal = document.getElementById("relatedQuestionsModal");
  const relatedModalBody = document.getElementById("relatedQuestionsModalBody");
  const relatedModalCloseBtn = document.getElementById("relatedQuestionsModalCloseBtn");
  const relatedModalBackdrop = relatedModal ? relatedModal.querySelector(".related-modal__backdrop") : null;
  initUserProfile(user);
  hydrateInitialConversations();
  renderChatHistory();
  renderMessages();
  refreshConversations();
  attachStaticHandlers();
  if (relatedModalCloseBtn) {
    relatedModalCloseBtn.addEventListener("click", closeRelatedQuestionsModal);
  }
  if (relatedModalBackdrop) {
    relatedModalBackdrop.addEventListener("click", closeRelatedQuestionsModal);
  }
  if (relatedModalBody) {
    relatedModalBody.addEventListener("click", handleRelatedQuestionSelection);
  }

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
      const res = await fetch(conversationsUrl, {
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      });
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
        credentials: "same-origin",
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
        credentials: "same-origin",
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
        const shouldHideGraph =
          !msg.citations ||
          !msg.citations.length ||
          (msg.content || "").includes("답변을 생성하지 못했습니다");
        const referencesHtml = msg.citations
          ? renderReferences(
              msg.citations,
              msg.reference_type || msg.metadata?.reference_type || "internal"
            )
          : "";
        wrapper.innerHTML = `
          <div class="message-avatar assistant">
            <i class="fa-solid fa-robot"></i>
          </div>
          <div class="message-content-wrapper">
            <div class="message-bubble assistant">${formatMessageContent(msg.content)}</div>
            ${referencesHtml}
            <div class="message-footer">
              ${renderFeedbackButtons(msg)}
              ${
                shouldHideGraph
                  ? ""
                  : `<div class="message-tool-buttons">
                      <button class="message-tool-btn message-graph-btn" type="button" data-message-id="${msg.id}">
                        <i class="fa-solid fa-diagram-project"></i>
                        그래프 그리기
                      </button>
                      <button class="message-tool-btn message-related-btn" type="button" data-message-id="${msg.id}">
                        <i class="fa-solid fa-wand-magic-sparkles"></i>
                        연관 질문 생성
                      </button>
                    </div>`
              }
            </div>
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
        const graphBtn = wrapper.querySelector(".message-graph-btn");
        if (graphBtn) {
          graphBtn.addEventListener("click", () => handleGraphButtonClick(graphBtn, msg.id));
        }
        const relatedBtn = wrapper.querySelector(".message-related-btn");
        if (relatedBtn) {
          relatedBtn.addEventListener("click", () => handleRelatedQuestionsButtonClick(msg.id));
        }
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

  function escapeHtml(text = "") {
    const map = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return String(text).replace(/[&<>"']/g, (char) => map[char]);
  }

  function renderReferences(citations, referenceType = "internal") {
    if (!citations || !citations.length) return "";
    const label = referenceType === "external" ? "참고 링크" : "참고 문헌";
    let html = `<div class="references-box"><div class="references-title">📚 ${label}</div>`;
    citations.forEach((ref) => {
      const titleText = typeof ref.title === "string" ? ref.title : "";
      const urlMatch = titleText.match(/https?:\/\/\S+/);
      const urlFromTitle = urlMatch ? urlMatch[0] : "";
      const urlLink = urlFromTitle
        || (typeof ref.url === "string" && /^https?:\/\//.test(ref.url) ? ref.url : "");
      html += `
        <div class="reference-item">
          <div class="reference-item-header">
            <span class="reference-number">[${ref.id ?? ""}]</span>
            <div class="reference-content">
              <div class="reference-title">
                ${ref.title || ""}
                ${
                  urlLink
                    ? `<a href="${urlLink}" target="_blank" rel="noopener" class="reference-url-link" title="새 창에서 열기">
                        <i class="fa-solid fa-arrow-up-right-from-square"></i>
                      </a>`
                    : ""
                }
              </div>
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
        <button class="feedback-btn ${msg.feedback === "positive" ? "active-positive" : ""}" data-feedback="positive" data-message-id="${msg.id}" title="도움이 되었습니다">
          <i class="fa-solid fa-thumbs-up"></i>
        </button>
        <button class="feedback-btn ${msg.feedback === "negative" ? "active-negative" : ""}" data-feedback="negative" data-message-id="${msg.id}" title="개선이 필요합니다">
          <i class="fa-solid fa-thumbs-down"></i>
        </button>
      </div>
    `;
  }

  /**
   * handleFeedback 함수는 메시지에 대한 피드백(좋아요/싫어요) 버튼 클릭 이벤트를 처리합니다.
   * @param {string|number} messageId - 피드백할 메시지의 ID
   * @param {"positive"|"negative"} feedbackType - 피드백 종류(positive: 좋아요, negative: 싫어요)
   */
  function handleFeedback(messageId, feedbackType) {
    // 현재 메시지 목록을 불러옴
    const messages = getCurrentMessages();
    // 대상 메시지 객체를 검색
    const target = messages.find((msg) => msg.id === messageId);
    if (!target) return;

    if (feedbackType === "positive") {
      const nextValue = target.feedback === "positive" ? "" : "positive";
      submitFeedback(messageId, nextValue, nextValue === "positive" ? "positive" : "", "");
    } else {
      // '싫어요'를 누르면 상세 사유 입력 모달 오픈
      openFeedbackModal(messageId, target);
    }
  }

  async function createConversation(title = "") {
    try {
      const res = await fetch(conversationsUrl, {
        method: "POST",
        credentials: "same-origin",
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

  /**
   * sendMessage 함수는 채팅 입력란의 사용자 메시지를 서버에 전송하고 UI를 최신 상태로 업데이트하는 비동기 함수
   * - 입력값 검증(공백, 중복전송 방지)
   * - 대화방이 없으면 새 대화 생성
   * - 임시 사용자 메시지 렌더링 및 로딩 메시지 표시
   * - 서버로 메시지 POST 요청 전송
   * - 정상 응답 시 임시 메시지를 실제 메시지로 대체, assistant 메시지 스트리밍 처리
   * - 오류 발생 시 임시 메시지 제거 및 메시지 전송 실패 알림
   * - 항상 로딩 상태, 전송상태 초기화
   * @param {string} content - 사용자가 입력한 메시지
   */
  async function sendMessage(content) {
    // 입력이 없거나 이미 전송 중이면 리턴
    if (!content.trim() || state.isSending) return;

    // 현재 대화방이 없으면 생성
    if (!state.currentConversationId) {
      await createConversation();
      if (!state.currentConversationId) {
        alert("대화를 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.");
        return;
      }
    }

    state.isSending = true;
    // 메시지 캐시가 없으면 생성
    if (!state.messagesCache[state.currentConversationId]) {
      state.messagesCache[state.currentConversationId] = [];
    }
    // 임시 사용자 메시지 객체 생성 및 캐시에 추가(UX 즉각반응용)
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
      // 서버에 메시지 전송 요청
      const res = await fetch(`${conversationBaseUrl}${state.currentConversationId}/messages/`, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
          Accept: "application/json",
        },
        body: JSON.stringify({ content }),
      });
      if (!res.ok) throw new Error("send_failed");

      const data = await res.json();

      // 임시 메시지를 대체/제거
      const conversationMsgs = state.messagesCache[state.currentConversationId] || [];
      const tempIndex = conversationMsgs.findIndex((msg) => msg.id === tempUserMessage.id);
      if (tempIndex !== -1) {
        conversationMsgs.splice(tempIndex, 1);
      }

      // 서버에서 받은 실제 메시지 추가
      const newMessages = data.messages || [];
      conversationMsgs.push(...newMessages);
      state.messagesCache[state.currentConversationId] = conversationMsgs;
      renderMessages();
      // 어시스턴트 메시지는 스트리밍 적용
      newMessages.filter((msg) => msg.role === "assistant").forEach(streamAssistantMessage);
      // 오류 메시지 있으면 콘솔 경고
      if (data.error) {
        console.warn("LLM 오류:", data.error);
      }
      // 대화 목록 새로고침
      await refreshConversations({ preserveCurrent: true });
    } catch (err) {
      // 전송 실패 시 임시 메시지 제거 후 UI 갱신
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
      // 전송 상태 및 로딩 메시지 초기화
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

    if (feedbackCancelBtn) {
      feedbackCancelBtn.addEventListener("click", () => closeFeedbackModal());
    }
    if (feedbackSubmitBtn) {
      feedbackSubmitBtn.addEventListener("click", submitNegativeFeedback);
    }
    if (feedbackRemoveBtn) {
      feedbackRemoveBtn.addEventListener("click", async () => {
        if (!state.pendingFeedbackMessageId) return closeFeedbackModal();
        await submitFeedback(state.pendingFeedbackMessageId, "");
        closeFeedbackModal();
      });
    }
    if (feedbackForm) {
      feedbackForm.querySelectorAll("input[name='feedbackReason']").forEach((radio) => {
        radio.addEventListener("change", updateFeedbackTextareaVisibility);
      });
    }
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

  async function submitFeedback(messageId, feedback, reasonCode = "", reasonText = "") {
    if (!messageId || !state.currentConversationId) return;
    try {
      const res = await fetch(`${messageFeedbackBaseUrl}${messageId}/feedback/`, {
        method: "PATCH",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
          Accept: "application/json",
        },
        body: JSON.stringify({ feedback, reason_code: reasonCode, reason_text: reasonText }),
      });
      if (!res.ok) throw new Error("feedback_failed");
      const data = await res.json();
      const updated = data.message;
      const newMessages = getCurrentMessages().map((msg) =>
        msg.id === updated.id ? { ...msg, ...updated } : msg
      );
      state.messagesCache[state.currentConversationId] = newMessages;
      renderMessages();
    } catch (err) {
      console.error(err);
      alert("피드백을 저장하지 못했습니다.");
    }
  }

  function openFeedbackModal(messageId, messageData = {}) {
    if (!feedbackModal) return;
    state.pendingFeedbackMessageId = messageId;
    feedbackModal.classList.remove("hidden");
    if (feedbackForm) {
      const code = messageData.feedback_reason_code || "";
      feedbackForm.querySelectorAll("input[name='feedbackReason']").forEach((radio) => {
        radio.checked = radio.value === code;
      });
    }
    if (feedbackTextarea) {
      feedbackTextarea.value = messageData.feedback_reason_text || "";
    }
    updateFeedbackTextareaVisibility();
  }

  function closeFeedbackModal() {
    if (!feedbackModal) return;
    feedbackModal.classList.add("hidden");
    state.pendingFeedbackMessageId = null;
    if (feedbackForm) {
      feedbackForm.querySelectorAll("input[name='feedbackReason']").forEach((radio) => {
        radio.checked = false;
      });
    }
    if (feedbackTextarea) feedbackTextarea.value = "";
    updateFeedbackTextareaVisibility();
  }

  function updateFeedbackTextareaVisibility() {
    if (!feedbackForm || !feedbackTextareaWrapper) return;
    const otherSelected = !!feedbackForm.querySelector("input[name='feedbackReason'][value='other']:checked");
    if (otherSelected) {
      feedbackTextareaWrapper.classList.remove("hidden");
    } else {
      feedbackTextareaWrapper.classList.add("hidden");
    }
  }

  async function submitNegativeFeedback() {
    if (!state.pendingFeedbackMessageId) return;
    if (!feedbackForm) return;
    const selected = feedbackForm.querySelector("input[name='feedbackReason']:checked");
    if (!selected) {
      alert("사유를 선택해 주세요.");
      return;
    }
    let reasonText = "";
    if (selected.value === "other") {
      reasonText = (feedbackTextarea?.value || "").trim();
      if (!reasonText) {
        alert("기타 사유를 입력해 주세요.");
        return;
      }
    }
    await submitFeedback(state.pendingFeedbackMessageId, "negative", selected.value, reasonText);
    closeFeedbackModal();
  }

  function handleRelatedQuestionsButtonClick(messageId) {
    if (!messageId || !relatedModal || !relatedModalBody) return;
    openRelatedQuestionsModal(messageId, { isLoading: true });
    fetchRelatedQuestions(messageId)
      .then((questions) => {
        renderRelatedQuestionsModal(messageId, { questions });
      })
      .catch((err) => {
        console.error(err);
        renderRelatedQuestionsModal(messageId, {
          error: "연관 질문을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.",
        });
      });
  }

  function openRelatedQuestionsModal(messageId, options = {}) {
    if (!relatedModal || !relatedModalBody) return;
    relatedModalBody.dataset.messageId = messageId || "";
    renderRelatedQuestionsModal(messageId, options);
    relatedModal.classList.remove("hidden");
  }

  function renderRelatedQuestionsModal(messageId, { isLoading = false, questions = [], error = "" } = {}) {
    if (!relatedModalBody) return;
    if (relatedModalBody.dataset.messageId !== String(messageId)) return;
    let questionsHtml = "";
    if (error) {
      questionsHtml = `<p class="related-modal__error">${error}</p>`;
    } else if (isLoading) {
      questionsHtml = `
        <div class="related-modal__loading">
          <div class="related-modal__spinner"></div>
          <p>연관 질문을 생성하는 중입니다...</p>
        </div>
      `;
    } else if (questions && questions.length) {
      questionsHtml = `
        <ol class="related-modal__questions">
          ${questions
            .map(
              (question) => `
            <li class="related-modal__question-item">
              <button
                type="button"
                class="related-modal__question-button"
                data-question="${encodeURIComponent(question)}"
              >
                <i class="fa-solid fa-circle-question"></i>
                <span>${escapeHtml(question)}</span>
              </button>
            </li>
          `
            )
            .join("")}
        </ol>
      `;
    } else {
      questionsHtml = `<p class="related-modal__empty">생성된 질문이 없습니다.</p>`;
    }

    relatedModalBody.innerHTML = `
      <div class="related-modal__section">
        <div class="related-modal__section-title">연관 질문 추천</div>
        ${questionsHtml}
      </div>
    `;
  }

  function closeRelatedQuestionsModal() {
    if (!relatedModal || !relatedModalBody) return;
    relatedModal.classList.add("hidden");
    relatedModalBody.dataset.messageId = "";
    relatedModalBody.innerHTML = "";
  }

  function handleRelatedQuestionSelection(event) {
    if (!relatedModalBody) return;
    const target = event.target;
    if (!(target instanceof Element)) return;
    const button = target.closest(".related-modal__question-button");
    if (!button) return;
    const encoded = button.dataset.question || "";
    let question = "";
    try {
      question = decodeURIComponent(encoded);
    } catch {
      question = encoded;
    }
    if (!question) return;
    applyRelatedQuestionToInput(question);
    closeRelatedQuestionsModal();
  }

  async function handleGraphButtonClick(button, messageId) {
    if (!button || !messageId) return;
    button.disabled = true;
    button.classList.add("graph-btn-loading");
    if (window.chatGraph && typeof window.chatGraph.showLoading === "function") {
      window.chatGraph.showLoading();
    }
    try {
      const graphCode = await fetchConceptGraph(messageId);
      if (window.chatGraph && typeof window.chatGraph.open === "function") {
        window.chatGraph.open(graphCode);
      }
    } catch (err) {
      console.error(err);
      alert("그래프를 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.");
      if (window.chatGraph && typeof window.chatGraph.close === "function") {
        window.chatGraph.close();
      }
    } finally {
      button.disabled = false;
      button.classList.remove("graph-btn-loading");
    }
  }

  async function fetchConceptGraph(messageId) {
    const url = `${conceptGraphBaseUrl}${messageId}/concept-graph/`;
    const res = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
        Accept: "application/json",
      },
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || "graph_fetch_failed");
    }
    const data = await res.json();
    return data.graph || "";
  }

  async function fetchRelatedQuestions(messageId) {
    const url = `${relatedQuestionsBaseUrl}${messageId}/related-questions/`;
    const res = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
        Accept: "application/json",
      },
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || "related_questions_failed");
    }
    const questions = Array.isArray(data.questions) ? data.questions : [];
    return questions.map((q) => (typeof q === "string" ? q.trim() : String(q))).filter(Boolean).slice(0, 3);
  }

  function getMessageById(messageId) {
    const messages = getCurrentMessages();
    return messages.find((msg) => String(msg.id) === String(messageId)) || null;
  }

  function applyRelatedQuestionToInput(question) {
    const chatInput = document.getElementById("chatInput");
    const sendBtn = document.getElementById("sendBtn");
    if (!chatInput || !sendBtn) return;
    chatInput.value = question;
    sendBtn.disabled = !chatInput.value.trim();
    sendBtn.style.background = sendBtn.disabled ? "#d1d5db" : "#3b82f6";
    sendBtn.style.cursor = sendBtn.disabled ? "not-allowed" : "pointer";
    chatInput.focus();
  }
});
