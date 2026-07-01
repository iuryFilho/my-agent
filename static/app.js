document.addEventListener("DOMContentLoaded", () => {
    // UI Elements
    const chatForm = document.getElementById("chat-form");
    const userInput = document.getElementById("user-input");
    const chatMessages = document.getElementById("chat-messages");
    const thinkingIndicator = document.getElementById("thinking-indicator");
    const thinkingText = document.getElementById("thinking-text");
    
    const agentModel = document.getElementById("agent-model");
    const agentProvider = document.getElementById("agent-provider");
    const agentMsgCount = document.getElementById("agent-msg-count");
    
    const toolsList = document.getElementById("tools-list");
    const filesList = document.getElementById("files-list");
    
    const refreshFilesBtn = document.getElementById("refresh-files-btn");
    const clearChatBtn = document.getElementById("clear-chat-btn");

    // CLI Terminal-like history state
    let commandHistory = [];
    let historyIndex = -1;
    let currentInputDraft = "";

    // Autocomplete state
    let availableCommands = [];
    let filteredCommands = [];
    let workspaceFiles = [];
    let activeSuggestionIndex = -1;
    const autocompleteDropdown = document.getElementById("autocomplete-dropdown");

    // Initialize UI icons
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    // Load initial data
    loadAgentStatus();
    loadAgentTools();
    loadWorkspaceFiles();
    loadAvailableCommands();

    // Event Listeners
    chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        sendMessage();
    });

    refreshFilesBtn.addEventListener("click", () => {
        loadWorkspaceFiles();
    });

    clearChatBtn.addEventListener("click", () => {
        executeClear();
    });

    // Toggle sidebar sections
    const toggleBtns = document.querySelectorAll(".toggle-section-btn");
    toggleBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const section = btn.closest(".sidebar-section");
            section.classList.toggle("collapsed");
        });
    });

    // Handle Arrow Up and Down to move through command history or autocomplete suggestions
    userInput.addEventListener("keydown", (e) => {
        const dropdownVisible = !autocompleteDropdown.classList.contains("hidden");
        
        if (e.key === "ArrowUp") {
            if (dropdownVisible) {
                e.preventDefault();
                if (activeSuggestionIndex > 0) {
                    activeSuggestionIndex--;
                } else {
                    activeSuggestionIndex = filteredCommands.length - 1;
                }
                renderSuggestions(filteredCommands);
            } else {
                if (commandHistory.length === 0) return;
                e.preventDefault();
                if (historyIndex === -1) {
                    currentInputDraft = userInput.value;
                }
                if (historyIndex < commandHistory.length - 1) {
                    historyIndex++;
                    userInput.value = commandHistory[commandHistory.length - 1 - historyIndex];
                }
            }
        } else if (e.key === "ArrowDown") {
            if (dropdownVisible) {
                e.preventDefault();
                if (activeSuggestionIndex < filteredCommands.length - 1) {
                    activeSuggestionIndex++;
                } else {
                    activeSuggestionIndex = 0;
                }
                renderSuggestions(filteredCommands);
            } else {
                e.preventDefault();
                if (historyIndex > 0) {
                    historyIndex--;
                    userInput.value = commandHistory[commandHistory.length - 1 - historyIndex];
                } else if (historyIndex === 0) {
                    historyIndex = -1;
                    userInput.value = currentInputDraft;
                    currentInputDraft = "";
                }
            }
        } else if (e.key === "Enter") {
            if (dropdownVisible && activeSuggestionIndex !== -1) {
                e.preventDefault();
                const sug = filteredCommands[activeSuggestionIndex];
                selectSuggestion(sug.name, sug.isFile);
            }
        } else if (e.key === "Escape") {
            if (dropdownVisible) {
                e.preventDefault();
                hideSuggestions();
            }
        } else if (e.key === "Tab") {
            if (dropdownVisible) {
                e.preventDefault();
                const idx = activeSuggestionIndex !== -1 ? activeSuggestionIndex : 0;
                const sug = filteredCommands[idx];
                selectSuggestion(sug.name, sug.isFile);
            }
        }
    });

    // Handle user input changes to trigger autocomplete dropdown
    userInput.addEventListener("input", () => {
        const val = userInput.value;
        if (val.startsWith("/")) {
            const parts = val.split(" ");
            const firstWord = parts[0];
            
            // Se for /view ou /delete, sugere nomes de arquivos do workspace
            if (parts.length > 1 && (firstWord === "/view" || firstWord === "/delete")) {
                const search = parts.slice(1).join(" ");
                filteredCommands = workspaceFiles
                    .filter(file => file.name.toLowerCase().startsWith(search.toLowerCase()))
                    .map(file => ({
                        name: file.name,
                        description: `Arquivo (${formatBytes(file.size)})`,
                        isFile: true
                    }));
                
                if (filteredCommands.length > 0) {
                    renderSuggestions(filteredCommands);
                } else {
                    hideSuggestions();
                }
            } else {
                // Sugestão padrão de comandos
                filteredCommands = availableCommands.filter(cmd => 
                    cmd.name.startsWith(firstWord)
                );
                
                if (filteredCommands.length > 0) {
                    renderSuggestions(filteredCommands);
                } else {
                    hideSuggestions();
                }
            }
        } else {
            hideSuggestions();
        }
    });

    // Hide suggestions if user clicks outside the form
    document.addEventListener("click", (e) => {
        if (!chatForm.contains(e.target)) {
            hideSuggestions();
        }
    });

    function renderSuggestions(cmds) {
        autocompleteDropdown.innerHTML = "";
        cmds.forEach((cmd, idx) => {
            const item = document.createElement("div");
            item.classList.add("autocomplete-item");
            if (idx === activeSuggestionIndex) {
                item.classList.add("active");
            }
            item.innerHTML = `
                <span class="command-name">${cmd.name}</span>
                <span class="command-desc">${cmd.description}</span>
            `;
            item.addEventListener("click", () => {
                selectSuggestion(cmd.name, cmd.isFile);
            });
            autocompleteDropdown.appendChild(item);
        });
        autocompleteDropdown.classList.remove("hidden");
    }

    function selectSuggestion(name, isFile = false) {
        if (isFile) {
            const val = userInput.value;
            const command = val.split(" ")[0];
            userInput.value = command + " " + name;
        } else {
            userInput.value = name + " ";
        }
        userInput.focus();
        hideSuggestions();
        
        if (!isFile) {
            const event = new Event('input', { bubbles: true });
            userInput.dispatchEvent(event);
        }
    }

    function hideSuggestions() {
        autocompleteDropdown.classList.add("hidden");
        filteredCommands = [];
        activeSuggestionIndex = -1;
    }

    async function loadAvailableCommands() {
        try {
            const response = await fetch("/api/commands");
            if (response.ok) {
                const data = await response.json();
                availableCommands = data.commands || [];
            }
        } catch (error) {
            console.error("Erro ao carregar comandos para autocompletar:", error);
        }
    }

    // Send User Message
    async function sendMessage() {
        hideSuggestions();
        const messageText = userInput.value.trim();
        if (!messageText) return;

        // Push to history
        if (commandHistory.length === 0 || commandHistory[commandHistory.length - 1] !== messageText) {
            commandHistory.push(messageText);
        }
        historyIndex = -1;
        currentInputDraft = "";

        // Clear input field immediately
        userInput.value = "";

        // Remove welcome screen if it exists
        const welcomeScreen = document.querySelector(".system-welcome");
        if (welcomeScreen) {
            welcomeScreen.remove();
        }

        // Render User Message in Chat
        appendMessage("user", messageText);
        scrollToBottom();

        // Show thinking indicator
        showThinking("Processando");

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ message: messageText })
            });

            if (!response.ok) {
                throw new Error("Erro na requisição ao servidor.");
            }

            const data = await response.json();
            
            // Hide thinking indicator
            hideThinking();
            
            let role;
            if (data.is_command) {
                role = "system";
            } else {
                role = "assistant";
            }
            
            appendMessage(role, data.response);
            scrollToBottom();

            // Reload sidebar details
            loadAgentStatus();
            loadWorkspaceFiles();

        } catch (error) {
            hideThinking();
            appendMessage("assistant", `Ocorreu um erro: ${error.message}`);
            scrollToBottom();
        }
    }

    // Clear history CLI equivalent
    async function executeClear() {
        showThinking("Limpando conversa");
        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ message: "/clear" })
            });
            hideThinking();
            if (response.ok) {
                chatMessages.innerHTML = "";
                loadAgentStatus();
                appendMessage("assistant", "Histórico de conversa limpo.");
            }
        } catch (error) {
            hideThinking();
            console.error("Erro ao limpar conversa:", error);
        }
    }

    // Append Message helper
    function appendMessage(role, text) {
        const msgDiv = document.createElement("div");
        msgDiv.classList.add("message", role);

        // Avatar SVG
        const avatarDiv = document.createElement("div");
        avatarDiv.classList.add("avatar");
        // Usar engrenagem para mensagens de sistema
        let iconName;
        switch (role) {
            case "user":
                iconName = "user";
                break;
            case "assistant":
                iconName = "bot";
                break;
            case "system":
                iconName = "cpu";
                break;
            default:
                iconName = "box";
                break;
        }
        avatarDiv.innerHTML = `<i data-lucide="${iconName}"></i>`;

        // Content
        const contentDiv = document.createElement("div");
        contentDiv.classList.add("message-content");
        contentDiv.innerHTML = formatMessageText(text);

        msgDiv.appendChild(avatarDiv);
        msgDiv.appendChild(contentDiv);
        
        chatMessages.appendChild(msgDiv);
        
        // Render new icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons({
                attrs: {
                    class: 'lucide-icon'
                },
                nameAttr: 'data-lucide',
                node: msgDiv
            });
        }
    }

    // Parse markdown text using the marked.js library with local fallback
    function formatMessageText(text) {
        if (!text) return "";
        
        if (typeof marked === 'undefined') {
            // Fallback para formatação simples em caso de falha de conexão (offline)
            let escaped = text
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;");
            
            escaped = escaped.replace(/```([\s\S]*?)```/g, (match, p1) => {
                return `<pre><code>${p1.trim()}</code></pre>`;
            });
            
            escaped = escaped.replace(/`([^`\n]+)`/g, "<code>$1</code>");
            escaped = escaped.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" class="chat-link">$1</a>');
            escaped = escaped.replace(/\n/g, "<br>");
            return escaped;
        }
        
        try {
            // Parse markdown to HTML
            let parsed = marked.parse(text);
            
            // Post-process links to open in a new tab and apply custom class
            const tempDiv = document.createElement("div");
            tempDiv.innerHTML = parsed;
            const links = tempDiv.querySelectorAll("a");
            links.forEach(link => {
                link.setAttribute("target", "_blank");
                link.classList.add("chat-link");
            });
            
            return tempDiv.innerHTML;
        } catch (err) {
            console.error("Error parsing markdown:", err);
            return text;
        }
    }

    // Load agent general details
    async function loadAgentStatus() {
        try {
            const response = await fetch("/api/status");
            if (response.ok) {
                const data = await response.json();
                agentModel.textContent = data.model;
                agentProvider.textContent = data.provider;
                agentMsgCount.textContent = data.total_messages;
            }
        } catch (error) {
            console.error("Erro ao carregar status do agente:", error);
        }
    }

    // Load registered tools in sidebar
    async function loadAgentTools() {
        try {
            const response = await fetch("/api/tools");
            if (response.ok) {
                const data = await response.json();
                toolsList.innerHTML = "";
                if (data.tools.length === 0) {
                    toolsList.innerHTML = '<div class="no-files">Nenhuma ferramenta ativa</div>';
                    return;
                }
                data.tools.forEach(tool => {
                    const toolItem = document.createElement("div");
                    toolItem.classList.add("tool-item");
                    toolItem.innerHTML = `
                        <span class="tool-name">
                            <i data-lucide="play" class="small-icon"></i>${tool.name}
                        </span>
                        <span class="tool-desc">${tool.description}</span>
                    `;
                    toolsList.appendChild(toolItem);
                });
                if (typeof lucide !== 'undefined') {
                    lucide.createIcons({ node: toolsList });
                }
            }
        } catch (error) {
            console.error("Erro ao carregar ferramentas:", error);
        }
    }

    // Load workspace files in sidebar
    async function loadWorkspaceFiles() {
        try {
            const response = await fetch("/api/files");
            if (response.ok) {
                const data = await response.json();
                workspaceFiles = data.files || [];
                filesList.innerHTML = "";
                if (data.files.length === 0) {
                    filesList.innerHTML = '<div class="no-files">Nenhum arquivo no workspace</div>';
                    return;
                }
                data.files.forEach(file => {
                    const fileItem = document.createElement("div");
                    fileItem.classList.add("file-item");
                    fileItem.innerHTML = `
                        <div class="file-info">
                            <i data-lucide="file-text"></i>
                            <span class="file-name" title="${file.path}">${file.name}</span>
                        </div>
                        <span class="file-size">${formatBytes(file.size)}</span>
                    `;
                    fileItem.addEventListener("dblclick", () => {
                        insertFilenameIntoInput(file.name);
                    });
                    filesList.appendChild(fileItem);
                });
                if (typeof lucide !== 'undefined') {
                    lucide.createIcons({ node: filesList });
                }
            }
        } catch (error) {
            console.error("Erro ao carregar arquivos:", error);
        }
    }

    // Helper to insert filename into user input
    function insertFilenameIntoInput(filename) {
        const val = userInput.value;
        if (val.length > 0 && !val.endsWith(" ")) {
            userInput.value = val + " " + filename;
        } else {
            userInput.value = val + filename;
        }
        userInput.focus();
        
        // Trigger input event for autocomplete suggestion logic
        const event = new Event('input', { bubbles: true });
        userInput.dispatchEvent(event);
    }

    // Size formatting helper
    function formatBytes(bytes, decimals = 1) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    // Thinking controller
    function showThinking(text) {
        thinkingText.textContent = text;
        thinkingIndicator.classList.remove("hidden");
        scrollToBottom();
    }

    function hideThinking() {
        thinkingIndicator.classList.add("hidden");
    }

    // Autoscroll
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});
