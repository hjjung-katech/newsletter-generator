/**
 * Newsletter Generator Web App
 * Frontend JavaScript for handling user interactions and API calls
 */

class NewsletterApp {
    constructor() {
        this.currentJobId = null;
        this.pollInterval = null;
        this.adminTokenStorageKey = 'newsletter-admin-api-token';
        this.savedPresets = [];
        this.selectedPresetId = '';
        this.init();
    }

    init() {
        this.bindEvents();
        this.hydrateAdminToken();
        this.toggleInputMethod();
        this.toggleScheduleSettings(document.getElementById('enableSchedule').checked);
        this.updateScheduleOptions();
        this.syncPresetActions();
        this.loadPresets();
    }

    bindEvents() {
        // Tab switching
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => this.switchTab(e.target.id));
        });

        // Input method switching
        document.querySelectorAll('input[name="inputMethod"]').forEach(radio => {
            radio.addEventListener('change', () => this.toggleInputMethod());
        });

        // Schedule checkbox
        document.getElementById('enableSchedule').addEventListener('change', (e) => {
            this.toggleScheduleSettings(e.target.checked);
        });

        // Frequency change
        document.getElementById('frequency').addEventListener('change', () => {
            this.updateScheduleOptions();
        });

        // Action buttons
        document.getElementById('generateBtn').addEventListener('click', () => this.generateNewsletter());
        document.getElementById('previewBtn').addEventListener('click', () => this.previewNewsletter());
        document.getElementById('downloadBtn').addEventListener('click', () => this.downloadNewsletter());
        document.getElementById('sendEmailBtn').addEventListener('click', () => this.sendEmail());
        document.getElementById('emailConfigBtn').addEventListener('click', () => this.checkEmailConfiguration());
        document.getElementById('adminToken').addEventListener('input', (e) => {
            this.persistAdminToken(e.target.value);
            this.loadPresets(this.selectedPresetId);
        });
        document.getElementById('presetSelect').addEventListener('change', (e) => this.handlePresetSelection(e.target.value));
        document.getElementById('applyPresetBtn').addEventListener('click', () => this.applySelectedPreset());
        document.getElementById('savePresetBtn').addEventListener('click', () => this.saveNewPreset());
        document.getElementById('updatePresetBtn').addEventListener('click', () => this.updateSelectedPreset());
        document.getElementById('deletePresetBtn').addEventListener('click', () => this.deleteSelectedPreset());
        document.getElementById('refreshPresetsBtn').addEventListener('click', () => this.loadPresets(this.selectedPresetId));

        // Navigation buttons
        document.getElementById('historyBtn').addEventListener('click', () => this.switchTab('historyTab'));
        document.getElementById('scheduleBtn').addEventListener('click', () => this.switchTab('scheduleManageTab'));
    }

    hydrateAdminToken() {
        const tokenInput = document.getElementById('adminToken');
        const storedToken = window.sessionStorage.getItem(this.adminTokenStorageKey) || '';
        tokenInput.value = storedToken;
    }

    persistAdminToken(value) {
        const normalized = (value || '').trim();
        if (normalized) {
            window.sessionStorage.setItem(this.adminTokenStorageKey, normalized);
            return;
        }

        window.sessionStorage.removeItem(this.adminTokenStorageKey);
    }

    getAdminToken() {
        return window.sessionStorage.getItem(this.adminTokenStorageKey) || '';
    }

    hasAdminToken() {
        return Boolean(this.getAdminToken());
    }

    buildHeaders({ includeJson = false, includeAdminToken = false } = {}) {
        const headers = {};

        if (includeJson) {
            headers['Content-Type'] = 'application/json';
        }

        if (includeAdminToken) {
            const adminToken = this.getAdminToken();
            if (adminToken) {
                headers['X-Admin-Token'] = adminToken;
            }
        }

        return headers;
    }

    getProtectedRouteMessage(defaultMessage = '운영 토큰이 필요합니다.') {
        return `${defaultMessage} 상단의 운영 토큰을 입력한 뒤 다시 시도해주세요.`;
    }

    setPresetStatus(message, tone = 'gray') {
        const presetStatus = document.getElementById('presetStatus');
        presetStatus.className = `mt-2 text-sm text-${tone}-600`;
        presetStatus.textContent = message;
    }

    syncPresetActions() {
        const hasSelection = Boolean(this.selectedPresetId);
        ['applyPresetBtn', 'updatePresetBtn', 'deletePresetBtn'].forEach((buttonId) => {
            const button = document.getElementById(buttonId);
            button.disabled = !hasSelection;
            button.classList.toggle('opacity-50', !hasSelection);
            button.classList.toggle('cursor-not-allowed', !hasSelection);
        });
    }

    renderPresetOptions(preferredPresetId = '') {
        const presetSelect = document.getElementById('presetSelect');
        const nextSelectedId = preferredPresetId || this.selectedPresetId;
        presetSelect.innerHTML = '';

        const placeholderOption = document.createElement('option');
        placeholderOption.value = '';
        placeholderOption.textContent = '프리셋을 선택하세요';
        presetSelect.appendChild(placeholderOption);

        this.savedPresets.forEach((preset) => {
            const option = document.createElement('option');
            option.value = preset.id;
            option.textContent = `${preset.name}${preset.is_default ? ' (기본)' : ''}`;
            option.selected = preset.id === nextSelectedId;
            presetSelect.appendChild(option);
        });

        this.selectedPresetId = presetSelect.value;
        this.syncPresetActions();
    }

    getSelectedPreset() {
        return this.savedPresets.find((preset) => preset.id === this.selectedPresetId) || null;
    }

    handlePresetSelection(presetId) {
        this.selectedPresetId = presetId || '';
        this.syncPresetActions();

        const preset = this.getSelectedPreset();
        if (preset) {
            const summary = preset.description
                ? `${preset.name}: ${preset.description}`
                : `${preset.name} 프리셋이 준비되었습니다.`;
            this.setPresetStatus(summary, 'gray');
            return;
        }

        this.setPresetStatus('운영 토큰이 있으면 프리셋을 저장하고 불러올 수 있습니다.');
    }

    async loadPresets(preferredPresetId = '') {
        const presetSelect = document.getElementById('presetSelect');

        try {
            const response = await fetch('/api/presets', {
                headers: this.buildHeaders({ includeAdminToken: true })
            });
            const result = await response.json();

            if (!response.ok) {
                this.savedPresets = [];
                presetSelect.innerHTML = '<option value="">프리셋을 선택하세요</option>';
                this.selectedPresetId = '';
                this.syncPresetActions();
                const message = response.status === 401 || response.status === 503
                    ? this.getProtectedRouteMessage(result.error || '프리셋을 불러올 수 없습니다.')
                    : (result.error || '프리셋을 불러올 수 없습니다.');
                this.setPresetStatus(message, 'yellow');
                return;
            }

            this.savedPresets = Array.isArray(result) ? result : [];
            const resolvedPresetId = preferredPresetId || this.selectedPresetId || this.savedPresets.find((preset) => preset.is_default)?.id || '';
            this.renderPresetOptions(resolvedPresetId);

            if (this.savedPresets.length === 0) {
                this.setPresetStatus('저장된 프리셋이 없습니다. 현재 입력값으로 새 프리셋을 저장해보세요.');
            } else if (this.selectedPresetId) {
                this.handlePresetSelection(this.selectedPresetId);
            } else {
                this.setPresetStatus('프리셋을 선택하면 현재 폼에 불러올 수 있습니다.');
            }
        } catch (error) {
            this.savedPresets = [];
            this.selectedPresetId = '';
            this.syncPresetActions();
            this.setPresetStatus(`프리셋 조회 실패: ${error.message}`, 'red');
        }
    }

    switchTab(tabId) {
        // Remove active class from all tabs
        document.querySelectorAll('.tab-button').forEach(button => {
            button.classList.remove('active', 'bg-blue-100', 'text-blue-700');
            button.classList.add('text-gray-500', 'hover:text-gray-700');
        });

        // Hide all panels
        document.querySelectorAll('.tab-panel').forEach(panel => {
            panel.classList.add('hidden');
        });

        // Activate selected tab
        const selectedTab = document.getElementById(tabId);
        selectedTab.classList.add('active', 'bg-blue-100', 'text-blue-700');
        selectedTab.classList.remove('text-gray-500', 'hover:text-gray-700');

        // Show corresponding panel
        const panelMap = {
            'generateTab': 'generatePanel',
            'historyTab': 'historyPanel',
            'scheduleManageTab': 'scheduleManagePanel'
        };

        const panelId = panelMap[tabId];
        if (panelId) {
            document.getElementById(panelId).classList.remove('hidden');

            // Load data for specific tabs
            if (tabId === 'historyTab') {
                this.loadHistory();
            } else if (tabId === 'scheduleManageTab') {
                this.loadSchedules();
            }
        }
    }

    toggleInputMethod() {
        const method = document.querySelector('input[name="inputMethod"]:checked').value;
        const keywordsInput = document.getElementById('keywordsInput');
        const domainInput = document.getElementById('domainInput');

        if (method === 'keywords') {
            keywordsInput.classList.remove('hidden');
            domainInput.classList.add('hidden');
        } else {
            keywordsInput.classList.add('hidden');
            domainInput.classList.remove('hidden');
        }
    }

    toggleScheduleSettings(enabled) {
        const scheduleSettings = document.getElementById('scheduleSettings');
        const generateBtn = document.getElementById('generateBtn');
        if (enabled) {
            scheduleSettings.classList.remove('hidden');
        } else {
            scheduleSettings.classList.add('hidden');
        }

        generateBtn.innerHTML = enabled
            ? '<i class="fas fa-calendar-plus mr-2"></i>예약 저장'
            : '<i class="fas fa-play mr-2"></i>생성하기';
    }

    updateScheduleOptions() {
        const frequency = document.getElementById('frequency').value;
        const weeklyOptions = document.getElementById('weeklyOptions');

        if (frequency === 'WEEKLY') {
            weeklyOptions.classList.remove('hidden');
        } else {
            weeklyOptions.classList.add('hidden');
        }
    }

    applyScheduleFromRRule(rrule) {
        if (!rrule) {
            document.getElementById('enableSchedule').checked = false;
            this.toggleScheduleSettings(false);
            return;
        }

        const parts = Object.fromEntries(
            rrule.split(';').map((part) => {
                const [key, value] = part.split('=');
                return [key, value];
            })
        );

        document.getElementById('enableSchedule').checked = true;
        this.toggleScheduleSettings(true);
        document.getElementById('frequency').value = parts.FREQ || 'WEEKLY';
        this.updateScheduleOptions();

        if (parts.BYHOUR && parts.BYMINUTE) {
            const hour = String(parts.BYHOUR).padStart(2, '0');
            const minute = String(parts.BYMINUTE).padStart(2, '0');
            document.getElementById('scheduleTime').value = `${hour}:${minute}`;
        }

        const selectedDays = new Set((parts.BYDAY || '').split(',').filter(Boolean));
        document.querySelectorAll('.weekday').forEach((checkbox) => {
            checkbox.checked = selectedDays.has(checkbox.value);
        });
    }

    applyParamsToForm(params = {}) {
        const keywords = params.keywords;

        if (keywords && keywords.length > 0) {
            document.getElementById('keywordsMethod').checked = true;
            document.getElementById('keywords').value = Array.isArray(keywords) ? keywords.join(', ') : String(keywords);
            document.getElementById('domain').value = '';
        } else if (params.domain) {
            document.getElementById('domainMethod').checked = true;
            document.getElementById('domain').value = params.domain;
            document.getElementById('keywords').value = '';
        }

        document.getElementById('period').value = String(params.period || 14);
        document.getElementById('templateStyle').value = params.template_style || 'compact';
        document.getElementById('emailCompatible').checked = Boolean(params.email_compatible);
        document.getElementById('email').value = params.email || '';
        this.applyScheduleFromRRule(params.rrule || '');
        this.toggleInputMethod();
    }

    applyPresetToForm(preset) {
        this.applyParamsToForm(preset?.params || {});
    }

    applySelectedPreset() {
        const preset = this.getSelectedPreset();
        if (!preset) {
            this.showError('불러올 프리셋을 선택해주세요.');
            return;
        }

        this.applyPresetToForm(preset);
        this.setPresetStatus(`${preset.name} 프리셋을 현재 폼에 적용했습니다.`, 'green');
        this.showSuccess(`프리셋 적용 완료: ${preset.name}`);
    }

    async generateNewsletter() {
        const data = this.collectFormData({ includeSchedule: true, includeEmail: true });
        if (!data) return;

        if (data.schedule) {
            await this.createSchedule(data);
            return;
        }

        await this.submitGeneration(data);
    }

    async submitGeneration(data) {
        const requestData = { ...data };
        delete requestData.schedule;
        delete requestData.rrule;

        this.showProgress();

        try {
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: this.buildHeaders({ includeJson: true }),
                body: JSON.stringify(requestData)
            });

            const result = await response.json();

            if (response.ok) {
                this.currentJobId = result.job_id;
                if (result.status === 'completed') {
                    this.showResults(result.result);
                } else {
                    this.startPolling(result.job_id);
                }
            } else {
                this.showError(result.error || 'Generation failed');
            }
        } catch (error) {
            this.showError('Network error: ' + error.message);
        }
    }

    async createSchedule(data) {
        const scheduleRequest = { ...data };
        delete scheduleRequest.schedule;

        try {
            const response = await fetch('/api/schedule', {
                method: 'POST',
                headers: this.buildHeaders({ includeJson: true, includeAdminToken: true }),
                body: JSON.stringify(scheduleRequest)
            });

            const result = await response.json();

            if (response.ok) {
                this.currentJobId = null;
                document.getElementById('progressSection').classList.add('hidden');
                document.getElementById('resultsSection').classList.add('hidden');
                await this.loadSchedules();
                this.switchTab('scheduleManageTab');
                this.showSuccess(`예약이 등록되었습니다. 다음 실행: ${new Date(result.next_run).toLocaleString()}`);
            } else {
                const message = response.status === 401 || response.status === 503
                    ? this.getProtectedRouteMessage(result.error || '예약 저장 권한이 없습니다.')
                    : (result.error || 'Schedule creation failed');
                this.showError(message);
            }
        } catch (error) {
            this.showError('Network error: ' + error.message);
        }
    }

    async previewNewsletter() {
        const data = this.collectFormData({ includeSchedule: false, includeEmail: false });
        if (!data) return;

        data.preview_only = true;
        await this.submitGeneration(data);
    }

    collectFormData(options = {}) {
        const includeSchedule = options.includeSchedule !== false;
        const includeEmail = options.includeEmail !== false;
        const method = document.querySelector('input[name="inputMethod"]:checked').value;
        const data = {};

        if (method === 'keywords') {
            const keywords = document.getElementById('keywords').value.trim();
            if (!keywords) {
                this.showError('키워드를 입력해주세요.');
                return null;
            }
            data.keywords = keywords.split(',').map(k => k.trim()).filter(k => k);
        } else {
            const domain = document.getElementById('domain').value.trim();
            if (!domain) {
                this.showError('도메인을 입력해주세요.');
                return null;
            }
            data.domain = domain;
        }

        const email = document.getElementById('email').value.trim();
        if (includeEmail && email) {
            data.email = email;
        }

        data.period = parseInt(document.getElementById('period').value, 10);
        data.template_style = document.getElementById('templateStyle').value;
        data.email_compatible = document.getElementById('emailCompatible').checked;

        // Schedule data
        const enableSchedule = document.getElementById('enableSchedule').checked;
        if (includeSchedule && enableSchedule) {
            if (!email) {
                this.showError('예약 발송을 위해서는 이메일 주소가 필요합니다.');
                return null;
            }

            const frequency = document.getElementById('frequency').value;
            const time = document.getElementById('scheduleTime').value;

            let rrule = `FREQ=${frequency}`;

            if (frequency === 'WEEKLY') {
                const selectedDays = Array.from(document.querySelectorAll('.weekday:checked'))
                    .map(cb => cb.value);
                if (selectedDays.length === 0) {
                    this.showError('주간 발송을 위해 요일을 선택해주세요.');
                    return null;
                }
                rrule += `;BYDAY=${selectedDays.join(',')}`;
            }

            const [hour, minute] = time.split(':');
            rrule += `;BYHOUR=${hour};BYMINUTE=${minute}`;

            data.rrule = rrule;
            data.schedule = true;
        }

        return data;
    }

    buildPresetRequest(existingPreset = null) {
        const params = this.collectFormData({ includeSchedule: true, includeEmail: true });
        if (!params) {
            return null;
        }

        const name = window.prompt(
            '프리셋 이름을 입력하세요.',
            existingPreset?.name || ''
        );
        if (name === null) {
            return null;
        }

        const normalizedName = String(name || '').trim();
        if (!normalizedName) {
            this.showError('프리셋 이름을 입력해주세요.');
            return null;
        }

        const descriptionInput = window.prompt(
            '프리셋 설명을 입력하세요. (선택)',
            existingPreset?.description || ''
        );
        if (descriptionInput === null) {
            return null;
        }

        const shouldSetDefault = window.confirm(
            existingPreset?.is_default
                ? '현재 기본 프리셋입니다. 기본 프리셋으로 유지할까요?'
                : '이 프리셋을 기본 프리셋으로 지정할까요?'
        );

        return {
            name: normalizedName,
            description: (descriptionInput || '').trim(),
            is_default: shouldSetDefault,
            params
        };
    }

    async saveNewPreset() {
        const payload = this.buildPresetRequest();
        if (!payload) {
            return;
        }

        try {
            const response = await fetch('/api/presets', {
                method: 'POST',
                headers: this.buildHeaders({ includeJson: true, includeAdminToken: true }),
                body: JSON.stringify(payload)
            });
            const result = await response.json();

            if (!response.ok) {
                const message = response.status === 401 || response.status === 503
                    ? this.getProtectedRouteMessage(result.error || '프리셋 저장 권한이 없습니다.')
                    : (result.error || '프리셋 저장에 실패했습니다.');
                this.showError(message);
                return;
            }

            await this.loadPresets(result.id);
            this.showSuccess(`프리셋 저장 완료: ${result.name}`);
        } catch (error) {
            this.showError('Network error: ' + error.message);
        }
    }

    async updateSelectedPreset() {
        const preset = this.getSelectedPreset();
        if (!preset) {
            this.showError('업데이트할 프리셋을 선택해주세요.');
            return;
        }

        const payload = this.buildPresetRequest(preset);
        if (!payload) {
            return;
        }

        try {
            const response = await fetch(`/api/presets/${preset.id}`, {
                method: 'PUT',
                headers: this.buildHeaders({ includeJson: true, includeAdminToken: true }),
                body: JSON.stringify(payload)
            });
            const result = await response.json();

            if (!response.ok) {
                const message = response.status === 401 || response.status === 503
                    ? this.getProtectedRouteMessage(result.error || '프리셋 수정 권한이 없습니다.')
                    : (result.error || '프리셋 수정에 실패했습니다.');
                this.showError(message);
                return;
            }

            await this.loadPresets(result.id);
            this.showSuccess(`프리셋 업데이트 완료: ${result.name}`);
        } catch (error) {
            this.showError('Network error: ' + error.message);
        }
    }

    async deleteSelectedPreset() {
        const preset = this.getSelectedPreset();
        if (!preset) {
            this.showError('삭제할 프리셋을 선택해주세요.');
            return;
        }

        if (!confirm(`프리셋 "${preset.name}"을 삭제하시겠습니까?`)) {
            return;
        }

        try {
            const response = await fetch(`/api/presets/${preset.id}`, {
                method: 'DELETE',
                headers: this.buildHeaders({ includeAdminToken: true })
            });
            const result = await response.json();

            if (!response.ok) {
                const message = response.status === 401 || response.status === 503
                    ? this.getProtectedRouteMessage(result.error || '프리셋 삭제 권한이 없습니다.')
                    : (result.error || '프리셋 삭제에 실패했습니다.');
                this.showError(message);
                return;
            }

            this.selectedPresetId = '';
            await this.loadPresets();
            this.showSuccess(`프리셋 삭제 완료: ${preset.name}`);
        } catch (error) {
            this.showError('Network error: ' + error.message);
        }
    }

    showProgress() {
        this.stopPolling();
        document.getElementById('progressSection').classList.remove('hidden');
        document.getElementById('resultsSection').classList.add('hidden');

        let progress = 0;
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');

        // Simulate progress
        const interval = setInterval(() => {
            progress += Math.random() * 10;
            if (progress > 90) progress = 90;

            progressBar.style.width = progress + '%';

            if (progress < 30) {
                progressText.textContent = '뉴스 수집 중...';
            } else if (progress < 60) {
                progressText.textContent = '내용 요약 중...';
            } else if (progress < 90) {
                progressText.textContent = '뉴스레터 구성 중...';
            }
        }, 500);

        // Clear interval when polling starts
        setTimeout(() => clearInterval(interval), 5000);
    }

    startPolling(jobId) {
        this.currentJobId = jobId; // Store current job ID
        this.pollCount = 0; // 폴링 횟수 카운터 추가
        this.maxPollCount = 900; // 최대 15분 (900초)

        this.pollInterval = setInterval(async () => {
            try {
                this.pollCount++;

                // 최대 폴링 횟수 초과 시 중단
                if (this.pollCount > this.maxPollCount) {
                    this.stopPolling();
                    this.showError('처리 시간이 너무 오래 걸립니다. 페이지를 새로고침하고 다시 시도해주세요.');
                    return;
                }

                const response = await fetch(`/api/status/${jobId}`);
                const result = await response.json();

                // Update progress text with email status
                const progressText = document.getElementById('progressText');
                if (result.sent) {
                    progressText.textContent = '뉴스레터 생성 완료 및 이메일 발송 완료...';
                } else {
                    progressText.textContent = `뉴스레터를 생성하고 있습니다... (${this.pollCount}초 경과)`;
                }

                if (result.status === 'completed') {
                    this.stopPolling();
                    console.log(`✅ 폴링 완료: ${this.pollCount}초 후 작업 완료`);
                    // Add job_id to result for iframe src
                    if (result.result) {
                        result.result.job_id = jobId;
                        result.result.sent = result.sent;
                    }
                    this.showResults(result.result);

                    // Show email success message
                    if (result.sent) {
                        this.showEmailSuccess(result.result?.email_to);
                    }
                } else if (result.status === 'failed') {
                    this.stopPolling();
                    console.log(`❌ 폴링 중단: ${this.pollCount}초 후 작업 실패`);
                    this.showError(result.result?.error || 'Generation failed');
                }
            } catch (error) {
                console.error('Polling error:', error);
                // 연속 오류 발생 시 폴링 중단
                if (this.pollCount > 10) {
                    this.stopPolling();
                    this.showError('서버와의 연결에 문제가 발생했습니다.');
                }
            }
        }, 1000); // 1초 간격으로 폴링
    }

    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
            this.pollCount = 0; // 카운터 리셋
        }
    }

    showResults(result) {
        document.getElementById('progressSection').classList.add('hidden');
        document.getElementById('resultsSection').classList.remove('hidden');

        const progressBar = document.getElementById('progressBar');
        progressBar.style.width = '100%';

        const preview = document.getElementById('newsletterPreview');

        // Create detailed results display
        let detailsHtml = '';

        // Generation Statistics
        if (result.generation_stats) {
            const stats = result.generation_stats;
            detailsHtml += `
                <div class="mb-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <h4 class="text-lg font-semibold text-blue-800 mb-3">
                        <i class="fas fa-chart-bar mr-2"></i>Generation Statistics
                    </h4>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                        ${stats.total_time ? `
                            <div class="bg-white p-3 rounded shadow-sm">
                                <div class="font-medium text-gray-700">Total Time</div>
                                <div class="text-xl font-bold text-blue-600">${stats.total_time.toFixed(2)}s</div>
                            </div>
                        ` : ''}
                        ${stats.articles_count ? `
                            <div class="bg-white p-3 rounded shadow-sm">
                                <div class="font-medium text-gray-700">Articles Found</div>
                                <div class="text-xl font-bold text-green-600">${stats.articles_count}</div>
                            </div>
                        ` : ''}
                        ${result.html_size ? `
                            <div class="bg-white p-3 rounded shadow-sm">
                                <div class="font-medium text-gray-700">Newsletter Size</div>
                                <div class="text-xl font-bold text-purple-600">${(result.html_size / 1024).toFixed(1)}KB</div>
                            </div>
                        ` : ''}
                    </div>
                    ${stats.step_times ? this.renderStepTimes(stats.step_times) : ''}
                    ${stats.generated_keywords ? `
                        <div class="mt-3 p-3 bg-white rounded shadow-sm">
                            <div class="font-medium text-gray-700 mb-2">Generated Keywords</div>
                            <div class="text-sm text-gray-600">${stats.generated_keywords}</div>
                        </div>
                    ` : ''}
                </div>
            `;
        }

        // Processing Information
        if (result.processing_info) {
            const info = result.processing_info;
            detailsHtml += `
                <div class="mb-4 p-4 bg-green-50 rounded-lg border border-green-200">
                    <h4 class="text-lg font-semibold text-green-800 mb-3">
                        <i class="fas fa-cogs mr-2"></i>Processing Information
                    </h4>
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                        <div class="bg-white p-2 rounded shadow-sm">
                            <div class="font-medium text-gray-700">CLI Mode</div>
                            <div class="font-bold ${info.using_real_cli ? 'text-green-600' : 'text-orange-600'}">
                                ${info.using_real_cli ? 'Real CLI' : 'Mock CLI'}
                            </div>
                        </div>
                        <div class="bg-white p-2 rounded shadow-sm">
                            <div class="font-medium text-gray-700">Template</div>
                            <div class="font-bold text-gray-600">${info.template_style}</div>
                        </div>
                        <div class="bg-white p-2 rounded shadow-sm">
                            <div class="font-medium text-gray-700">Email Mode</div>
                            <div class="font-bold text-gray-600">${info.email_compatible ? 'Yes' : 'No'}</div>
                        </div>
                        <div class="bg-white p-2 rounded shadow-sm">
                            <div class="font-medium text-gray-700">Period</div>
                            <div class="font-bold text-gray-600">${info.period_days} days</div>
                        </div>
                    </div>
                </div>
            `;
        }

        // Input Parameters
        if (result.input_params) {
            const params = result.input_params;
            detailsHtml += `
                <div class="mb-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                    <h4 class="text-lg font-semibold text-gray-800 mb-3">
                        <i class="fas fa-info-circle mr-2"></i>Input Parameters
                    </h4>
                    <div class="text-sm">
                        ${params.keywords ? `
                            <div class="mb-2">
                                <span class="font-medium text-gray-700">Keywords:</span>
                                <span class="ml-2 px-2 py-1 bg-blue-100 text-blue-800 rounded">${params.keywords}</span>
                            </div>
                        ` : ''}
                        ${params.domain ? `
                            <div class="mb-2">
                                <span class="font-medium text-gray-700">Domain:</span>
                                <span class="ml-2 px-2 py-1 bg-purple-100 text-purple-800 rounded">${params.domain}</span>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }

        // Newsletter Content
        detailsHtml += `
            <div class="p-4 bg-white rounded-lg border border-gray-200">
                <h4 class="text-lg font-semibold text-gray-800 mb-3">
                    <i class="fas fa-newspaper mr-2"></i>Newsletter Content
                </h4>
                <div class="border rounded bg-gray-50">
                    ${result.html_content ?
                        (result.job_id ?
                            `<iframe id="newsletterFrame"
                                     style="width: 100%; height: 600px; border: none;"
                                     src="/api/newsletter-html/${result.job_id}"
                                     sandbox="allow-same-origin allow-scripts">
                             </iframe>` :
                            `<iframe id="newsletterFrame"
                                     style="width: 100%; height: 600px; border: none;"
                                     sandbox="allow-same-origin allow-scripts">
                             </iframe>`) :
                        '<p class="text-gray-500 p-4">Newsletter content could not be loaded.</p>'
                    }
                </div>
            </div>
        `;

        preview.innerHTML = detailsHtml;

        // Load HTML content using blob URL if no job_id available
        if (result.html_content && !result.job_id) {
            setTimeout(() => {
                const iframe = document.getElementById('newsletterFrame');
                if (iframe) {
                    const blob = new Blob([result.html_content], { type: 'text/html; charset=utf-8' });
                    const blobUrl = URL.createObjectURL(blob);
                    iframe.src = blobUrl;

                    // Clean up blob URL after iframe loads
                    iframe.onload = () => {
                        URL.revokeObjectURL(blobUrl);
                    };
                }
            }, 100);
        }

        // Update button states
        this.updateResultButtons(result);

        if (this.hasAdminToken()) {
            this.loadHistory();
        }
    }

    renderStepTimes(stepTimes) {
        if (!stepTimes || Object.keys(stepTimes).length === 0) return '';

        const maxTime = Math.max(...Object.values(stepTimes));

        return `
            <div class="mt-3 p-3 bg-white rounded shadow-sm">
                <div class="font-medium text-gray-700 mb-3">Processing Steps</div>
                <div class="space-y-2">
                    ${Object.entries(stepTimes).map(([step, time]) => `
                        <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-600 capitalize">${step.replace(/_/g, ' ')}</span>
                            <div class="flex items-center space-x-2">
                                <div class="w-24 bg-gray-200 rounded-full h-2">
                                    <div class="bg-blue-500 h-2 rounded-full" style="width: ${(time / maxTime) * 100}%"></div>
                                </div>
                                <span class="text-sm font-medium text-gray-700">${time.toFixed(2)}s</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    updateResultButtons(result) {
        const downloadBtn = document.getElementById('downloadBtn');
        const sendEmailBtn = document.getElementById('sendEmailBtn');

        // Enable/disable buttons based on result status
        if (result.status === 'success' && result.html_content) {
            downloadBtn.disabled = false;
            downloadBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            sendEmailBtn.disabled = false;
            sendEmailBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        } else {
            downloadBtn.disabled = true;
            downloadBtn.classList.add('opacity-50', 'cursor-not-allowed');
            sendEmailBtn.disabled = true;
            sendEmailBtn.classList.add('opacity-50', 'cursor-not-allowed');
        }
    }

    showError(message) {
        document.getElementById('progressSection').classList.add('hidden');
        alert('오류: ' + message);
    }

    showSuccess(message) {
        const notification = document.createElement('div');
        notification.className = 'fixed top-4 right-4 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded shadow-lg z-50';
        notification.innerHTML = `
            <div class="flex items-center">
                <i class="fas fa-check-circle mr-2"></i>
                <span>${message}</span>
                <button class="ml-4 text-green-700 hover:text-green-900" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }

    showEmailSuccess(email) {
        this.showSuccess(`메일 발송 완료: ${email}`);
    }

    async loadHistory() {
        const historyList = document.getElementById('historyList');

        try {
            const response = await fetch('/api/history', {
                headers: this.buildHeaders({ includeAdminToken: true })
            });
            const history = await response.json();

            if (!response.ok) {
                const message = response.status === 401 || response.status === 503
                    ? this.getProtectedRouteMessage(history.error || '히스토리를 불러올 수 없습니다.')
                    : (history.error || '히스토리를 불러올 수 없습니다.');
                historyList.innerHTML = `<p class="text-amber-600">${message}</p>`;
                return;
            }

            if (history.length === 0) {
                historyList.innerHTML = '<p class="text-gray-500">아직 생성된 뉴스레터가 없습니다.</p>';
                return;
            }

            historyList.innerHTML = history.map(item => `
                <div class="border-b border-gray-200 py-4">
                    <div class="flex justify-between items-start">
                        <div>
                            <h4 class="text-sm font-medium text-gray-900">
                                ${item.params?.keywords ?
                                  `키워드: ${Array.isArray(item.params.keywords) ? item.params.keywords.join(', ') : item.params.keywords}` :
                                  `도메인: ${item.params?.domain || 'Unknown'}`}
                            </h4>
                            <p class="text-sm text-gray-500">${new Date(item.created_at).toLocaleString()}</p>
                            <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                                item.status === 'completed' ? 'bg-green-100 text-green-800' :
                                item.status === 'failed' ? 'bg-red-100 text-red-800' :
                                'bg-yellow-100 text-yellow-800'
                            }">${item.status}</span>
                        </div>
                        <div class="space-x-2">
                            ${item.status === 'completed' ? `
                                <button onclick="app.viewHistoryItem('${item.id}')"
                                        class="text-blue-600 hover:text-blue-900 text-sm">보기</button>
                                <button onclick="app.rerunHistoryItem('${item.id}')"
                                        class="text-green-600 hover:text-green-900 text-sm">다시 실행</button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            historyList.innerHTML = `<p class="text-red-600">히스토리 조회 실패: ${error.message}</p>`;
        }
    }

    async loadSchedules() {
        const schedulesList = document.getElementById('schedulesList');

        try {
            const response = await fetch('/api/schedules', {
                headers: this.buildHeaders({ includeAdminToken: true })
            });
            const schedules = await response.json();

            if (!response.ok) {
                const message = response.status === 401 || response.status === 503
                    ? this.getProtectedRouteMessage(schedules.error || '예약 목록을 불러올 수 없습니다.')
                    : (schedules.error || '예약 목록을 불러올 수 없습니다.');
                schedulesList.innerHTML = `<p class="text-amber-600">${message}</p>`;
                return;
            }

            if (schedules.length === 0) {
                schedulesList.innerHTML = '<p class="text-gray-500">예약된 발송이 없습니다.</p>';
                return;
            }

            schedulesList.innerHTML = schedules.map(schedule => `
                <div class="border-b border-gray-200 py-4">
                    <div class="flex justify-between items-start">
                        <div>
                            <h4 class="text-sm font-medium text-gray-900">
                                ${schedule.params?.keywords ?
                                  `키워드: ${Array.isArray(schedule.params.keywords) ? schedule.params.keywords.join(', ') : schedule.params.keywords}` :
                                  `도메인: ${schedule.params?.domain || 'Unknown'}`}
                            </h4>
                            <p class="text-sm text-gray-500">
                                이메일: ${schedule.params?.email || 'Unknown'}
                            </p>
                            <p class="text-sm text-gray-500">
                                다음 실행: ${new Date(schedule.next_run).toLocaleString()}
                            </p>
                            <p class="text-sm text-gray-500">
                                규칙: ${schedule.rrule}
                            </p>
                        </div>
                        <div class="space-x-2">
                            <button onclick="app.runScheduleNow('${schedule.id}')"
                                    class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm">
                                즉시 실행
                            </button>
                            <button onclick="app.cancelSchedule('${schedule.id}')"
                                    class="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm">
                                취소
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            schedulesList.innerHTML = `<p class="text-red-600">예약 목록 조회 실패: ${error.message}</p>`;
        }
    }

    async cancelSchedule(scheduleId) {
        if (!confirm('이 예약을 취소하시겠습니까?')) return;

        try {
            const response = await fetch(`/api/schedule/${scheduleId}`, {
                method: 'DELETE',
                headers: this.buildHeaders({ includeAdminToken: true })
            });

            if (response.ok) {
                this.loadSchedules(); // Reload schedules
                this.showSuccess('예약이 취소되었습니다.');
            } else {
                const result = await response.json();
                const message = response.status === 401 || response.status === 503
                    ? this.getProtectedRouteMessage(result.error || '예약 취소 권한이 없습니다.')
                    : (result.error || 'Unknown error');
                alert('취소 실패: ' + message);
            }
        } catch (error) {
            alert('Network error: ' + error.message);
        }
    }

    async runScheduleNow(scheduleId) {
        try {
            const response = await fetch(`/api/schedule/${scheduleId}/run`, {
                method: 'POST',
                headers: this.buildHeaders({ includeAdminToken: true })
            });

            const result = await response.json();

            if (!response.ok) {
                const message = response.status === 401 || response.status === 503
                    ? this.getProtectedRouteMessage(result.error || '즉시 실행 권한이 없습니다.')
                    : (result.error || 'Immediate execution failed');
                this.showError(message);
                return;
            }

            this.switchTab('generateTab');

            if (result.status === 'completed' && result.result) {
                result.result.job_id = result.job_id;
                this.currentJobId = result.job_id;
                this.showResults(result.result);
                this.showSuccess('예약 작업이 즉시 실행되었습니다.');
            } else if (result.status === 'queued' && result.job_id) {
                this.currentJobId = result.job_id;
                this.showProgress();
                this.startPolling(result.job_id);
                this.showSuccess('예약 작업이 큐에 등록되었습니다.');
            } else {
                this.showSuccess('예약 작업 실행이 요청되었습니다.');
            }

            this.loadSchedules();
        } catch (error) {
            this.showError('Network error: ' + error.message);
        }
    }

    async viewHistoryItem(itemId) {
        try {
            console.log('viewHistoryItem called with itemId:', itemId);
            const response = await fetch(`/api/status/${itemId}`);
            const result = await response.json();
            console.log('API response:', result);

            if (result.result?.html_content) {
                console.log('HTML content found, switching to generate tab');
                // Add job_id to result for iframe src
                result.result.job_id = itemId;
                this.currentJobId = itemId;
                // Switch to generate tab and show the result
                this.switchTab('generateTab');
                this.showResults(result.result);
                console.log('Results displayed successfully');
            } else {
                console.log('No HTML content found in result');
                alert('뉴스레터 콘텐츠를 찾을 수 없습니다.');
            }
        } catch (error) {
            console.error('Error in viewHistoryItem:', error);
            alert('Failed to load item: ' + error.message);
        }
    }

    async rerunHistoryItem(itemId) {
        try {
            const response = await fetch(`/api/status/${itemId}`);
            const result = await response.json();

            if (result.params) {
                this.applyParamsToForm(result.params);
                this.switchTab('generateTab');
            }
        } catch (error) {
            alert('Failed to load parameters: ' + error.message);
        }
    }

    downloadNewsletter() {
        if (!this.currentJobId) {
            // Try to get HTML content from current result
            const iframe = document.getElementById('newsletterFrame');
            if (iframe && iframe.src && iframe.src.startsWith('blob:')) {
                alert('다운로드 기능을 위해 페이지를 새로고침하거나 뉴스레터를 다시 생성해주세요.');
                return;
            }

            alert('다운로드할 뉴스레터가 없습니다.');
            return;
        }

        // Create a link to download from the API endpoint
        const downloadUrl = `/api/newsletter-html/${this.currentJobId}`;
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = `newsletter_${this.currentJobId}.html`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    async sendEmail() {
        if (!this.currentJobId) {
            alert('발송할 뉴스레터가 없습니다.');
            return;
        }

        const email = document.getElementById('email').value.trim();
        if (!email) {
            alert('이메일 주소를 입력해주세요.');
            return;
        }

        // 이메일 설정 확인
        try {
            const configResponse = await fetch('/api/email-config', {
                headers: this.buildHeaders({ includeAdminToken: true })
            });
            const configResult = await configResponse.json();

            if (!configResponse.ok) {
                alert(configResult.error || this.getProtectedRouteMessage('이메일 설정을 확인할 수 없습니다.'));
                return;
            }

            if (!configResult.ready) {
                if (confirm('이메일 설정이 완료되지 않았습니다. 테스트 이메일을 발송해보시겠습니까?')) {
                    await this.sendTestEmail(email);
                    return;
                } else {
                    alert('이메일 발송을 위해 환경변수 설정이 필요합니다:\n- POSTMARK_SERVER_TOKEN\n- EMAIL_SENDER');
                    return;
                }
            }
        } catch (error) {
            console.error('Email config check failed:', error);
        }

        try {
            const response = await fetch('/api/send-email', {
                method: 'POST',
                headers: this.buildHeaders({ includeJson: true, includeAdminToken: true }),
                body: JSON.stringify({
                    job_id: this.currentJobId,
                    email: email
                })
            });

            const result = await response.json();

            if (response.ok) {
                alert('이메일이 성공적으로 발송되었습니다!');
            } else {
                const message = response.status === 401 || response.status === 503
                    ? this.getProtectedRouteMessage(result.error || '이메일 발송 권한이 없습니다.')
                    : (result.error || 'Unknown error');
                alert('이메일 발송 실패: ' + message);
            }
        } catch (error) {
            alert('Network error: ' + error.message);
        }
    }

    async sendTestEmail(email) {
        if (!email) {
            email = prompt('테스트 이메일을 받을 주소를 입력하세요:');
            if (!email) return;
        }

        try {
            const response = await fetch('/api/test-email', {
                method: 'POST',
                headers: this.buildHeaders({ includeJson: true, includeAdminToken: true }),
                body: JSON.stringify({ email: email })
            });

            const result = await response.json();

            if (response.ok) {
                alert(`테스트 이메일이 ${email}로 발송되었습니다!\n메시지 ID: ${result.message_id || 'N/A'}`);
            } else {
                const message = response.status === 401 || response.status === 503
                    ? this.getProtectedRouteMessage(result.error || '테스트 이메일 발송 권한이 없습니다.')
                    : (result.error || 'Unknown error');
                alert('테스트 이메일 발송 실패: ' + message);
            }
        } catch (error) {
            alert('Network error: ' + error.message);
        }
    }

    async checkEmailConfiguration() {
        try {
            const response = await fetch('/api/email-config', {
                headers: this.buildHeaders({ includeAdminToken: true })
            });
            const result = await response.json();

            if (!response.ok) {
                alert(result.error || this.getProtectedRouteMessage('설정 확인 권한이 없습니다.'));
                return;
            }

            let message = '이메일 설정 상태:\n';
            message += `Postmark 토큰: ${result.postmark_token_configured ? '✓ 설정됨' : '✗ 미설정'}\n`;
            message += `발신자 이메일: ${result.from_email_configured ? '✓ 설정됨' : '✗ 미설정'}\n`;
            message += `전체 상태: ${result.ready ? '✓ 준비 완료' : '✗ 설정 필요'}`;

            alert(message);

            if (!result.ready) {
                const testEmail = prompt('테스트 이메일을 발송해보시겠습니까? (이메일 주소 입력)');
                if (testEmail) {
                    await this.sendTestEmail(testEmail);
                }
            }

        } catch (error) {
            alert('설정 확인 실패: ' + error.message);
        }
    }

    escapeHtmlForSrcdoc(html) {
        return html
            .replace(/&/g, '&amp;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\n/g, '\\n')
            .replace(/\r/g, '\\r');
    }

    async suggestKeywords() {
        const domainInput = document.getElementById('domain');
        const domain = domainInput.value.trim();
        const resultDiv = document.getElementById('keywords-result');
        const button = document.getElementById('btn-suggest');

        if (!domain) {
            resultDiv.innerHTML = '<div class="text-red-600 text-sm">도메인을 입력해주세요.</div>';
            return;
        }

        // Show loading state
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>추천 중...';
        resultDiv.innerHTML = '<div class="text-blue-600 text-sm">키워드를 생성하고 있습니다...</div>';

        try {
            const response = await fetch('/api/suggest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ domain: domain })
            });

            const data = await response.json();

            if (response.ok && data.keywords && data.keywords.length > 0) {
                // Display suggested keywords
                const keywordsList = data.keywords.map(keyword =>
                    `<span class="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full mr-2 mb-2 cursor-pointer hover:bg-blue-200" onclick="app.addKeywordToInput('${keyword}')">${keyword}</span>`
                ).join('');

                resultDiv.innerHTML = `
                    <div class="text-sm text-gray-700 mb-2">추천 키워드 (클릭하여 추가):</div>
                    <div class="flex flex-wrap">${keywordsList}</div>
                    <button onclick="app.useAllKeywords(${JSON.stringify(data.keywords).replace(/"/g, '&quot;')})"
                            class="mt-2 text-xs bg-green-100 text-green-800 px-2 py-1 rounded hover:bg-green-200">
                        모든 키워드 사용
                    </button>
                `;
            } else {
                resultDiv.innerHTML = '<div class="text-yellow-600 text-sm">키워드를 생성할 수 없습니다. 다른 도메인을 시도해보세요.</div>';
            }
        } catch (error) {
            resultDiv.innerHTML = '<div class="text-red-600 text-sm">오류가 발생했습니다: ' + error.message + '</div>';
        } finally {
            // Restore button state
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-lightbulb mr-1"></i>추천받기';
        }
    }

    addKeywordToInput(keyword) {
        const keywordsInput = document.getElementById('keywords');
        const currentKeywords = keywordsInput.value.trim();

        if (currentKeywords) {
            keywordsInput.value = currentKeywords + ', ' + keyword;
        } else {
            keywordsInput.value = keyword;
        }

        // Switch to keywords method
        document.getElementById('keywordsMethod').checked = true;
        this.toggleInputMethod();
    }

    useAllKeywords(keywords) {
        const keywordsInput = document.getElementById('keywords');
        keywordsInput.value = keywords.join(', ');

        // Switch to keywords method
        document.getElementById('keywordsMethod').checked = true;
        this.toggleInputMethod();
    }
}

// Global function for onclick handlers
function suggestKeywords() {
    app.suggestKeywords();
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new NewsletterApp();
});
