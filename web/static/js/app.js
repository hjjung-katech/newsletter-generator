/**
 * Newsletter Generator Web App
 * Frontend JavaScript for handling user interactions and API calls
 */

const NewsletterAppRequestResponseHelpers = window.NewsletterAppRequestResponseHelpers;
const NewsletterAppViewStateHelpers = window.NewsletterAppViewStateHelpers;
const NewsletterAppSelectionVisibilityHelpers = window.NewsletterAppSelectionVisibilityHelpers;

if (!NewsletterAppRequestResponseHelpers) {
    throw new Error('NewsletterAppRequestResponseHelpers must be loaded before app.js');
}

if (!NewsletterAppViewStateHelpers) {
    throw new Error('NewsletterAppViewStateHelpers must be loaded before app.js');
}

if (!NewsletterAppSelectionVisibilityHelpers) {
    throw new Error('NewsletterAppSelectionVisibilityHelpers must be loaded before app.js');
}

class NewsletterApp {
    constructor() {
        this.currentJobId = null;
        this.pollInterval = null;
        this.adminTokenStorageKey = 'newsletter-admin-api-token';
        this.savedPresets = [];
        this.selectedPresetId = '';
        this.archiveSearchResults = [];
        this.selectedArchiveReferences = [];
        this.analyticsData = null;
        this.sourcePolicies = [];
        this.editingSourcePolicyId = '';
        this.init();
    }

