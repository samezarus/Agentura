/**
 * AI Agent Chat - JavaScript
 *
 * Основная логика веб-чата:
 * - Управление темами (тёмная/светлая)
 * - Загрузка и отображение списка сессий
 * - Отправка и получение сообщений
 * - Создание новых чатов
 * - Удаление сессий
 */

// ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================

let currentSessionId = null;  // ID текущей открытой сессии
const API_BASE = '';         // Базовый URL для API запросов

// ==================== УПРАВЛЕНИЕ БОКОВОЙ ПАНЕЛЬЮ ====================

/**
 * Переключает состояние боковой панели (свернута/развернута)
 */
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const expandBtn = document.getElementById('sidebarExpandBtn');
    const toggleIcon = document.getElementById('sidebarToggleIcon');

    sidebar.classList.toggle('collapsed');

    if (sidebar.classList.contains('collapsed')) {
        expandBtn.classList.add('visible');
        toggleIcon.textContent = '▶';
        localStorage.setItem('sidebarCollapsed', 'true');
    } else {
        expandBtn.classList.remove('visible');
        toggleIcon.textContent = '◀';
        localStorage.setItem('sidebarCollapsed', 'false');
    }
}

/**
 * Инициализирует состояние боковой панели
 */
function initSidebar() {
    const collapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (collapsed) {
        document.getElementById('sidebar').classList.add('collapsed');
        document.getElementById('sidebarExpandBtn').classList.add('visible');
        document.getElementById('sidebarToggleIcon').textContent = '▶';
    }
}

// ==================== УПРАВЛЕНИЕ ТЕМАМИ ====================

/**
 * Иниализирует тему при загрузке страницы
 * Читает сохранённое значение из localStorage
 */
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme);
}

/**
 * Применяет тему к документу
 * @param {string} theme - 'dark' или 'light'
 */
function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    // Обновляем иконку (☼️ для тёмной, ☀️ для светлой)
    document.getElementById('themeIcon').textContent = theme === 'dark' ? '🌙' : '🌙';
}

/**
 * Переключает тему (тёмная → светлая → тёмная)
 */
function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    setTheme(next);
}

// ==================== УПРАВЛЕНИЕ СЕССИЯМИ ====================

/**
 * Загружает список всех сессий с сервера
 * Обновляет боковую панель
 */
function loadSessions() {
    fetch(`${API_BASE}/api/sessions`)
        .then(r => r.json())
        .then(data => {
            // Сортировка: новые чаты (с большим timestamp) сверху
            data.sessions.sort((a, b) => b.id.localeCompare(a.id));

            const list = document.getElementById('sessionsList');
            list.innerHTML = '';
            data.sessions.forEach(session => {
                const item = document.createElement('div');
                item.className = `session-item${session.id === currentSessionId ? ' active' : ''}`;

                // Заголовок чата
                const title = document.createElement('div');
                title.className = 'session-title';
                title.textContent = session.title;
                title.onclick = () => loadChat(session.id);

                // Кнопка меню (три точки)
                const menuBtn = document.createElement('button');
                menuBtn.className = 'session-menu-btn';
                menuBtn.innerHTML = '⋮';
                menuBtn.title = 'Меню';
                menuBtn.onclick = (e) => toggleSessionMenu(e, session.id);

                // Выпадающее меню
                const menu = document.createElement('div');
                menu.className = 'session-menu';
                menu.id = `menu-${session.id}`;

                // Пункт "Удалить"
                const deleteItem = document.createElement('div');
                deleteItem.className = 'session-menu-item danger';
                deleteItem.innerHTML = '🗑 Удалить';
                deleteItem.onclick = (e) => {
                    e.stopPropagation();
                    deleteSession(session.id);
                };

                menu.appendChild(deleteItem);
                item.appendChild(title);
                item.appendChild(menuBtn);
                item.appendChild(menu);
                list.appendChild(item);
            });
        })
        .catch(err => console.error('Error loading sessions:', err));
}

/**
 * Переключает видимость выпадающего меню
 * @param {Event} event - событие клика
 * @param {string} sessionId - ID сессии
 */
function toggleSessionMenu(event, sessionId) {
    event.stopPropagation();

    // Закрываем все другие меню
    document.querySelectorAll('.session-menu.show').forEach(menu => {
        if (menu.id !== `menu-${sessionId}`) {
            menu.classList.remove('show');
        }
    });

    // Переключаем текущее меню
    const menu = document.getElementById(`menu-${sessionId}`);
    menu.classList.toggle('show');
}

/**
 * Удаляет сессию по ID
 * @param {string} sessionId - ID сессии для удаления
 */
function deleteSession(sessionId) {
    if (!confirm('Удалить этот чат?')) return;

    // Закрываем меню
    const menu = document.getElementById(`menu-${sessionId}`);
    if (menu) menu.classList.remove('show');

    fetch(`${API_BASE}/sessions/${sessionId}`, {
        method: 'DELETE'
    })
        .then(r => r.json())
        .then(data => {
            // Если удалили текущий открытый чат - сбрасываем состояние
            if (sessionId === currentSessionId) {
                currentSessionId = null;
                document.getElementById('chatHeader').textContent = 'Выберите чат';
                document.getElementById('messagesContainer').innerHTML =
                    '<div class="empty-state"><div>Выберите чат из списка или создайте новый</div></div>';
                document.getElementById('inputArea').style.display = 'none';
            }
            loadSessions();
        })
        .catch(err => {
            console.error('Error deleting session:', err);
            alert('Ошибка удаления чата');
        });
}

