const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const repoRoot = path.resolve(__dirname, '../..');
const helpers = require(path.join(repoRoot, 'web/static/js/app_view_state_helpers.js'));

test('resolveResultButtonState enables actions only for successful html results', () => {
    assert.deepEqual(
        helpers.resolveResultButtonState({
            status: 'success',
            html_content: '<html>ok</html>'
        }),
        {
            downloadDisabled: false,
            sendEmailDisabled: false
        }
    );

    assert.deepEqual(
        helpers.resolveResultButtonState({
            status: 'processing',
            html_content: ''
        }),
        {
            downloadDisabled: true,
            sendEmailDisabled: true
        }
    );
});

test('buildHistoryListHtml renders derived badges and actions for completed items', () => {
    const html = helpers.buildHistoryListHtml([
        {
            id: 'job-pending',
            created_at: '2026-03-12T00:00:00Z',
            status: 'completed',
            approval_status: 'pending',
            params: {
                keywords: ['AI', 'Battery']
            }
        },
        {
            id: 'job-approved',
            created_at: '2026-03-12T01:00:00Z',
            status: 'completed',
            approval_status: 'approved',
            params: {
                domain: 'Mobility'
            }
        }
    ]);

    assert.match(html, /키워드: AI, Battery/);
    assert.match(html, /도메인: Mobility/);
    assert.match(html, /bg-green-100 text-green-800\">completed/);
    assert.match(html, /bg-amber-100 text-amber-800\">pending/);
    assert.match(html, /app\.approveHistoryItem\('job-pending'\)/);
    assert.match(html, /app\.rerunHistoryItem\('job-approved'\)/);
});

test('buildApprovalsListHtml renders delivery view model with note and actions', () => {
    const html = helpers.buildApprovalsListHtml([
        {
            id: 'approval-1',
            created_at: '2026-03-12T02:00:00Z',
            approval_status: 'pending',
            delivery_status: 'pending_approval',
            approval_note: 'review this',
            params: {
                domain: 'Semiconductor',
                email: 'ops@example.com'
            }
        }
    ]);

    assert.match(html, /도메인: Semiconductor/);
    assert.match(html, /이메일: ops@example.com/);
    assert.match(html, /메모: review this/);
    assert.match(html, /pending_approval/);
    assert.match(html, /app\.rejectHistoryItem\('approval-1'\)/);
});

test('analytics helpers render summary cards and deduplicated event payloads', () => {
    const cardsHtml = helpers.buildAnalyticsSummaryCardsHtml({
        generation: {
            completed: 8,
            failed: 1,
            success_rate: 88.9,
            average_duration_seconds: 12.3,
            total_cost_usd: 1.2345
        },
        email: {
            sent: 5,
            failed: 1,
            deduplicated: 2
        },
        schedule: {
            completed: 4,
            failed: 1,
            created: 6,
            queued: 2
        }
    });
    const eventsHtml = helpers.buildAnalyticsEventsHtml([
        {
            event_type: 'schedule_run',
            status: 'queued',
            deduplicated: true,
            created_at: '2026-03-12T03:00:00Z',
            job_id: 'job-1',
            schedule_id: 'sched-1',
            payload: {
                mode: 'async',
                template_style: 'compact'
            }
        }
    ]);

    assert.match(cardsHtml, /Generation/);
    assert.match(cardsHtml, /Email Delivery/);
    assert.match(cardsHtml, /deduplicated 2/);
    assert.match(eventsHtml, /schedule_run/);
    assert.match(eventsHtml, /deduplicated/);
    assert.match(eventsHtml, /mode<\/span>: async/);
});

test('source policy helpers summarize counts, preserve sort order, and render badges', () => {
    const policies = [
        {
            id: 'policy-block',
            pattern: 'zeta.com',
            policy_type: 'block',
            is_active: false,
            updated_at: '2026-03-12T04:00:00Z'
        },
        {
            id: 'policy-allow',
            pattern: 'alpha.com',
            policy_type: 'allow',
            is_active: true,
            updated_at: '2026-03-12T05:00:00Z'
        }
    ];
    const summary = helpers.summarizeSourcePolicies(policies);
    const html = helpers.buildSourcePoliciesHtml(policies);

    assert.equal(summary.message, '활성 정책 1개 (allow 1 / block 0)');
    assert.ok(html.indexOf('alpha.com') < html.indexOf('zeta.com'));
    assert.match(html, /active/);
    assert.match(html, /paused/);
    assert.match(html, /app\.toggleSourcePolicyActive\('policy-block', true\)/);
});

test('schedule list helper renders params, next run, and actions', () => {
    const html = helpers.buildSchedulesListHtml([
        {
            id: 'schedule-1',
            next_run: '2026-03-12T06:00:00Z',
            rrule: 'FREQ=WEEKLY;BYDAY=MO',
            params: {
                keywords: ['AI'],
                email: 'alerts@example.com'
            }
        }
    ]);

    assert.match(html, /키워드: AI/);
    assert.match(html, /alerts@example.com/);
    assert.match(html, /FREQ=WEEKLY;BYDAY=MO/);
    assert.match(html, /app\.runScheduleNow\('schedule-1'\)/);
});

test('section state helpers preserve empty, error, and content decisions', () => {
    assert.match(
        helpers.resolveHistorySectionState({ history: [] }).html,
        /아직 생성된 뉴스레터가 없습니다/
    );
    assert.match(
        helpers.resolveApprovalsSectionState({
            errorMessage: '권한이 없습니다.',
            errorTone: 'yellow'
        }).html,
        /text-amber-600/
    );
    assert.match(
        helpers.resolveSchedulesSectionState({
            schedules: [{ id: 'schedule-1', next_run: '2026-03-12T06:00:00Z', rrule: 'FREQ=WEEKLY', params: {} }]
        }).html,
        /schedule-1/
    );
});

test('analytics and source policy section helpers preserve derived section state', () => {
    const analytics = helpers.resolveAnalyticsSectionState({
        result: {
            window_days: 7,
            summary: { generation: { completed: 2 } },
            recent_events: [{ event_type: 'schedule_run' }]
        }
    });
    assert.equal(analytics.statusTone, 'green');
    assert.equal(analytics.summary.generation.completed, 2);
    assert.equal(analytics.events.length, 1);

    const emptyPolicies = helpers.resolveSourcePoliciesSectionState({
        sourcePolicies: [],
        editingSourcePolicyId: ''
    });
    assert.match(emptyPolicies.html, /등록된 소스 정책이 없습니다/);
    assert.equal(emptyPolicies.shouldResetForm, true);

    const errorPolicies = helpers.resolveSourcePoliciesSectionState({
        errorMessage: '소스 정책을 불러올 수 없습니다.',
        errorTone: 'red'
    });
    assert.equal(errorPolicies.statusTone, 'red');
    assert.match(errorPolicies.html, /text-red-600/);
});

test('keyword suggestion view helper preserves loading, success, and error render states', () => {
    const loading = helpers.resolveKeywordSuggestionView({ phase: 'loading' });
    assert.equal(loading.buttonDisabled, true);
    assert.match(loading.buttonHtml, /추천 중/);

    const success = helpers.resolveKeywordSuggestionView({
        phase: 'success',
        keywords: ['AI', 'Robotics']
    });
    assert.match(success.resultHtml, /추천 키워드/);
    assert.match(success.resultHtml, /app\.addKeywordToInput\('AI'\)/);
    assert.match(success.resultHtml, /모든 키워드 사용/);

    const error = helpers.resolveKeywordSuggestionView({
        phase: 'error',
        errorMessage: 'boom'
    });
    assert.match(error.resultHtml, /오류가 발생했습니다: boom/);
});

test('index templates load both helper scripts before app shell', () => {
    ['index.html', 'index_en.html'].forEach((templateName) => {
        const template = fs.readFileSync(path.join(repoRoot, 'web/templates', templateName), 'utf8');
        const requestHelpersIndex = template.indexOf('js/app_request_response_helpers.js');
        const viewHelpersIndex = template.indexOf('js/app_view_state_helpers.js');
        const appIndex = template.indexOf('js/app.js');

        assert.notEqual(requestHelpersIndex, -1, `${templateName} should load request/response helper`);
        assert.notEqual(viewHelpersIndex, -1, `${templateName} should load view-state helper`);
        assert.notEqual(appIndex, -1, `${templateName} should load app shell`);
        assert.ok(requestHelpersIndex < appIndex, `${templateName} should load request/response helper before app.js`);
        assert.ok(viewHelpersIndex < appIndex, `${templateName} should load view-state helper before app.js`);
    });
});