    init() {
        this.bindEvents();
        this.hydrateAdminToken();
        this.toggleInputMethod();
        this.toggleScheduleSettings(document.getElementById('enableSchedule').checked);
        this.updateScheduleOptions();
        this.syncPresetActions();
        this.renderSelectedArchiveReferences();
        this.renderArchiveSearchResults();
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
            this.loadArchiveSearchResults(document.getElementById('archiveSearchInput').value);
            this.hydrateArchiveReferences(this.selectedArchiveReferences.map((reference) => reference.job_id));
            this.loadAnalytics();
            this.loadSourcePolicies();
        });
        document.getElementById('presetSelect').addEventListener('change', (e) => this.handlePresetSelection(e.target.value));
        document.getElementById('applyPresetBtn').addEventListener('click', () => this.applySelectedPreset());
        document.getElementById('savePresetBtn').addEventListener('click', () => this.saveNewPreset());
        document.getElementById('updatePresetBtn').addEventListener('click', () => this.updateSelectedPreset());
        document.getElementById('deletePresetBtn').addEventListener('click', () => this.deleteSelectedPreset());
        document.getElementById('refreshPresetsBtn').addEventListener('click', () => this.loadPresets(this.selectedPresetId));
        document.getElementById('searchArchiveBtn').addEventListener('click', () => this.loadArchiveSearchResults());
        document.getElementById('clearArchiveSelectionBtn').addEventListener('click', () => this.clearArchiveReferences());
        document.getElementById('archiveSearchInput').addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                this.loadArchiveSearchResults();
            }
        });
        document.getElementById('refreshAnalyticsBtn').addEventListener('click', () => this.loadAnalytics());
        document.getElementById('refreshSourcePoliciesBtn').addEventListener('click', () => this.loadSourcePolicies());
        document.getElementById('saveSourcePolicyBtn').addEventListener('click', () => this.saveSourcePolicy());
        document.getElementById('cancelSourcePolicyEditBtn').addEventListener('click', () => this.resetSourcePolicyForm());

        // Navigation buttons
        document.getElementById('historyBtn').addEventListener('click', () => this.switchTab('historyTab'));
        document.getElementById('analyticsBtn').addEventListener('click', () => this.switchTab('analyticsTab'));
        document.getElementById('approvalBtn').addEventListener('click', () => this.switchTab('approvalTab'));
        document.getElementById('sourcesBtn').addEventListener('click', () => this.switchTab('sourcePolicyTab'));
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
        presetStatus.className = NewsletterAppSelectionVisibilityHelpers.buildPresetStatusClassName(tone);
        presetStatus.textContent = message;
    }

    syncPresetActions() {
        const presetActionState = NewsletterAppSelectionVisibilityHelpers.resolvePresetActionState(this.selectedPresetId);
        ['applyPresetBtn', 'updatePresetBtn', 'deletePresetBtn'].forEach((buttonId) => {
            const button = document.getElementById(buttonId);
            button.disabled = presetActionState.disabled;
            presetActionState.inactiveClasses.forEach((className) => {
                button.classList.toggle(className, presetActionState.disabled);
            });
        });
    }

    setArchiveStatus(message, tone = 'gray') {
        const status = document.getElementById('archiveStatus');
        status.className = NewsletterAppSelectionVisibilityHelpers.buildArchiveStatusClassName(tone);
        status.textContent = message;
    }

    normalizeArchiveReference(entry = {}) {
        return NewsletterAppRequestResponseHelpers.normalizeArchiveReference(entry);
    }

    renderSelectedArchiveReferences() {
        const container = document.getElementById('selectedArchiveReferences');
        container.innerHTML = NewsletterAppSelectionVisibilityHelpers.buildSelectedArchiveReferencesHtml(this.selectedArchiveReferences);
    }

    renderArchiveSearchResults() {
        const container = document.getElementById('archiveSearchResults');
        container.innerHTML = NewsletterAppSelectionVisibilityHelpers.buildArchiveSearchResultsHtml(
            this.archiveSearchResults,
            this.selectedArchiveReferences
        );
    }

    async loadArchiveSearchResults(queryOverride = null) {
        const query = typeof queryOverride === 'string'
            ? queryOverride.trim()
            : document.getElementById('archiveSearchInput').value.trim();

        if (!this.hasAdminToken()) {
            this.archiveSearchResults = [];
            this.renderArchiveSearchResults();
            this.setArchiveStatus(this.getProtectedRouteMessage('운영 토큰이 있어야 과거 뉴스레터를 검색할 수 있습니다.'), 'yellow');
            return;
        }

        try {
            const params = new URLSearchParams({
                limit: '8'
            });
            if (query) {
                params.set('q', query);
            }

            const response = await fetch(`/api/archive/search?${params.toString()}`, {
                headers: this.buildHeaders({ includeAdminToken: true })
            });
            const result = await response.json();

            if (!response.ok) {
                const message = response.status === 401 || response.status === 503
                    ? this.getProtectedRouteMessage(result.error || '과거 뉴스레터를 불러올 수 없습니다.')
                    : (result.error || '과거 뉴스레터를 불러올 수 없습니다.');
                this.archiveSearchResults = [];
                this.renderArchiveSearchResults();
                this.setArchiveStatus(message, 'yellow');
                return;
            }

            this.archiveSearchResults = Array.isArray(result.results)
                ? result.results.map((entry) => this.normalizeArchiveReference(entry))
                : [];
            this.renderArchiveSearchResults();
            this.setArchiveStatus(
                this.archiveSearchResults.length
                    ? `${this.archiveSearchResults.length}개의 과거 뉴스레터를 찾았습니다.`
                    : '조건에 맞는 과거 뉴스레터가 없습니다.',
                this.archiveSearchResults.length ? 'green' : 'gray'
            );
        } catch (error) {
            this.archiveSearchResults = [];
            this.renderArchiveSearchResults();
            this.setArchiveStatus(`과거 뉴스레터 조회 실패: ${error.message}`, 'red');
        }
    }

    async hydrateArchiveReferences(referenceIds = []) {
        const hydrationState = NewsletterAppSelectionVisibilityHelpers.resolveHydratedArchiveReferences(
            this.selectedArchiveReferences,
            referenceIds
        );
        const normalizedIds = hydrationState.normalizedIds;

        if (!normalizedIds.length) {
            this.selectedArchiveReferences = [];
            this.renderSelectedArchiveReferences();
            return;
        }

        this.selectedArchiveReferences = hydrationState.nextSelectedReferences;
        this.renderSelectedArchiveReferences();

        if (!this.hasAdminToken()) {
            this.setArchiveStatus('선택된 참고본 ID는 유지됩니다. 운영 토큰을 입력하면 세부 정보를 복원합니다.', 'yellow');
            return;
        }

        const loadedReferences = await Promise.all(normalizedIds.map(async (jobId) => {
            try {
                const response = await fetch(`/api/archive/${jobId}`, {
                    headers: this.buildHeaders({ includeAdminToken: true })
                });
                if (!response.ok) {
                    return placeholderMap.get(jobId) || this.normalizeArchiveReference({ job_id: jobId, title: jobId });
                }
                const payload = await response.json();
                return this.normalizeArchiveReference(payload);
            } catch (error) {
                return placeholderMap.get(jobId) || this.normalizeArchiveReference({ job_id: jobId, title: jobId });
            }
        }));

        this.selectedArchiveReferences = loadedReferences;
        this.renderSelectedArchiveReferences();
    }

    toggleArchiveReference(jobId) {
        const selectionResult = NewsletterAppSelectionVisibilityHelpers.resolveArchiveSelectionUpdate({
            selectedArchiveReferences: this.selectedArchiveReferences,
            archiveSearchResults: this.archiveSearchResults,
            jobId
        });

        if (selectionResult.error) {
            this.showError(selectionResult.error);
            return;
        }

        this.selectedArchiveReferences = selectionResult.nextSelectedReferences;
        this.renderSelectedArchiveReferences();
        this.renderArchiveSearchResults();

        if (selectionResult.statusMessage) {
            this.setArchiveStatus(selectionResult.statusMessage, selectionResult.statusTone || 'gray');
        }
    }

    removeArchiveReference(jobId) {
        this.selectedArchiveReferences = NewsletterAppSelectionVisibilityHelpers.removeArchiveReference(
            this.selectedArchiveReferences,
            jobId
        );
        this.renderSelectedArchiveReferences();
        this.renderArchiveSearchResults();
    }

    clearArchiveReferences() {
        this.selectedArchiveReferences = [];
        this.renderSelectedArchiveReferences();
        this.renderArchiveSearchResults();
        this.setArchiveStatus('선택된 참고본을 초기화했습니다.');
    }

    setSourcePolicyStatus(message, tone = 'gray') {
        const status = document.getElementById('sourcePolicyStatus');
        status.className = NewsletterAppSelectionVisibilityHelpers.buildSourcePolicyStatusClassName(tone);
        status.textContent = message;
    }

    setSourcePolicySummary(message, tone = 'gray') {
        const summary = document.getElementById('sourcePolicySummary');
        summary.className = NewsletterAppSelectionVisibilityHelpers.buildSourcePolicySummaryClassName(tone);
        summary.textContent = message;
    }

    resetSourcePolicyForm() {
        this.editingSourcePolicyId = '';
        document.getElementById('sourcePolicyId').value = '';
        document.getElementById('sourcePattern').value = '';
        document.getElementById('sourcePolicyType').value = 'allow';
        document.getElementById('sourcePolicyActive').checked = true;
        document.getElementById('sourcePolicyFormTitle').textContent = '새 정책 추가';
        this.setSourcePolicyStatus('운영 토큰이 있으면 소스 정책을 추가하고 수정할 수 있습니다.');
    }

    buildSourcePolicyPayload() {
        const payloadResult = NewsletterAppRequestResponseHelpers.buildSourcePolicyPayload({
            pattern: document.getElementById('sourcePattern').value,
            policyType: document.getElementById('sourcePolicyType').value,
            isActive: document.getElementById('sourcePolicyActive').checked
        });

        if (payloadResult.error) {
            this.showError(payloadResult.error);
            return null;
        }

        return payloadResult.payload;
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
        const tabState = NewsletterAppSelectionVisibilityHelpers.resolveTabPanelState(tabId);
        if (tabState.panelId) {
            document.getElementById(tabState.panelId).classList.remove('hidden');

            switch (tabState.loadAction) {
            case 'history':
                this.loadHistory();
                break;
            case 'analytics':
                this.loadAnalytics();
                break;
            case 'approvals':
                this.loadApprovals();
                break;
            case 'sourcePolicies':
                this.loadSourcePolicies();
                break;
            case 'schedules':
                this.loadSchedules();
                break;
            default:
                break;
            }
        }
    }

    toggleInputMethod() {
        const method = document.querySelector('input[name="inputMethod"]:checked').value;
        const keywordsInput = document.getElementById('keywordsInput');
        const domainInput = document.getElementById('domainInput');
        const visibilityState = NewsletterAppSelectionVisibilityHelpers.resolveInputMethodVisibility(method);

        keywordsInput.classList.toggle('hidden', visibilityState.keywordsHidden);
        domainInput.classList.toggle('hidden', visibilityState.domainHidden);
    }

    applyScheduleView(enabled) {
        const scheduleSettings = document.getElementById('scheduleSettings');
        const generateBtn = document.getElementById('generateBtn');
        const weeklyOptions = document.getElementById('weeklyOptions');
        const scheduleViewState = NewsletterAppSelectionVisibilityHelpers.resolveScheduleViewState({
            enabled,
            frequency: document.getElementById('frequency').value
        });

        scheduleSettings.classList.toggle('hidden', scheduleViewState.scheduleSettingsHidden);
        weeklyOptions.classList.toggle('hidden', scheduleViewState.weeklyOptionsHidden);
        generateBtn.innerHTML = scheduleViewState.generateButtonHtml;
    }

    toggleScheduleSettings(enabled) {
        this.applyScheduleView(enabled);
    }

    updateScheduleOptions() {
        this.applyScheduleView(document.getElementById('enableSchedule').checked);
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
        this.hydrateArchiveReferences(params.archive_reference_ids || []);
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
                    this.showResults(
                        NewsletterAppRequestResponseHelpers.normalizeGenerationResultEnvelope(result, result.job_id) || result.result
                    );
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
        const requestResult = NewsletterAppRequestResponseHelpers.buildGenerationRequest({
            method: document.querySelector('input[name="inputMethod"]:checked').value,
            keywordsInput: document.getElementById('keywords').value,
            domainInput: document.getElementById('domain').value,
            emailInput: document.getElementById('email').value,
            periodValue: document.getElementById('period').value,
            templateStyle: document.getElementById('templateStyle').value,
            emailCompatible: document.getElementById('emailCompatible').checked,
            archiveReferenceIds: this.selectedArchiveReferences.map((reference) => reference.job_id),
            enableSchedule: document.getElementById('enableSchedule').checked,
            frequency: document.getElementById('frequency').value,
            scheduleTime: document.getElementById('scheduleTime').value,
            selectedWeekdays: Array.from(document.querySelectorAll('.weekday:checked')).map((checkbox) => checkbox.value)
        }, {
            includeSchedule,
            includeEmail
        });

        if (requestResult.error) {
            this.showError(requestResult.error);
            return null;
        }

        return requestResult.data;
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

        const payloadResult = NewsletterAppRequestResponseHelpers.buildPresetPayload({
            params,
            name,
            description: descriptionInput,
            isDefault: shouldSetDefault
        });

        if (payloadResult.error) {
            this.showError(payloadResult.error);
            return null;
        }

        return payloadResult.payload;
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
                    const normalizedResult = NewsletterAppRequestResponseHelpers.normalizeGenerationResultEnvelope(result, jobId);
                    this.showResults(normalizedResult || result.result);

                    // Show email success message
                    if (result.sent) {
                        this.showEmailSuccess((normalizedResult || result.result)?.email_to);
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
        preview.innerHTML = NewsletterAppRequestResponseHelpers.buildResultDetailsHtml(result);

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
            this.loadApprovals();
        }
    }

    updateResultButtons(result) {
        const downloadBtn = document.getElementById('downloadBtn');
        const sendEmailBtn = document.getElementById('sendEmailBtn');
        const buttonState = NewsletterAppViewStateHelpers.resolveResultButtonState(result);

        if (!buttonState.downloadDisabled) {
            downloadBtn.disabled = false;
            downloadBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        } else {
            downloadBtn.disabled = true;
            downloadBtn.classList.add('opacity-50', 'cursor-not-allowed');
        }

        if (!buttonState.sendEmailDisabled) {
            sendEmailBtn.disabled = false;
            sendEmailBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        } else {
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
                historyList.innerHTML = NewsletterAppViewStateHelpers.resolveHistorySectionState({
                    errorMessage: message,
                    errorTone: 'yellow'
                }).html;
                return;
            }

            historyList.innerHTML = NewsletterAppViewStateHelpers.resolveHistorySectionState({ history }).html;
        } catch (error) {
            historyList.innerHTML = NewsletterAppViewStateHelpers.resolveHistorySectionState({
                errorMessage: `히스토리 조회 실패: ${error.message}`,
                errorTone: 'red'
            }).html;
        }
    }

    async loadApprovals() {
        const approvalsList = document.getElementById('approvalsList');

        try {
            const response = await fetch('/api/approvals', {
                headers: this.buildHeaders({ includeAdminToken: true })
            });
            const approvals = await response.json();

            if (!response.ok) {
                const message = response.status === 401 || response.status === 503
                    ? this.getProtectedRouteMessage(approvals.error || '승인 대기함을 불러올 수 없습니다.')
                    : (approvals.error || '승인 대기함을 불러올 수 없습니다.');
                approvalsList.innerHTML = NewsletterAppViewStateHelpers.resolveApprovalsSectionState({
                    errorMessage: message,
                    errorTone: 'yellow'
                }).html;
                return;
            }

            approvalsList.innerHTML = NewsletterAppViewStateHelpers.resolveApprovalsSectionState({ approvals }).html;
        } catch (error) {
            approvalsList.innerHTML = NewsletterAppViewStateHelpers.resolveApprovalsSectionState({
                errorMessage: `승인 대기함 조회 실패: ${error.message}`,
                errorTone: 'red'
            }).html;
        }
    }

    setAnalyticsStatus(message, tone = 'gray') {
        const status = document.getElementById('analyticsStatus');
        status.className = NewsletterAppSelectionVisibilityHelpers.buildAnalyticsStatusClassName(tone);
        status.textContent = message;
    }

    renderAnalyticsCards(summary = {}) {
        const container = document.getElementById('analyticsSummaryCards');
        container.innerHTML = NewsletterAppViewStateHelpers.buildAnalyticsSummaryCardsHtml(summary);
    }

    renderAnalyticsEvents(events = []) {
        const eventsList = document.getElementById('analyticsEventsList');
        eventsList.innerHTML = NewsletterAppViewStateHelpers.buildAnalyticsEventsHtml(events);
    }

    async loadAnalytics() {
        const analyticsWindow = document.getElementById('analyticsWindow');
        const windowDays = parseInt(analyticsWindow.value, 10) || 7;

        try {
            const response = await fetch(`/api/analytics?window_days=${windowDays}&recent_limit=25`, {
                headers: this.buildHeaders({ includeAdminToken: true })
            });
            const result = await response.json();

            if (!response.ok) {
                const message = response.status === 401 || response.status === 503
                    ? this.getProtectedRouteMessage(result.error || 'Analytics를 불러올 수 없습니다.')
                    : (result.error || 'Analytics를 불러올 수 없습니다.');
                const analyticsState = NewsletterAppViewStateHelpers.resolveAnalyticsSectionState({
                    errorMessage: message,
                    errorTone: 'yellow'
                });
                this.analyticsData = null;
                this.setAnalyticsStatus(analyticsState.statusMessage, analyticsState.statusTone);
                this.renderAnalyticsCards(analyticsState.summary);
                this.renderAnalyticsEvents(analyticsState.events);
                return;
            }

            const analyticsState = NewsletterAppViewStateHelpers.resolveAnalyticsSectionState({ result });
            this.analyticsData = result;
            this.setAnalyticsStatus(analyticsState.statusMessage, analyticsState.statusTone);
            this.renderAnalyticsCards(analyticsState.summary);
            this.renderAnalyticsEvents(analyticsState.events);
        } catch (error) {
            const analyticsState = NewsletterAppViewStateHelpers.resolveAnalyticsSectionState({
                errorMessage: `Analytics 조회 실패: ${error.message}`,
                errorTone: 'red'
            });
            this.analyticsData = null;
            this.setAnalyticsStatus(analyticsState.statusMessage, analyticsState.statusTone);
            this.renderAnalyticsCards(analyticsState.summary);
            this.renderAnalyticsEvents(analyticsState.events);
        }
    }

    async loadSourcePolicies() {
        const sourcePoliciesList = document.getElementById('sourcePoliciesList');

        try {
            const response = await fetch('/api/source-policies', {
                headers: this.buildHeaders({ includeAdminToken: true })
            });
            const policies = await response.json();

            if (!response.ok) {
                this.sourcePolicies = [];
                const message = response.status === 401 || response.status === 503
                    ? this.getProtectedRouteMessage(policies.error || '소스 정책을 불러올 수 없습니다.')
                    : (policies.error || '소스 정책을 불러올 수 없습니다.');
                const sectionState = NewsletterAppViewStateHelpers.resolveSourcePoliciesSectionState({
                    errorMessage: message,
                    errorTone: 'yellow',
                    editingSourcePolicyId: this.editingSourcePolicyId
                });
                sourcePoliciesList.innerHTML = sectionState.html;
                this.setSourcePolicySummary(sectionState.summaryMessage, sectionState.summaryTone);
                this.setSourcePolicyStatus(sectionState.statusMessage, sectionState.statusTone);
                return;
            }

            this.sourcePolicies = Array.isArray(policies) ? policies : [];
            this.renderSourcePolicies();
        } catch (error) {
            this.sourcePolicies = [];
            const sectionState = NewsletterAppViewStateHelpers.resolveSourcePoliciesSectionState({
                errorMessage: `소스 정책 조회 실패: ${error.message}`,
                errorTone: 'red',
                editingSourcePolicyId: this.editingSourcePolicyId
            });
            sourcePoliciesList.innerHTML = sectionState.html;
            this.setSourcePolicySummary(sectionState.summaryMessage, sectionState.summaryTone);
            this.setSourcePolicyStatus(sectionState.statusMessage, sectionState.statusTone);
        }
    }

    renderSourcePolicies() {
        const sourcePoliciesList = document.getElementById('sourcePoliciesList');

        const sectionState = NewsletterAppViewStateHelpers.resolveSourcePoliciesSectionState({
            sourcePolicies: this.sourcePolicies,
            editingSourcePolicyId: this.editingSourcePolicyId
        });
        sourcePoliciesList.innerHTML = sectionState.html;
        this.setSourcePolicySummary(sectionState.summaryMessage, sectionState.summaryTone);

        if (sectionState.shouldResetForm) {
            this.resetSourcePolicyForm();
        }
    }

    editSourcePolicy(policyId) {
        const policy = this.sourcePolicies.find((item) => item.id === policyId);
        if (!policy) {
            this.showError('편집할 소스 정책을 찾을 수 없습니다.');
            return;
        }

        this.editingSourcePolicyId = policy.id;
        document.getElementById('sourcePolicyId').value = policy.id;
        document.getElementById('sourcePattern').value = policy.pattern;
        document.getElementById('sourcePolicyType').value = policy.policy_type;
        document.getElementById('sourcePolicyActive').checked = Boolean(policy.is_active);
        document.getElementById('sourcePolicyFormTitle').textContent = '정책 편집';
        this.setSourcePolicyStatus(`${policy.pattern} 정책을 편집 중입니다.`, 'green');
        document.getElementById('sourcePattern').focus();
    }

    async saveSourcePolicy() {
        const payload = this.buildSourcePolicyPayload();
        if (!payload) {
            return;
        }

        const isEditing = Boolean(this.editingSourcePolicyId);
        const url = isEditing ? `/api/source-policies/${this.editingSourcePolicyId}` : '/api/source-policies';
        const method = isEditing ? 'PUT' : 'POST';

        try {
            const response = await fetch(url, {
                method,
                headers: this.buildHeaders({ includeJson: true, includeAdminToken: true }),
                body: JSON.stringify(payload)
            });
            const result = await response.json();

            if (!response.ok) {
                const message = response.status === 401 || response.status === 503
                    ? this.getProtectedRouteMessage(result.error || '소스 정책 저장 권한이 없습니다.')
                    : (result.error || '소스 정책 저장에 실패했습니다.');
                this.showError(message);
                this.setSourcePolicyStatus(message, response.status === 409 ? 'yellow' : 'red');
                return;
            }

            this.resetSourcePolicyForm();
            await this.loadSourcePolicies();
            this.showSuccess(isEditing ? '소스 정책이 업데이트되었습니다.' : '소스 정책이 추가되었습니다.');
            this.setSourcePolicyStatus(
                isEditing ? '소스 정책 업데이트가 반영되었습니다.' : '새 소스 정책이 저장되었습니다.',
                'green'
            );
        } catch (error) {
            this.showError('Network error: ' + error.message);
            this.setSourcePolicyStatus(`소스 정책 저장 실패: ${error.message}`, 'red');
        }
    }

    async toggleSourcePolicyActive(policyId, nextActive) {
        const policy = this.sourcePolicies.find((item) => item.id === policyId);
        if (!policy) {
            this.showError('상태를 변경할 소스 정책을 찾을 수 없습니다.');
            return;
        }

        try {
            const response = await fetch(`/api/source-policies/${policyId}`, {
                method: 'PUT',
                headers: this.buildHeaders({ includeJson: true, includeAdminToken: true }),
                body: JSON.stringify({
                    pattern: policy.pattern,
                    policy_type: policy.policy_type,
                    is_active: nextActive
                })
            });
            const result = await response.json();

            if (!response.ok) {
                const message = response.status === 401 || response.status === 503
                    ? this.getProtectedRouteMessage(result.error || '소스 정책 변경 권한이 없습니다.')
                    : (result.error || '소스 정책 상태 변경에 실패했습니다.');
                this.showError(message);
                return;
            }

            await this.loadSourcePolicies();
            this.showSuccess(`소스 정책을 ${nextActive ? '활성화' : '비활성화'}했습니다.`);
        } catch (error) {
            this.showError('Network error: ' + error.message);
        }
    }

    async deleteSourcePolicy(policyId) {
        const policy = this.sourcePolicies.find((item) => item.id === policyId);
        if (!policy) {
            this.showError('삭제할 소스 정책을 찾을 수 없습니다.');
            return;
        }

        if (!confirm(`소스 정책 "${policy.pattern}"을 삭제하시겠습니까?`)) {
            return;
        }

        try {
            const response = await fetch(`/api/source-policies/${policyId}`, {
                method: 'DELETE',
                headers: this.buildHeaders({ includeAdminToken: true })
            });
            const result = await response.json();

            if (!response.ok) {
                const message = response.status === 401 || response.status === 503
                    ? this.getProtectedRouteMessage(result.error || '소스 정책 삭제 권한이 없습니다.')
                    : (result.error || '소스 정책 삭제에 실패했습니다.');
                this.showError(message);
                return;
            }

            if (this.editingSourcePolicyId === policyId) {
                this.resetSourcePolicyForm();
            }

            await this.loadSourcePolicies();
            this.showSuccess(`소스 정책 삭제 완료: ${policy.pattern}`);
        } catch (error) {
            this.showError('Network error: ' + error.message);
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
                schedulesList.innerHTML = NewsletterAppViewStateHelpers.resolveSchedulesSectionState({
                    errorMessage: message,
                    errorTone: 'yellow'
                }).html;
                return;
            }

            schedulesList.innerHTML = NewsletterAppViewStateHelpers.resolveSchedulesSectionState({ schedules }).html;
        } catch (error) {
            schedulesList.innerHTML = NewsletterAppViewStateHelpers.resolveSchedulesSectionState({
                errorMessage: `예약 목록 조회 실패: ${error.message}`,
                errorTone: 'red'
            }).html;
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
                this.currentJobId = result.job_id;
                this.showResults(
                    NewsletterAppRequestResponseHelpers.normalizeGenerationResultEnvelope(result, result.job_id) || result.result
                );
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
                const normalizedResult = NewsletterAppRequestResponseHelpers.normalizeGenerationResultEnvelope(result, itemId);
                this.currentJobId = itemId;
                // Switch to generate tab and show the result
                this.switchTab('generateTab');
                this.showResults(normalizedResult || result.result);
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

    async approveHistoryItem(itemId) {
        try {
            const response = await fetch(`/api/approvals/${itemId}/approve`, {
                method: 'POST',
                headers: this.buildHeaders({ includeJson: true, includeAdminToken: true }),
                body: JSON.stringify({})
            });
            const result = await response.json();

            if (!response.ok) {
                const message = response.status === 401 || response.status === 503
                    ? this.getProtectedRouteMessage(result.error || '승인 권한이 없습니다.')
                    : (result.error || '승인에 실패했습니다.');
                this.showError(message);
                return;
            }

            this.showSuccess('승인 완료. 이제 이메일 발송 버튼으로 발송할 수 있습니다.');
            await this.loadApprovals();
            await this.loadHistory();
        } catch (error) {
            this.showError('Network error: ' + error.message);
        }
    }

    async rejectHistoryItem(itemId) {
        const note = prompt('반려 사유를 입력하세요. (선택)');

        try {
            const response = await fetch(`/api/approvals/${itemId}/reject`, {
                method: 'POST',
                headers: this.buildHeaders({ includeJson: true, includeAdminToken: true }),
                body: JSON.stringify({ note: note || '' })
            });
            const result = await response.json();

            if (!response.ok) {
                const message = response.status === 401 || response.status === 503
                    ? this.getProtectedRouteMessage(result.error || '반려 권한이 없습니다.')
                    : (result.error || '반려에 실패했습니다.');
                this.showError(message);
                return;
            }

            this.showSuccess('뉴스레터를 반려하고 draft 상태로 유지했습니다.');
            await this.loadApprovals();
            await this.loadHistory();
        } catch (error) {
            this.showError('Network error: ' + error.message);
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
            resultDiv.innerHTML = NewsletterAppViewStateHelpers.resolveKeywordSuggestionView({
                phase: 'missing-domain'
            }).resultHtml;
            return;
        }

        const loadingState = NewsletterAppViewStateHelpers.resolveKeywordSuggestionView({ phase: 'loading' });
        button.disabled = loadingState.buttonDisabled;
        button.innerHTML = loadingState.buttonHtml;
        resultDiv.innerHTML = loadingState.resultHtml;

        try {
            const response = await fetch('/api/suggest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ domain: domain })
            });

            const data = await response.json();

            resultDiv.innerHTML = NewsletterAppViewStateHelpers.resolveKeywordSuggestionView(
                response.ok && data.keywords && data.keywords.length > 0
                    ? { phase: 'success', keywords: data.keywords }
                    : { phase: 'empty' }
            ).resultHtml;
        } catch (error) {
            resultDiv.innerHTML = NewsletterAppViewStateHelpers.resolveKeywordSuggestionView({
                phase: 'error',
                errorMessage: error.message
            }).resultHtml;
        } finally {
            const idleState = NewsletterAppViewStateHelpers.resolveKeywordSuggestionView();
            button.disabled = idleState.buttonDisabled;
            button.innerHTML = idleState.buttonHtml;
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