/**
 * Создаёт новую сессию с уникальным ID
 */
function createNewChat() {
    const sessionId = 'chat_' + Date.now();
    loadChat(sessionId);
}

/**
 * Загружает и открывает чат по ID
 * @param {string} sessionId - ID сессии для загрузки
 */
function loadChat(sessionId) {
    currentSessionId = sessionId;
    document.getElementById('chatHeader').textContent = sessionId;
    document.getElementById('inputArea').style.display = 'block';

    fetch(`${API_BASE}/api/sessions/${sessionId}`)
        .then(r => r.json())
        .then(data => {
            displayMessages(data.messages || []);
        })
        .catch(err => {
            console.error('Error loading chat:', err);
            displayMessages([]);
        });

    // Обновляем активное состояние в боковой панели
    loadSessions();
}

// ==================== ОТОБРАЖЕНИЕ СООБЩЕНИЙ ====================

/**
 * Форматирует timestamp в читаемое время
 * @param {string} timestamp - ISO timestamp
 * @returns {string} - отформатированное время (HH:MM:SS)
 */
function formatTime(timestamp) {
    if (!timestamp) return '';
    try {
        const date = new Date(timestamp);

        const dateStr = date.toLocaleDateString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });

        const timeStr = date.toLocaleTimeString('ru-RU', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });

        return `${timeStr} - ${dateStr}`;
    } catch (e) {
        return '';
    }
}

/**
 * Вычисляет время между двумя timestamp
 * @param {string} startTime - начальный ISO timestamp
 * @param {string} endTime - конечный ISO timestamp
 * @returns {string} - отформатированное время (X.Xs)
 */
function calculateResponseTime(startTime, endTime) {
    if (!startTime || !endTime) return '';
    try {
        const start = new Date(startTime).getTime();
        const end = new Date(endTime).getTime();
        const diff = (end - start) / 1000; // в секундах
        if (diff < 1) return `${(diff * 1000).toFixed(0)}ms`;
        return `${diff.toFixed(1)}s`;
    } catch (e) {
        return '';
    }
}

/**
 * Отображает список сообщений в чате
 * @param {Array} messages - массив сообщений с сервера
 */
function displayMessages(messages) {
    const container = document.getElementById('messagesContainer');
    container.innerHTML = '';

    if (messages.length === 0) {
        container.innerHTML = '<div class="empty-state"><div>Начните диалог</div></div>';
        return;
    }

    messages.forEach((msg, index) => {
        const div = document.createElement('div');
        div.className = `message ${msg.from_ === 'user' ? 'user' : 'assistant'}`;
        div.dataset.index = index;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = msg.from_ === 'user' ? 'Вы' : 'AI';

        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'message-content-wrapper';

        const content = document.createElement('div');
        content.className = 'message-content';
        content.innerHTML = formatMessage(msg.message);

        contentWrapper.appendChild(content);

        // Добавляем метаданные (время, модель)
        if (msg.timestamp || msg.model) {
            const meta = document.createElement('div');
            meta.className = 'message-meta';

            const timeStr = formatTime(msg.timestamp);
            const modelStr = msg.model || '';

            // Для сообщений ассистента показываем время отклика
            let responseTimeStr = '';
            if (msg.from_ === 'assistant' && msg.timestamp && index > 0) {
                const prevMsg = messages[index - 1];
                if (prevMsg && prevMsg.timestamp) {
                    responseTimeStr = calculateResponseTime(prevMsg.timestamp, msg.timestamp);
                }
            }

            // Собираем строку метаданных
            const metaParts = [];
            if (timeStr) metaParts.push(timeStr);
            if (modelStr) metaParts.push(modelStr);
            if (responseTimeStr) metaParts.push(`⏱ ${responseTimeStr}`);

            meta.textContent = metaParts.join(' | ');
            contentWrapper.appendChild(meta);
        }

        div.appendChild(avatar);
        div.appendChild(contentWrapper);

        // Добавляем меню только для сообщений пользователя
        if (msg.from_ === 'user') {
            // Обёртка для кнопки и меню (position: relative)
            const menuWrapper = document.createElement('div');
            menuWrapper.style.cssText = 'position: relative; display: flex; align-items: center;';

            // Кнопка меню (три точки)
            const menuBtn = document.createElement('button');
            menuBtn.className = 'message-menu-btn';
            menuBtn.innerHTML = '⋮';
            menuBtn.title = 'Меню';
            menuBtn.onclick = (e) => toggleMessageMenu(e, index);

            // Выпадающее меню
            const menu = document.createElement('div');
            menu.className = 'message-menu';
            menu.id = `msg-menu-${index}`;

            // Пункт "Удалить"
            const deleteItem = document.createElement('div');
            deleteItem.className = 'message-menu-item danger';
            deleteItem.innerHTML = '🗑 Удалить';
            deleteItem.onclick = (e) => {
                e.stopPropagation();
                deleteMessagePair(index);
            };

            menu.appendChild(deleteItem);
            menuWrapper.appendChild(menuBtn);
            menuWrapper.appendChild(menu);
            div.appendChild(menuWrapper);
        }

        container.appendChild(div);
    });

    scrollToBottom();
}

