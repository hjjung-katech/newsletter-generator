(function(root, factory) {
    const helpers = factory();
    root.NewsletterAppViewStateHelpers = helpers;

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = helpers;
    }
})(typeof window !== 'undefined' ? window : globalThis, function() {
    function formatParamsLabel(params = {}) {
        return params?.keywords
            ? `키워드: ${Array.isArray(params.keywords) ? params.keywords.join(', ') : params.keywords}`
            : `도메인: ${params?.domain || 'Unknown'}`;
    }

    function buildHistoryStatusBadge(status) {
        const toneClass = status === 'completed'
            ? 'bg-green-100 text-green-800'
            : status === 'failed'
                ? 'bg-red-100 text-red-800'
                : 'bg-yellow-100 text-yellow-800';

        return `<span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full ${toneClass}">${status}</span>`;
    }

    function buildApprovalStatusBadge(status) {
        if (!status || status === 'not_requested') {
            return '';
        }

        const toneClass = status === 'pending'
            ? 'bg-amber-100 text-amber-800'
            : status === 'approved'
                ? 'bg-blue-100 text-blue-800'
                : 'bg-red-100 text-red-800';

        return `<span class="inline-flex ml-2 px-2 py-1 text-xs font-semibold rounded-full ${toneClass}">${status}</span>`;
    }

    function buildHistoryActionsHtml(item = {}) {
        if (item.status !== 'completed') {
            return '';
        }

        if (item.approval_status === 'pending') {
            return `
                                <button onclick="app.viewHistoryItem('${item.id}')"
                                        class="text-blue-600 hover:text-blue-900 text-sm">보기</button>
                                <button onclick="app.approveHistoryItem('${item.id}')"
                                        class="text-emerald-600 hover:text-emerald-900 text-sm">승인</button>
                                <button onclick="app.rejectHistoryItem('${item.id}')"
                                        class="text-red-600 hover:text-red-900 text-sm">반려</button>
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
                            ${buildHistoryStatusBadge(item.status)}
                            ${buildApprovalStatusBadge(item.approval_status)}
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
                            <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-amber-100 text-amber-800">${item.approval_status}</span>
                            <span class="inline-flex ml-2 px-2 py-1 text-xs font-semibold rounded-full bg-slate-100 text-slate-700">${item.delivery_status}</span>
                            ${item.approval_note ? `<p class="mt-2 text-sm text-gray-500">메모: ${item.approval_note}</p>` : ''}
                        </div>
                        <div class="space-x-2 whitespace-nowrap">
                            <button onclick="app.viewHistoryItem('${item.id}')"
                                    class="text-blue-600 hover:text-blue-900 text-sm">보기</button>
                            <button onclick="app.approveHistoryItem('${item.id}')"
                                    class="bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1 rounded text-sm">
                                승인
                            </button>
                            <button onclick="app.rejectHistoryItem('${item.id}')"
                                    class="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm">
                                반려
                            </button>
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

        return {
            activeCount: activePolicies.length,
            allowCount,
            blockCount,
            message: `활성 정책 ${activePolicies.length}개 (allow ${allowCount} / block ${blockCount})`
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
                                </div>
                                <p class="mt-2 text-sm text-gray-500">업데이트: ${updatedAt}</p>
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
        buildHistoryListHtml,
        buildSchedulesListHtml,
        buildSourcePoliciesHtml,
        resolveResultButtonState,
        sortSourcePolicies,
        summarizeSourcePolicies
    };
});
