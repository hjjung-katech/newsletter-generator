(function(root, factory) {
    const helpers = factory();
    root.NewsletterAppViewStateHelpers = helpers;

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = helpers;
    }
})(typeof window !== 'undefined' ? window : globalThis, function() {
    const approvalStateLabelMap = {
        pending: '승인 대기',
        approved: '승인 완료',
        rejected: '반려됨',
        unavailable: '승인 불필요',
        unknown: '승인 상태 미상'
    };

    function formatParamsLabel(params = {}) {
        return params?.keywords
            ? `키워드: ${Array.isArray(params.keywords) ? params.keywords.join(', ') : params.keywords}`
            : `도메인: ${params?.domain || 'Unknown'}`;
    }

    function resolveExecutionVisibility(source = {}) {
        const visibility = source?.execution_visibility || source?.latest_execution || {};
        const hasDerivedScheduleContext = !source?.execution_visibility
            && !source?.latest_execution
            && Boolean(source?.next_run);
        const rawStatus = visibility.raw_status || source.status || 'unknown';
        const statusCategory = visibility.status_category
            || (hasDerivedScheduleContext
                ? 'empty'
                : null)
            || (rawStatus === 'completed'
                ? 'completed'
                : rawStatus === 'failed'
                    ? 'failed'
                    : rawStatus === 'processing'
                        ? 'running'
                        : rawStatus === 'pending' || rawStatus === 'queued'
                            ? 'queued'
                            : 'unknown');
        const statusLabel = visibility.status_label
            || (hasDerivedScheduleContext ? '실행 이력 없음' : rawStatus);
        return {
            rawStatus,
            statusCategory,
            statusLabel,
            statusMessage: visibility.status_message
                || (hasDerivedScheduleContext ? '아직 실행 이력이 없습니다.' : ''),
            primaryTimestamp: visibility.primary_timestamp || source.created_at || null,
            approvalLabel: visibility.approval_label || '',
            deliveryLabel: visibility.delivery_label || '',
            resultTitle: visibility.result_title || source?.result?.title || ''
        };
    }

    function resolveApprovalVisibility(source = {}) {
        const visibility = source?.approval_visibility || {};
        const executionVisibility = resolveExecutionVisibility(source);
        const hasApprovableContent = Boolean(source?.result?.html_content);
        const rawApprovalStatus = visibility.raw_approval_status || source?.approval_status || '';
        const approvalState = visibility.approval_state
            || (!rawApprovalStatus || rawApprovalStatus === 'not_requested'
                ? 'unavailable'
                : rawApprovalStatus === 'pending' || rawApprovalStatus === 'approved' || rawApprovalStatus === 'rejected'
                    ? rawApprovalStatus
                    : 'unknown');
        const primaryTimestamp = visibility.primary_timestamp
            || source?.approved_at
            || source?.rejected_at
            || source?.created_at
            || null;

        return {
            rawApprovalStatus,
            approvalState,
            approvalLabel: visibility.approval_label || approvalStateLabelMap[approvalState] || rawApprovalStatus || '',
            approvalMessage: visibility.approval_message
                || (approvalState === 'pending'
                    ? '검토 후 승인 또는 반려할 수 있습니다.'
                    : approvalState === 'approved'
                        ? '승인이 완료되었습니다.'
                        : approvalState === 'rejected'
                            ? '반려되어 draft 상태로 유지됩니다.'
                            : approvalState === 'unavailable'
                                ? '승인 대상이 아닙니다.'
                                : '승인 상태를 확인할 수 없습니다.'),
            primaryTimestamp,
            timestampLabel: visibility.timestamp_label || (primaryTimestamp ? '기준 시각' : ''),
            canResolve: Boolean(visibility.can_resolve ?? (approvalState === 'pending' && executionVisibility.statusCategory === 'completed')),
            canApprove: Boolean(visibility.can_approve ?? (approvalState === 'pending' && executionVisibility.statusCategory === 'completed' && hasApprovableContent)),
            canReject: Boolean(visibility.can_reject ?? (approvalState === 'pending' && executionVisibility.statusCategory === 'completed')),
            isResolved: approvalState === 'approved' || approvalState === 'rejected'
        };
    }

    function buildExecutionStatusBadge(label, statusCategory) {
        const toneClass = statusCategory === 'completed'
            ? 'bg-green-100 text-green-800'
            : statusCategory === 'failed'
                ? 'bg-red-100 text-red-800'
                : statusCategory === 'running'
                    ? 'bg-blue-100 text-blue-800'
                    : statusCategory === 'empty'
                        ? 'bg-slate-100 text-slate-700'
                        : 'bg-yellow-100 text-yellow-800';

        return `<span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full ${toneClass}">${label}</span>`;
    }

    function buildHistoryStatusBadge(item = {}) {
        const visibility = resolveExecutionVisibility(item);
        return buildExecutionStatusBadge(visibility.statusLabel, visibility.statusCategory);
    }

    function buildApprovalStatusBadge(status, label = '') {
        if (!status || status === 'not_requested' || status === 'unavailable') {
            return '';
        }

        const toneClass = status === 'pending'
            ? 'bg-amber-100 text-amber-800'
            : status === 'approved'
                ? 'bg-blue-100 text-blue-800'
                : status === 'rejected'
                    ? 'bg-red-100 text-red-800'
                    : 'bg-slate-100 text-slate-700';

        return `<span class="inline-flex ml-2 px-2 py-1 text-xs font-semibold rounded-full ${toneClass}">${label || status}</span>`;
    }

    function buildDeliveryStatusBadge(status, label = '') {
        if (!status) {
            return '';
        }

        const toneClass = status === 'sent'
            ? 'bg-green-100 text-green-800'
            : status === 'approved'
                ? 'bg-blue-100 text-blue-800'
                : status === 'pending_approval'
                    ? 'bg-amber-100 text-amber-800'
                    : status === 'send_failed'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-slate-100 text-slate-700';

        return `<span class="inline-flex ml-2 px-2 py-1 text-xs font-semibold rounded-full ${toneClass}">${label || status}</span>`;
    }

    function formatVisibilityTimestamp(timestamp) {
        if (!timestamp) {
            return '';
        }

        return new Date(timestamp).toLocaleString();
    }

    function resolvePersonalizationVisibility(source = {}) {
        const visibility = source?.personalization_visibility || {};
        const overrideLabels = Array.isArray(visibility.override_labels)
            ? visibility.override_labels
            : [];

        return {
            personalizationState: visibility.personalization_state || 'unknown',
            statusLabel: visibility.status_label || '개인화 상태 미상',
            statusMessage: visibility.status_message || '',
            effectiveTemplateStyle: visibility.effective_template_style || source?.params?.template_style || 'compact',
            effectivePeriod: visibility.effective_period ?? source?.params?.period ?? 14,
            emailModeLabel: visibility.email_mode_label
                || ((visibility.email_compatible ?? source?.params?.email_compatible) ? '이메일 호환 모드' : '기본 모드'),
            overrideCount: visibility.override_count ?? overrideLabels.length,
            overrideLabels,
            archiveReferenceCount: visibility.archive_reference_count ?? 0,
            sourcePolicyOverrideCount: visibility.source_policy_override_count ?? 0,
            sourcePolicyLinkState: visibility.source_policy_link_state || 'unknown',
            sourcePolicyMessage: visibility.source_policy_message || '',
            hasRecentRelatedExecution: Boolean(visibility.has_recent_related_execution),
            recentUsageLabel: visibility.recent_usage_label || ''
        };
    }

    function resolveEffectiveSettingsProvenance(source = {}) {
        const provenance = source?.effective_settings_provenance || {};
        const summaryTokens = Array.isArray(provenance.summary_tokens)
            ? provenance.summary_tokens
            : [];
        const diagnostics = provenance.diagnostics || {};
        const diagnosticReasonCodes = Array.isArray(diagnostics.reason_codes)
            ? diagnostics.reason_codes
            : [];
        const diagnosticDetails = Array.isArray(diagnostics.details)
            ? diagnostics.details
            : [];
        const diagnosticFieldExplanations = Array.isArray(diagnostics.field_explanations)
            ? diagnostics.field_explanations
                .filter((item) => item && typeof item === 'object')
                .map((item) => ({
                    axis: item.axis || '',
                    axisLabel: item.axis_label || '',
                    field: item.field || '',
                    fieldLabel: item.field_label || '',
                    expectedValue: item.expected_value,
                    currentValue: item.current_value,
                    expectedLabel: item.expected_label || '',
                    currentLabel: item.current_label || '',
                    summary: item.summary || '',
                    detail: item.detail || ''
                }))
            : [];

        return {
            effectiveState: provenance.effective_state || 'unknown',
            statusLabel: provenance.status_label || '설정 provenance 미상',
            statusMessage: provenance.status_message || '',
            presetName: provenance.preset_name || '',
            presetIsDefault: Boolean(provenance.preset_is_default),
            personalizationLabel: provenance.personalization_label || '',
            sourcePolicyLabel: provenance.source_policy_label || '',
            defaultModeLabel: provenance.default_mode_label || '',
            linkageLabel: provenance.linkage_label || '',
            recentExecutionLabel: provenance.recent_execution_label || '',
            recentExecutionMessage: provenance.recent_execution_message || '',
            recentExecutionTimestamp: provenance.recent_execution_timestamp || null,
            summaryTokens,
            diagnosticPrimaryReasonCode: diagnostics.primary_reason_code || '',
            diagnosticSummary: diagnostics.summary || '',
            diagnosticReasonCodes,
            diagnosticDetails,
            diagnosticFieldSummary: diagnostics.field_summary || '',
            diagnosticFieldExplanations
        };
    }

    function buildEffectiveSettingsProvenanceBadge(source = {}) {
        const provenance = resolveEffectiveSettingsProvenance(source);
        const toneClass = provenance.effectiveState === 'overridden'
            ? 'bg-blue-100 text-blue-800'
            : provenance.effectiveState === 'default'
                ? 'bg-slate-100 text-slate-700'
                : provenance.effectiveState === 'detached'
                    ? 'bg-amber-100 text-amber-800'
                    : provenance.effectiveState === 'effective'
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-slate-100 text-slate-700';
        return `<span class="inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${toneClass}">${provenance.statusLabel}</span>`;
    }

    function buildEffectiveSettingsProvenanceMetaHtml(source = {}, { compact = false } = {}) {
        const provenance = resolveEffectiveSettingsProvenance(source);
        if (!provenance.statusMessage && provenance.summaryTokens.length === 0) {
            return '';
        }

        const parts = [
            `<div class="${compact ? 'mt-1' : 'mt-2'} flex flex-wrap gap-2">${buildEffectiveSettingsProvenanceBadge(source)}</div>`
        ];

        if (provenance.statusMessage) {
            parts.push(`<p class="mt-1 text-sm text-gray-500">${provenance.statusMessage}</p>`);
        }
        if (provenance.diagnosticSummary) {
            parts.push(`<p class="mt-1 text-xs text-amber-700">해석: ${provenance.diagnosticSummary}</p>`);
        }
        if (provenance.diagnosticFieldSummary) {
            parts.push(`<p class="mt-1 text-xs text-sky-700">차이 축: ${provenance.diagnosticFieldSummary}</p>`);
        }
        if (provenance.diagnosticFieldExplanations.length > 0) {
            const detailText = provenance.diagnosticFieldExplanations
                .map((item) => item.detail || item.summary)
                .filter(Boolean)
                .slice(0, 2)
                .join(' · ');
            if (detailText) {
                parts.push(`<p class="mt-1 text-xs text-gray-500">세부: ${detailText}</p>`);
            }
        }
        if (provenance.diagnosticDetails.length > 1) {
            parts.push(`<p class="mt-1 text-xs text-gray-500">${provenance.diagnosticDetails.slice(1).join(' · ')}</p>`);
        }
        if (provenance.summaryTokens.length > 0) {
            parts.push(`<p class="mt-1 text-xs text-gray-500">${provenance.summaryTokens.join(' · ')}</p>`);
        }
        if (provenance.recentExecutionTimestamp) {
            parts.push(`<p class="mt-1 text-xs text-gray-500">최근 관련 실행: ${formatVisibilityTimestamp(provenance.recentExecutionTimestamp)}</p>`);
        }

        return parts.join('');
    }

    function buildPersonalizationVisibilityBadge(source = {}) {
        const visibility = resolvePersonalizationVisibility(source);
        const toneClass = visibility.personalizationState === 'overridden'
            ? 'bg-violet-100 text-violet-800'
            : visibility.personalizationState === 'default'
                ? 'bg-slate-100 text-slate-700'
                : visibility.personalizationState === 'empty'
                    ? 'bg-amber-100 text-amber-800'
                    : 'bg-slate-100 text-slate-700';

        return `<span class="inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${toneClass}">${visibility.statusLabel}</span>`;
    }

    function buildPersonalizationMetaHtml(source = {}, { compact = false } = {}) {
        const visibility = resolvePersonalizationVisibility(source);
        const parts = [];
        const detailTokens = [
            `템플릿 ${visibility.effectiveTemplateStyle}`,
            `${visibility.effectivePeriod}일`,
            visibility.emailModeLabel
        ];

        if (visibility.archiveReferenceCount > 0) {
            detailTokens.push(`아카이브 ${visibility.archiveReferenceCount}개`);
        }
        if (visibility.sourcePolicyOverrideCount > 0) {
            detailTokens.push(`소스 정책 오버라이드 ${visibility.sourcePolicyOverrideCount}개`);
        }

        parts.push(
            `<p class="${compact ? 'mt-1' : 'mt-2'} text-xs text-gray-500">개인화: ${detailTokens.join(' · ')}</p>`
        );

        if (visibility.overrideCount > 0 && visibility.overrideLabels.length > 0) {
            parts.push(
                `<p class="mt-1 text-xs text-gray-500">오버라이드: ${visibility.overrideLabels.join(', ')}</p>`
            );
        }
        if (visibility.statusMessage) {
            parts.push(`<p class="mt-1 text-sm text-gray-500">${visibility.statusMessage}</p>`);
        }
        if (visibility.sourcePolicyMessage) {
            parts.push(`<p class="mt-1 text-xs text-gray-500">소스 정책 연결: ${visibility.sourcePolicyMessage}</p>`);
        }

        return parts.join('');
    }

    function buildExecutionMetaHtml(source = {}, { includeResultTitle = true, includeTimestamp = true } = {}) {
        const visibility = resolveExecutionVisibility(source);
        const parts = [];

        if (visibility.statusMessage) {
            parts.push(`<p class="mt-2 text-sm text-gray-500">${visibility.statusMessage}</p>`);
        }
        if (includeTimestamp && visibility.primaryTimestamp) {
            parts.push(`<p class="mt-1 text-xs text-gray-500">기준 시각: ${formatVisibilityTimestamp(visibility.primaryTimestamp)}</p>`);
        }
        if (includeResultTitle && visibility.resultTitle) {
            parts.push(`<p class="mt-1 text-xs text-gray-500">결과: ${visibility.resultTitle}</p>`);
        }

        return parts.join('');
    }

    function buildApprovalMetaHtml(source = {}) {
        const visibility = resolveApprovalVisibility(source);
        const parts = [];

        if (visibility.approvalState !== 'unavailable' && visibility.approvalMessage) {
            parts.push(`<p class="mt-2 text-sm text-gray-500">${visibility.approvalMessage}</p>`);
        }
        if (visibility.primaryTimestamp && visibility.timestampLabel) {
            parts.push(`<p class="mt-1 text-xs text-gray-500">${visibility.timestampLabel}: ${formatVisibilityTimestamp(visibility.primaryTimestamp)}</p>`);
        }

        return parts.join('');
    }

    function buildHistoryActionsHtml(item = {}) {
        const approvalVisibility = resolveApprovalVisibility(item);

        if (item.status !== 'completed') {
            return '';
        }

        if (approvalVisibility.canResolve) {
            return `
                                <button onclick="app.viewHistoryItem('${item.id}')"
                                        class="text-blue-600 hover:text-blue-900 text-sm">보기</button>
                                ${approvalVisibility.canApprove ? `
                                <button onclick="app.approveHistoryItem('${item.id}')"
                                        class="text-emerald-600 hover:text-emerald-900 text-sm">승인</button>
                                ` : ''}
                                ${approvalVisibility.canReject ? `
                                <button onclick="app.rejectHistoryItem('${item.id}')"
                                        class="text-red-600 hover:text-red-900 text-sm">반려</button>
                                ` : ''}
                            `;
        }

        return `
                                <button onclick="app.viewHistoryItem('${item.id}')"
                                        class="text-blue-600 hover:text-blue-900 text-sm">보기</button>
                                <button onclick="app.rerunHistoryItem('${item.id}')"
                                        class="text-green-600 hover:text-green-900 text-sm">다시 실행</button>
                            `;
    }

    function buildHistoryListHtml(history = []) {
        return history.map((item) => `
                <div class="border-b border-gray-200 py-4">
                    <div class="flex justify-between items-start">
                        <div>
                            <h4 class="text-sm font-medium text-gray-900">${formatParamsLabel(item.params || {})}</h4>
                            <p class="text-sm text-gray-500">${new Date(item.created_at).toLocaleString()}</p>
                            ${buildHistoryStatusBadge(item)}
                            ${buildApprovalStatusBadge(resolveApprovalVisibility(item).approvalState, resolveApprovalVisibility(item).approvalLabel)}
                            ${buildDeliveryStatusBadge(item.delivery_status, resolveExecutionVisibility(item).deliveryLabel)}
                            ${buildExecutionMetaHtml(item)}
                            ${buildPersonalizationMetaHtml(item, { compact: true })}
                            ${buildEffectiveSettingsProvenanceMetaHtml(item, { compact: true })}
                        </div>
                        <div class="space-x-2">
                            ${buildHistoryActionsHtml(item)}
                        </div>
                    </div>
                </div>
            `).join('');
    }

    function buildApprovalsListHtml(approvals = []) {
        return approvals.map((item) => `
                <div class="border-b border-gray-200 py-4">
                    <div class="flex justify-between items-start gap-4">
                        <div>
                            <h4 class="text-sm font-medium text-gray-900">${formatParamsLabel(item.params || {})}</h4>
                            <p class="text-sm text-gray-500">${new Date(item.created_at).toLocaleString()}</p>
                            <p class="text-sm text-gray-500">이메일: ${item.params?.email || '미지정'}</p>
                            ${buildExecutionStatusBadge(resolveExecutionVisibility(item).statusLabel, resolveExecutionVisibility(item).statusCategory)}
                            ${buildApprovalStatusBadge(resolveApprovalVisibility(item).approvalState, resolveApprovalVisibility(item).approvalLabel)}
                            ${buildDeliveryStatusBadge(item.delivery_status, resolveExecutionVisibility(item).deliveryLabel)}
                            ${item.approval_note ? `<p class="mt-2 text-sm text-gray-500">메모: ${item.approval_note}</p>` : ''}
                            ${buildApprovalMetaHtml(item)}
                            ${buildExecutionMetaHtml(item, { includeResultTitle: false, includeTimestamp: false })}
                            ${buildPersonalizationMetaHtml(item, { compact: true })}
                            ${buildEffectiveSettingsProvenanceMetaHtml(item, { compact: true })}
                        </div>
                        <div class="space-x-2 whitespace-nowrap">
                            <button onclick="app.viewHistoryItem('${item.id}')"
                                    class="text-blue-600 hover:text-blue-900 text-sm">보기</button>
                            ${resolveApprovalVisibility(item).canApprove ? `<button onclick="app.approveHistoryItem('${item.id}')"
                                    class="bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1 rounded text-sm">
                                승인
                            </button>` : ''}
                            ${resolveApprovalVisibility(item).canReject ? `<button onclick="app.rejectHistoryItem('${item.id}')"
                                    class="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm">
                                반려
                            </button>` : ''}
                        </div>
                    </div>
                </div>
            `).join('');
    }

    function buildAnalyticsSummaryCardsHtml(summary = {}) {
        const generation = summary.generation || {};
        const email = summary.email || {};
        const schedule = summary.schedule || {};
        const cards = [
            {
                label: 'Generation',
                body: `
                    <div class="text-3xl font-bold ${generation.failed ? 'text-amber-700' : 'text-blue-700'}">${generation.completed ?? 0}</div>
                    <p class="mt-1 text-sm text-gray-500">completed / ${generation.failed ?? 0} failed</p>
                    <p class="mt-2 text-xs text-gray-500">success rate ${generation.success_rate ?? '-'}%</p>
                `
            },
            {
                label: 'Email Delivery',
                body: `
                    <div class="text-3xl font-bold text-emerald-700">${email.sent ?? 0}</div>
                    <p class="mt-1 text-sm text-gray-500">sent / ${email.failed ?? 0} failed</p>
                    <p class="mt-2 text-xs text-gray-500">deduplicated ${email.deduplicated ?? 0}</p>
                `
            },
            {
                label: 'Schedules',
                body: `
                    <div class="text-3xl font-bold text-indigo-700">${schedule.completed ?? 0}</div>
                    <p class="mt-1 text-sm text-gray-500">completed / ${schedule.failed ?? 0} failed</p>
                    <p class="mt-2 text-xs text-gray-500">created ${schedule.created ?? 0} / queued ${schedule.queued ?? 0}</p>
                `
            },
            {
                label: 'Duration & Cost',
                body: `
                    <div class="text-3xl font-bold text-purple-700">${summary.generation?.average_duration_seconds ?? '-'}</div>
                    <p class="mt-1 text-sm text-gray-500">avg seconds per completed run</p>
                    <p class="mt-2 text-xs text-gray-500">total cost $${(summary.generation?.total_cost_usd ?? 0).toFixed(4)}</p>
                `
            }
        ];

        return cards.map((card) => `
            <div class="rounded-lg border border-gray-200 bg-white px-4 py-5 shadow-sm">
                <div class="text-sm font-medium text-gray-500">${card.label}</div>
                <div class="mt-3">${card.body}</div>
            </div>
        `).join('');
    }

    function buildAnalyticsEventsHtml(events = []) {
        if (!Array.isArray(events) || events.length === 0) {
            return `
                <div class="rounded-lg border border-gray-200 bg-gray-50 px-4 py-5 text-sm text-gray-500">
                    아직 analytics 이벤트가 없습니다.
                </div>
            `;
        }

        return events.map((event) => {
            const createdAt = event.created_at ? new Date(event.created_at).toLocaleString() : '-';
            const payloadPairs = Object.entries(event.payload || {}).slice(0, 4);
            return `
                <div class="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
                    <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                        <div>
                            <div class="flex flex-wrap items-center gap-2">
                                <span class="inline-flex rounded-full bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-800">${event.event_type}</span>
                                ${event.status ? `<span class="inline-flex rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">${event.status}</span>` : ''}
                                ${event.deduplicated ? '<span class="inline-flex rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800">deduplicated</span>' : ''}
                            </div>
                            <p class="mt-2 text-sm text-gray-500">${createdAt}</p>
                            <p class="mt-1 text-sm text-gray-500">job: ${event.job_id || '-'}</p>
                            <p class="text-sm text-gray-500">schedule: ${event.schedule_id || '-'}</p>
                        </div>
                        <div class="min-w-0 flex-1 rounded-md bg-gray-50 px-3 py-2 text-xs text-gray-600 md:max-w-xl">
                            ${payloadPairs.length > 0
                                ? payloadPairs.map(([key, value]) => `<div><span class="font-medium text-gray-700">${key}</span>: ${String(value)}</div>`).join('')
                                : 'payload 없음'}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    function summarizeSourcePolicies(sourcePolicies = []) {
        const activePolicies = sourcePolicies.filter((policy) => policy.is_active);
        const allowCount = activePolicies.filter((policy) => policy.policy_type === 'allow').length;
        const blockCount = activePolicies.filter((policy) => policy.policy_type === 'block').length;
        const linkedPolicyCount = sourcePolicies.filter((policy) =>
            resolveSourcePolicyVisibility(policy).linkedPresetCount > 0
        ).length;
        const appliedPolicyCount = sourcePolicies.filter((policy) =>
            resolveSourcePolicyVisibility(policy).visibilityState === 'applied'
        ).length;
        const detachedPolicyCount = sourcePolicies.filter((policy) =>
            resolveSourcePolicyVisibility(policy).visibilityState === 'detached'
        ).length;

        return {
            activeCount: activePolicies.length,
            allowCount,
            blockCount,
            linkedPolicyCount,
            appliedPolicyCount,
            detachedPolicyCount,
            message: `활성 정책 ${activePolicies.length}개 (allow ${allowCount} / block ${blockCount}) · 프리셋 연결 ${linkedPolicyCount}개 · 최근 반영 ${appliedPolicyCount}개`,
            statusMessage: detachedPolicyCount > 0
                ? `활성 정책 ${detachedPolicyCount}개는 아직 프리셋이나 최근 실행과 연결되지 않았습니다.`
                : (appliedPolicyCount > 0
                    ? `최근 실행에 반영된 정책 ${appliedPolicyCount}개를 확인했습니다.`
                    : null),
            statusTone: detachedPolicyCount > 0
                ? 'yellow'
                : (appliedPolicyCount > 0 ? 'green' : 'gray')
        };
    }

    function sortSourcePolicies(sourcePolicies = []) {
        return sourcePolicies
            .slice()
            .sort((left, right) => {
                if (left.policy_type !== right.policy_type) {
                    return left.policy_type.localeCompare(right.policy_type);
                }
                return left.pattern.localeCompare(right.pattern);
            });
    }

    function resolveSourcePolicyVisibility(policy = {}) {
        const visibility = policy?.source_policy_visibility || {};
        const linkage = policy?.preset_linkage_visibility || {};
        const linkedPresets = Array.isArray(policy?.linked_presets) ? policy.linked_presets : [];
        const latestExecution = policy?.latest_related_execution || null;
        const visibilityState = visibility.visibility_state
            || (policy.is_active ? 'enabled' : 'disabled');
        const linkedPresetCount = visibility.linked_preset_count ?? linkage.linked_preset_count ?? linkedPresets.length;
        const linkedDefaultPresetCount = visibility.linked_default_preset_count ?? linkage.linked_default_preset_count ?? linkedPresets.filter((preset) => preset?.is_default).length;
        const linkedPresetNames = Array.isArray(visibility.linked_preset_names) && visibility.linked_preset_names.length > 0
            ? visibility.linked_preset_names
            : linkedPresets.map((preset) => preset?.name).filter(Boolean);

        return {
            visibilityState,
            statusLabel: visibility.status_label
                || (visibilityState === 'applied'
                    ? '최근 반영'
                    : visibilityState === 'enabled'
                        ? '활성'
                        : visibilityState === 'detached'
                            ? '연결 없음'
                            : visibilityState === 'disabled'
                                ? '비활성'
                                : '상태 미상'),
            statusMessage: visibility.status_message || linkage.message || '',
            policyTypeLabel: visibility.policy_type_label || '',
            linkedPresetCount,
            linkedDefaultPresetCount,
            linkedPresetNames,
            linkageMessage: linkage.message || '',
            latestExecution,
            hasLatestExecution: Boolean(latestExecution),
            recentUsageState: visibility.recent_usage_state || (latestExecution ? 'recent' : 'empty')
        };
    }

    function buildSourcePolicyVisibilityBadge(policy = {}) {
        const visibility = resolveSourcePolicyVisibility(policy);
        const toneClass = visibility.visibilityState === 'applied'
            ? 'bg-green-100 text-green-800'
            : visibility.visibilityState === 'enabled'
                ? 'bg-blue-100 text-blue-800'
                : visibility.visibilityState === 'detached'
                    ? 'bg-amber-100 text-amber-800'
                    : visibility.visibilityState === 'disabled'
                        ? 'bg-slate-100 text-slate-700'
                        : 'bg-slate-100 text-slate-700';

        return `<span class="inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${toneClass}">${visibility.statusLabel}</span>`;
    }

    function buildSourcePolicyMetaHtml(policy = {}) {
        const visibility = resolveSourcePolicyVisibility(policy);
        const parts = [];

        if (visibility.policyTypeLabel) {
            parts.push(`<p class="mt-2 text-sm text-gray-500">${visibility.policyTypeLabel}</p>`);
        }
        if (visibility.statusMessage) {
            parts.push(`<p class="mt-1 text-sm text-gray-500">${visibility.statusMessage}</p>`);
        }
        if (visibility.linkedPresetCount > 0) {
            const names = visibility.linkedPresetNames.slice(0, 3).join(', ');
            const defaultSuffix = visibility.linkedDefaultPresetCount > 0
                ? ` · 기본 ${visibility.linkedDefaultPresetCount}개`
                : '';
            parts.push(`<p class="mt-1 text-xs text-gray-500">연결된 프리셋 ${visibility.linkedPresetCount}개${defaultSuffix}${names ? ` · ${names}` : ''}</p>`);
        }
        if (visibility.hasLatestExecution) {
            const execution = visibility.latestExecution || {};
            parts.push(
                `<div class="mt-2 flex flex-wrap items-center gap-2">${
                    buildExecutionStatusBadge(
                        resolveExecutionVisibility(execution).statusLabel,
                        resolveExecutionVisibility(execution).statusCategory
                    )
                }<span class="text-xs text-gray-500">최근 실행 ${
                    formatVisibilityTimestamp(resolveExecutionVisibility(execution).primaryTimestamp) || '-'
                }</span></div>`
            );
            parts.push(buildExecutionMetaHtml(execution));
        }
        parts.push(buildEffectiveSettingsProvenanceMetaHtml(policy, { compact: true }));

        return parts.join('');
    }

    function buildSourcePoliciesHtml(sourcePolicies = []) {
        return sortSourcePolicies(sourcePolicies).map((policy) => {
            const typeBadge = policy.policy_type === 'allow'
                ? 'bg-emerald-100 text-emerald-800'
                : 'bg-rose-100 text-rose-800';
            const activeBadge = policy.is_active
                ? 'bg-blue-100 text-blue-800'
                : 'bg-slate-100 text-slate-700';
            const updatedAt = policy.updated_at ? new Date(policy.updated_at).toLocaleString() : '-';

            return `
                    <div class="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
                        <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                            <div>
                                <div class="flex flex-wrap items-center gap-2">
                                    <code class="rounded bg-gray-100 px-2 py-1 text-sm font-semibold text-gray-800">${policy.pattern}</code>
                                    <span class="inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${typeBadge}">${policy.policy_type}</span>
                                    <span class="inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${activeBadge}">${policy.is_active ? 'active' : 'paused'}</span>
                                    ${buildSourcePolicyVisibilityBadge(policy)}
                                </div>
                                <p class="mt-2 text-sm text-gray-500">업데이트: ${updatedAt}</p>
                                ${buildSourcePolicyMetaHtml(policy)}
                            </div>
                            <div class="flex flex-wrap gap-2">
                                <button onclick="app.editSourcePolicy('${policy.id}')"
                                        class="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100">
                                    편집
                                </button>
                                <button onclick="app.toggleSourcePolicyActive('${policy.id}', ${policy.is_active ? 'false' : 'true'})"
                                        class="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">
                                    ${policy.is_active ? '비활성화' : '활성화'}
                                </button>
                                <button onclick="app.deleteSourcePolicy('${policy.id}')"
                                        class="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700">
                                    삭제
                                </button>
                            </div>
                        </div>
                    </div>
                `;
        }).join('');
    }

    function buildSchedulesListHtml(schedules = []) {
        return schedules.map((schedule) => `
                <div class="border-b border-gray-200 py-4">
                    <div class="flex justify-between items-start">
                        <div>
                            <h4 class="text-sm font-medium text-gray-900">${formatParamsLabel(schedule.params || {})}</h4>
                            <p class="text-sm text-gray-500">
                                이메일: ${schedule.params?.email || 'Unknown'}
                            </p>
                            <p class="text-sm text-gray-500">
                                다음 실행: ${new Date(schedule.next_run).toLocaleString()}
                            </p>
                            <p class="text-sm text-gray-500">
                                규칙: ${schedule.rrule}
                            </p>
                            ${buildExecutionStatusBadge(resolveExecutionVisibility(schedule).statusLabel, resolveExecutionVisibility(schedule).statusCategory)}
                            ${buildExecutionMetaHtml(schedule, { includeResultTitle: false })}
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
    }

    function buildPresetVisibilityBadge(label, toneClass) {
        return `<span class="inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${toneClass}">${label}</span>`;
    }

    function buildPresetSelectionSummaryHtml(preset = {}, { selectedPresetId = '' } = {}) {
        const visibility = preset?.preset_visibility || {};
        const latestExecution = preset?.latest_related_execution || {};
        const executionVisibility = latestExecution?.execution_visibility || {};
        const sourcePolicyVisibility = preset?.source_policy_visibility || {};
        const isSelected = Boolean(preset?.id) && preset.id === selectedPresetId;

        const badges = [];
        if (isSelected) {
            badges.push(buildPresetVisibilityBadge('선택됨', 'bg-blue-100 text-blue-800'));
        }
        if (preset?.is_default) {
            badges.push(buildPresetVisibilityBadge('기본', 'bg-emerald-100 text-emerald-800'));
        }
        if (visibility?.preset_type_label) {
            badges.push(buildPresetVisibilityBadge(visibility.preset_type_label, 'bg-slate-100 text-slate-700'));
        }
        if (visibility?.is_scheduled) {
            badges.push(buildPresetVisibilityBadge('예약', 'bg-indigo-100 text-indigo-800'));
        }
        badges.push(buildPersonalizationVisibilityBadge(preset));

        const executionHtml = latestExecution?.job_id
            ? `
                <p class="text-sm text-gray-600">
                    최근 연관 실행:
                    ${buildExecutionStatusBadge(executionVisibility.statusLabel || latestExecution.status || '상태 미상', executionVisibility.statusCategory || 'unknown')}
                </p>
                ${executionVisibility.statusMessage ? `<p class="mt-1 text-xs text-gray-500">${executionVisibility.statusMessage}</p>` : ''}
                ${latestExecution.created_at ? `<p class="mt-1 text-xs text-gray-500">최근 연관 실행 시각: ${formatVisibilityTimestamp(latestExecution.created_at)}</p>` : ''}
                ${latestExecution.title ? `<p class="mt-1 text-xs text-gray-500">최근 결과: ${latestExecution.title}</p>` : ''}
            `
            : `
                <p class="text-sm text-gray-600">연관된 최근 실행 이력이 없습니다.</p>
            `;

        const sourcePolicyHtml = sourcePolicyVisibility?.message
            ? `<p class="mt-2 text-xs text-gray-500">소스 정책: ${sourcePolicyVisibility.message}</p>`
            : '';

        const updatedAtHtml = preset?.updated_at
            ? `<p class="mt-2 text-xs text-gray-500">프리셋 업데이트: ${formatVisibilityTimestamp(preset.updated_at)}</p>`
            : '';

        return `
            <div class="mt-3 rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm text-gray-700">
                <div class="flex flex-wrap gap-2">
                    ${badges.join('')}
                </div>
                <div class="mt-3 space-y-1">
                    ${buildEffectiveSettingsProvenanceMetaHtml(preset)}
                    ${buildPersonalizationMetaHtml(preset)}
                    ${executionHtml}
                    ${sourcePolicyHtml}
                    ${updatedAtHtml}
                </div>
            </div>
        `;
    }

    function resolvePresetSelectionView({ preset = null, selectedPresetId = '' } = {}) {
        if (!preset) {
            return {
                statusMessage: '운영 토큰이 있으면 프리셋을 저장하고 불러올 수 있습니다.',
                statusTone: 'gray',
                detailsHtml: ''
            };
        }

        const visibility = preset?.preset_visibility || {};
        const latestExecution = preset?.latest_related_execution || {};
        const executionVisibility = latestExecution?.execution_visibility || {};
        const isSelected = Boolean(preset?.id) && preset.id === selectedPresetId;
        const description = String(preset?.description || '').trim();
        const baseMessage = description
            ? `${preset.name}: ${description}`
            : `${preset.name} 프리셋이 준비되었습니다.`;

        let statusTone = isSelected ? 'green' : 'gray';
        if (executionVisibility?.statusCategory === 'failed') {
            statusTone = 'yellow';
        }
        if (visibility?.availability_state === 'empty') {
            statusTone = 'yellow';
        }

        return {
            statusMessage: baseMessage,
            statusTone,
            detailsHtml: buildPresetSelectionSummaryHtml(preset, { selectedPresetId })
        };
    }

    function buildSectionMessageHtml(message = '', tone = 'gray') {
        const toneClass = tone === 'red'
            ? 'text-red-600'
            : tone === 'yellow'
                ? 'text-amber-600'
                : 'text-gray-500';

        return `<p class="${toneClass}">${message}</p>`;
    }

    function resolveListSectionState({ items = [], errorMessage = '', emptyMessage = '', errorTone = 'yellow', renderItems }) {
        if (errorMessage) {
            return {
                state: 'error',
                html: buildSectionMessageHtml(errorMessage, errorTone)
            };
        }

        if (!Array.isArray(items) || items.length === 0) {
            return {
                state: 'empty',
                html: buildSectionMessageHtml(emptyMessage, 'gray')
            };
        }

        return {
            state: 'content',
            html: renderItems(items)
        };
    }

    function resolveHistorySectionState({ history = [], errorMessage = '', errorTone = 'yellow' } = {}) {
        return resolveListSectionState({
            items: history,
            errorMessage,
            emptyMessage: '아직 생성된 뉴스레터가 없습니다.',
            errorTone,
            renderItems: buildHistoryListHtml
        });
    }

    function resolveApprovalsSectionState({ approvals = [], errorMessage = '', errorTone = 'yellow' } = {}) {
        return resolveListSectionState({
            items: approvals,
            errorMessage,
            emptyMessage: '승인 요청 이력이 없습니다.',
            errorTone,
            renderItems: buildApprovalsListHtml
        });
    }

    function resolveSchedulesSectionState({ schedules = [], errorMessage = '', errorTone = 'yellow' } = {}) {
        return resolveListSectionState({
            items: schedules,
            errorMessage,
            emptyMessage: '예약된 발송이 없습니다.',
            errorTone,
            renderItems: buildSchedulesListHtml
        });
    }

    function resolveAnalyticsSectionState({ result = null, errorMessage = '', errorTone = 'yellow' } = {}) {
        if (errorMessage) {
            return {
                hasData: false,
                statusMessage: errorMessage,
                statusTone: errorTone,
                summary: {},
                events: []
            };
        }

        const windowDays = result?.window_days ?? 0;
        const recentEvents = Array.isArray(result?.recent_events) ? result.recent_events : [];

        return {
            hasData: true,
            statusMessage: `최근 ${windowDays}일 기준 analytics 요약과 최근 ${recentEvents.length}건 이벤트를 표시합니다.`,
            statusTone: 'green',
            summary: result?.summary || {},
            events: recentEvents
        };
    }

    function resolveSourcePoliciesSectionState({
        sourcePolicies = [],
        editingSourcePolicyId = '',
        errorMessage = '',
        errorTone = 'yellow'
    } = {}) {
        if (errorMessage) {
            return {
                hasPolicies: false,
                html: buildSectionMessageHtml(errorMessage, errorTone),
                summaryMessage: errorMessage,
                summaryTone: errorTone,
                statusMessage: errorMessage,
                statusTone: errorTone,
                shouldResetForm: false
            };
        }

        if (!Array.isArray(sourcePolicies) || sourcePolicies.length === 0) {
            return {
                hasPolicies: false,
                html: buildSectionMessageHtml('등록된 소스 정책이 없습니다.', 'gray'),
                summaryMessage: '현재 적용 중인 소스 정책이 없습니다. 필요하면 allow/block 정책을 추가하세요.',
                summaryTone: 'gray',
                statusMessage: null,
                statusTone: 'gray',
                shouldResetForm: !editingSourcePolicyId
            };
        }

        const summary = summarizeSourcePolicies(sourcePolicies);
        return {
            hasPolicies: true,
            html: buildSourcePoliciesHtml(sourcePolicies),
            summaryMessage: summary.message,
            summaryTone: 'gray',
            statusMessage: summary.statusMessage,
            statusTone: summary.statusTone,
            shouldResetForm: !editingSourcePolicyId
        };
    }

    function resolveKeywordSuggestionView({ phase = 'idle', keywords = [], errorMessage = '' } = {}) {
        if (phase === 'loading') {
            return {
                buttonDisabled: true,
                buttonHtml: '<i class="fas fa-spinner fa-spin mr-1"></i>추천 중...',
                resultHtml: '<div class="text-blue-600 text-sm">키워드를 생성하고 있습니다...</div>'
            };
        }

        if (phase === 'missing-domain') {
            return {
                buttonDisabled: false,
                buttonHtml: '<i class="fas fa-lightbulb mr-1"></i>추천받기',
                resultHtml: '<div class="text-red-600 text-sm">도메인을 입력해주세요.</div>'
            };
        }

        if (phase === 'error') {
            return {
                buttonDisabled: false,
                buttonHtml: '<i class="fas fa-lightbulb mr-1"></i>추천받기',
                resultHtml: `<div class="text-red-600 text-sm">오류가 발생했습니다: ${errorMessage}</div>`
            };
        }

        if (phase === 'empty') {
            return {
                buttonDisabled: false,
                buttonHtml: '<i class="fas fa-lightbulb mr-1"></i>추천받기',
                resultHtml: '<div class="text-yellow-600 text-sm">키워드를 생성할 수 없습니다. 다른 도메인을 시도해보세요.</div>'
            };
        }

        const safeKeywords = Array.isArray(keywords) ? keywords : [];
        const keywordsList = safeKeywords.map((keyword) =>
            `<span class="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full mr-2 mb-2 cursor-pointer hover:bg-blue-200" onclick="app.addKeywordToInput('${keyword}')">${keyword}</span>`
        ).join('');

        return {
            buttonDisabled: false,
            buttonHtml: '<i class="fas fa-lightbulb mr-1"></i>추천받기',
            resultHtml: `
                <div class="text-sm text-gray-700 mb-2">추천 키워드 (클릭하여 추가):</div>
                <div class="flex flex-wrap">${keywordsList}</div>
                <button onclick="app.useAllKeywords(${JSON.stringify(safeKeywords).replace(/"/g, '&quot;')})"
                        class="mt-2 text-xs bg-green-100 text-green-800 px-2 py-1 rounded hover:bg-green-200">
                    모든 키워드 사용
                </button>
            `
        };
    }

    function resolveResultButtonState(result = {}) {
        const enabled = result.status === 'success' && Boolean(result.html_content);
        return {
            downloadDisabled: !enabled,
            sendEmailDisabled: !enabled
        };
    }

    return {
        buildAnalyticsEventsHtml,
        buildAnalyticsSummaryCardsHtml,
        buildApprovalsListHtml,
        buildApprovalMetaHtml,
        buildEffectiveSettingsProvenanceMetaHtml,
        buildPersonalizationMetaHtml,
        buildPresetSelectionSummaryHtml,
        buildSectionMessageHtml,
        buildHistoryListHtml,
        buildSchedulesListHtml,
        buildSourcePoliciesHtml,
        buildSourcePolicyMetaHtml,
        resolveApprovalVisibility,
        resolveEffectiveSettingsProvenance,
        resolveAnalyticsSectionState,
        resolveApprovalsSectionState,
        resolveHistorySectionState,
        resolveKeywordSuggestionView,
        resolveListSectionState,
        resolvePersonalizationVisibility,
        resolvePresetSelectionView,
        resolveResultButtonState,
        resolveSchedulesSectionState,
        resolveSourcePolicyVisibility,
        resolveSourcePoliciesSectionState,
        sortSourcePolicies,
        summarizeSourcePolicies
    };
});