/**
 * Форматирует текст сообщения с поддержкой Markdown
 * Использует marked.js для парсинга Markdown в HTML
 * @param {string} text - исходный текст (может содержать Markdown)
 * @returns {string} - оторматированный HTML
 */
function formatMessage(text) {
    if (typeof marked !== 'undefined') {
        // Парсим Markdown через marked.js
        return marked.parse(escapeHtml(text));
    } else {
        // Резервный вариант если marked не загрузился
        return escapeHtml(text).replace(/\n/g, '<br>');
    }
}

/**
 * Экранирует HTML символы для защиты от XSS
 * @param {string} text - исходный текст
 * @returns {string} - экранированный текст
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Прокручивает контейнер сообщений вниз
 */
function scrollToBottom() {
    const container = document.getElementById('messagesContainer');
    container.scrollTop = container.scrollHeight;
}

/**
 * Удаляет пару сообщений (пользователь + AI)
 * @param {number} index - индекс сообщения пользователя
 */
function deleteMessagePair(index) {
    if (!currentSessionId) return;

    fetch(`${API_BASE}/api/sessions/${currentSessionId}/messages/${index}`, {
        method: 'DELETE'
    })
        .then(r => r.json())
        .then(data => {
            loadChat(currentSessionId);
            loadSessions(); // Обновить заголовок в sidebar
        })
        .catch(err => {
            console.error('Error deleting message:', err);
            alert('Ошибка удаления сообщения');
        });
}

// ==================== ОТПРАВКА СООБЩЕНИЙ ====================

/**
 * Отправляет сообщение пользователя на сервер
 * @param {Event} event - событие отправки формы
 */
function sendMessage(event) {
    event.preventDefault();
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    if (!message || !currentSessionId) return;

    const sendBtn = document.getElementById('sendButton');
    sendBtn.disabled = true;
    sendBtn.innerHTML = '<div class="loading"></div>';

    fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            session_id: currentSessionId,
            prompt: message
        })
    })
        .then(r => r.json())
        .then(data => {
            input.value = '';
            loadChat(currentSessionId);
        })
        .catch(err => {
            console.error('Error sending message:', err);
            alert('Ошибка отправки сообщения');
        })
        .finally(() => {
            sendBtn.disabled = false;
            sendBtn.textContent = 'Отправить';
        });
}

// ==================== УДАЛЕНИЕ СЕССИЙ ====================

/**
 * Удаляет все сессии с подтверждением
 */
function clearAllSessions() {
    if (!confirm('Удалить все чаты?')) return;

    fetch(`${API_BASE}/sessions`, {
        method: 'DELETE'
    })
        .then(r => r.json())
        .then(data => {
            currentSessionId = null;
            document.getElementById('chatHeader').textContent = 'Выберите чат';
            document.getElementById('messagesContainer').innerHTML = '<div class="empty-state"><div>Выберите чат из списка или создайте новый</div></div>';
            document.getElementById('inputArea').style.display = 'none';
            loadSessions();
        })
        .catch(err => {
            console.error('Error clearing sessions:', err);
            alert('Ошибка очистки');
        });
}

// ==================== ИНИЦИАЛИЗАЦИЯ ====================

// Инициализируем боковую панель
initSidebar();

// Иниализируем тему при загрузке
initTheme();

// Загружаем список сессий
loadSessions();

// Обновляем список каждые 5 секунд
setInterval(loadSessions, 5000);

// Обработчик Enter для отправки сообщения
document.getElementById('messageInput')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage(e);
    }
});

/**
 * Переключает видимость выпадающего меню сообщения
 * @param {Event} event - событие клика
 * @param {number} index - индекс сообщения
 */
function toggleMessageMenu(event, index) {
    event.stopPropagation();

    // Закрываем все другие меню
    document.querySelectorAll('.message-menu.show').forEach(menu => {
        if (menu.id !== `msg-menu-${index}`) {
            menu.classList.remove('show');
        }
    });

    // Переключаем текущее меню
    const menu = document.getElementById(`msg-menu-${index}`);
    menu.classList.toggle('show');
}

// Закрытие всех меню при клике вне их
document.addEventListener('click', (e) => {
    // Закрываем меню сессий
    if (!e.target.closest('.session-menu-btn') && !e.target.closest('.session-menu')) {
        document.querySelectorAll('.session-menu.show').forEach(menu => {
            menu.classList.remove('show');
        });
    }
    // Закрываем меню сообщений
    if (!e.target.closest('.message-menu-btn') && !e.target.closest('.message-menu')) {
        document.querySelectorAll('.message-menu.show').forEach(menu => {
            menu.classList.remove('show');
        });
    }
});
