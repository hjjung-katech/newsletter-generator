(function(root, factory) {
    const helpers = factory();
    root.NewsletterAppSelectionVisibilityHelpers = helpers;

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = helpers;
    }
})(typeof window !== 'undefined' ? window : globalThis, function() {
    function buildClassName(baseClassName, tone, toneMap) {
        return `${baseClassName} ${toneMap[tone] || toneMap.gray}`.trim();
    }

    function buildPresetStatusClassName(tone = 'gray') {
        return buildClassName('mt-2 text-sm', tone, {
            gray: 'text-gray-600',
            green: 'text-green-600',
            yellow: 'text-yellow-600',
            red: 'text-red-600'
        });
    }

    function buildArchiveStatusClassName(tone = 'gray') {
        return buildClassName('text-sm', tone, {
            gray: 'text-gray-600',
            green: 'text-green-600',
            yellow: 'text-amber-600',
            red: 'text-red-600'
        });
    }

    function buildSourcePolicyStatusClassName(tone = 'gray') {
        return buildClassName('mt-2 text-sm', tone, {
            gray: 'text-gray-500',
            green: 'text-green-600',
            yellow: 'text-amber-600',
            red: 'text-red-600'
        });
    }

    function buildSourcePolicySummaryClassName(tone = 'gray') {
        return buildClassName('mb-4 rounded-lg border px-4 py-3 text-sm', tone, {
            gray: 'border-gray-200 bg-gray-50 text-gray-600',
            green: 'border-green-200 bg-green-50 text-green-700',
            yellow: 'border-amber-200 bg-amber-50 text-amber-700',
            red: 'border-red-200 bg-red-50 text-red-700'
        });
    }

    function buildAnalyticsStatusClassName(tone = 'gray') {
        return buildClassName('mt-4 rounded-lg border px-4 py-3 text-sm', tone, {
            gray: 'border-gray-200 bg-gray-50 text-gray-600',
            green: 'border-green-200 bg-green-50 text-green-700',
            yellow: 'border-amber-200 bg-amber-50 text-amber-700',
            red: 'border-red-200 bg-red-50 text-red-700'
        });
    }

    function resolvePresetActionState(selectedPresetId = '') {
        const hasSelection = Boolean(selectedPresetId);
        return {
            hasSelection,
            disabled: !hasSelection,
            inactiveClasses: ['opacity-50', 'cursor-not-allowed']
        };
    }

    function isArchiveReferenceSelected(selectedArchiveReferences = [], jobId = '') {
        return selectedArchiveReferences.some((reference) => reference.job_id === jobId);
    }

    function buildSelectedArchiveReferencesHtml(selectedArchiveReferences = []) {
        if (!Array.isArray(selectedArchiveReferences) || selectedArchiveReferences.length === 0) {
            return '<p class="text-sm text-gray-500">선택된 참고본이 없습니다.</p>';
        }

        return selectedArchiveReferences.map((reference) => `
            <div class="rounded-md border border-blue-100 bg-blue-50 p-3">
                <div class="flex items-start justify-between gap-3">
                    <div>
                        <p class="text-sm font-semibold text-gray-900">${reference.title}</p>
                        <p class="mt-1 text-sm text-gray-600">${reference.snippet}</p>
                        <p class="mt-2 text-xs text-gray-500">${reference.source_value || reference.job_id}</p>
                    </div>
                    <button onclick="app.removeArchiveReference('${reference.job_id}')"
                            class="rounded-md border border-red-200 bg-white px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50">
                        제거
                    </button>
                </div>
            </div>
        `).join('');
    }

    function buildArchiveSearchResultsHtml(archiveSearchResults = [], selectedArchiveReferences = []) {
        if (!Array.isArray(archiveSearchResults) || archiveSearchResults.length === 0) {
            return '<p class="text-sm text-gray-500">검색어를 입력하면 최근 뉴스레터를 불러옵니다.</p>';
        }

        const selectedIds = new Set(
            Array.isArray(selectedArchiveReferences)
                ? selectedArchiveReferences.map((reference) => reference.job_id)
                : []
        );

        return archiveSearchResults.map((reference) => {
            const isSelected = selectedIds.has(reference.job_id);
            return `
                <div class="rounded-md border border-gray-200 p-3">
                    <div class="flex items-start justify-between gap-3">
                        <div>
                            <p class="text-sm font-semibold text-gray-900">${reference.title}</p>
                            <p class="mt-1 text-sm text-gray-600">${reference.snippet}</p>
                            <p class="mt-2 text-xs text-gray-500">${reference.source_value || reference.job_id}</p>
                        </div>
                        <button onclick="app.toggleArchiveReference('${reference.job_id}')"
                                class="rounded-md px-2 py-1 text-xs font-medium ${isSelected ? 'bg-red-100 text-red-700 hover:bg-red-200' : 'bg-blue-100 text-blue-700 hover:bg-blue-200'}">
                            ${isSelected ? '선택 해제' : '참고 추가'}
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    function resolveArchiveSelectionUpdate({
        selectedArchiveReferences = [],
        archiveSearchResults = [],
        jobId = '',
        maxSelections = 3
    } = {}) {
        const selected = Array.isArray(selectedArchiveReferences) ? selectedArchiveReferences.slice() : [];
        const selectedIds = new Set(selected.map((reference) => reference.job_id));

        if (selectedIds.has(jobId)) {
            return {
                nextSelectedReferences: selected.filter((reference) => reference.job_id !== jobId),
                operation: 'removed'
            };
        }

        if (selected.length >= maxSelections) {
            return {
                error: '과거 뉴스레터 참고본은 최대 3개까지 선택할 수 있습니다.'
            };
        }

        const match = Array.isArray(archiveSearchResults)
            ? archiveSearchResults.find((reference) => reference.job_id === jobId)
            : null;
        if (!match) {
            return {
                error: '선택한 참고본 정보를 찾을 수 없습니다.'
            };
        }

        const nextSelectedReferences = [...selected, match];
        return {
            nextSelectedReferences,
            operation: 'added',
            statusMessage: `${nextSelectedReferences.length}개의 참고본을 선택했습니다.`,
            statusTone: 'green'
        };
    }

    function removeArchiveReference(selectedArchiveReferences = [], jobId = '') {
        return Array.isArray(selectedArchiveReferences)
            ? selectedArchiveReferences.filter((reference) => reference.job_id !== jobId)
            : [];
    }

    function buildArchiveReferenceSnapshot(selectedArchiveReferences = []) {
        return new Map(
            Array.isArray(selectedArchiveReferences)
                ? selectedArchiveReferences.map((reference) => [reference.job_id, reference])
                : []
        );
    }

    function resolveHydratedArchiveReferences(selectedArchiveReferences = [], referenceIds = []) {
        const normalizedIds = Array.isArray(referenceIds)
            ? referenceIds.map((item) => String(item || '').trim()).filter(Boolean).slice(0, 3)
            : [];

        if (!normalizedIds.length) {
            return {
                normalizedIds,
                nextSelectedReferences: [],
                missingIds: []
            };
        }

        const snapshot = buildArchiveReferenceSnapshot(selectedArchiveReferences);
        const nextSelectedReferences = normalizedIds.map((jobId) => snapshot.get(jobId) || {
            job_id: jobId,
            title: jobId,
            snippet: '선택된 참고본 세부 정보를 불러오지 못했습니다.',
            source_value: '',
            created_at: null
        });

        return {
            normalizedIds,
            nextSelectedReferences,
            missingIds: normalizedIds.filter((jobId) => !snapshot.has(jobId))
        };
    }

    function resolveTabPanelState(tabId = '') {
        const panelMap = {
            generateTab: 'generatePanel',
            historyTab: 'historyPanel',
            analyticsTab: 'analyticsPanel',
            approvalTab: 'approvalPanel',
            sourcePolicyTab: 'sourcePolicyPanel',
            scheduleManageTab: 'scheduleManagePanel'
        };
        const loadActionMap = {
            historyTab: 'history',
            analyticsTab: 'analytics',
            approvalTab: 'approvals',
            sourcePolicyTab: 'sourcePolicies',
            scheduleManageTab: 'schedules'
        };

        return {
            panelId: panelMap[tabId] || null,
            loadAction: loadActionMap[tabId] || null
        };
    }

    function resolveInputMethodVisibility(method = 'keywords') {
        const normalizedMethod = method === 'domain' ? 'domain' : 'keywords';
        return {
            keywordsHidden: normalizedMethod !== 'keywords',
            domainHidden: normalizedMethod !== 'domain'
        };
    }

    function resolveScheduleViewState({ enabled = false, frequency = 'WEEKLY' } = {}) {
        const normalizedFrequency = String(frequency || 'WEEKLY').toUpperCase();
        return {
            scheduleSettingsHidden: !enabled,
            weeklyOptionsHidden: normalizedFrequency !== 'WEEKLY',
            generateButtonHtml: enabled
                ? '<i class="fas fa-calendar-plus mr-2"></i>예약 저장'
                : '<i class="fas fa-play mr-2"></i>생성하기'
        };
    }

    return {
        buildPresetStatusClassName,
        buildArchiveStatusClassName,
        buildSourcePolicyStatusClassName,
        buildSourcePolicySummaryClassName,
        buildAnalyticsStatusClassName,
        resolvePresetActionState,
        isArchiveReferenceSelected,
        buildSelectedArchiveReferencesHtml,
        buildArchiveSearchResultsHtml,
        resolveArchiveSelectionUpdate,
        removeArchiveReference,
        buildArchiveReferenceSnapshot,
        resolveHydratedArchiveReferences,
        resolveTabPanelState,
        resolveInputMethodVisibility,
        resolveScheduleViewState
    };
});
